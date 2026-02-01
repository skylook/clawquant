#!/usr/bin/env python3
"""
MA策略验证脚本
验证移动平均线策略的基本功能和参数优化
"""

import os
import sys
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime, timedelta
import json

print("="*60)
print("MA策略验证脚本")
print("="*60)

# 创建MA策略类
class MAStrategy(bt.Strategy):
    """移动平均线策略"""
    
    params = (
        ('sma_period', 20),    # 短期均线周期
        ('lma_period', 50),    # 长期均线周期
        ('atr_period', 14),    # ATR周期（用于止损）
        ('atr_multiplier', 2.0),  # ATR倍数
    )
    
    def __init__(self):
        # 移动平均线
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period)
        self.lma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.lma_period)
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.sma, self.lma)
        
        # ATR指标（用于动态止损）
        self.atr = bt.indicators.AverageTrueRange(
            self.data, period=self.params.atr_period)
        
        # 跟踪变量
        self.order = None
        self.stop_price = 0
        self.entry_price = 0
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                # 设置止损价
                self.stop_price = self.entry_price - self.atr[0] * self.params.atr_multiplier
                print(f'买入 @ {order.executed.price:.2f}, 止损 @ {self.stop_price:.2f}')
            elif order.issell():
                print(f'卖出 @ {order.executed.price:.2f}')
                self.stop_price = 0
            
            self.bar_executed = len(self)
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单取消/拒绝: {order.status}')
        
        self.order = None
    
    def next(self):
        # 如果有未完成订单，不执行新操作
        if self.order:
            return
        
        # 检查止损
        if self.position and self.stop_price > 0:
            if self.data.close[0] <= self.stop_price:
                print(f'触发止损 @ {self.data.close[0]:.2f}')
                self.order = self.sell()
                return
        
        # 检查是否持有仓位
        if not self.position:
            # 金叉：短期均线上穿长期均线，买入
            if self.crossover > 0:
                print(f'金叉信号: SMA{self.params.sma_period}上穿LMA{self.params.lma_period}')
                self.order = self.buy()
        
        else:
            # 死叉：短期均线下穿长期均线，卖出
            if self.crossover < 0:
                print(f'死叉信号: SMA{self.params.sma_period}下穿LMA{self.params.lma_period}')
                self.order = self.sell()
            
            # 更新动态止损
            if self.stop_price > 0:
                # 跟踪止损：价格上涨时提高止损价
                new_stop = self.data.close[0] - self.atr[0] * self.params.atr_multiplier
                if new_stop > self.stop_price:
                    self.stop_price = new_stop


def create_test_data():
    """创建测试数据"""
    print("📊 创建测试数据...")
    
    # 创建日期范围
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    n = len(dates)
    
    # 创建基础趋势
    np.random.seed(42)
    base_trend = np.linspace(100, 150, n)
    
    # 添加季节性波动
    seasonal = 10 * np.sin(2 * np.pi * np.arange(n) / 252)  # 一年周期
    
    # 添加随机波动
    random_noise = np.random.normal(0, 5, n)
    
    # 合成价格
    prices = base_trend + seasonal + random_noise
    
    # 确保价格为正
    prices = np.abs(prices)
    
    # 创建OHLCV数据
    data = pd.DataFrame({
        'Open': prices * 0.995,
        'High': prices * 1.015,
        'Low': prices * 0.985,
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, n)
    }, index=dates)
    
    print(f"✅ 创建测试数据: {len(data)} 条记录")
    print(f"数据范围: {data.index[0].date()} 到 {data.index[-1].date()}")
    print(f"价格范围: ${data['Close'].min():.2f} - ${data['Close'].max():.2f}")
    
    return data


def run_single_backtest(data, params):
    """运行单次回测"""
    # 初始化Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    
    # 设置手续费
    cerebro.broker.setcommission(commission=0.001)  # 0.1%
    
    # 添加数据
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    
    # 添加策略
    cerebro.addstrategy(MAStrategy, **params)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
    
    # 运行回测
    results = cerebro.run()
    strat = results[0]
    
    # 收集结果
    final_value = cerebro.broker.getvalue()
    initial_cash = 100000.0
    profit = final_value - initial_cash
    profit_pct = (profit / initial_cash) * 100
    
    # 获取分析器数据
    returns_analyzer = strat.analyzers.returns.get_analysis()
    sharpe_analyzer = strat.analyzers.sharpe.get_analysis()
    drawdown_analyzer = strat.analyzers.drawdown.get_analysis()
    trades_analyzer = strat.analyzers.trades.get_analysis()
    
    result = {
        'params': params,
        'final_value': final_value,
        'initial_cash': initial_cash,
        'profit': profit,
        'profit_pct': profit_pct,
        'annual_return': returns_analyzer.get('rnorm100', 0) if returns_analyzer else 0,
        'sharpe_ratio': sharpe_analyzer.get('sharperatio', 0) if sharpe_analyzer else 0,
        'max_drawdown': drawdown_analyzer.get('max', {}).get('drawdown', 0) if drawdown_analyzer else 0,
        'max_drawdown_length': drawdown_analyzer.get('max', {}).get('len', 0) if drawdown_analyzer else 0,
        'total_trades': trades_analyzer.get('total', {}).get('total', 0) if trades_analyzer else 0,
        'won_trades': trades_analyzer.get('won', {}).get('total', 0) if trades_analyzer else 0,
        'lost_trades': trades_analyzer.get('lost', {}).get('total', 0) if trades_analyzer else 0,
    }
    
    # 计算胜率
    if result['total_trades'] > 0:
        result['win_rate'] = (result['won_trades'] / result['total_trades']) * 100
    else:
        result['win_rate'] = 0
    
    return result


