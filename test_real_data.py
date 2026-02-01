"""
测试获取真实市场数据
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def test_akshare():
    """测试akshare获取A股数据"""
    print("尝试使用akshare获取A股数据...")
    
    try:
        import akshare as ak
        
        # 测试获取上证指数
        print("1. 获取上证指数日线数据...")
        sz_index = ak.stock_zh_index_daily(symbol="sh000001")
        
        if not sz_index.empty:
            print(f"✅ 成功获取上证指数数据: {len(sz_index)} 条")
            print(f"   时间范围: {sz_index.index[0]} 到 {sz_index.index[-1]}")
            print(f"   列名: {list(sz_index.columns)}")
            print(f"   最新收盘价: {sz_index['close'].iloc[-1]}")
            return sz_index
        else:
            print("❌ akshare返回空数据")
            return pd.DataFrame()
            
    except ImportError:
        print("❌ 无法导入akshare，请先安装: pip install akshare")
        return pd.DataFrame()
    except Exception as e:
        print(f"⚠️  akshare获取失败: {e}")
        return pd.DataFrame()

def test_yfinance_with_retry():
    """测试yfinance带重试"""
    print("\n尝试使用yfinance获取美股数据...")
    
    try:
        import yfinance as yf
        import time
        
        # 尝试多次
        for attempt in range(3):
            try:
                print(f"  尝试 {attempt+1}/3...")
                
                if attempt > 0:
                    time.sleep(2 ** attempt)  # 指数退避
                
                # 获取标普500
                sp500 = yf.download("^GSPC", period="10y", progress=False)
                
                if not sp500.empty:
                    print(f"✅ 成功获取标普500数据: {len(sp500)} 条")
                    print(f"   时间范围: {sp500.index[0].date()} 到 {sp500.index[-1].date()}")
                    print(f"   最新收盘价: ${sp500['Close'].iloc[-1]:.2f}")
                    return sp500
                    
            except Exception as e:
                print(f"  尝试 {attempt+1} 失败: {e}")
        
        print("❌ 所有yfinance尝试都失败")
        return pd.DataFrame()
        
    except ImportError:
        print("❌ 无法导入yfinance")
        return pd.DataFrame()

def test_alternative_sources():
    """测试其他数据源"""
    print("\n测试其他数据源...")
    
    # 测试baostock
    try:
        import baostock as bs
        import pandas as pd
        
        print("1. 测试baostock...")
        
        # 登录
        lg = bs.login()
        
        if lg.error_code == '0':
            print("✅ baostock登录成功")
            
            # 获取上证指数
            rs = bs.query_history_k_data_plus(
                "sh.000001",
                "date,code,open,high,low,close,volume",
                start_date='2014-01-01',
                end_date='2024-12-31',
                frequency="d",
                adjustflag="3"
            )
            
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
                print(f"✅ 获取上证指数数据: {len(df)} 条")
                print(f"   时间范围: {df.index[0].date()} 到 {df.index[-1].date()}")
                
                bs.logout()
                return df
            else:
                print("❌ baostock返回空数据")
                bs.logout()
                return pd.DataFrame()
        else:
            print(f"❌ baostock登录失败: {lg.error_msg}")
            return pd.DataFrame()
            
    except ImportError:
        print("⚠️  baostock未安装: pip install baostock")
    except Exception as e:
        print(f"⚠️  baostock测试失败: {e}")
    
    return pd.DataFrame()

def create_fallback_data():
    """创建备用数据（如果所有真实数据源都失败）"""
    print("\n所有真实数据源都失败，创建高质量模拟数据...")
    
    # 创建更真实的模拟数据
    dates = pd.date_range('2014-01-01', '2024-12-31', freq='B')
    n = len(dates)
    
    # 基于历史统计的参数
    market_params = {
        'A股': {'base': 2000, 'drift': 0.0004, 'vol': 0.018, 'name': '上证指数'},
        '美股': {'base': 1800, 'drift': 0.0006, 'vol': 0.012, 'name': '标普500'},
        '港股': {'base': 23000, 'drift': 0.0003, 'vol': 0.015, 'name': '恒生指数'}
    }
    
    all_data = {}
    
    for market, params in market_params.items():
        print(f"创建 {params['name']} 模拟数据...")
        
        np.random.seed(42)
        
        # 基础收益率
        returns = np.random.normal(params['drift'], params['vol'], n)
        
        # 添加真实市场特征
        for i in range(n):
            year = dates[i].year
            month = dates[i].month
            
            # 年度效应
            if market == 'A股':
                if year == 2015: returns[i] += 0.0015  # 2015牛市
                elif year == 2016: returns[i] -= 0.001  # 2016调整
                elif year == 2018: returns[i] -= 0.0008  # 2018贸易战
            elif market == '美股':
                if year == 2020 and month == 3: returns[i] -= 0.025  # 2020疫情
                elif year >= 2020 and month > 3: returns[i] += 0.001  # 复苏
            
            # 月度效应
            if month == 1: returns[i] += 0.0005  # 1月效应
            elif month == 12: returns[i] += 0.0003  # 12月效应
        
        # 价格序列
        price = params['base'] * np.exp(np.cumsum(returns))
        
        # 创建DataFrame
        data = pd.DataFrame({
            'Close': price,
            'Open': price * (1 + np.random.normal(0, 0.005, n)),
            'High': price * (1 + np.random.normal(0.01, 0.005, n)),
            'Low': price * (1 - np.random.normal(0.01, 0.005, n)),
            'Volume': np.random.lognormal(14, 0.8, n) * 1000000
        }, index=dates)
        
        all_data[params['name']] = data
        
        # 计算统计
        total_ret = (price[-1] / price[0] - 1)
        ann_vol = data['Close'].pct_change().std() * np.sqrt(252)
        
        print(f"  ✅ 创建完成: {len(data)} 条")
        print(f"     总收益率: {total_ret:.2%}")
        print(f"     年化波动: {ann_vol:.2%}")
    
    return all_data

def main():
    """主函数"""
    print("=" * 60)
    print("测试真实市场数据获取")
    print("=" * 60)
    
    real_data_available = False
    data_sources = {}
    
    # 1. 测试akshare (A股)
    sz_data = test_akshare()
    if not sz_data.empty:
        real_data_available = True
        data_sources['A股_上证指数'] = sz_data
    
    # 2. 测试yfinance (美股)
    sp500_data = test_yfinance_with_retry()
    if not sp500_data.empty:
        real_data_available = True
        data_sources['美股_标普500'] = sp500_data
    
    # 3. 测试其他数据源
    if not real_data_available:
        alt_data = test_alternative_sources()
        if not alt_data.empty:
            real_data_available = True
            data_sources['A股_上证指数_baostock'] = alt_data
    
    # 4. 如果都没有，使用高质量模拟数据
    if not real_data_available:
        print("\n" + "=" * 60)
        print("警告: 无法获取真实数据，使用高质量模拟数据")
        print("=" * 60)
        data_sources = create_fallback_data()
    
    # 显示结果汇总
    print("\n" + "=" * 60)
    print("数据获取结果汇总")
    print("=" * 60)
    
    for name, data in data_sources.items():
        print(f"\n{name}:")
        print(f"  数据条数: {len(data)}")
        print(f"  时间范围: {data.index[0]} 到 {data.index[-1]}")
        
        if 'Close' in data.columns:
            close_prices = data['Close']
        elif 'close' in data.columns:
            close_prices = data['close']
        else:
            continue
            
        total_return = (close_prices.iloc[-1] / close_prices.iloc[0] - 1)
        print(f"  总收益率: {total_return:.2%}")
        
        # 计算年化波动率
        returns = close_prices.pct_change().dropna()
        if len(returns) > 0:
            ann_vol = returns.std() * np.sqrt(252)
            print(f"  年化波动率: {ann_vol:.2%}")
    
    print(f"\n📊 总计获取 {len(data_sources)} 个市场的数据")
    
    # 保存数据
    if data_sources:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for name, data in data_sources.items():
            safe_name = name.replace(' ', '_').replace('/', '_')
            filename = f"{safe_name}_{timestamp}.csv"
            data.to_csv(filename)
            print(f"📁 {name} 数据已保存到: {filename}")
    
    return data_sources

if __name__ == "__main__":
    data = main()
    
    if data:
        print("\n✅ 数据获取测试完成!")
    else:
        print("\n❌ 数据获取失败")