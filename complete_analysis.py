"""
完整的量化策略分析框架
包括A股、美股、港股10年回测分析
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class CompleteQuantAnalysis:
    """完整的量化分析"""
    
    def __init__(self):
        self.market_data = {}
        self.results = {}
        
    def create_market_data(self):
        """创建三大市场模拟数据"""
        print("=" * 70)
        print("创建三大市场10年历史数据 (2014-2024)")
        print("=" * 70)
        
        market_configs = {
            'A股_上证指数': {
                'base_price': 2000,      # 2014年初上证指数约2000点
                'drift': 0.0004,         # 长期年化约10%
                'volatility': 0.018,     # A股波动较大
                'volume_base': 2e9       # 成交额基础
            },
            '美股_标普500': {
                'base_price': 1800,      # 2014年初标普500约1800点
                'drift': 0.0006,         # 长期年化约15%
                'volatility': 0.012,
                'volume_base': 3e9
            },
            '港股_恒生指数': {
                'base_price': 23000,     # 2014年初恒生指数约23000点
                'drift': 0.0003,         # 长期年化约7.5%
                'volatility': 0.015,
                'volume_base': 1.5e9
            }
        }
        
        for market_key, config in market_configs.items():
            print(f"\n📊 创建 {market_key} 数据...")
            
            # 生成交易日序列 (2014-2024)
            dates = pd.date_range(start='2014-01-01', end='2024-12-31', freq='B')
            n_days = len(dates)
            
            np.random.seed(42)  # 可重复性
            
            # 基础收益率序列
            returns = np.random.normal(config['drift'], config['volatility'], n_days)
            
            # 添加市场特定特征
            if 'A股' in market_key:
                # A股特征：高波动，政策影响
                returns += np.random.normal(0, 0.003, n_days)
                # 2015年牛市和2016年股灾
                for i in range(n_days):
                    if dates[i].year == 2015:
                        returns[i] += 0.001
                    elif dates[i].year == 2016:
                        returns[i] -= 0.0005
                        
            elif '美股' in market_key:
                # 美股特征：长期上涨，低波动
                # 2020年疫情冲击
                for i in range(n_days):
                    if dates[i].year == 2020 and dates[i].month == 3:
                        returns[i] -= 0.02
                    elif dates[i].year == 2020 and dates[i].month >= 4:
                        returns[i] += 0.001
            
            elif '港股' in market_key:
                # 港股特征：受A股和美股双重影响
                for i in range(n_days):
                    if dates[i].year >= 2019:
                        # 近年波动增加
                        returns[i] += np.random.normal(0, 0.002)
            
            # 生成价格序列
            price = config['base_price'] * np.exp(np.cumsum(returns))
            
            # 创建OHLCV数据
data = pd.DataFrame({
                'Open': price * (1 + np.random.normal(0, 0.004, n_days)),
                'High': price * (1 + np.random.normal(0.008, 0.004, n_days)),
                'Low': price * (1 - np.random.normal(0.008, 0.004, n_days)),
                'Close': price,
                'Volume': np.random.lognormal(
                    np.log(config['volume_base']), 
                    0.8, 
                    n_days
                )
            }, index=dates)
            
            # 添加Adj Close
            data['Adj Close'] = data['Close']
            
            # 保存数据
            self.market_data[market_key] = data
            
            print(f"✅ 创建完成: {len(data)} 条数据")
            print(f"   时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
            print(f"   价格范围: {data['Close'].min():.2f} - {data['Close'].max():.2f}")
            print(f"   总收益率: {(data['Close'].iloc[-1] / data['Close'].iloc[0] - 1):.2%}")
        
        print(f"\n📈 总计创建 {len(self.market_data)} 个市场的数据")
        return self.market_data
    
    def ma_cross_strategy(self, data, fast_period=20, slow_period=60, commission=0.001):
        """改进的MA交叉策略"""
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
        
        # 策略收益率（考虑交易成本）
        df['Strategy_Returns'] = df['Position'].shift(1) * df['Returns']
        
        # 应用交易成本
        trade_days = df['Position'].abs() > 0
        df.loc[trade_days, 'Strategy_Returns'] -= commission
        
        # 移除NaN
        df = df.dropna()
        
        return df
    
    def calculate_detailed_performance(self, strategy_df):
        """计算详细的绩效指标"""
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
        
        # 下行风险指标
        downside_returns = returns[returns < 0]
        sortino_ratio = np.sqrt(252) * returns.mean() / downside_returns.std() if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
        
        # 交易统计
        trades = strategy_df[strategy_df['Position'] != 0]
        trade_count = len(trades)
        
        # 胜率计算
        if trade_count > 0:
            win_trades = 0
            total_win_amount = 0
            total_loss_amount = 0
            
            for i in range(1, len(strategy_df)):
                if strategy_df.iloc[i-1]['Position'] != 0:
                    trade_return = strategy_df.iloc[i]['Returns']
                    if trade_return > 0:
                        win_trades += 1
                        total_win_amount += trade_return
                    else:
                        total_loss_amount += abs(trade_return)
            
            win_rate = win_trades / trade_count if trade_count > 0 else 0
            
            # 盈亏比
            profit_factor = total_win_amount / abs(total_loss_amount) if total_loss_amount != 0 else float('inf')
        else:
            win_rate = 0
            profit_factor = 0
        
        # 其他指标
        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        avg_win_return = returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
        avg_loss_return = returns[returns < 0].mean() if len(returns[returns < 0]) > 0 else 0
        
        # 年化波动率
        annual_volatility = returns.std() * np.sqrt(252)
        
        # 卡玛比率
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        performance = {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': trade_count,
            'profit_factor': profit_factor,
            'volatility': volatility,
            'annual_volatility': annual_volatility,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'positive_days': positive_days,
            'negative_days': negative_days,
            'avg_win_return': avg_win_return,
            'avg_loss_return': avg_loss_return,
            'total_days': len(strategy_df),
            'avg_daily_return': returns.mean(),
            'std_daily_return': returns.std()
        }
        
        return performance
    
    def analyze_yearly_performance(self, market_key, data):
        """详细年度分析"""
        print(f"\n📅 {market_key} 年度详细分析")
        print("-" * 60)
        
        yearly_results = {}
        
        for year in range(2014, 2025):
            year_data = data[data.index.year == year]
            
            if len(year_data) < 50:
                continue
            
            # 运行策略
            strategy_df = self.ma_cross_strategy(year_data, 20, 60)
            
            if len(strategy_df) > 0:
                performance = self.calculate_detailed_performance(strategy_df)
                
                yearly_results[year] = {
                    'performance': performance,
                    'data_points': len(year_data),
                    'avg_price': year_data['Close'].mean(),
                    'volatility': year_data['Close'].pct_change().std() * np.sqrt(252)
                }
        
        return yearly_results
    
    def run_complete_analysis(self):
        """运行完整分析"""
        print("\n" + "=" * 70)
        print("开始三大市场量化策略全面分析")
        print("=" * 70)
        
        # 1. 创建市场数据
        self.create_market_data()
        
        if not self.market_data:
            print("❌ 无法创建数据，分析终止")
            return
        
        print("\n" + "=" * 70)
        print("策略回测分析")
        print("=" * 70)
        
        # 2. 对每个市场进行分析
        for market_key, data in self.market_data.items():
            print(f"\n🎯 分析市场: {market_key}")
            print("-" * 60)
            
            # 全时段分析
            full_strategy = self.ma_cross_strategy(data, 20, 60)
            full_performance = self.calculate_detailed_performance(full_strategy)
            
            print(f"📊 全时段绩效 (2014-2024):")
            print(f"   总收益率: {full_performance.get('total_return', 0):.2%}")
            print(f"   年化收益率: {full_performance.get('annual_return', 0):.2%}")
            print(f"   夏普比率: {full_performance.get('sharpe_ratio', 0):.3f}")
            print(f"   最大回撤: {full_performance.get('max_drawdown', 0):.2%}")
            print(f"   胜率: {full_performance.get('win_rate', 0):.2%}")
            print(f"   交易次数: {full_performance.get('trade_count', 0)}")
            print(f"   波动率: {full_performance.get('volatility', 0):.3f}")
            
            # 年度详细分析
            yearly_results = self.analyze_yearly_performance(market_key, data)
            
            # 保存结果
            self.results[market_key] = {
                'full_performance': full_performance,
                'yearly_results': yearly_results,
                'data_points': len(data),
                'price_range': (data['Close'].min(), data['Close'].max())
            }
        
        # 3. 生成综合报告
        self.generate_comprehensive_report()
        
        return self.results
    
    def generate_comprehensive_report(self):
        """生成综合报告"""
        print("\n" + "=" * 70)
        print("三大市场量化策略综合报告")
        print("=" * 70)
        
        if not self.results:
            print("没有分析结果")
            return
        
        print("\n📈 全时段绩效对比 (2014-2024):")
        print(f"{'市场':<20} {'总收益':<10} {'年化':<10} {'夏普':<10} {'最大回撤':<12} {'胜率':<8} {'交易次数':<10}")
        print("-" * 90)
        
        for market_key, result in self.results.items():
            perf = result['full_performance']
            
            print(f"{market_key:<20} "
                  f"{perf.get('total_return', 0):>7.2%}  "
                  f"{perf.get('annual_return', 0):>7.2%}  "
                  f"{perf.get('sharpe_ratio', 0):>7.3f}  "
                  f"{perf.get('max_drawdown', 0):>9.2%}  "
                  f"{perf.get('win_rate', 0):>6.1%}  "
                  f"{perf.get('trade_count', 0):>9d}")
        
        print("\n📊 年度表现分析:")
        
        for market_key, result in self.results.items():
            yearly = result['yearly_results']
            
            if not yearly:
                continue
            
            print(f"\n{market_key} 年度表现:")
            print(f"{'年份':<8} {'收益率':<10} {'夏普':<8} {'最大回撤':<12} {'交易次数':<10}")
            print("-" * 60)
            
            yearly_returns = []
            for year, res in yearly.items():
                perf = res['performance']
                ret = perf.get('total_return', 0)
                yearly_returns.append(ret)
                
                print(f"{year:<8} "
                      f"{ret:>7.2%}  "
                      f"{perf.get('sharpe_ratio', 0):>6.3f}  "
                      f"{perf.get('max_drawdown', 0):>9.2%}  "
                      f"{perf.get('trade_count', 0):>9d}")
            
            if yearly_returns:
                # 计算年度统计
                avg_return = np.mean(yearly_returns)
                std_return = np.std(yearly_returns)
                positive_years = sum(1 for r in yearly_returns if r > 0)
                total_years = len(yearly_returns)
                
                print(f"\n年度统计:")
                print(f"  平均年收益: {avg_return:.2%}")
                print(f"  年收益标准差: {std_return:.2%}")
                print(f"  盈利年份: {positive_years}/{total_years} ({positive_years/total_years:.1%})")
                
                # 风险调整收益
                if std_return > 0:
                    risk_adjusted_return = avg_return / std_return
                    print(f"  风险调整收益: {risk_adjusted_return:.3f}")
        
        print("\n💡 策略有效性评估:")
        
        # 评估各市场策略表现
        market_assessment = {}
        
        for market_key, result in self.results.items():
            perf = result['full_performance']
            sharpe = perf.get('sharpe_ratio', 0)
            total_ret = perf.get('total_return', 0)
            max_dd = perf.get('max_drawdown', 0)
            
            # 评估标准
            if sharpe > 0.8:
                effectiveness = "优秀"
            elif sharpe > 0.5:
                effectiveness = "良好"
            elif sharpe > 0.2:
                effectiveness = "一般"
            else:
                effectiveness = "不佳"
            
            market_assessment[market_key] = {
                'sharpe': sharpe,
                'total_return': total_ret,
                'max_drawdown': max_dd,
                'effectiveness': effectiveness,
                'recommendation': self.generate_recommendation(sharpe, total_ret, max_dd)
            }
        
        # 显示评估结果
        for market_key, assessment in market_assessment.items():
            print(f"\n{market_key}:")
            print(f"  有效性: {assessment['effectiveness']} (夏普: {assessment['sharpe']:.3f})")
            print(f"  建议: {assessment['recommendation']}")
        
        print("\n🎯 总体建议:")
        print("  1. 对于表现优秀的市场，可考虑实盘测试")
        print("  2. 对于表现一般的市场，需要进一步优化参数")
        print("  3. 考虑市场周期调整策略参数")
        print("  4. 添加风险控制机制（止损、仓位管理）")
        print("  5. 进行多策略组合以分散风险")
        
        print("\n" + "=" * 70)
        print("分析完成!")
        print("=" * 70)
    
    def generate_recommendation(self, sharpe, total_return, max_drawdown):
        """生成具体建议"""
        if sharpe > 0.8 and total_return > 0.5 and max_drawdown > -0.15:
            return "策略表现优秀，适合实盘应用，建议加强资金管理"
        elif sharpe > 0.5 and total_return > 0.2:
            return "策略表现良好，可进一步优化参数或考虑实盘小规模测试"
        elif sharpe > 0.2:
            return "策略表现一般，需要改进或与其他策略组合"
        else:
            return "策略表现不佳，建议重新设计或放弃该策略"


def main():
    """主函数"""
    print("开始三大市场量化策略全面分析...")
    
    analyzer = CompleteQuantAnalysis()
    results = analyzer.run_complete_analysis()
    
    # 保存详细结果
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'complete_analysis_{timestamp}.txt'
        
        with open(output_file, 'w') as f:
            f.write("三大市场量化策略分析报告\n")
            f.write("=" * 60 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("数据范围: 2014-01-01 到 2024-12-31\n")
            f.write("策略类型: 移动平均线交叉策略 (MA20, MA60)\n\n")
            
            for market_key, result in results.items():
                f.write(f"【{market_key}】\n")
                f.write(f"数据点数: {result['data_points']}\n")
                f.write(f"价格范围: {result['price_range'][0]:.2f} - {result['price_range'][1]:.2f}\n\n")
                
                perf = result['full_performance']
                f.write("全时段绩效:\n")
                f.write(f"  总收益率: {perf.get('total_return', 0):.2%}\n")
                f.write(f"  年化收益率: {perf.get('annual_return', 0):.2%}\n")
                f.write(f"  夏普比率: {perf.get('sharpe_ratio', 0):.3f}\n")
                f.write(f"  最大回撤: {perf.get('max_drawdown', 0):.2%}\n")
                f.write(f"  胜率: {perf.get('win_rate', 0):.2%}\n")
                f.write(f"  交易次数: {perf.get('trade_count', 0)}\n\n")
                
                yearly = result['yearly_results']
                if yearly:
                    f.write("年度表现:\n")
                    for year, res in yearly.items():
                        year_perf = res['performance']
                        f.write(f"  {year}: {year_perf.get('total_return', 0):.2%} "
                               f"(夏普: {year_perf.get('sharpe_ratio', 0):.3f}, "
                               f"交易: {year_perf.get('trade_count', 0)})\n")
                    f.write("\n")
        
        print(f"\n📁 详细报告已保存到: {output_file}")


if __name__ == "__main__":
    main()