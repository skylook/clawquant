"""
简化版量化策略测试
用于验证系统基本功能
"""

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

class SimpleQuantTester:
    """简化版量化测试器"""
    
    def __init__(self):
        self.results = {}
        
    def fetch_data(self, symbol="000001.SS", start="2020-01-01", end="2024-01-01"):
        """获取数据"""
        print(f"获取数据: {symbol} ({start} 到 {end})")
        
        try:
            # 尝试获取上证指数数据
            data = yf.download(symbol, start=start, end=end)
            
            if data.empty:
                print("数据为空，尝试使用替代符号")
                # 尝试使用沪深300
                data = yf.download("510300.SS", start=start, end=end)
            
            print(f"获取到 {len(data)} 条数据")
            print(f"时间范围: {data.index[0]} 到 {data.index[-1]}")
            
            return data
        
        except Exception as e:
            print(f"数据获取失败: {e}")
            # 创建模拟数据
            print("创建模拟数据进行测试...")
            dates = pd.date_range(start=start, end=end, freq='D')
            np.random.seed(42)
            
            # 模拟价格数据
            returns = np.random.normal(0.0005, 0.015, len(dates))
            price = 100 * np.exp(np.cumsum(returns))
            
            data = pd.DataFrame({
                'Open': price * (1 + np.random.normal(0, 0.01, len(dates))),
                'High': price * (1 + np.random.normal(0.02, 0.01, len(dates))),
                'Low': price * (1 - np.random.normal(0.02, 0.01, len(dates))),
                'Close': price,
                'Volume': np.random.lognormal(10, 1, len(dates))
            }, index=dates)
            
            print(f"创建了 {len(data)} 条模拟数据")
            return data
    
    def calculate_indicators(self, data):
        """计算技术指标"""
        print("\n计算技术指标...")
        
        df = data.copy()
        
        # 移动平均线
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_60'] = df['Close'].rolling(window=60).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # 布林带
        df['BB_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        
        print("技术指标计算完成")
        return df
    
    def ma_strategy(self, df, fast_period=20, slow_period=60):
        """移动平均线策略"""
        print(f"\n运行MA策略 (快线={fast_period}, 慢线={slow_period})...")
        
        signals = pd.DataFrame(index=df.index)
        signals['price'] = df['Close']
        
        # 计算信号
        signals['fast_ma'] = df['Close'].rolling(window=fast_period).mean()
        signals['slow_ma'] = df['Close'].rolling(window=slow_period).mean()
        
        # 生成交易信号
        signals['position'] = 0
        signals['position'][fast_period:] = np.where(
            signals['fast_ma'][fast_period:] > signals['slow_ma'][fast_period:], 1, 0
        )
        
        # 计算持仓变化
        signals['signal'] = signals['position'].diff()
        
        # 计算收益率
        signals['returns'] = signals['price'].pct_change()
        signals['strategy_returns'] = signals['signal'].shift(1) * signals['returns']
        
        # 计算累计收益
        signals['cumulative_returns'] = (1 + signals['returns']).cumprod()
        signals['cumulative_strategy'] = (1 + signals['strategy_returns']).cumprod()
        
        return signals
    
    def analyze_performance(self, signals):
        """分析绩效"""
        print("\n分析策略绩效...")
        
        returns = signals['strategy_returns'].dropna()
        
        if len(returns) == 0:
            print("没有交易信号")
            return {}
        
        # 基本统计
        total_return = signals['cumulative_strategy'].iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # 风险调整收益
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计
        trades = signals[signals['signal'] != 0]
        buy_signals = trades[trades['signal'] > 0]
        sell_signals = trades[trades['signal'] < 0]
        
        # 胜率
        if len(buy_signals) > 0:
            # 简化计算：买入后下一期收益为正即为胜
            win_trades = 0
            for idx in buy_signals.index:
                if idx + 1 < len(signals):
                    if signals.loc[idx + 1, 'returns'] > 0:
                        win_trades += 1
            
            win_rate = win_trades / len(buy_signals) if len(buy_signals) > 0 else 0
        else:
            win_rate = 0
        
        performance = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'avg_return': returns.mean(),
            'std_return': returns.std()
        }
        
        print("绩效分析完成:")
        print(f"  总收益率: {total_return:.2%}")
        print(f"  年化收益率: {annual_return:.2%}")
        print(f"  夏普比率: {sharpe_ratio:.2f}")
        print(f"  最大回撤: {max_drawdown:.2%}")
        print(f"  胜率: {win_rate:.2%}")
        print(f"  总交易次数: {len(trades)}")
        
        return performance
    
    def optimize_parameters(self, df, param_grid):
        """参数优化"""
        print("\n开始参数优化...")
        
        best_score = -np.inf
        best_params = None
        best_performance = None
        
        # 简单的网格搜索
        for fast in param_grid.get('fast_period', [5, 10, 20, 30]):
            for slow in param_grid.get('slow_period', [20, 30, 60, 120]):
                if fast >= slow:
                    continue  # 快线必须小于慢线
                
                try:
                    signals = self.ma_strategy(df, fast, slow)
                    performance = self.analyze_performance(signals)
                    
                    # 使用夏普比率作为评分标准
                    score = performance.get('sharpe_ratio', 0)
                    
                    if score > best_score:
                        best_score = score
                        best_params = {'fast_period': fast, 'slow_period': slow}
                        best_performance = performance
                        
                        print(f"  新最佳参数: fast={fast}, slow={slow}, 夏普={score:.3f}")
                
                except Exception as e:
                    print(f"  参数组合失败: fast={fast}, slow={slow}, 错误: {e}")
        
        print(f"\n优化完成:")
        print(f"  最佳参数: {best_params}")
        print(f"  最佳夏普比率: {best_score:.3f}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'best_performance': best_performance
        }
    
    def run_test(self):
        """运行完整测试"""
        print("=" * 60)
        print("简化版量化策略测试")
        print("=" * 60)
        
        # 1. 获取数据
        data = self.fetch_data()
        
        # 2. 计算指标
        df = self.calculate_indicators(data)
        
        # 3. 运行默认策略
        print("\n" + "=" * 60)
        print("测试默认MA策略 (20, 60)")
        print("=" * 60)
        signals = self.ma_strategy(df)
        default_perf = self.analyze_performance(signals)
        
        # 4. 参数优化
        print("\n" + "=" * 60)
        print("参数优化")
        print("=" * 60)
        param_grid = {
            'fast_period': [5, 10, 20, 30, 40],
            'slow_period': [20, 30, 60, 90, 120]
        }
        optimization_result = self.optimize_parameters(df, param_grid)
        
        # 5. 运行优化后的策略
        print("\n" + "=" * 60)
        print("运行优化后的策略")
        print("=" * 60)
        if optimization_result['best_params']:
            best_fast = optimization_result['best_params']['fast_period']
            best_slow = optimization_result['best_params']['slow_period']
            
            print(f"使用最佳参数: fast={best_fast}, slow={best_slow}")
            optimized_signals = self.ma_strategy(df, best_fast, best_slow)
            optimized_perf = self.analyze_performance(optimized_signals)
        else:
            optimized_perf = None
        
        # 保存结果
        self.results = {
            'default_performance': default_perf,
            'optimization_result': optimization_result,
            'optimized_performance': optimized_perf
        }
        
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        
        return self.results
    
    def generate_report(self):
        """生成报告"""
        if not self.results:
            print("没有测试结果")
            return
        
        print("\n" + "=" * 60)
        print("量化策略测试报告")
        print("=" * 60)
        
        default = self.results.get('default_performance', {})
        optimized = self.results.get('optimized_performance', {})
        opt_result = self.results.get('optimization_result', {})
        
        print("\n📊 绩效对比:")
        print(f"{'指标':<15} {'默认策略':<12} {'优化策略':<12} {'改进':<10}")
        print("-" * 50)
        
        metrics = ['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
        metric_names = ['总收益率', '年化收益', '夏普比率', '最大回撤', '胜率']
        
        for metric, name in zip(metrics, metric_names):
            default_val = default.get(metric, 0)
            optimized_val = optimized.get(metric, 0) if optimized else 0
            
            if metric == 'max_drawdown':
                # 最大回撤越小越好
                improvement = default_val - optimized_val
                sign = "+" if improvement > 0 else ""
            else:
                # 其他指标越大越好
                improvement = optimized_val - default_val
                sign = "+" if improvement > 0 else ""
            
            if metric in ['total_return', 'annual_return', 'max_drawdown']:
                default_fmt = f"{default_val:.2%}"
                optimized_fmt = f"{optimized_val:.2%}" if optimized else "N/A"
                improvement_fmt = f"{sign}{improvement:.2%}"
            elif metric == 'sharpe_ratio':
                default_fmt = f"{default_val:.3f}"
                optimized_fmt = f"{optimized_val:.3f}" if optimized else "N/A"
                improvement_fmt = f"{sign}{improvement:.3f}"
            else:  # win_rate
                default_fmt = f"{default_val:.1%}"
                optimized_fmt = f"{optimized_val:.1%}" if optimized else "N/A"
                improvement_fmt = f"{sign}{improvement:.1%}"
            
            print(f"{name:<15} {default_fmt:<12} {optimized_fmt:<12} {improvement_fmt:<10}")
        
        if opt_result.get('best_params'):
            print(f"\n🔧 最佳参数配置:")
            for param, value in opt_result['best_params'].items():
                print(f"  {param}: {value}")
        
        print("\n💡 建议:")
        if optimized and optimized.get('sharpe_ratio', 0) > default.get('sharpe_ratio', 0):
            print("  ✅ 优化后的策略表现更好，建议使用优化参数")
        else:
            print("  ⚠️  优化效果不明显，可能需要调整参数范围或策略逻辑")
        
        if default.get('max_drawdown', 0) < -0.20:
            print("  ⚠️  最大回撤较大，建议加强风险控制")
        
        if default.get('total_trades', 0) < 10:
            print("  ⚠️  交易次数较少，策略可能不够活跃")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    # 运行测试
    tester = SimpleQuantTester()
    results = tester.run_test()
    
    # 生成报告
    tester.generate_report()