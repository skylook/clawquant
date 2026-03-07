"""
可视化工具模块
提供策略性能监控和可视化功能
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from loguru import logger

from config.settings import RESULTS_DIR


class PerformanceVisualizer:
    """性能可视化器"""
    
    def __init__(self, output_dir: str = None):
        """
        初始化可视化器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "visualizations")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置绘图样式
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def plot_strategy_comparison(self, 
                               results: Dict[str, Any], 
                               filename: str = "strategy_comparison.html") -> str:
        """
        绘制策略比较图表
        
        Args:
            results: 回测结果
            filename: 输出文件名
            
        Returns:
            文件路径
        """
        # 提取策略性能数据
        strategies_data = []
        
        if 'comparison' in results and 'ranking' in results['comparison']:
            for rank_info in results['comparison']['ranking']:
                strategy_key = rank_info['strategy_key']
                strategies_data.append({
                    'Strategy': strategy_key,
                    'Total Return': rank_info.get('total_return', 0) * 100,
                    'Sharpe Ratio': rank_info.get('sharpe_ratio', 0),
                    'Max Drawdown': rank_info.get('max_drawdown', 0) * 100,
                    'Win Rate': rank_info.get('win_rate', 0) * 100,
                    'Overall Score': rank_info.get('overall_score', 0)
                })
        
        if not strategies_data:
            logger.warning("没有找到策略比较数据")
            return ""
        
        df = pd.DataFrame(strategies_data)
        
        # 创建子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('总收益率', '夏普比率', '最大回撤', '胜率'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 总收益率
        fig.add_trace(
            go.Bar(x=df['Strategy'], y=df['Total Return'], name='总收益率 (%)'),
            row=1, col=1
        )
        
        # 夏普比率
        fig.add_trace(
            go.Bar(x=df['Strategy'], y=df['Sharpe Ratio'], name='夏普比率'),
            row=1, col=2
        )
        
        # 最大回撤
        fig.add_trace(
            go.Bar(x=df['Strategy'], y=df['Max Drawdown'], name='最大回撤 (%)'),
            row=2, col=1
        )
        
        # 胜率
        fig.add_trace(
            go.Bar(x=df['Strategy'], y=df['Win Rate'], name='胜率 (%)'),
            row=2, col=2
        )
        
        fig.update_layout(height=800, showlegend=False, title_text="策略性能比较")
        
        # 保存图表
        filepath = os.path.join(self.output_dir, filename)
        fig.write_html(filepath)
        
        logger.info(f"策略比较图表已保存: {filepath}")
        return filepath
    
    def plot_equity_curve(self, 
                         trade_logs: pd.DataFrame, 
                         strategy_name: str = "Strategy",
                         filename: str = "equity_curve.html") -> str:
        """
        绘制权益曲线
        
        Args:
            trade_logs: 交易日志
            strategy_name: 策略名称
            filename: 输出文件名
            
        Returns:
            文件路径
        """
        if trade_logs.empty:
            logger.warning("交易日志为空")
            return ""
        
        # 确保有时间索引
        if 'datetime' not in trade_logs.columns:
            logger.warning("交易日志中没有datetime列")
            return ""
        
        # 计算累计收益曲线
        trade_logs_sorted = trade_logs.sort_values('datetime').copy()
        
        # 如果没有portfolio_value列，则基于pnl计算权益曲线
        if 'portfolio_value' not in trade_logs_sorted.columns:
            initial_value = 100000  # 假设初始资金
            trade_logs_sorted['portfolio_value'] = initial_value + trade_logs_sorted['pnl'].cumsum()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=trade_logs_sorted['datetime'],
            y=trade_logs_sorted['portfolio_value'],
            mode='lines',
            name='权益曲线',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title=f'{strategy_name} 权益曲线',
            xaxis_title='日期',
            yaxis_title='权益 (元)',
            hovermode='x unified'
        )
        
        # 保存图表
        filepath = os.path.join(self.output_dir, filename)
        fig.write_html(filepath)
        
        logger.info(f"权益曲线已保存: {filepath}")
        return filepath
    
    def plot_drawdown_chart(self, 
                           portfolio_values: List[float], 
                           dates: List[datetime],
                           strategy_name: str = "Strategy",
                           filename: str = "drawdown_chart.html") -> str:
        """
        绘制回撤图表
        
        Args:
            portfolio_values: 投资组合价值序列
            dates: 日期序列
            strategy_name: 策略名称
            filename: 输出文件名
            
        Returns:
            文件路径
        """
        if len(portfolio_values) < 2:
            logger.warning("投资组合价值数据不足")
            return ""
        
        # 计算回撤
        values_series = pd.Series(portfolio_values, index=dates)
        rolling_max = values_series.expanding().max()
        drawdown = (values_series - rolling_max) / rolling_max * 100
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=drawdown.values,
            mode='lines',
            name='回撤 (%)',
            fill='tonexty',
            fillcolor='rgba(255, 0, 0, 0.3)',
            line=dict(color='red', width=2)
        ))
        
        fig.update_layout(
            title=f'{strategy_name} 回撤分析',
            xaxis_title='日期',
            yaxis_title='回撤 (%)',
            hovermode='x unified'
        )
        
        # 保存图表
        filepath = os.path.join(self.output_dir, filename)
        fig.write_html(filepath)
        
        logger.info(f"回撤图表已保存: {filepath}")
        return filepath
    
    def plot_risk_metrics(self, 
                         risk_metrics: Dict[str, float],
                         strategy_name: str = "Strategy",
                         filename: str = "risk_metrics.html") -> str:
        """
        绘制风险指标图表
        
        Args:
            risk_metrics: 风险指标字典
            strategy_name: 策略名称
            filename: 输出文件名
            
        Returns:
            文件路径
        """
        metrics_names = []
        metrics_values = []
        
        # 选择要显示的风险指标
        display_metrics = {
            'Volatility': 'volatility',
            'Sharpe Ratio': 'sharpe_ratio', 
            'Max Drawdown': 'max_drawdown',
            'Current Drawdown': 'current_drawdown'
        }
        
        for display_name, key in display_metrics.items():
            if key in risk_metrics:
                metrics_names.append(display_name)
                # 转换为百分比显示
                if key in ['volatility', 'max_drawdown', 'current_drawdown']:
                    metrics_values.append(risk_metrics[key] * 100)
                else:
                    metrics_values.append(risk_metrics[key])
        
        if not metrics_names:
            logger.warning("没有可用的风险指标数据")
            return ""
        
        fig = go.Figure(data=[
            go.Bar(x=metrics_names, y=metrics_values)
        ])
        
        fig.update_layout(
            title=f'{strategy_name} 风险指标',
            xaxis_title='指标',
            yaxis_title='数值',
            showlegend=False
        )
        
        # 保存图表
        filepath = os.path.join(self.output_dir, filename)
        fig.write_html(filepath)
        
        logger.info(f"风险指标图表已保存: {filepath}")
        return filepath
    
    def generate_strategy_report(self, 
                                results: Dict[str, Any],
                                strategy_name: str = "Strategy") -> str:
        """
        生成策略报告
        
        Args:
            results: 策略结果
            strategy_name: 策略名称
            
        Returns:
            报告文件路径
        """
        # 生成各种图表
        comparison_file = self.plot_strategy_comparison(results)
        # Note: Other charts require additional data not always available in results
        
        # 创建HTML报告
        report_filename = f"strategy_report_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = os.path.join(self.output_dir, report_filename)
        
        # 构建报告内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>策略报告 - {strategy_name}</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .chart-container {{ margin: 10px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>策略报告 - {strategy_name}</h1>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h2>策略概览</h2>
                <p><strong>策略类型:</strong> {results.get('strategy_type', 'Unknown')}</p>
                <p><strong>参数:</strong> {str(results.get('params', {}))}</p>
            </div>
            
            <div class="section">
                <h2>性能指标</h2>
                <table>
                    <tr><th>指标</th><th>数值</th></tr>
        """
        
        # 添加性能指标
        perf_summary = results.get('performance_summary', {})
        for metric, value in perf_summary.items():
            if isinstance(value, (int, float)):
                if metric in ['total_return', 'annual_return', 'max_drawdown']:
                    html_content += f"<tr><td>{metric}</td><td>{value:.2%}</td></tr>\n"
                elif metric in ['sharpe_ratio', 'sortino_ratio', 'calmar_ratio']:
                    html_content += f"<tr><td>{metric}</td><td>{value:.4f}</td></tr>\n"
                else:
                    html_content += f"<tr><td>{metric}</td><td>{value}</td></tr>\n"
        
        html_content += """
                </table>
            </div>
        """
        
        # 添加图表引用（如果有）
        if comparison_file:
            relative_path = os.path.relpath(comparison_file, self.output_dir)
            html_content += f"""
            <div class="section">
                <h2>策略比较</h2>
                <iframe src="{relative_path}" width="100%" height="600px"></iframe>
            </div>
            """
        
        html_content += """
            <div class="section">
                <h2>交易建议</h2>
                <p><strong>操作:</strong> """ + results.get('recommendation', {}).get('action', 'N/A') + """</p>
                <p><strong>置信度:</strong> """ + results.get('recommendation', {}).get('confidence', 'N/A') + """</p>
        """
        
        suggestions = results.get('recommendation', {}).get('suggestions', [])
        if suggestions:
            html_content += "<ul>"
            for suggestion in suggestions:
                html_content += f"<li>{suggestion}</li>"
            html_content += "</ul>"
        
        warnings = results.get('recommendation', {}).get('warnings', [])
        if warnings:
            html_content += "<h3>风险警告:</h3><ul>"
            for warning in warnings:
                html_content += f"<li>{warning}</li>"
            html_content += "</ul>"
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        # 写入文件
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"策略报告已生成: {report_path}")
        return report_path


class RealTimeMonitor:
    """实时监控器"""
    
    def __init__(self, refresh_interval: int = 60):
        """
        初始化实时监控器
        
        Args:
            refresh_interval: 刷新间隔（秒）
        """
        self.refresh_interval = refresh_interval
        self.visualizer = PerformanceVisualizer()
        self.alerts = []
        
    def add_alert(self, condition_func, message: str, severity: str = "INFO"):
        """
        添加监控警报
        
        Args:
            condition_func: 条件函数
            message: 警报消息
            severity: 严重程度
        """
        self.alerts.append({
            'condition': condition_func,
            'message': message,
            'severity': severity
        })
    
    def check_alerts(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        检查警报条件
        
        Args:
            data: 监控数据
            
        Returns:
            触发的警报列表
        """
        triggered_alerts = []
        
        for alert in self.alerts:
            try:
                if alert['condition'](data):
                    triggered_alerts.append({
                        'message': alert['message'],
                        'severity': alert['severity'],
                        'timestamp': datetime.now()
                    })
            except Exception as e:
                logger.error(f"检查警报时出错: {e}")
        
        return triggered_alerts
    
    def generate_monitoring_dashboard(self, 
                                    strategy_results: List[Dict[str, Any]], 
                                    output_file: str = "monitoring_dashboard.html"):
        """
        生成监控仪表板
        
        Args:
            strategy_results: 策略结果列表
            output_file: 输出文件名
        """
        # 创建仪表板内容
        dashboard_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>策略监控仪表板</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .dashboard-header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; }}
                .metric-card {{ 
                    background-color: white; 
                    padding: 15px; 
                    margin: 10px; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    display: inline-block;
                    width: 200px;
                    text-align: center;
                }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .container {{ display: flex; flex-wrap: wrap; }}
                .chart-section {{ background-color: white; margin: 10px; padding: 15px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>量化策略监控仪表板</h1>
                <p>最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="container">
        """
        
        # 为每个策略添加指标卡片
        for result in strategy_results:
            strategy_name = result.get('strategy_type', 'Unknown')
            perf_summary = result.get('performance_summary', {})
            
            total_return = perf_summary.get('total_return', 0)
            sharpe_ratio = perf_summary.get('sharpe_ratio', 0)
            max_drawdown = perf_summary.get('max_drawdown', 0)
            
            # 格式化数值
            return_str = f"{total_return:.2%}"
            return_class = "positive" if total_return >= 0 else "negative"
            drawdown_str = f"{max_drawdown:.2%}"
            drawdown_class = "negative"
            
            dashboard_content += f"""
                <div class="metric-card">
                    <h3>{strategy_name}</h3>
                    <p><strong>总收益</strong></p>
                    <p class="{return_class}">{return_str}</p>
                    <p><strong>夏普比率</strong></p>
                    <p>{sharpe_ratio:.2f}</p>
                    <p><strong>最大回撤</strong></p>
                    <p class="{drawdown_class}">{drawdown_str}</p>
                </div>
            """
        
        dashboard_content += """
            </div>
        """
        
        # 添加图表区域
        dashboard_content += """
            <div class="chart-section">
                <h2>性能比较</h2>
                <p>策略性能比较图表将在此处显示</p>
            </div>
            
            <div class="chart-section">
                <h2>风险监控</h2>
                <p>风险指标图表将在此处显示</p>
            </div>
        </body>
        </html>
        """
        
        # 保存仪表板
        output_path = os.path.join(self.visualizer.output_dir, output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_content)
        
        logger.info(f"监控仪表板已生成: {output_path}")
        return output_path


# ========== 使用示例 ==========
if __name__ == "__main__":
    print("测试可视化模块...")
    
    # 创建可视化器实例
    viz = PerformanceVisualizer()
    
    # 示例数据
    sample_results = {
        'comparison': {
            'ranking': [
                {
                    'strategy_key': 'MA',
                    'total_return': 0.15,
                    'sharpe_ratio': 0.8,
                    'max_drawdown': -0.08,
                    'win_rate': 0.6,
                    'overall_score': 0.75
                },
                {
                    'strategy_key': 'MACD',
                    'total_return': 0.12,
                    'sharpe_ratio': 0.7,
                    'max_drawdown': -0.1,
                    'win_rate': 0.55,
                    'overall_score': 0.65
                }
            ]
        }
    }
    
    # 生成比较图表
    chart_path = viz.plot_strategy_comparison(sample_results)
    print(f"比较图表已生成: {chart_path}")
    
    print("可视化模块测试完成")