def run_parameter_optimization(data):
    """运行参数优化"""
    print("\n" + "="*60)
    print("参数优化流程")
    print("="*60)
    
    # 定义参数搜索空间
    param_grid = {
        'sma_period': [5, 10, 15, 20, 25, 30],
        'lma_period': [40, 50, 60, 70, 80, 100],
        'atr_multiplier': [1.5, 2.0, 2.5, 3.0]
    }
    
    results = []
    
    print("开始参数优化搜索...")
    print(f"参数组合总数: {len(param_grid['sma_period']) * len(param_grid['lma_period']) * len(param_grid['atr_multiplier'])}")
    
    count = 0
    for sma in param_grid['sma_period']:
        for lma in param_grid['lma_period']:
            if sma >= lma:
                continue  # 跳过无效组合
            
            for atr_mult in param_grid['atr_multiplier']:
                params = {
                    'sma_period': sma,
                    'lma_period': lma,
                    'atr_period': 14,
                    'atr_multiplier': atr_mult
                }
                
                count += 1
                if count % 10 == 0:
                    print(f"进度: {count} 个组合已测试")
                
                try:
                    result = run_single_backtest(data, params)
                    results.append(result)
                except Exception as e:
                    print(f"❌ 参数组合测试失败: {params}, 错误: {e}")
    
    print(f"✅ 参数优化完成，共测试 {len(results)} 个有效组合")
    
    return results


def analyze_results(results):
    """分析优化结果"""
    print("\n" + "="*60)
    print("优化结果分析")
    print("="*60)
    
    if not results:
        print("❌ 没有有效结果可供分析")
        return None
    
    # 转换为DataFrame便于分析
    df = pd.DataFrame(results)
    
    # 按不同指标排序找到最佳参数
    metrics = {
        '最终资金': ('final_value', 'desc'),
        '收益率': ('profit_pct', 'desc'),
        '夏普比率': ('sharpe_ratio', 'desc'),
        '最大回撤': ('max_drawdown', 'asc'),  # 回撤越小越好
        '胜率': ('win_rate', 'desc')
    }
    
    best_params = {}
    
    for metric_name, (col, order) in metrics.items():
        if order == 'desc':
            best_idx = df[col].idxmax()
        else:
            best_idx = df[col].idxmin()
        
        best_row = df.loc[best_idx]
        best_params[metric_name] = {
            '参数': best_row['params'],
            '值': best_row[col],
            '收益率': f"{best_row['profit_pct']:.2f}%",
            '夏普比率': f"{best_row['sharpe_ratio']:.3f}",
            '最大回撤': f"{best_row['max_drawdown']:.2f}%",
            '胜率': f"{best_row['win_rate']:.1f}%"
        }
    
    # 打印最佳参数
    print("\n📊 按不同指标的最佳参数组合:")
    for metric, info in best_params.items():
        params = info['参数']
        print(f"\n{metric}:")
        print(f"  SMA={params['sma_period']}, LMA={params['lma_period']}, ATR倍数={params['atr_multiplier']}")
        print(f"  最终资金: ${info['值']:,.2f}" if metric == '最终资金' else f"  {metric}: {info['值']}")
        print(f"  收益率: {info['收益率']}")
        print(f"  夏普比率: {info['夏普比率']}")
        print(f"  最大回撤: {info['最大回撤']}")
        print(f"  胜率: {info['胜率']}")
    
    # 统计信息
    print("\n📈 整体统计:")
    print(f"  平均收益率: {df['profit_pct'].mean():.2f}%")
    print(f"  最高收益率: {df['profit_pct'].max():.2f}%")
    print(f"  最低收益率: {df['profit_pct'].min():.2f}%")
    print(f"  平均夏普比率: {df['sharpe_ratio'].mean():.3f}")
    print(f"  平均最大回撤: {df['max_drawdown'].mean():.2f}%")
    print(f"  平均胜率: {df['win_rate'].mean():.1f}%")
    
    # 找到综合最佳（夏普比率高且回撤小）
    df['composite_score'] = df['sharpe_ratio'] * (100 - df['max_drawdown']) / 100
    best_composite_idx = df['composite_score'].idxmax()
    best_composite = df.loc[best_composite_idx]
    
    print(f"\n⭐ 综合最佳参数 (夏普×回撤调整):")
    print(f"  SMA={best_composite['params']['sma_period']}, "
          f"LMA={best_composite['params']['lma_period']}, "
          f"ATR倍数={best_composite['params']['atr_multiplier']}")
    print(f"  综合评分: {best_composite['composite_score']:.3f}")
    print(f"  收益率: {best_composite['profit_pct']:.2f}%")
    print(f"  夏普比率: {best_composite['sharpe_ratio']:.3f}")
    print(f"  最大回撤: {best_composite['max_drawdown']:.2f}%")
    print(f"  胜率: {best_composite['win_rate']:.1f}%")
    
    return {
        'dataframe': df,
        'best_by_metric': best_params,
        'best_composite': best_composite.to_dict()
    }


