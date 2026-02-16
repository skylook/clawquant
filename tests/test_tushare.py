"""
测试tushare获取港美股数据
使用提供的token
"""

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TushareTester:
    """tushare测试器"""
    
    def __init__(self, token):
        self.token = token
        self.pro = None
        
    def init_tushare(self):
        """初始化tushare"""
        print("初始化tushare...")
        
        try:
            # 设置token
            ts.set_token(self.token)
            
            # 创建pro接口
            self.pro = ts.pro_api()
            
            print("✅ tushare初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ tushare初始化失败: {e}")
            return False
    
    def test_a_share_data(self):
        """测试A股数据"""
        print("\n📈 测试A股数据获取...")
        
        try:
            # 获取上证指数日线数据
            print("  获取上证指数日线数据...")
            
            # 方法1：使用pro接口
            df = self.pro.index_daily(
                ts_code='000001.SH',
                start_date='20140101',
                end_date='20241231'
            )
            
            if not df.empty:
                print(f"✅ 成功获取上证指数数据: {len(df)} 条")
                print(f"   时间范围: {df['trade_date'].iloc[-1]} 到 {df['trade_date'].iloc[0]}")
                print(f"   最新收盘: {df['close'].iloc[0]}")
                
                # 格式化数据
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df.set_index('trade_date', inplace=True)
                df.sort_index(inplace=True)
                
                return df
            else:
                print("❌ 上证指数数据为空")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"⚠️  A股数据获取失败: {e}")
            return pd.DataFrame()
    
    def test_us_stock_data(self):
        """测试美股数据"""
        print("\n📈 测试美股数据获取...")
        
        try:
            # tushare可能不支持直接获取美股数据
            # 尝试获取标普500相关的ETF或指数
            print("  尝试获取标普500相关数据...")
            
            # 搜索相关标的
            df = self.pro.us_basic()
            
            if not df.empty:
                print(f"✅ 获取美股基础信息: {len(df)} 条")
                print(f"   标的列表 (前5个):")
                for i, row in df.head(5).iterrows():
                    print(f"     {row['ts_code']}: {row['name']}")
                
                # 尝试获取具体标的的数据
                if len(df) > 0:
                    sample_code = df.iloc[0]['ts_code']
                    print(f"\n  尝试获取 {sample_code} 日线数据...")
                    
                    us_data = self.pro.us_daily(
                        ts_code=sample_code,
                        start_date='20240101',
                        end_date='20241231'
                    )
                    
                    if not us_data.empty:
                        print(f"✅ 成功获取美股日线数据: {len(us_data)} 条")
                        return us_data
                    else:
                        print("❌ 美股日线数据为空")
            else:
                print("❌ 无法获取美股基础信息")
                
            return pd.DataFrame()
            
        except Exception as e:
            print(f"⚠️  美股数据获取失败: {e}")
            return pd.DataFrame()
    
    def test_hk_stock_data(self):
        """测试港股数据"""
        print("\n📈 测试港股数据获取...")
        
        try:
            # 获取恒生指数
            print("  获取恒生指数日线数据...")
            
            hk_data = self.pro.index_daily(
                ts_code='HSI.HI',  # 恒生指数
                start_date='20140101',
                end_date='20241231'
            )
            
            if not hk_data.empty:
                print(f"✅ 成功获取恒生指数数据: {len(hk_data)} 条")
                print(f"   时间范围: {hk_data['trade_date'].iloc[-1]} 到 {hk_data['trade_date'].iloc[0]}")
                print(f"   最新收盘: {hk_data['close'].iloc[0]}")
                
                # 格式化数据
                hk_data['trade_date'] = pd.to_datetime(hk_data['trade_date'])
                hk_data.set_index('trade_date', inplace=True)
                hk_data.sort_index(inplace=True)
                
                return hk_data
            else:
                print("❌ 恒生指数数据为空")
                
                # 尝试其他港股指数
                print("  尝试获取其他港股指数...")
                hk_indexes = self.pro.index_basic(market='HK')
                
                if not hk_indexes.empty:
                    print(f"✅ 获取港股指数列表: {len(hk_indexes)} 个")
                    for i, row in hk_indexes.head(3).iterrows():
                        print(f"     {row['ts_code']}: {row['name']}")
                
                return pd.DataFrame()
                
        except Exception as e:
            print(f"⚠️  港股数据获取失败: {e}")
            return pd.DataFrame()
    
    def test_market_data(self):
        """测试市场数据获取能力"""
        print("\n📊 测试tushare市场数据能力...")
        
        try:
            # 测试数据接口
            print("1. 测试指数列表...")
            indexes = self.pro.index_basic()
            if not indexes.empty:
                print(f"✅ 可获取指数数量: {len(indexes)}")
                print(f"   示例: {indexes['name'].iloc[0]} ({indexes['ts_code'].iloc[0]})")
            
            print("\n2. 测试股票列表...")
            stocks = self.pro.stock_basic(exchange='', list_status='L')
            if not stocks.empty:
                print(f"✅ 可获取股票数量: {len(stocks)}")
                print(f"   市场分布:")
                for exchange in stocks['exchange'].value_counts().head(3).items():
                    print(f"     {exchange[0]}: {exchange[1]} 只")
            
            print("\n3. 测试交易日历...")
            trade_cal = self.pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20241231')
            if not trade_cal.empty:
                trade_days = trade_cal[trade_cal['is_open'] == 1]
                print(f"✅ 2024年交易日: {len(trade_days)} 天")
            
            return True
            
        except Exception as e:
            print(f"⚠️  市场数据测试失败: {e}")
            return False
    
    def run_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("开始tushare数据获取测试")
        print("=" * 60)
        
        # 1. 初始化
        if not self.init_tushare():
            return {}
        
        # 2. 测试市场数据能力
        self.test_market_data()
        
        # 3. 测试A股数据
        a_share_data = self.test_a_share_data()
        
        # 4. 测试港股数据
        hk_data = self.test_hk_stock_data()
        
        # 5. 测试美股数据
        us_data = self.test_us_stock_data()
        
        # 汇总结果
        results = {
            'A股_上证指数': a_share_data,
            '港股_恒生指数': hk_data,
            '美股_样本': us_data
        }
        
        # 统计成功获取的数据
        successful = sum(1 for data in results.values() if not data.empty)
        print(f"\n📊 测试结果: 成功获取 {successful}/{len(results)} 个市场的数据")
        
        # 保存数据
        if successful > 0:
            self.save_data(results)
        
        return results
    
    def save_data(self, results):
        """保存数据"""
        print("\n💾 保存获取的数据...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for market_name, data in results.items():
            if not data.empty:
                safe_name = market_name.replace(' ', '_').replace('/', '_')
                filename = f"tushare_{safe_name}_{timestamp}.csv"
                
                data.to_csv(filename)
                print(f"✅ {market_name} 数据已保存: {filename}")
        
        print("📁 数据保存完成")


def main():
    """主函数"""
    # 使用你提供的token
    token = "d5d70ef905f6a135ad9cd9a49f2c7ec53ac37eea7e874bcc0519a261"
    
    print(f"使用tushare token: {token[:10]}...")
    
    tester = TushareTester(token)
    results = tester.run_tests()
    
    if results:
        print("\n✅ tushare测试完成!")
        
        # 显示数据统计
        for market_name, data in results.items():
            if not data.empty:
                print(f"\n{market_name}:")
                print(f"  数据条数: {len(data)}")
                if 'close' in data.columns:
                    print(f"  最新收盘: {data['close'].iloc[-1]}")
                    if len(data) > 1:
                        returns = data['close'].pct_change().dropna()
                        if len(returns) > 0:
                            total_return = (data['close'].iloc[-1] / data['close'].iloc[0] - 1)
                            print(f"  总收益率: {total_return:.2%}")
    else:
        print("\n❌ tushare测试失败，可能token无效或接口限制")


if __name__ == "__main__":
    main()