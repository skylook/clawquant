"""
多市场量化策略回测分析
分析MA策略在美股和港股的表现（2014-2024）
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class MultiMarketAnalyzer:
    """多市场分析器"""
    
    def __init__(self):
        self.data = {}
        self.results = {}
        
    def fetch_market_data(self):
        """获取市场数据"""
        print("=" * 70)
        print("开始获取多市场历史数据 (2014-2024)")
        print("=" * 70)
        
        market_configs = {
            '美股_标普500': {'symbol': '^GSPC', 'name': 'S&P 500'},
            '港股_恒生指数': {'symbol': '^HSI', 'name': 'Hang Seng Index'},
        }
        
        for market_key, config in market_configs.items():
            print(f"\n📥 获取 {config['name']} 数据...")
            
            try:
                # 获取10年数据
                data = yf.download(
                    config['symbol'],
                    start='2014-01-01',
                    end='2024-12-31',
                    progress=False
                )
                
                if not data.empty:
                    # 重命名列，使其更易读
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
                    self.data[market_key] = data
                    
                    print(f"✅ 成功获取 {len(data)} 条数据")
                    print(f"   时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
                    print(f"   价格范围: ${data['Close'].min():.2f} - ${data['Close'].max():.2f}")
                else:
                    print(f"❌ 数据为空")
                    
            except Exception as e:
                print(f"⚠️  获取失败: {e}")
        
        print(f"\n📊 总计获取 {len(self.data)} 个市场的数据")
        return self.data
    
    def ma_cross_strategy(self, data, fast_period=20, slow_period=60):
        """移动平均线交叉策略"""
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
        
        # 移除NaN
        df = df.dropna()
        
        return df
    
    def calculate_performance_metrics(self, strategy_df):
        """计算绩效指标"""
        if len(strategy_df) == 0:
            return {}
        
        returns = strategy_df['Strategy_Returns']
        
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
        
        # 索提诺比率（只考虑下行风险）
        downside_returns = returns[returns < 0]
        sortino_ratio = np.sqrt(252) * returns.mean() / downside_returns.std() if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
        
        # 交易统计
        trades = strategy_df[strategy_df['Position'] != 0]
        trade_count = len(trades)
        
        # 胜率计算
        if trade_count > 0:
            win_trades = 0
            for i in range(1, len(strategy_df)):
                if strategy_df.iloc[i-1]['Position'] > 0:  # 买入信号
                    if strategy_df.iloc[i]['Returns'] > 0:
                        win_trades += 1
            
            win_rate = win_trades / trade_count if trade_count > 0 else 0
        else:
            win_rate = 0
        
        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(252)
        
        # 卡玛比率（年化收益/最大回撤）
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        performance = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'avg_daily_return': returns.mean(),
            'std_daily_return': returns.std(),
            'annual_volatility': annual_volatility,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'total_days': len(strategy_df),
            'positive_days': (returns > 0).sum(),
            'negative_days': (returns < 0).sum()
        }
        
        return performance
    
    def analyze_by_year(self, market_key, data, fast_period=20, slow_period=60):
        """按年度分析"""
        print(f"\n📅 开始年度分析: {market_key}")
        
        yearly_results = {}
        
        # 按年分组
        for year in range(2014, 2025):
            year_data = data[data.index.year == year]
            
            if len(year_data) < 50:  # 至少需要50个交易日
                continue
            
            # 运行策略
            strategy_df = self.ma_cross_strategy(year_data, fast_period, slow_period)
            
            if len(strategy_df) > 0:
                # 计算绩效
                performance = self.calculate_performance_metrics(strategy_df)
                yearly_results[year] = {
                    'performance': performance,
                    'data_points': len(year_data),
                    'trade_count': performance.get('trade_count', 0)
                }
                
                print(f"   {year}: {len(year_data)}个交易日, "
                      f"收益={performance.get('total_return', 0):.2%}, "
                      f"交易次数={performance.get('trade_count', 0)}")
        
        return yearly_results
    
    def run_analysis(self):
        """运行完整分析"""
        print("\n" + "=" * 70)
        print("开始多市场量化策略分析")
        print("=" * 70)
        
        # 1. 获取数据
        self.fetch_market_data()
        
        if not self.data:
            print("❌ 无法获取数据，分析终止")
            return
        
        print("\n" + "=" * 70)
        print("策略回测分析")
        print("=" * 70)
        
        # 2. 对每个市场进行分析
        for market_key, data in self.data.items():
            print(f"\n🎯 分析市场: {market_key}")
            print("-" * 50)
            
            # 全时段分析
            full_strategy = self.ma_cross_strategy(data, 20, 60)
            full_performance = self.calculate_performance_metrics(full_strategy)
            
            print(f"📊 全时段绩效 (2014-2024):")
            print(f"   总收益率: {full_performance.get('total_return', 0):.2%}")
            print(f"   年化收益率: {full_performance.get('annual_return', 0):.2%}")
            print(f"   夏普比率: {full_performance.get('sharpe_ratio', 0):.3f}")
            print(f"   最大回撤: {full_performance.get('max_drawdown', 0):.2%}")
            print(f"   胜率: {full_performance.get('win_rate', 0):.2%}")
            print(f"   交易次数: {full_performance.get('trade_count', 0)}")
            
            # 年度分析
            yearly_results = self.analyze_by_year(market_key, data)
            
            # 保存结果
            self.results[market_key] = {
                'full_performance': full_performance,
                'yearly_results': yearly_results,
                'data_points': len(data)
            }
        
        # 3. 生成对比报告
        self.generate_comparison_report()
        
        return self.results
    
    def generate_comparison_report(self):
        """生成对比报告"""
        print("\n" + "=" * 70)
        print("多市场策略对比报告")
        print("=" * 70)
        
        if not self.results:
            print("没有分析结果")
            return
        
        print("\n📈 全时段绩效对比:")
        print(f"{'市场':<20} {'总收益率':<12} {'年化收益':<12} {'夏普比率':<12} {'最大回撤':<12} {'胜率':<10}")
        print("-" * 80)
        
        for market_key, result in self.results.items():
            perf = result['full_performance']
            
            print(f"{market_key:<20} "
                  f"{perf.get('total_return', 0):.2%}    "
                  f"{perf.get('annual_return', 0):.2%}    "
                  f"{perf.get('sharpe_ratio', 0):.3f}      "
                  f"{perf.get('max_drawdown', 0):.2%}      "
                  f"{perf.get('win_rate', 0):.2%}")
        
        print("\n📊 年度表现统计:")
        
        for market_key, result in self.results.items():
            yearly = result['yearly_results']
            
            if not yearly:
                continue
            
            print(f"\n{market_key} 年度表现:")
            
            # 计算各年度收益率
            yearly_returns = []
            for year, res in yearly.items():
                ret = res['performance'].get('total_return', 0)
                yearly_returns.append(ret)
                
                print(f"  {year}: {ret:.2%}")
            
            if yearly_returns:
                avg_return = np.mean(yearly_returns)
                std_return = np.std(yearly_returns)
                positive_years = sum(1 for r in yearly_returns if r > 0)
                total_years = len(yearly_returns)
                
                print(f"\n  统计:")
                print(f"    平均年收益: {avg_return:.2%}")
                print(f"    收益标准差: {std_return:.2%}")
                print(f"    盈利年份: {positive_years}/{total_years} ({positive_years/total_years:.1%})")
                
                # 计算最大连续盈利/亏损
                max_consecutive_win = 0
                max_consecutive_loss = 0
                current_win = 0
                current_loss = 0
                
                for ret in yearly_returns:
                    if ret > 0:
                        current_win += 1
                        current_loss = 0
                        max_consecutive_win = max(max_consecutive_win, current_win)
                    else:
                        current_loss += 1
                        current_win = 0
                        max_consecutive_loss = max(max_consecutive_loss, current_loss)
                
                print(f"    最长连续盈利: {max_consecutive_win}年")
                print(f"    最长连续亏损: {max_consecutive_loss}年")
        
        print("\n💡 分析结论:")
        
        # 总结各市场表现
        market_summary = {}
        for market_key, result in self.results.items():
            perf = result['full_performance']
            sharpe = perf.get('sharpe_ratio', 0)
            total_ret = perf.get('total_return', 0)
            
            market_summary[market_key] = {
                'sharpe': sharpe,
                'total_return': total_ret,
                'trade_count': perf.get('trade_count', 0)
            }
        
        # 找出表现最好的市场
        if market_summary:
            best_by_sharpe = max(market_summary.items(), key=lambda x: x[1]['sharpe'])
            best_by_return = max(market_summary.items(), key=lambda x: x[1]['total_return'])
            
            print(f"  1. 按夏普比率: {best_by_sharpe[0]} 表现最好 ({best_by_sharpe[1]['sharpe']:.3f})")
            print(f"  2. 按总收益率: {best_by_return[0]} 表现最好 ({best_by_return[1]['total_return']:.2%})")
            
            # 评估策略有效性
            for market_key, summary in market_summary.items():
                sharpe = summary['sharpe']
                
                if sharpe > 0.5:
                    print(f"  3. {market_key}: 策略有效 (夏普比率 > 0.5)")
                elif sharpe > 0:
                    print(f"  3. {market_key}: 策略表现一般 (夏普比率 > 0)")
                else:
                    print(f"  3. {market_key}: 策略表现不佳 (夏普比率 ≤ 0)")
            
            print(f"\n🎯 建议:")
            print(f"  1. 对于表现好的市场，可考虑增加仓位或优化参数")
            print(f"  2. 对于表现不佳的市场，需要调整策略或考虑其他策略类型")
            print(f"  3. 考虑市场特性调整参数 (如A股可能需要不同的参数范围)")
        
        print("\n" + "=" * 70)
        print("分析完成!")
        print("=" * 70)


def main():
    """主函数"""
    print("开始多市场量化策略分析...")
    
    analyzer = MultiMarketAnalyzer()
    results = analyzer.run_analysis()
    
    # 保存结果到文件
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'multi_market_analysis_{timestamp}.txt'
        
        with open(output_file, 'w') as f:
            f.write("多市场量化策略分析报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for market_key, result in results.items():
                f.write(f"市场: {market_key}\n")
                f.write(f"数据点数: {result['data_points']}\n")
                
                perf = result['full_performance']
                f.write(f"全时段总收益率: {perf.get('total_return', 0):.2%}\n")
                f.write(f"夏普比率: {perf.get('sharpe_ratio', 0):.3f}\n")
                f.write(f"最大回撤: {perf.get('max_drawdown', 0):.2%}\n")
                f.write(f"交易次数: {perf.get('trade_count', 0)}\n\n")
        
        print(f"\n📁 详细报告已保存到: {output_file}")


if __name__ == "__main__":
    main()