def save_results(results, analysis):
    """保存结果到文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = 'validation_results'
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存原始结果
    results_file = os.path.join(output_dir, f'optimization_results_{timestamp}.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # 保存分析报告
    report_file = os.path.join(output_dir, f'analysis_report_{timestamp}.txt')
    with open(report_file, 'w') as f:
        f.write("MA策略参数优化分析报告\n")
        f.write("="*50 + "\n")
        f.write(f"生成时间: {datetime.now()}\n")
        f.write(f"测试参数组合数: {len(results)}\n\n")
        
        f.write("最佳参数组合:\n")
        f.write("-"*30 + "\n")
        
        if analysis and 'best_composite' in analysis:
            best = analysis['best_composite']
            params = eval(best['params']) if isinstance(best['params'], str) else best['params']
            f.write(f"综合最佳参数:\n")
            f.write(f"  SMA周期: {params['sma_period']}\n")
            f.write(f"  LMA周期: {params['lma_period']}\n")
            f.write(f"  ATR倍数: {params['atr_multiplier']}\n")
            f.write(f"  收益率: {best['profit_pct']:.2f}%\n")
            f.write(f"  夏普比率: {best['sharpe_ratio']:.3f}\n")
            f.write(f"  最大回撤: {best['max_drawdown']:.2f}%\n")
            f.write(f"  胜率: {best['win_rate']:.1f}%\n")
        
        f.write("\n性能统计:\n")
        f.write("-"*30 + "\n")
        if analysis and 'dataframe' in analysis:
            df = analysis['dataframe']
            f.write(f"平均收益率: {df['profit_pct'].mean():.2f}%\n")
            f.write(f"收益率标准差: {df['profit_pct'].std():.2f}%\n")
            f.write(f"最高收益率: {df['profit_pct'].max():.2f}%\n")
            f.write(f"最低收益率: {df['profit_pct'].min():.2f}%\n")
            f.write(f"平均夏普比率: {df['sharpe_ratio'].mean():.3f}\n")
            f.write(f"平均最大回撤: {df['max_drawdown'].mean():.2f}%\n")
    
    print(f"\n✅ 结果已保存:")
    print(f"   原始数据: {results_file}")
    print(f"   分析报告: {report_file}")


def main():
    """主函数"""
    print("MA策略验证流程")
    print("-"*40)
    
    # 1. 创建测试数据
    data = create_test_data()
    
    # 2. 运行基准测试
    print("\n1. 基准MA策略测试")
    print("-"*30)
    
    baseline_params = {
        'sma_period': 20,
        'lma_period': 50,
        'atr_period': 14,
        'atr_multiplier': 2.0
    }
    
    baseline_result = run_single_backtest(data, baseline_params)
    
    print(f"基准策略结果:")
    print(f"  参数: SMA={baseline_params['sma_period']}, LMA={baseline_params['lma_period']}")
    print(f"  最终资金: ${baseline_result['final_value']:,.2f}")
    print(f"  收益率: {baseline_result['profit_pct']:.2f}%")
    print(f"  夏普比率: {baseline_result['sharpe_ratio']:.3f}")
    print(f"  最大回撤: {baseline_result['max_drawdown']:.2f}%")
    print(f"  胜率: {baseline_result['win_rate']:.1f}%")
    
    # 3. 运行参数优化
    print("\n2. 参数优化流程")
    optimization_results = run_parameter_optimization(data)
    
    # 4. 分析结果
    analysis = analyze_results(optimization_results)
    
    # 5. 保存结果
    save_results(optimization_results, analysis)
    
    print("\n" + "="*60)
    print("✅ MA策略验证完成")
    print("="*60)


if __name__ == "__main__":
    main()