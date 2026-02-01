"""
基于真实A股数据的量化分析
使用上证指数1990-2026年真实数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class RealDataAnalysis:
    """真实数据分析"""
    
    def __init__(self):
        self.data = None
        self.results = {}
    
    def load_real_data(self):
        """加载真实A股数据"""
        print("=" * 60)
        print("加载真实A股数据 (上证指数 1990-2026)")
        print("=" * 60)
        
        try:
            # 尝试从缓存加载
            cache_file = "./real_data_cache/A股_上证指数_20260201_144802.csv"
            
            print(f"从缓存加载数据: {cache_file}")
            data = pd.read_csv(cache_file, index_col='Date', parse_dates=True)
            
            if data.empty:
                print("❌ 缓存数据为空")
                return None
            
            print(f"✅ 成功加载真实数据: {len(data)} 条")
            print(f"   时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
            print(f"   列名: {list(data.columns)}")
            
            # 确保有标准列名

            if 'Close' not in data.columns and 'close' in data.columns:
                data.rename(columns={'close': 'Close'}, inplace=True)
            
            self.data = data
            return data
            
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return None
    
    def prepare_data_for_analysis(self, start_year=2014, end_year=2024):
        """准备分析数据（2014-2024）"""
        if self.data is None:
            print("❌ 没有数据可供分析")
            return None
        
        print(f"\n📅 准备分析数据: {start_year}年 - {end_year}年")
        
        # 筛选时间范围

        mask = (self.data.index.year >= start_year) & (self.data.index.year <= end_year)
        analysis_data = self.data[mask].copy()
        
        if len(analysis_data) == 0:
            print(f"❌ 在 {start_year}-{end_year} 范围内没有数据")
            return None
        
        print(f"✅ 分析数据: {len(analysis_data)} 条")
        print(f"   时间范围: {analysis_data.index[0].date()} 到 {analysis_data.index[-1].date()}")
        
        # 计算基础统计

        total_return = (analysis_data['Close'].iloc[-1] / analysis_data['Close'].iloc[0] - 1)
        annual_return = (1 + total_return) ** (252 / len(analysis_data)) - 1
        volatility = analysis_data['Close'].pct_change().std() * np.sqrt(252)
        
        print(f"   总收益率: {total_return:.2%}")
        print(f"   年化收益: {annual_return:.2%}")
        print(f"   年化波动: {volatility:.2%}")
        
        return analysis_data
    
    def ma_strategy(self, data, fast_period=20, slow_period=60, commission=0.001):
        """MA交叉策略"""
        df = data.copy()
        
        # 计算移动平均线

        df['MA_fast'] = df['Close'].rolling(window=fast_period).mean()
        df['MA_slow'] = df['Close'].rolling(window=slow_period).mean()
        
        # 生成交易信号

        df['Signal'] = 0
        df.loc[df['MA_fast'] > df['MA_slow'], 'Signal'] = 1
        df.loc[df['MA_fast'] < df['MA_slow'], 'Signal'] = -1
        
        # 计算持仓变化

        df['Position'] = df['Signal'].diff()
        
        # 计算收益率

        df['Returns'] = df['Close'].pct_change()
        df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
        
        # 应用交易成本

        trade_days = df['Position'].abs() > 0
        df.loc[trade_days, 'Strategy_Returns'] -= commission
        
        # 移除NaN

        df = df.dropna()
        
        return df
    
    def calculate_performance(self, strategy_df):
        """计算绩效指标"""
        if len(strategy_df) == 0:
            return {}
        
        returns = strategy_df['Strategy_Returns']
        
        # 基本收益指标

        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # 风险指标

        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # 最大回撤

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计

        trades = strategy_df[strategy_df['Position'] != 0]
        trade_count = len(trades)
        
        # 胜率计算

        if trade_count > 0:
            win_trades = 0
            for i in range(1, len(strategy_df)):
                if strategy_df.iloc[i-1]['Position'] != 0:
                    if strategy_df.iloc[i]['Returns'] > 0:
                        win_trades += 1
            win_rate = win_trades / trade_count
        else:
            win_rate = 0
        
        # 其他指标

        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        avg_daily_return = returns.mean()
        std_daily_return = returns.std()
        
        performance = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'volatility': volatility,
            'positive_days': positive_days,
            'negative_days': negative_days,
            'avg_daily_return': avg_daily_return,
            'std_daily_return': std_daily_return,
            'total_days': len(strategy_df)
        }
        
        return performance
    
    def analyze_by_year(self, data):
        """按年度分析"""
        print("\n📅 开始年度详细分析")
        print("-" * 50)
        
        yearly_results = {}
        
        for year in range(2014, 2025):
            year_data = data[data.index.year == year]
            
            if len(year_data) < 50:
                continue
            
            # 运行策略

            strategy_df = self.ma_strategy(year_data, 20, 60)
            
            if len(strategy_df) > 0:
                # 计算绩效

                performance = self.calculate_performance(strategy_df)
                
                # 市场表现

                market_return = (year_data['Close'].iloc[-1] / year_data['Close'].iloc[0] - 1)
                
                yearly_results[year] = {
                    'performance': performance,
                    'market_return': market_return,
                    'data_points': len(year_data),
                    'avg_price': year_data['Close'].mean()
                }
                
                print(f"{year}: "
                      f"策略收益={performance.get('total_return', 0):.2%}, "
                      f"市场收益={market_return:.2%}, "
                      f"交易次数={performance.get('trade_count', 0)}")
        
        return yearly_results
    
    def optimize_parameters(self, data):
        """参数优化"""
        print("\n🔧 开始参数优化")
        print("-" * 50)
        
        param_grid = {
            'fast_period': [5, 10, 15, 20, 25, 30],
            'slow_period': [30, 40, 50, 60, 70, 80, 90, 100]
        }
        
        best_score = -np.inf
        best_params = None
        best_performance = None
        
        results = []
        
        for fast in param_grid['fast_period']:
            for slow in param_grid['slow_period']:
                if fast >= slow:
                    continue
                
                try:
                    # 运行策略

                    strategy_df = self.ma_strategy(data, fast, slow)
                    performance = self.calculate_performance(strategy_df)
                    
                    if performance:
                        score = performance['sharpe_ratio']
                        results.append({
                            'fast': fast,
                            'slow': slow,
                            'sharpe': score,
                            'total_return': performance['total_return'],
                            'max_drawdown': performance['max_drawdown'],
                            'trade_count': performance['trade_count']
                        })
                        
                        if score > best_score:
                            best_score = score
                            best_params = {'fast_period': fast, 'slow_period': slow}
                            best_performance = performance
                            
                            print(f"  新最佳: fast={fast}, slow={slow}, 夏普={score:.3f}")
                
                except Exception as e:
                    print(f"  参数组合失败: fast={fast}, slow={slow}, 错误: {e}")
        
        # 显示优化结果

        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('sharpe', ascending=False)
            
            print(f"\n优化结果 (前5名):")
            print(results_df.head(5).to_string(index=False))
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'best_performance': best_performance,
            'all_results': results
        }
    
    def run_analysis(self):
        """运行完整分析"""
        print("\n" + "=" * 60)
        print("开始基于真实A股数据的量化分析")
        print("=" * 60)
        
        # 1. 加载真实数据

        data = self.load_real_data()
        if data is None:
            print("❌ 无法加载数据，分析终止")
            return
        
        # 2. 准备分析数据 (2014-2024)

        analysis_data = self.prepare_data_for_analysis(2014, 2024)
        if analysis_data is None:
            return
        
        print("\n" + "=" * 60)
        print("MA策略回测分析")
        print("=" * 60)
        
        # 3. 默认策略分析

        print("\n🔹 默认策略 (MA20, MA60):")
        default_strategy = self.ma_strategy(analysis_data, 20, 60)
        default_performance = self.calculate_performance(default_strategy)
        
        print(f"   总收益率: {default_performance.get('total_return', 0):.2%}")
        print(f"   年化收益: {default_performance.get('annual_return', 0):.2%}")
        print(f"   夏普比率: {default_performance.get('sharpe_ratio', 0):.3f}")
        print(f"   最大回撤: {default_performance.get('max_drawdown', 0):.2%}")
        print(f"   胜率: {default_performance.get('win_rate', 0):.2%}")
        print(f"   交易次数: {default_performance.get('trade_count', 0)}")
        
        # 4. 参数优化

        print("\n🔹 参数优化:")
        optimization_result = self.optimize_parameters(analysis_data)
        
        # 5. 优化策略分析

        if optimization_result['best_params']:
            print(f"\n🔹 优化策略:")
            best_fast = optimization_result['best_params']['fast_period']
            best_slow = optimization_result['best_params']['slow_period']
            
            optimized_strategy = self.ma_strategy(analysis_data, best_fast, best_slow)
            optimized_performance = self.calculate_performance(optimized_strategy)
            
            print(f"   最佳参数: fast={best_fast}, slow={best_slow}")
            print(f"   总收益率: {optimized_performance.get('total_return', 0):.2%}")
            print(f"   夏普比率: {optimized_performance.get('sharpe_ratio', 0):.3f}")
            print(f"   最大回撤: {optimized_performance.get('max_drawdown', 0):.2%}")
        
        # 6. 年度分析

        yearly_results = self.analyze_by_year(analysis_data)
        
        # 保存结果

        self.results = {
            'default_performance': default_performance,
            'optimization_result': optimization_result,
            'optimized_performance': optimized_performance if optimization_result['best_params'] else None,
            'yearly_results': yearly_results,
            'data_info': {
                'total_points': len(data),
                'analysis_points': len(analysis_data),
                'time_range': (analysis_data.index[0].date(), analysis_data.index[-1].date())
            }
        }
        
        # 生成报告

        self.generate_report()
        
        return self.results
    
    def generate_report(self):
        """生成分析报告"""
        print("\n" + "=" * 60)
        print("真实A股数据量化分析报告")
        print("=" * 60)
        
        if not self.results:
            print("没有分析结果")
            return
        
        default = self.results.get('default_performance', {})
        optimized = self.results.get('optimized_performance', {})
        opt_result = self.results.get('optimization_result', {})
        
        print("\n📊 策略绩效对比:")
        print(f"{'指标':<15} {'默认策略':<12} {'优化策略':<12} {'改进':<10}")
        print("-" * 60)
        
        metrics = ['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
        metric_names = ['总收益率', '年化收益', '夏普比率', '最大回撤', '胜率']
        
        for metric, name in zip(metrics, metric_names):
            default_val = default.get(metric, 0)
            optimized_val = optimized.get(metric, 0) if optimized else 0
            
            if metric == 'max_drawdown':
                improvement = default_val - optimized_val
                sign = "+" if improvement > 0 else ""
            else:
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
            else:
                default_fmt = f"{default_val:.1%}"
                optimized_fmt = f"{optimized_val:.1%}" if optimized else "N/A"
                improvement_fmt = f"{sign}{improvement:.1%}"
            
            print(f"{name:<15} {default_fmt:<12} {optimized_fmt:<12} {improvement_fmt:<10}")
        
        if opt_result.get('best_params'):
            print(f"\n🔧 最佳参数配置:")
            for param, value in opt_result['best_params'].items():
                print(f"  {param}: {value}")
        
        # 年度表现总结

        yearly = self.results.get('yearly_results', {})
        if yearly:
            print(f"\n📅 年度表现统计:")
            
            profitable_years = sum(1 for y in yearly.values() if y['performance']['total_return'] > 0)
            total_years = len(yearly)
            
            print(f"  盈利年份: {profitable_years}/{total_years} ({profitable_years/total_years:.0%})")
            
            # 计算年度收益率

            yearly_returns = [y['performance']['total_return'] for y in yearly.values()]
            if yearly_returns:
                avg_return = np.mean(yearly_returns)
                std_return = np.std(yearly_returns)
                print(f"  平均年收益: {avg_return:.2%}")
                print(f"  年收益波动: {std_return:.2%}")
        
        print("\n💡 策略有效性评估:")
        
        sharpe_default = default.get('sharpe_ratio', 0)
        sharpe_optimized = optimized.get('sharpe_ratio', 0) if optimized else 0
        
        if sharpe_optimized > 0.5:
            print("  ✅ 优化策略表现良好，适合进一步测试")
        elif sharpe_optimized > 0.2:
            print("  ⚠️  优化策略表现一般，需要改进")
        else:
            print("  ❌ 策略表现不佳，建议重新设计")
        
        if default.get('max_drawdown', 0) < -0.20:
            print("  ⚠️  最大回撤较大，需要加强风险控制")
        
        print("\n🎯 建议:")
        print("  1. 基于优化参数进行更深入的回测")
        print("  2. 添加止损止盈等风险控制机制")
        print("  3. 测试其他策略类型 (MACD, RSI等)")
        print("  4. 考虑市场状态调整策略参数")
        
        print("\n" + "=" * 60)
        print("分析完成!")
        print("=" * 60)


def main():
    """主函数"""
    print("开始基于真实A股数据的量化分析...")
    
    analyzer = RealDataAnalysis()
    results = analyzer.run_analysis()
    
    # 保存详细报告

    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f'real_data_analysis_report_{timestamp}.txt'
        
        with open(report_file, 'w') as f:
            f.write("真实A股数据量化分析报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"数据范围: 2014-2024\n")
            f.write(f"数据来源: akshare (上证指数)\n\n")
            
            default = results.get('default_performance', {})
            optimized = results.get('optimized_performance', {})
            
            f.write("策略绩效:\n")
            f.write(f"  默认策略 (MA20, MA60):\n")
            f.write(f"    总收益率: {default.get('total_return', 0):.2%}\n")
            f.write(f"    夏普比率: {default.get('sharpe_ratio', 0):.3f}\n")
            f.write(f"    最大回撤: {default.get('max_drawdown', 0):.2%}\n")
            f.write(f"    交易次数: {default.get('trade_count', 0)}\n\n")
            
            if optimized:
                f.write(f"  优化策略:\n")
                f.write(f"    总收益率: {optimized.get('total_return', 0):.2%}\n")
                f.write(f"    夏普比率: {optimized.get('sharpe_ratio', 0):.3f}\n")
                f.write(f"    最大回撤: {optimized.get('max_drawdown', 0):.2%}\n")
            
            opt_result = results.get('optimization_result', {})
            if opt_result.get('best_params'):
                f.write(f"\n最佳参数:\n")
                for param, value in opt_result['best_params'].items():
                    f.write(f"  {param}: {value}\n")
        
        print(f"\n📁 详细报告已保存到: {report_file}")


if __name__ == "__main__":
    main()