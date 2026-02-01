#!/usr/bin/env python3
"""
MA策略测试脚本
验证移动平均线策略的基本功能
"""

import os
import sys
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入项目策略
try:
    from strategies.ma_strategy import MAStrategy
    from strategies.base_strategy import BaseStrategy
    print("✅ 成功导入项目策略")
except ImportError as e:
    print(f"⚠️  无法导入项目策略: {e}")
    print("使用简化版MA策略进行测试")

# 创建简化版MA策略用于测试
class SimpleMAStrategy(bt.Strategy):
    """简化版移动平均线策略"""
    
    params = (
        ('sma_period', 20),
        ('lma_period', 50),
    )
    
    def __init__(self):
        # 移动平均线
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.sma_period)
        self.lma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.lma_period)
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.sma, self.lma)
        
        # 跟踪订单
        self.order = None
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f'买入 @ {order.executed.price:.2f}')
            elif order.issell():
                logger.info(f'卖出 @ {order.executed.price:.2f}')
            
            self.bar_executed = len(self)
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f'订单取消/拒绝: {order.status}')
        
        self.order = None
    
    def next(self):
        # 如果有未完成订单，不执行新操作
        if self.order:
            return
        
        # 检查是否持有仓位
        if not self.position:
            # 金叉：短期均线上穿长期均线，买入
            if self.crossover > 0:
                logger.info(f'金叉信号: SMA{self.params.sma_period}上穿LMA{self.params.lma_period}')
                self.order = self.buy()
        
        else:
            # 死叉：短期均线下穿长期均线，卖出
            if self.crossover < 0:
                logger.info(f'死叉信号: SMA{self.params.sma_period}下穿LMA{self.params.lma_period}')
                self.order = self.sell()


def fetch_test_data(symbol='AAPL', period='6mo'):
    """获取测试数据"""
    print(f"📊 下载 {symbol} 数据 ({period})...")
    
    try:
        # 使用yfinance获取数据
        data = yf.download(symbol, period=period, progress=False)
        
        if data.empty:
            raise ValueError(f"无法获取 {symbol} 数据")
        
        print(f"✅ 成功获取 {len(data)} 条数据")
        print(f"数据范围: {data.index[0]} 到 {data.index[-1]}")
        print(f"数据列: {list(data.columns)}")
        
        return data
    except Exception as e:
        print(f"❌ 数据获取失败: {e}")
        # 创建模拟数据作为后备
        print("使用模拟数据进行测试...")
        return create_mock_data()


def create_mock_data():
    """创建模拟数据"""
    dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='D')
    n = len(dates)
    
    # 创建随机价格序列
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.0005, 0.02, n)
    prices = base_price * np.exp(np.cumsum(returns))
    
    # 添加一些趋势
    trend = np.linspace(0, 20, n)
    prices += trend
    
    # 创建DataFrame
    data = pd.DataFrame({
        'Open': prices * 0.99,
        'High': prices * 1.02,
        'Low': prices * 0.98,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, n)
    }, index=dates)
    
    print(f"📊 创建模拟数据: {len(data)} 条记录")
    return data


def run_backtest(data, strategy_class, strategy_params=None):
    """运行回测"""
    print("\n" + "="*60)
    print("开始回测")
    print("="*60)
    
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
    if strategy_params:
        cerebro.addstrategy(strategy_class, **strategy_params)
    else:
        cerebro.addstrategy(strategy_class)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.0)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # 运行回测
    print("运行回测中...")
    results = cerebro.run()
    
    # 获取策略实例
    strat = results[0]
    
    # 打印结果
    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    
    # 最终资金
    final_value = cerebro.broker.getvalue()
    initial_cash = 100000.0
    profit = final_value - initial_cash
    profit_pct = (profit / initial_cash) * 100
    
    print(f"初始资金: ${initial_cash:,.2f}")
    print(f"最终资金: ${final_value:,.2f}")
    print(f"总收益: ${profit:,.2f} ({profit_pct:.2f}%)")
    
    # 分析器结果
    returns_analyzer = strat.analyzers.returns.get_analysis()
    sharpe_analyzer = strat.analyzers.sharpe.get_analysis()
    drawdown_analyzer = strat.analyzers.drawdown.get_analysis()
    
    if 'rnorm100' in returns_analyzer:
        print(f"年化收益: {returns_analyzer['rnorm100']:.2f}%")
    
    if 'sharperatio' in sharpe_analyzer:
        print(f"夏普比率: {sharpe_analyzer['sharperatio']:.3f}")
    
    if 'max' in drawdown_analyzer:
        print(f"最大回撤: {drawdown_analyzer['max'].drawdown:.2f}%")
        print(f"最长回撤期: {drawdown_analyzer['max'].len} 天")
    
    # 交易统计
    trades_analyzer = strat.analyzers.trades.get_analysis()
    if trades_analyzer.total.total:
        print(f"\n交易统计:")
        print(f"总交易次数: {trades_analyzer.total.total}")
        print(f"盈利交易: {trades_analyzer.won.total}")
        print(f"亏损交易: {trades_analyzer.lost.total}")
        print(f"胜率: {(trades_analyzer.won.total/trades_analyzer.total.total)*100:.1f}%")
        
        if 'pnl' in trades_analyzer.total:
            print(f"平均每笔收益: ${trades_analyzer.total.pnl.average:.2f}")
    
    return {
        'final_value': final_value,
        'profit': profit,
        'profit_pct': profit_pct,
        'returns': returns_analyzer,
        'sharpe': sharpe_analyzer,
        'drawdown': drawdown_analyzer,
        'trades': trades_analyzer
    }


