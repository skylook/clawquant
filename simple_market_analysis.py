"""
简化版三大市场量化分析
基于模拟数据的A股、美股、港股10年回测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class SimpleMarketAnalysis:
    """简化版市场分析"""
    
    def __init__(self):
        self.results = {}
    
    def create_simulated_markets(self):
        """创建三大市场模拟数据"""
        print("=" * 60)
        print("创建三大市场10年模拟数据 (2014-2024)")
        print("=" * 60)
        
        markets = {
            'A股_上证指数': {'base': 2000, 'drift': 0.0004, 'vol': 0.018},
            '美股_标普500': {'base': 1800, 'drift': 0.0006, 'vol': 0.012},
            '港股_恒生指数': {'base': 23000, 'drift': 0.0003, 'vol': 0.015}
        }
        
        market_data = {}
        
        for name, params in markets.items():
            print(f"\n📊 创建 {name} 数据...")
            
            # 生成交易日
            dates = pd.date_range('2014-01-01', '2024-12-31', freq='B')
            n = len(dates)
            
            np.random.seed(42)
            
            # 基础收益率
            returns = np.random.normal(params['drift'], params['vol'], n)
            
            # 市场特定调整
            if 'A股' in name:
                # A股：高波动，政策市特征
                for i in range(n):
                    if dates[i].year == 2015:  # 2015年牛市
                        returns[i] += 0.0015
                    elif dates[i].year == 2016:  # 2016年调整
                        returns[i] -= 0.001
                    elif dates[i].year == 2018:  # 2018年贸易战
                        returns[i] -= 0.0008
                    elif dates[i].year >= 2020:  # 近年波动
                        returns[i] += np.random.normal(0, 0.002)
            
            elif '美股' in name:
                # 美股：长期牛市
                for i in range(n):
                    if dates[i].year == 2020 and dates[i].month == 3:
                        returns[i] -= 0.025  # 2020年3月疫情冲击
                    elif dates[i].year >= 2020 and dates[i].month > 3:
                        returns[i] += 0.001  # 疫情后复苏
            
            elif '港股' in name:
                # 港股：受双重影响
                for i in range(n):
                    if dates[i].year >= 2019:
                        returns[i] += np.random.normal(0, 0.0015)
            
            # 价格序列
            price = params['base'] * np.exp(np.cumsum(returns))
            
            # 创建DataFrame
            data = pd.DataFrame({
                'Close': price,
                'Open': price * (1 + np.random.normal(0, 0.005, n)),
                'High': price * (1 + np.random.normal(0.01, 0.005, n)),
                'Low': price * (1 - np.random.normal(0.01, 0.005, n)),
                'Volume': np.random.lognormal(14, 1, n) * 1000
            }, index=dates)
            
            market_data[name] = data
            
            # 计算统计
            total_return = (price[-1] / price[0] - 1)
            annual_vol = data['Close'].pct_change().std() * np.sqrt(252)
            
            print(f"✅ 数据创建完成: {len(data)} 条")
            print(f"   价格范围: {price.min():.2f} - {price.max():.2f}")
            print(f"   总收益率: {total_return:.2%}")
            print(f"   年化波动率: {annual_vol:.2%}")
        
        return market_data
    
    def ma_strategy(self, data, fast=20, slow=60):
        """MA交叉策略"""
        df = data.copy()
        
        # 计算均线
        df['MA_fast'] = df['Close'].rolling(fast).mean()
        df['MA_slow'] = df['Close'].rolling(slow).mean()
        
        # 信号
        df['Signal'] = 0
        df.loc[df['MA_fast'] > df['MA_slow'], 'Signal'] = 1
        df.loc[df['MA_fast'] < df['MA_slow'], 'Signal'] = -1
        
        # 持仓变化
        df['Position'] = df['Signal'].diff()
        
        # 收益率
        df['Returns'] = df['Close'].pct_change()
        df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
        
        # 交易成本
        trade_days = df['Position'].abs() > 0
        df.loc[trade_days, 'Strategy_Returns'] -= 0.001  # 0.1%手续费
        
        return df.dropna()
    
    def calculate_performance(self, strategy_df):
        """计算绩效"""
        if len(strategy_df) == 0:
            return {}
        
        returns = strategy_df['Strategy_Returns']
        
        # 基本指标
        total_return = (1 + returns).prod() - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # 风险指标
        sharpe = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        # 交易统计
        trades = strategy_df[strategy_df['Position'] != 0]
        trade_count = len(trades)
        
        # 胜率
        if trade_count > 0:
            wins = 0
            for i in range(1, len(strategy_df)):
                if strategy_df.iloc[i-1]['Position'] != 0:
                    if strategy_df.iloc[i]['Returns'] > 0:
                        wins += 1
            win_rate = wins / trade_count
        else:
            win_rate = 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'volatility': returns.std() * np.sqrt(252)
        }
    
    def analyze_by_year(self, market_name, data):
        """年度分析"""
        yearly_results = {}
        
        for year in range(2014, 2025):
            year_data = data[data.index.year == year]
            
            if len(year_data) < 50:
                continue
            
            strategy_df = self.ma_strategy(year_data)
            perf = self.calculate_performance(strategy_df)
            
            yearly_results[year] = {
                'performance': perf,
                'data_points': len(year_data),
                'market_return': (year_data['Close'].iloc[-1] / year_data['Close'].iloc[0] - 1)
            }
        
        return yearly_results
    
    def run_analysis(self):
        """运行分析"""
        print("\n" + "=" * 60)
        print("开始三大市场量化策略分析")
        print("=" * 60)
        
        # 1. 创建数据
        market_data = self.create_simulated_markets()
        
        # 2. 分析每个市场
        for market_name, data in market_data.items():
            print(f"\n🎯 分析: {market_name}")
            print("-" * 50)
            
            # 全时段
            strategy_df = self.ma_strategy(data)
            perf = self.calculate_performance(strategy_df)
            
            print(f"📊 全时段绩效:")
            print(f"   总收益率: {perf['total_return']:.2%}")
            print(f"   年化收益: {perf['annual_return']:.2%}")
            print(f"   夏普比率: {perf['sharpe_ratio']:.3f}")
            print(f"   最大回撤: {perf['max_drawdown']:.2%}")
            print(f"   胜率: {perf['win_rate']:.2%}")
            print(f"   交易次数: {perf['trade_count']}")
            
            # 年度分析
            yearly = self.analyze_by_year(market_name, data)
            
            # 保存结果
            self.results[market_name] = {
                'full_performance': perf,
                'yearly_results': yearly,
                'data_info': {
                    'points': len(data),
                    'price_range': (data['Close'].min(), data['Close'].max()),
                    'market_return': (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1)
                }
            }
        
        # 3. 生成报告
        self.generate_report()
        
        return self.results
    
    def generate_report(self):
        """生成报告"""
        print("\n" + "=" * 60)
        print("三大市场量化策略分析报告")
        print("=" * 60)
        
        if not self.results:
            print("没有分析结果")
            return
        
        print("\n📈 全时段绩效对比:")
        print(f"{'市场':<20} {'总收益':<10} {'年化':<10} {'夏普':<10} {'最大回撤':<12} {'胜率':<8}")
        print("-" * 80)
        
        for market, result in self.results.items():
            perf = result['full_performance']
            print(f"{market:<20} "
                  f"{perf['total_return']:>7.2%}  "
                  f"{perf['annual_return']:>7.2%}  "
                  f"{perf['sharpe_ratio']:>7.3f}  "
                  f"{perf['max_drawdown']:>9.2%}  "
                  f"{perf['win_rate']:>6.1%}")
        
        print("\n📊 策略有效性评估:")
        
        for market, result in self.results.items():
            perf = result['full_performance']
            sharpe = perf['sharpe_ratio']
            
            if sharpe > 0.7:
                rating = "优秀"
                suggestion = "适合实盘应用"
            elif sharpe > 0.4:
                rating = "良好"
                suggestion = "可进一步优化"
            elif sharpe > 0.1:
                rating = "一般"
                suggestion = "需要改进"
            else:
                rating = "不佳"
                suggestion = "建议放弃或重新设计"
            
            print(f"\n{market}:")
            print(f"  评级: {rating} (夏普: {sharpe:.3f})")
            print(f"  建议: {suggestion}")
            
            # 年度表现总结
            yearly = result['yearly_results']
            if yearly:
                profitable_years = sum(1 for y in yearly.values() if y['performance']['total_return'] > 0)
                total_years = len(yearly)
                print(f"  盈利年份: {profitable_years}/{total_years} ({profitable_years/total_years:.0%})")
        
        print("\n💡 关键发现:")
        print("  1. MA策略在不同市场表现差异显著")
        print("  2. 市场特性影响策略参数有效性")
        print("  3. 需要考虑交易成本和市场摩擦")
        print("  4. 年度分析显示策略稳定性重要")
        
        print("\n🎯 后续建议:")
        print("  1. 获取真实数据进行验证")
        print("  2. 测试更多策略类型 (MACD, RSI等)")
        print("  3. 进行参数优化和稳健性测试")
        print("  4. 考虑多策略组合降低风险")
        
        print("\n" + "=" * 60)
        print("分析完成!")
        print("=" * 60)


def main():
    """主函数"""
    print("开始三大市场量化策略分析...")
    
    analyzer = SimpleMarketAnalysis()
    results = analyzer.run_analysis()
    
    # 保存结果
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'analysis_report_{timestamp}.txt', 'w') as f:
            f.write("三大市场量化分析报告\n")
            f.write("=" * 50 + "\n\n")
            
            for market, result in results.items():
                f.write(f"{market}\n")
                f.write(f"总收益率: {result['full_performance']['total_return']:.2%}\n")
                f.write(f"夏普比率: {result['full_performance']['sharpe_ratio']:.3f}\n")
                f.write(f"最大回撤: {result['full_performance']['max_drawdown']:.2%}\n\n")
        
        print(f"\n📁 报告已保存")


if __name__ == "__main__":
    main()