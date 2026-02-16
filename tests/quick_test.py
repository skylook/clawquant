"""
快速量化策略测试
使用模拟数据验证策略逻辑
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class QuickQuantTest:
    """快速量化测试"""
    
    def __init__(self):
        self.results = {}
    
    def create_mock_data(self, days=1000, start_price=100):
        """创建模拟数据"""
        print(f"创建 {days} 天的模拟数据...")
        
        dates = pd.date_range(start='2020-01-01', periods=days, freq='D')
        np.random.seed(42)
        
        # 模拟收益率
        returns = np.random.normal(0.0005, 0.015, days)
        
        # 生成价格序列
        price = start_price * np.exp(np.cumsum(returns))
        
        # 创建OHLCV数据
        data = pd.DataFrame({
            'Open': price * (1 + np.random.normal(0, 0.01, days)),
            'High': price * (1 + np.random.normal(0.02, 0.01, days)),
            'Low': price * (1 - np.random.normal(0.02, 0.01, days)),
            'Close': price,
            'Volume': np.random.lognormal(10, 1, days)
        }, index=dates)
        
        print(f"模拟数据创建完成: {len(data)} 条记录")
        print(f"价格范围: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
        
        return data
    
    def simple_ma_strategy(self, data, fast=20, slow=60):
        """简单的移动平均线策略"""
        print(f"\n运行MA策略: 快线={fast}, 慢线={slow}")
        
        df = data.copy()
        
        # 计算移动平均线
        df['MA_fast'] = df['Close'].rolling(window=fast).mean()
        df['MA_slow'] = df['Close'].rolling(window=slow).mean()
        
        # 生成信号
        df['Signal'] = 0
        df.loc[df['MA_fast'] > df['MA_slow'], 'Signal'] = 1
        df.loc[df['MA_fast'] < df['MA_slow'], 'Signal'] = -1
        
        # 计算持仓变化
        df['Position'] = df['Signal'].diff()
        
        # 计算收益率
        df['Returns'] = df['Close'].pct_change()
        df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
        
        # 移除NaN
        df = df.dropna()
        
        return df
    
    def calculate_performance(self, df):
        """计算绩效指标"""
        if len(df) == 0:
            return {}
        
        returns = df['Strategy_Returns']
        
        # 基本指标
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # 风险指标
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计
        trades = df[df['Position'] != 0]
        trade_count = len(trades)
        
        # 胜率（简化计算）
        if trade_count > 0:
            win_trades = 0
            for i in range(1, len(df)):
                if df.iloc[i-1]['Position'] > 0:  # 买入信号
                    if df.iloc[i]['Returns'] > 0:
                        win_trades += 1
            
            win_rate = win_trades / trade_count if trade_count > 0 else 0
        else:
            win_rate = 0
        
        performance = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'avg_daily_return': returns.mean(),
            'std_daily_return': returns.std(),
            'total_days': len(df)
        }
        
        return performance
    
    def run_optimization(self, data, param_grid):
        """运行参数优化"""
        print("\n开始参数优化...")
        
        best_score = -np.inf
        best_params = None
        best_perf = None
        
        results = []
        
        for fast in param_grid['fast_period']:
            for slow in param_grid['slow_period']:
                if fast >= slow:
                    continue
                
                try:
                    df = self.simple_ma_strategy(data, fast, slow)
                    perf = self.calculate_performance(df)
                    
                    if perf:
                        score = perf['sharpe_ratio']
                        results.append({
                            'fast': fast,
                            'slow': slow,
                            'sharpe': score,
                            'total_return': perf['total_return'],
                            'max_drawdown': perf['max_drawdown']
                        })
                        
                        if score > best_score:
                            best_score = score
                            best_params = {'fast_period': fast, 'slow_period': slow}
                            best_perf = perf
                            
                            print(f"  新最佳: fast={fast}, slow={slow}, 夏普={score:.3f}")
                
                except Exception as e:
                    print(f"  参数失败: fast={fast}, slow={slow}, 错误: {e}")
        
        # 按夏普比率排序
        results_df = pd.DataFrame(results)
        if not results_df.empty:
            results_df = results_df.sort_values('sharpe', ascending=False)
            print(f"\n优化结果 (前5名):")
            print(results_df.head(5).to_string(index=False))
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'best_performance': best_perf,
            'all_results': results
        }
    
    def run_test(self):
        """运行完整测试"""
        print("=" * 60)
        print("快速量化策略测试")
        print("=" * 60)
        
        # 1. 创建模拟数据
        data = self.create_mock_data(days=1000)
        
        # 2. 测试默认策略
        print("\n" + "-" * 40)
        print("测试默认策略 (20, 60)")
        print("-" * 40)
        df_default = self.simple_ma_strategy(data, 20, 60)
        perf_default = self.calculate_performance(df_default)
        
        print(f"默认策略绩效:")
        print(f"  总收益率: {perf_default.get('total_return', 0):.2%}")
        print(f"  夏普比率: {perf_default.get('sharpe_ratio', 0):.3f}")
        print(f"  最大回撤: {perf_default.get('max_drawdown', 0):.2%}")
        print(f"  交易次数: {perf_default.get('trade_count', 0)}")
        
        # 3. 参数优化
        print("\n" + "-" * 40)
        print("参数优化")
        print("-" * 40)
        param_grid = {
            'fast_period': [5, 10, 15, 20, 25, 30],
            'slow_period': [30, 40, 50, 60, 70, 80, 90, 100]
        }
        
        opt_result = self.run_optimization(data, param_grid)
        
        # 4. 测试优化策略
        if opt_result['best_params']:
            print("\n" + "-" * 40)
            print("测试优化策略")
            print("-" * 40)
            
            best_fast = opt_result['best_params']['fast_period']
            best_slow = opt_result['best_params']['slow_period']
            
            df_optimized = self.simple_ma_strategy(data, best_fast, best_slow)
            perf_optimized = self.calculate_performance(df_optimized)
            
            print(f"优化策略绩效:")
            print(f"  参数: fast={best_fast}, slow={best_slow}")
            print(f"  总收益率: {perf_optimized.get('total_return', 0):.2%}")
            print(f"  夏普比率: {perf_optimized.get('sharpe_ratio', 0):.3f}")
            print(f"  最大回撤: {perf_optimized.get('max_drawdown', 0):.2%}")
        
        # 保存结果
        self.results = {
            'default_performance': perf_default,
            'optimization_result': opt_result,
            'optimized_performance': perf_optimized if opt_result['best_params'] else None
        }
        
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
        
        metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
        metric_names = ['总收益率', '夏普比率', '最大回撤', '胜率']
        
        for metric, name in zip(metrics, metric_names):
            default_val = default.get(metric, 0)
            optimized_val = optimized.get(metric, 0) if optimized else 0
            
            if metric == 'max_drawdown':
                improvement = default_val - optimized_val
                sign = "+" if improvement > 0 else ""
            else:
                improvement = optimized_val - default_val
                sign = "+" if improvement > 0 else ""
            
            if metric in ['total_return', 'max_drawdown']:
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
            improvement = optimized.get('sharpe_ratio', 0) - default.get('sharpe_ratio', 0)
            print(f"  ✅ 优化策略表现更好，夏普比率提高了 {improvement:.3f}")
            
            if optimized.get('total_return', 0) > default.get('total_return', 0):
                ret_improvement = optimized.get('total_return', 0) - default.get('total_return', 0)
                print(f"  ✅ 总收益率提高了 {ret_improvement:.2%}")
        else:
            print("  ⚠️  优化效果不明显")
        
        if default.get('max_drawdown', 0) < -0.15:
            print("  ⚠️  最大回撤较大，建议加强风险控制")
        
        if default.get('trade_count', 0) < 20:
            print("  ⚠️  交易次数较少，策略可能不够活跃")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    print("开始快速量化策略测试...")
    tester = QuickQuantTest()
    results = tester.run_test()
    tester.generate_report()
    
    print("\n测试完成！")