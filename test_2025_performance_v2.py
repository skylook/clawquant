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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtrader as bt

class MACrossStrategy(bt.Strategy):
    params = (
        ('fast_period', 5),
        ('slow_period', 70),
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
    )
    
    def __init__(self):
        self.fast_ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.slow_period)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self.atr = bt.indicators.AverageTrueRange(self.data, period=self.params.atr_period)
        self.order = None
        self.stop_price = 0
        
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
        if self.position and self.stop_price > 0:
            if self.data.close[0] <= self.stop_price:
                self.order = self.sell()
                return
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.sell()
        if self.stop_price > 0:
            new_stop = self.data.close[0] - self.atr[0] * self.params.atr_multiplier
            if new_stop > self.stop_price:
                self.stop_price = new_stop


def run_backtest(data_file, start_date, end_date, strategy_params, name):
    df = pd.read_csv(data_file)
    df['date'] = pd.to_datetime(df['date'])
    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    df = df.sort_values('date')
    
    if len(df) == 0:
        print(f"❌ 无数据: {start_date} 至 {end_date}")
        return None
    
    first_close = df['close'].iloc[0]
    last_close = df['close'].iloc[-1]
    market_return = (last_close - first_close) / first_close * 100
    
    cerebro = bt.Cerebro()
    
    class PandasData(bt.feeds.PandasData):
        params = (('datetime', 'date'), ('open', 'open'), ('high', 'high'), 
                  ('low', 'low'), ('close', 'close'), ('volume', 'volume'),
                  ('openinterest', None))
    
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(MACrossStrategy, **strategy_params)
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(commission=0.00025)
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.03)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    results = cerebro.run()
    strat = results[0]
    
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - 100000) / 100000 * 100
    
    returns = strat.analyzers.returns.get_analysis()
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    sharpe_val = sharpe.get('sharperatio') or 0 if sharpe else 0
    max_dd = drawdown.get('max', {}).get('drawdown', 0) if drawdown and isinstance(drawdown.get('max'), dict) else 0
    trade_num = trades.get('total', {}).get('total', 0) if trades and isinstance(trades.get('total'), dict) else (trades.get('total', 0) if trades else 0)
    
    return {
        'name': name,
        'days': len(df),
        'market_return': market_return,
        'strategy_return': total_return,
        'outperformance': total_return - market_return,
        'sharpe': sharpe_val,
        'max_drawdown': max_dd,
        'trades': trade_num
    }


if __name__ == "__main__":
    print("="*65)
    print("   MA_CROSS 策略表现分析 (fast=5, slow=70)")
    print("="*65)
    
    data_file = "A股_上证指数_20260201_144545.csv"
    params = {'fast_period': 5, 'slow_period': 70, 'atr_period': 14, 'atr_multiplier': 2.0}
    
    periods = [
        ('2025-01-01', '2025-12-31', '2025年全年'),
        ('2025-10-01', '2025-12-31', '2025年Q4'),
        ('2024-01-01', '2024-12-31', '2024年对比'),
        ('2025-01-01', '2025-01-31', '2025年1月'),
        ('2025-12-01', '2025-12-31', '2025年12月'),
    ]
    
    results = []
    for start, end, name in periods:
        r = run_backtest(data_file, start, end, params, name)
        if r:
            results.append(r)
    
    print("\n" + "="*65)
    print("   回测结果汇总")
    print("="*65)
    print(f"\n{'时间段':<16} {'天数':>5} {'策略收益':>10} {'大盘收益':>10} {'超额':>8} {'夏普':>8} {'回撤%':>8} {'交易':>6}")
    print("-"*65)
    for r in results:
        print(f"{r['name']:<14} {r['days']:>5} {r['strategy_return']:>+9.2f}% {r['market_return']:>+9.2f}% {r['outperformance']:>+7.2f}% {r['sharpe']:>7.3f} {-r['max_drawdown']:>7.2f}% {r['trades']:>6}")
    
    print("\n" + "="*65)
    print("   关键发现")
    print("="*65)
    
    r2025 = next((r for r in results if r['name'] == '2025年全年'), None)
    if r2025:
        if r2025['outperformance'] < 0:
            print(f"\n⚠️ 2025年策略跑输大盘 {abs(r2025['outperformance']):.2f}%")
            print("   大盘强势上涨行情中，均线策略可能产生多次假信号")
        else:
            print(f"\n✅ 2025年策略跑赢大盘 {r2025['outperformance']:.2f}%")
