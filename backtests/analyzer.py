"""
回测结果分析器模块
分析回测结果并生成报告
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional
import os
from datetime import datetime
from loguru import logger

from config.settings import BACKTEST_RESULTS_DIR, BEST_STRATEGIES_DIR, BACKTEST
from utils.logger import log_performance


class BacktestAnalyzer:
    """回测分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.results_dir = BACKTEST_RESULTS_DIR
        self.best_strategies_dir = BEST_STRATEGIES_DIR
        
        # 确保目录存在
        os.makedirs(self.best_strategies_dir, exist_ok=True)
    
    def analyze_single_backtest(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析单个回测结果
        
        Args:
            result: 回测结果
            
        Returns:
            分析结果
        """
        analysis = {
            'strategy_type': result['strategy_type'],
            'params': result['params'],
            'performance_summary': {},
            'risk_metrics': {},
            'trade_analysis': {},
            'recommendation': {}
        }
        
        performance = result['performance']
        
        # 性能摘要
        analysis['performance_summary'] = {
            'total_return': performance.get('total_return', 0),
            'annual_return': performance.get('annual_return', 0),
            'final_value': result.get('final_value', 0),
            'sharpe_ratio': performance.get('sharpe_ratio', 0),
            'max_drawdown': performance.get('max_drawdown', 0),
            'win_rate': performance.get('win_rate', 0),
            'profit_factor': performance.get('profit_factor', 0)
        }
        
        # 风险指标
        analysis['risk_metrics'] = self._calculate_risk_metrics(performance)
        
        # 交易分析
        analysis['trade_analysis'] = self._analyze_trades(result['trade_logs'])
        
        # 策略评估
        analysis['strategy_evaluation'] = self._evaluate_strategy(performance)
        
        # 生成建议
        analysis['recommendation'] = self._generate_recommendation(analysis)
        
        return analysis
    
    def _calculate_risk_metrics(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算风险指标。

        计算的指标包括：

        * **最大回撤** (max_drawdown): 从高点到低点的最大亏损幅度。
        * **卡玛比率** (calmar_ratio): 年化收益率除以最大回撤绝对值。
          反映单位最大风险所获得的年化超额收益，数值越高越好。
          公式: annual_return / |max_drawdown|
        * **索提诺比率** (sortino_ratio): 仅惩罚下行波动的风险调整收益率。
          若 performance 中包含 'downside_deviation' 则直接使用，
          否则以 sharpe_ratio * 1.2 估算并在结果中标注。
        * **欧米伽比率** (omega_ratio): 收益分布中正收益期望值与负收益
          期望绝对值的比率，阈值默认为 0。
          公式: E[max(R - threshold, 0)] / E[max(threshold - R, 0)]
          仅在 performance 中包含 'daily_returns' 时计算。
          数值 > 1 表示正收益期望高于负收益期望。
        * **波动率** (volatility): 若 performance 中已包含则直接采用。
        * **风险调整收益率** (risk_adjusted_return): total_return / (1 + |max_drawdown|)。
        """
        risk_metrics = {}

        # 最大回撤
        max_drawdown = performance.get('max_drawdown', 0)
        risk_metrics['max_drawdown'] = max_drawdown

        # 卡玛比率（年化收益 / 最大回撤绝对值）
        # 正确公式: calmar = annual_return / |max_drawdown|
        # 分母取绝对值以兼容正负两种符号约定（某些引擎以负数报告回撤）。
        annual_return = performance.get('annual_return', 0)
        abs_drawdown = abs(max_drawdown)
        if abs_drawdown != 0:
            risk_metrics['calmar_ratio'] = annual_return / abs_drawdown
        else:
            risk_metrics['calmar_ratio'] = float('inf') if annual_return > 0 else 0

        # 索提诺比率（基于下行偏差）
        downside_deviation = performance.get('downside_deviation', None)
        if downside_deviation is not None and downside_deviation > 0:
            risk_metrics['sortino_ratio'] = annual_return / downside_deviation
        else:
            # 无法计算真实 Sortino，使用 Sharpe 估算并标记
            sharpe_ratio = performance.get('sharpe_ratio', 0)
            risk_metrics['sortino_ratio'] = (sharpe_ratio or 0) * 1.2
            risk_metrics['sortino_estimated'] = True

        # 欧米伽比率（Omega Ratio）
        # 仅在 performance 中包含 'daily_returns' 时计算；否则跳过。
        daily_returns = performance.get('daily_returns', None)
        omega = self._calculate_omega_ratio(daily_returns)
        if omega is not None:
            risk_metrics['omega_ratio'] = omega

        # 波动率
        if 'volatility' in performance:
            risk_metrics['volatility'] = performance['volatility']

        # 风险调整收益率
        if 'sharpe_ratio' in performance and 'total_return' in performance:
            risk_metrics['risk_adjusted_return'] = (
                performance['total_return'] / (1 + abs_drawdown)
            )

        return risk_metrics

    def _calculate_omega_ratio(
        self,
        daily_returns: Any,
        threshold: float = 0.0,
    ) -> Optional[float]:
        """
        计算欧米伽比率 (Omega Ratio)。

        Omega 衡量收益分布相对于给定阈值的"上行潜力"与"下行风险"之比。
        值大于 1 表示正超额收益期望超过负超额收益期望。

        公式::

            Omega = E[max(R - threshold, 0)] / E[max(threshold - R, 0)]

        参数
        ----------
        daily_returns : list, pd.Series, or np.ndarray
            每日收益率序列（小数形式，例如 0.01 表示 1%）。
            若为 ``None`` 或空序列则返回 ``None``。
        threshold : float, optional
            基准收益率阈值（默认 0.0，即零收益线）。
            常用值为无风险日收益率（如 0.02/252）。

        返回
        -----
        float or None
            欧米伽比率，若数据不足或分母为零则返回 ``None``。
        """
        if daily_returns is None:
            return None

        try:
            if isinstance(daily_returns, pd.Series):
                returns_arr = daily_returns.dropna().to_numpy(dtype=float)
            else:
                returns_arr = np.asarray(daily_returns, dtype=float)
                # Remove NaN / Inf values
                returns_arr = returns_arr[np.isfinite(returns_arr)]
        except (TypeError, ValueError):
            return None

        if returns_arr.size < 2:
            return None

        gains = np.maximum(returns_arr - threshold, 0.0)
        losses = np.maximum(threshold - returns_arr, 0.0)

        expected_gain = gains.mean()
        expected_loss = losses.mean()

        if expected_loss == 0.0:
            # All returns exceed the threshold: omega is theoretically infinite.
            return None

        return float(expected_gain / expected_loss)
    
    def _analyze_trades(self, trade_logs: pd.DataFrame) -> Dict[str, Any]:
        """分析交易记录"""
        trade_analysis = {}
        
        if trade_logs.empty:
            return trade_analysis
        
        try:
            # 基本统计
            trade_analysis['total_trades'] = len(trade_logs)
            
            # 买入卖出统计
            if 'action' in trade_logs.columns:
                buy_trades = trade_logs[trade_logs['action'] == 'BUY']
                sell_trades = trade_logs[trade_logs['action'] == 'SELL']
                
                trade_analysis['buy_count'] = len(buy_trades)
                trade_analysis['sell_count'] = len(sell_trades)
            
            # 盈亏统计
            if 'pnl' in trade_logs.columns:
                profitable_trades = trade_logs[trade_logs['pnl'] > 0]
                losing_trades = trade_logs[trade_logs['pnl'] < 0]
                
                trade_analysis['profitable_count'] = len(profitable_trades)
                trade_analysis['losing_count'] = len(losing_trades)
                trade_analysis['win_rate'] = trade_analysis['profitable_count'] / trade_analysis['total_trades'] if trade_analysis['total_trades'] > 0 else 0
                
                # 平均盈亏
                if len(profitable_trades) > 0:
                    trade_analysis['avg_profit'] = profitable_trades['pnl'].mean()
                    trade_analysis['max_profit'] = profitable_trades['pnl'].max()
                
                if len(losing_trades) > 0:
                    trade_analysis['avg_loss'] = losing_trades['pnl'].mean()
                    trade_analysis['max_loss'] = losing_trades['pnl'].min()
                
                # 盈亏比
                if 'avg_profit' in trade_analysis and 'avg_loss' in trade_analysis:
                    if trade_analysis['avg_loss'] != 0:
                        trade_analysis['profit_loss_ratio'] = abs(trade_analysis['avg_profit'] / trade_analysis['avg_loss'])
            
            # 持仓时间分析（如果有时间信息）
            if 'datetime' in trade_logs.columns and 'action' in trade_logs.columns:
                # 这里可以添加持仓时间分析
                pass
        
        except Exception as e:
            logger.warning(f"交易分析失败: {e}")
        
        return trade_analysis
    
    def _evaluate_strategy(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """评估策略质量"""
        evaluation = {}
        
        # 计算综合得分
        score = 0
        score_details = {}
        
        for metric, weight in BACKTEST.METRIC_WEIGHTS.items():
            if metric in performance:
                value = performance[metric]
                
                # 标准化处理
                if metric == 'max_drawdown':
                    value = abs(value)  # 回撤取绝对值
                    normalized_value = 1 - min(value, 1)  # 回撤越小越好
                else:
                    # 其他指标越大越好
                    normalized_value = min(max(value, -1), 1)  # 限制在[-1, 1]范围内
                
                metric_score = normalized_value * abs(weight)
                score += metric_score
                score_details[metric] = metric_score
        
        evaluation['overall_score'] = score
        evaluation['score_details'] = score_details
        
        # 策略评级
        if score > 0.6:
            evaluation['rating'] = '优秀'
            evaluation['rating_color'] = 'green'
        elif score > 0.3:
            evaluation['rating'] = '良好'
            evaluation['rating_color'] = 'blue'
        elif score > 0:
            evaluation['rating'] = '一般'
            evaluation['rating_color'] = 'yellow'
        else:
            evaluation['rating'] = '较差'
            evaluation['rating_color'] = 'red'
        
        # 策略稳定性评估
        stability_indicators = []
        
        if 'sharpe_ratio' in performance and performance['sharpe_ratio'] > 1:
            stability_indicators.append('夏普比率良好')
        
        if 'win_rate' in performance and performance['win_rate'] > 0.5:
            stability_indicators.append('胜率较高')
        
        if 'profit_factor' in performance and performance['profit_factor'] > 1.5:
            stability_indicators.append('盈亏比较优')
        
        if 'max_drawdown' in performance and abs(performance['max_drawdown']) < 0.2:
            stability_indicators.append('回撤控制良好')
        
        evaluation['stability_indicators'] = stability_indicators
        evaluation['stability_score'] = len(stability_indicators) / 4  # 4个指标
        
        return evaluation
    
    def _generate_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成策略建议"""
        recommendation = {
            'action': '持有',
            'confidence': '中等',
            'suggestions': [],
            'warnings': []
        }
        
        perf_summary = analysis['performance_summary']
        risk_metrics = analysis['risk_metrics']
        strategy_eval = analysis['strategy_evaluation']
        
        # 基于综合得分决定行动
        overall_score = strategy_eval.get('overall_score', 0)
        
        if overall_score > 0.7:
            recommendation['action'] = '强烈推荐'
            recommendation['confidence'] = '高'
        elif overall_score > 0.4:
            recommendation['action'] = '推荐'
            recommendation['confidence'] = '中'
        elif overall_score > 0:
            recommendation['action'] = '谨慎使用'
            recommendation['confidence'] = '低'
        else:
            recommendation['action'] = '不推荐'
            recommendation['confidence'] = '低'
        
        # 添加具体建议
        if perf_summary.get('total_return', 0) > 0.3:
            recommendation['suggestions'].append('收益率较高，适合趋势行情')
        elif perf_summary.get('total_return', 0) < 0:
            recommendation['warnings'].append('收益率为负，需检查策略逻辑')
        
        if perf_summary.get('max_drawdown', 0) < -0.2:
            recommendation['warnings'].append('最大回撤较大，注意风险控制')
        
        if perf_summary.get('win_rate', 0) < 0.4:
            recommendation['suggestions'].append('胜率较低，建议优化入场信号')
        
        if perf_summary.get('profit_factor', 0) < 1:
            recommendation['warnings'].append('盈亏比小于1，盈利交易不足以覆盖亏损')
        
        # 添加优化建议
        if len(recommendation['suggestions']) == 0:
            recommendation['suggestions'].append('策略表现稳定，可继续使用')
        
        return recommendation
    
    def analyze_multiple_backtests(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析多个回测结果
        
        Args:
            results: 多个回测结果字典
            
        Returns:
            多结果分析
        """
        analysis_results = {}
        comparison_data = []
        
        logger.info(f"开始分析 {len(results)} 个回测结果")
        
        for key, result in results.items():
            # 分析单个结果
            analysis = self.analyze_single_backtest(result)
            analysis_results[key] = analysis
            
            # 准备比较数据
            comp_row = {
                'strategy_key': key,
                'strategy_type': result['strategy_type'],
                'overall_score': analysis['strategy_evaluation']['overall_score']
            }
            
            # 添加性能指标
            for metric, value in analysis['performance_summary'].items():
                comp_row[metric] = value
            
            comparison_data.append(comp_row)
        
        # 比较分析
        comparison = self._compare_strategies(comparison_data)
        
        # 找到最佳策略
        best_strategy = self._identify_best_strategy(analysis_results, comparison)
        
        # 保存最佳策略
        if best_strategy:
            self._save_best_strategy(best_strategy)
        
        return {
            'individual_analyses': analysis_results,
            'comparison': comparison,
            'best_strategy': best_strategy
        }
    
    def _compare_strategies(self, comparison_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """比较多个策略"""
        comparison = {
            'summary': {},
            'ranking': [],
            'correlation': {}
        }
        
        if not comparison_data:
            return comparison
        
        # 创建DataFrame以便分析
        df = pd.DataFrame(comparison_data)
        
        # 基本统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col not in ['strategy_key', 'overall_score']:
                comparison['summary'][col] = {
                    'mean': df[col].mean(),
                    'std': df[col].std(),
                    'min': df[col].min(),
                    'max': df[col].max(),
                    'median': df[col].median()
                }
        
        # 策略排名
        if 'overall_score' in df.columns:
            ranked_df = df.sort_values('overall_score', ascending=False)
            
            for _, row in ranked_df.iterrows():
                ranking_entry = {
                    'strategy_key': row['strategy_key'],
                    'strategy_type': row['strategy_type'],
                    'overall_score': row['overall_score'],
                    'total_return': row.get('total_return', 0),
                    'sharpe_ratio': row.get('sharpe_ratio', 0)
                }
                comparison['ranking'].append(ranking_entry)
        
        # 相关性分析
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            comparison['correlation'] = corr_matrix.to_dict()
        
        return comparison
    
    def _identify_best_strategy(self, analysis_results: Dict[str, Any],
                               comparison: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """识别最佳策略"""
        if not comparison.get('ranking'):
            return None
        
        # 获取排名第一的策略
        top_ranking = comparison['ranking'][0]
        strategy_key = top_ranking['strategy_key']
        
        if strategy_key in analysis_results:
            best_analysis = analysis_results[strategy_key]
            
            # 创建最佳策略信息
            best_strategy = {
                'strategy_key': strategy_key,
                'strategy_type': best_analysis['strategy_type'],
                'params': best_analysis['params'],
                'performance_summary': best_analysis['performance_summary'],
                'strategy_evaluation': best_analysis['strategy_evaluation'],
                'recommendation': best_analysis['recommendation'],
                'ranking_info': top_ranking,
                'selection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"识别到最佳策略: {strategy_key}")
            logger.info(f"综合得分: {top_ranking['overall_score']:.4f}")
            
            return best_strategy
        
        return None
    
    def _save_best_strategy(self, best_strategy: Dict[str, Any]):
        """保存最佳策略"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            strategy_type = best_strategy['strategy_type']
            
            # 创建最佳策略目录
            strategy_dir = os.path.join(self.best_strategies_dir, f"{strategy_type}_{timestamp}")
            os.makedirs(strategy_dir, exist_ok=True)
            
            # 保存策略信息
            info_file = os.path.join(strategy_dir, "strategy_info.txt")
            
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write("最佳策略信息\n")
                f.write("=" * 50 + "\n")
                f.write(f"策略类型: {best_strategy['strategy_type']}\n")
                f.write(f"选择时间: {best_strategy['selection_time']}\n")
                f.write(f"综合得分: {best_strategy['ranking_info']['overall_score']:.4f}\n")
                f.write(f"排名: 第1名\n")
                
                f.write("\n参数配置:\n")
                for param, value in best_strategy['params'].items():
                    f.write(f"  {param}: {value}\n")
                
                f.write("\n性能摘要:\n")
                for metric, value in best_strategy['performance_summary'].items():
                    f.write(f"  {metric}: {value}\n")
                
                f.write("\n策略评估:\n")
                eval_info = best_strategy['strategy_evaluation']
                f.write(f"  综合得分: {eval_info['overall_score']:.4f}\n")
                f.write(f"  评级: {eval_info['rating']}\n")
                f.write(f"  稳定性指标: {', '.join(eval_info['stability_indicators'])}\n")
                
                f.write("\n建议:\n")
                rec_info = best_strategy['recommendation']
                f.write(f"  操作建议: {rec_info['action']}\n")
                f.write(f"  置信度: {rec_info['confidence']}\n")
                f.write(f"  具体建议:\n")
                for suggestion in rec_info['suggestions']:
                    f.write(f"    • {suggestion}\n")
                if rec_info['warnings']:
                    f.write(f"  警告:\n")
                    for warning in rec_info['warnings']:
                        f.write(f"    • {warning}\n")
            
            # 保存为JSON格式（便于程序读取）
            import json
            json_file = os.path.join(strategy_dir, "strategy_info.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(best_strategy, f, indent=2, ensure_ascii=False, default=str)
            
            # 创建策略配置文件（便于直接使用）
            config_file = os.path.join(strategy_dir, "strategy_config.py")
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(f"# 最佳策略配置 - {strategy_type}\n")
                f.write(f"# 生成时间: {best_strategy['selection_time']}\n")
                f.write(f"# 综合得分: {best_strategy['ranking_info']['overall_score']:.4f}\n\n")
                
                f.write("STRATEGY_CONFIG = {\n")
                f.write(f"    'strategy_type': '{best_strategy['strategy_type']}',\n")
                f.write("    'params': {\n")
                for param, value in best_strategy['params'].items():
                    f.write(f"        '{param}': {repr(value)},\n")
                f.write("    },\n")
                f.write("    'performance_summary': {\n")
                for metric, value in best_strategy['performance_summary'].items():
                    f.write(f"        '{metric}': {repr(value)},\n")
                f.write("    }\n")
                f.write("}\n")
            
            logger.info(f"最佳策略已保存: {strategy_dir}")
        
        except Exception as e:
            logger.warning(f"保存最佳策略失败: {e}")
    
    def generate_report(self, analysis_results: Dict[str, Any],
                       output_dir: str = None) -> str:
        """
        生成分析报告
        
        Args:
            analysis_results: 分析结果
            output_dir: 输出目录
            
        Returns:
            报告文件路径
        """
        if output_dir is None:
            output_dir = self.best_strategies_dir
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = os.path.join(output_dir, f"analysis_report_{timestamp}")
        os.makedirs(report_dir, exist_ok=True)
        
        try:
            # 生成文本报告
            text_report = self._generate_text_report(analysis_results, report_dir)
            
            # 生成图表
            self._generate_charts(analysis_results, report_dir)
            
            # 生成汇总文件
            summary_file = self._generate_summary_file(analysis_results, report_dir)
            
            logger.info(f"分析报告已生成: {report_dir}")
            
            return report_dir
        
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return ""
    
    def _generate_text_report(self, analysis_results: Dict[str, Any],
                             report_dir: str) -> str:
        """生成文本报告"""
        report_file = os.path.join(report_dir, "analysis_report.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("量化策略分析报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析策略数: {len(analysis_results.get('individual_analyses', {}))}\n\n")
            
            # 最佳策略信息
            best_strategy = analysis_results.get('best_strategy')
            if best_strategy:
                f.write("最佳策略\n")
                f.write("-" * 40 + "\n")
                f.write(f"策略类型: {best_strategy['strategy_type']}\n")
                f.write(f"综合得分: {best_strategy['ranking_info']['overall_score']:.4f}\n")
                f.write(f"总收益率: {best_strategy['performance_summary'].get('total_return', 0):.2%}\n")
                f.write(f"夏普比率: {best_strategy['performance_summary'].get('sharpe_ratio', 0):.2f}\n")
                f.write(f"最大回撤: {best_strategy['performance_summary'].get('max_drawdown', 0):.2%}\n")
                f.write(f"操作建议: {best_strategy['recommendation']['action']}\n\n")
            
            # 策略比较
            comparison = analysis_results.get('comparison', {})
            if comparison.get('ranking'):
                f.write("策略排名\n")
                f.write("-" * 40 + "\n")
                for i, ranking in enumerate(comparison['ranking'][:10], 1):  # 显示前10名
                    f.write(f"{i}. {ranking['strategy_key']} - ")
                    f.write(f"得分: {ranking['overall_score']:.4f}, ")
                    f.write(f"收益: {ranking.get('total_return', 0):.2%}, ")
                    f.write(f"夏普: {ranking.get('sharpe_ratio', 0):.2f}\n")
                f.write("\n")
            
            # 详细分析
            f.write("详细分析\n")
            f.write("-" * 40 + "\n")
            
            individual_analyses = analysis_results.get('individual_analyses', {})
            for key, analysis in individual_analyses.items():
                f.write(f"\n策略: {key}\n")
                f.write(f"类型: {analysis['strategy_type']}\n")
                f.write(f"综合得分: {analysis['strategy_evaluation']['overall_score']:.4f}\n")
                f.write(f"评级: {analysis['strategy_evaluation']['rating']}\n")
                
                perf = analysis['performance_summary']
                f.write(f"总收益率: {perf.get('total_return', 0):.2%}\n")
                f.write(f"夏普比率: {perf.get('sharpe_ratio', 0):.2f}\n")
                f.write(f"最大回撤: {perf.get('max_drawdown', 0):.2%}\n")
                f.write(f"胜率: {perf.get('win_rate', 0):.2%}\n")
                f.write(f"建议: {analysis['recommendation']['action']}\n")
        
        return report_file
    
    def _generate_charts(self, analysis_results: Dict[str, Any], report_dir: str):
        """生成图表"""
        try:
            # 设置图表样式
            plt.style.use('seaborn-v0_8-darkgrid')
            sns.set_palette("husl")
            
            # 策略得分对比图
            comparison = analysis_results.get('comparison', {})
            if comparison.get('ranking'):
                ranking_data = comparison['ranking']
                
                # 只取前10名
                top_n = min(10, len(ranking_data))
                top_strategies = ranking_data[:top_n]
                
                fig, axes = plt.subplots(2, 2, figsize=(15, 12))
                
                # 1. 综合得分柱状图
                strategy_names = [s['strategy_key'] for s in top_strategies]
                scores = [s['overall_score'] for s in top_strategies]
                
                axes[0, 0].barh(strategy_names, scores, color='steelblue')
                axes[0, 0].set_xlabel('综合得分')
                axes[0, 0].set_title('策略综合得分对比')
                axes[0, 0].invert_yaxis()
                
                # 2. 收益率对比
                returns = [s.get('total_return', 0) for s in top_strategies]
                axes[0, 1].barh(strategy_names, returns, color='lightcoral')
                axes[0, 1].set_xlabel('总收益率')
                axes[0, 1].set_title('策略收益率对比')
                axes[0, 1].invert_yaxis()
                
                # 3. 夏普比率对比
                sharpes = [s.get('sharpe_ratio', 0) for s in top_strategies]
                axes[1, 0].barh(strategy_names, sharpes, color='mediumseagreen')
                axes[1, 0].set_xlabel('夏普比率')
                axes[1, 1].set_title('策略风险调整收益对比')
                axes[1, 0].invert_yaxis()
                
                # 4. 散点图：收益率 vs 最大回撤
                drawdowns = [s.get('max_drawdown', 0) for s in top_strategies]
                scatter = axes[1, 1].scatter(returns, drawdowns, c=scores, cmap='viridis', s=100, alpha=0.7)
                axes[1, 1].set_xlabel('总收益率')
                axes[1, 1].set_ylabel('最大回撤')
                axes[1, 1].set_title('收益率 vs 最大回撤')
                axes[1, 1].grid(True, alpha=0.3)
                
                # 添加颜色条
                plt.colorbar(scatter, ax=axes[1, 1], label='综合得分')
                
                plt.tight_layout()
                chart_file = os.path.join(report_dir, "strategy_comparison.png")
                plt.savefig(chart_file, dpi=300, bbox_inches='tight')
                plt.close()
            
            # 相关性热力图
            if comparison.get('correlation'):
                corr_data = pd.DataFrame(comparison['correlation'])
                
                plt.figure(figsize=(10, 8))
                sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='coolwarm',
                           center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8})
                plt.title('策略指标相关性热力图')
                
                heatmap_file = os.path.join(report_dir, "correlation_heatmap.png")
                plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
                plt.close()
        
        except Exception as e:
            logger.warning(f"生成图表失败: {e}")
    
    def _generate_summary_file(self, analysis_results: Dict[str, Any],
                              report_dir: str) -> str:
        """生成汇总文件"""
        summary_file = os.path.join(report_dir, "summary.json")
        
        try:
            import json
            
            # 创建简化版的汇总信息
            summary = {
                'report_generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_strategies_analyzed': len(analysis_results.get('individual_analyses', {})),
                'best_strategy': None,
                'top_strategies': []
            }
            
            # 最佳策略信息
            best_strategy = analysis_results.get('best_strategy')
            if best_strategy:
                summary['best_strategy'] = {
                    'strategy_type': best_strategy['strategy_type'],
                    'overall_score': best_strategy['ranking_info']['overall_score'],
                    'total_return': best_strategy['performance_summary'].get('total_return', 0),
                    'sharpe_ratio': best_strategy['performance_summary'].get('sharpe_ratio', 0)
                }
            
            # 前5名策略
            comparison = analysis_results.get('comparison', {})
            if comparison.get('ranking'):
                for ranking in comparison['ranking'][:5]:
                    summary['top_strategies'].append({
                        'strategy_key': ranking['strategy_key'],
                        'strategy_type': ranking['strategy_type'],
                        'overall_score': ranking['overall_score'],
                        'total_return': ranking.get('total_return', 0),
                        'sharpe_ratio': ranking.get('sharpe_ratio', 0)
                    })
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
            return summary_file
        
        except Exception as e:
            logger.warning(f"生成汇总文件失败: {e}")
            return ""


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试分析器
    print("测试回测分析器...")
    
    # 创建分析器
    analyzer = BacktestAnalyzer()
    
    # 创建测试数据
    test_result = {
        'strategy_type': 'MA',
        'params': {'sma_period': 10, 'lma_period': 30},
        'performance': {
            'total_return': 0.3567,
            'annual_return': 0.1254,
            'sharpe_ratio': 1.2345,
            'max_drawdown': -0.1567,
            'win_rate': 0.5567,
            'profit_factor': 1.7890,
            'trades_count': 123
        },
        'trade_logs': pd.DataFrame({
            'datetime': pd.date_range('2023-01-01', periods=10),
            'action': ['BUY', 'SELL'] * 5,
            'price': [100 + i for i in range(10)],
            'pnl': [10, -5, 15, -3, 20, -8, 12, -2, 18, -6]
        }),
        'final_value': 135670.45,
        'total_return': 0.3567
    }
    
    # 分析单个回测
    print("分析单个回测结果...")
    analysis = analyzer.analyze_single_backtest(test_result)
    
    print(f"策略类型: {analysis['strategy_type']}")
    print(f"综合得分: {analysis['strategy_evaluation']['overall_score']:.4f}")
    print(f"策略评级: {analysis['strategy_evaluation']['rating']}")
    print(f"操作建议: {analysis['recommendation']['action']}")
    
    # 测试多结果分析
    print("\n测试多结果分析...")
    multiple_results = {
        'MA_1': test_result,
        'MA_2': {**test_result, 'strategy_type': 'MA', 'performance': {**test_result['performance'], 'total_return': 0.4567}},
        'MACD_1': {**test_result, 'strategy_type': 'MACD', 'performance': {**test_result['performance'], 'total_return': 0.2567}}
    }
    
    multi_analysis = analyzer.analyze_multiple_backtests(multiple_results)
    
    print(f"分析策略数: {len(multi_analysis['individual_analyses'])}")
    if multi_analysis['best_strategy']:
        print(f"最佳策略: {multi_analysis['best_strategy']['strategy_type']}")
        print(f"最佳得分: {multi_analysis['best_strategy']['ranking_info']['overall_score']:.4f}")
    
    print("\n分析器测试完成!")