def test_parameter_combinations(data):
    """测试不同参数组合"""
    print("\n" + "="*60)
    print("参数优化测试")
    print("="*60)
    
    # 定义参数范围
    sma_periods = [10, 20, 30]
    lma_periods = [50, 60, 100]
    
    results = []
    
    for sma in sma_periods:
        for lma in lma_periods:
            if sma >= lma:
                continue  # 跳过无效组合
            
            print(f"\n测试参数: SMA={sma}, LMA={lma}")
            
            params = {
                'sma_period': sma,
                'lma_period': lma
            }
            
            try:
                result = run_backtest(data, SimpleMAStrategy, params)
                
                results.append({
                    'sma': sma,
                    'lma': lma,
                    'final_value': result['final_value'],
                    'profit_pct': result['profit_pct'],
                    'sharpe': result['sharpe'].get('sharperatio', 0) if result['sharpe'] else 0,
                    'max_drawdown': result['drawdown'].get('max', {}).get('drawdown', 0) if result['drawdown'] else 0
                })
                
            except Exception as e:
                print(f"❌ 参数组合测试失败: {e}")
    
    # 显示最佳结果
    if results:
        print("\n" + "="*60)
        print("参数优化结果汇总")
        print("="*60)
        
        # 按最终资金排序
        results_sorted = sorted(results, key=lambda x: x['final_value'], reverse=True)
        
        print("\n排名前3的参数组合:")
        for i, r in enumerate(results_sorted[:3], 1):
            print(f"{i}. SMA={r['sma']}, LMA={r['lma']}: "
                  f"最终资金=${r['final_value']:,.2f} "
                  f"(收益={r['profit_pct']:.2f}%, "
                  f"夏普={r['sharpe']:.3f}, "
                  f"最大回撤={r['max_drawdown']:.2f}%)")
    
    return results


def main():
    """主函数"""
    print("="*60)
    print("MA策略测试脚本")
    print("="*60)
    
    # 1. 获取数据
    data = fetch_test_data('AAPL', '6mo')
    
    # 2. 基本回测测试
    print("\n1. 基本MA策略回测 (SMA=20, LMA=50)")
    basic_params = {'sma_period': 20, 'lma_period': 50}
    basic_result = run_backtest(data, SimpleMAStrategy, basic_params)
    
    # 3. 参数优化测试
    print("\n2. 参数优化测试")
    optimization_results = test_parameter_combinations(data)
    
    # 4. 项目策略测试（如果可用）
    try:
        print("\n3. 测试项目MA策略")
        project_params = {
            'sma_period': 20,
            'lma_period': 60,
            'use_atr_stop': False,  # 简化测试
            'trend_filter': False
        }
        project_result = run_backtest(data, MAStrategy, project_params)
    except NameError:
        print("⚠️  项目策略不可用，跳过项目策略测试")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    # 保存结果
    output_dir = 'test_results'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = os.path.join(output_dir, f'test_summary_{timestamp}.txt')
    
    with open(summary_file, 'w') as f:
        f.write("MA策略测试总结\n")
        f.write("="*40 + "\n")
        f.write(f"测试时间: {datetime.now()}\n")
        f.write(f"数据范围: {data.index[0]} 到 {data.index[-1]}\n")
        f.write(f"数据条数: {len(data)}\n")
        f.write(f"基本策略收益: {basic_result['profit_pct']:.2f}%\n")
        
        if optimization_results:
            best = max(optimization_results, key=lambda x: x['final_value'])
            f.write(f"最佳参数组合: SMA={best['sma']}, LMA={best['lma']}\n")
            f.write(f"最佳收益: {best['profit_pct']:.2f}%\n")
    
    print(f"✅ 测试结果已保存到: {summary_file}")


if __name__ == "__main__":
    # 配置日志
    logger.remove()  # 移除默认处理器
    logger.add(sys.stderr, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    main()