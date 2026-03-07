#!/usr/bin/env python3
"""
2025年策略表现回测分析
最优策略：MA_CROSS (fast=5, slow=70)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入backtrader
import backtrader as bt

# 创建MA_CROSS策略
class MACrossStrategy(bt.Strategy):
    """双均线交叉策略 - 最优参数版"""
    params = (
        ('fast_period', 5),    # 最优快线周期
        ('slow_period', 70),   # 最优慢线周期
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
    )
    
    def __init__(self):
        # 移动平均线
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period)
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        # ATR指标
        self.atr = bt.indicators.AverageTrueRange(
            self.data, period=self.params.atr_period)
        
        self.order = None
        self.stop_price = 0
        self.trades = []
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.stop_price = self.entry_price - self.atr[0] * self.params.atr_multiplier
            else:
                self.stop_price = 0
        self.order = None
        
    def next(self):
        if self.order:
            return
            
        # 检查止损
        if self.position and self.stop_price > 0:
            if self.data.close[0] <= self.stop_price:
                self.order = self.sell()
                return
                
        if not self.position:
            if self.crossover > 0:  # 金叉买入
                self.order = self.buy()
        else:
            if self.crossover < 0:  # 死叉卖出
                self.order = self.sell()
                
        # 动态止损
        if self.stop_price > 0:
            new_stop = self.data.close[0] - self.atr[0] * self.params.atr_multiplier
            if new_stop > self.stop_price:
                self.stop_price = new_stop


def run_backtest_for_period(data_file, start_date, end_date, strategy_class, strategy_params, initial_capital=100000):
    """运行指定时间段的回测"""
    
    # 加载数据
    df = pd.read_csv(data_file)
    df['date'] = pd.to_datetime(df['date'])
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    df = df.sort_values('date')
    
    if len(df) == 0:
        print(f"❌ 没有数据: {start_date} 到 {end_date}")
        return None
        
    print(f"\n{'='*60}")
    print(f"回测区间: {start_date} 至 {end_date}")
    print(f"数据条数: {len(df)}")
    print(f"策略参数: {strategy_params}")
    print(f"{'='*60}")
    
    # 计算大盘收益（买入持有）
    first_close = df['close'].iloc[0]
    last_close = df['close'].iloc[-1]
    market_return = (last_close - first_close) / first_close * 100
    
    print(f"\n📊 大盘表现（买入持有）:")
    print(f"   起始价格: {first_close:.2f}")
    print(f"   结束价格: {last_close:.2f}")
    print(f"   期间收益: {market_return:.2f}%")
    
    # 设置回测
    cerebro = bt.Cerebro()
    
    # 创建数据源
    class PandasData(bt.feeds.PandasData):
        params = (
            ('datetime', 'date'),
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'volume'),
            ('openinterest', None),
        )
    
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(strategy_class, **strategy_params)
    
    # 设置初始资金
    cerebro.broker.setcash(initial_capital)
    
    # 设置手续费
    cerebro.broker.setcommission(commission=0.00025)  # 万2.5
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.03)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # 运行回测
    print(f"\n🔄 运行策略回测...")
    results = cerebro.run()
    strat = results[0]
    
    # 获取结果
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - initial_capital) / initial_capital * 100
    
    # 获取分析结果
    returns = strat.analyzers.returns.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    print(f"\n📈 策略表现:")
    print(f"   总收益率: {total_return:.2f}%")
    print(f"   年化收益率: {returns.get('rnorm100', 0):.2f}%")
    print(f"   夏普比率: {sharpe.get('sharperatio', 0):.3f}")
    print(f"   最大回撤: {-drawdown.get('max', {}).get('drawdown', 0):.2f}%")
    print(f"   交易次数: {trades.get('total', {}).get('total', 0) if trades else 0}")
    
    print(f"\n🏆 策略 vs 大盘对比:")
    outperformance = total_return - market_return
    print(f"   策略收益: {total_return:.2f}%")
    print(f"   大盘收益: {market_return:.2f}%")
    print(f"   超额收益: {outperformance:+.2f}%")
    
    return {
        'period': f"{start_date} 至 {end_date}",
        'market_return': market_return,
        'strategy_return': total_return,
        'outperformance': outperformance,
        'sharpe': sharpe.get('sharperatio', 0),
        'max_drawdown': -drawdown.get('max', {}).get('drawdown', 0),
        'trades': trades.get('total', {}).get('total', 0) if trades else 0
    }


if __name__ == "__main__":
    print("="*60)
    print("MA_CROSS 策略表现分析")
    print("最优参数: fast=5, slow=70")
    print("="*60)
    
    data_file = "A股_上证指数_20260201_144545.csv"
    
    strategy_params = {
        'fast_period': 5,
        'slow_period': 70,
        'atr_period': 14,
        'atr_multiplier': 2.0
    }
    
    results = []
    
    # 测试2025年全年
    result_2025 = run_backtest_for_period(
        data_file, 
        '2025-01-01', 
        '2025-12-31', 
        MACrossStrategy, 
        strategy_params
    )
    if result_2025:
        results.append(result_2025)
    
    # 测试最近3个月（2025年10-12月）
    result_recent = run_backtest_for_period(
        data_file,
        '2025-10-01',
        '2025-12-31',
        MACrossStrategy,
        strategy_params
    )
    if result_recent:
        results.append(result_recent)
    
    # 测试2024年（对比参考）
    result_2024 = run_backtest_for_period(
        data_file,
        '2024-01-01',
        '2024-12-31',
        MACrossStrategy,
        strategy_params
    )
    if result_2024:
        results.append(result_2024)
    
    # 总结
    print(f"\n{'='*60}")
    print("📋 总结对比")
    print(f"{'='*60}")
    for r in results:
        print(f"\n{r['period']}:")
        print(f"  策略收益: {r['strategy_return']:+.2f}% | 大盘收益: {r['market_return']:+.2f}% | 超额: {r['outperformance']:+.2f}%")
        print(f"  夏普比率: {r['sharpe']:.3f} | 最大回撤: {r['max_drawdown']:.2f}% | 交易次数: {r['trades']}")
