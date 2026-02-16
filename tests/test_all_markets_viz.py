"""
测试所有市场的可视化数据格式
"""

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from run_multimarket_backtest import load_a_share, load_hk_share, load_us_share
from web.charts import draw_pro_kline

def test_market_visualization(name, loader_fn):
    """测试单个市场的可视化"""
    print(f"\n{'='*60}")
    print(f"测试 {name} 可视化")
    print('='*60)
    
    try:
        # 加载数据
        df, symbol, start, end = loader_fn()
        print(f"✅ 数据加载成功: {symbol}, {len(df)} 行")
        
        # 重置索引（模拟 streamlit_app.py 的处理）
        df_chart = df.copy().reset_index()
        print(f"原始列: {df_chart.columns.tolist()}")
        
        # 转换为中文列名
        column_mapping = {
            'date': '日期', 'Date': '日期',
            'open': '开盘', 'Open': '开盘',
            'high': '最高', 'High': '最高',
            'low': '最低', 'Low': '最低',
            'close': '收盘', 'Close': '收盘',
            'volume': '成交量', 'Volume': '成交量'
        }
        df_chart = df_chart.rename(columns=column_mapping)
        
        # 确保必需列存在
        required_cols = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
        if not all(col in df_chart.columns for col in required_cols):
            print(f"❌ 缺少必需列。当前列: {df_chart.columns.tolist()}")
            return False
        
        # 只保留需要的列
        df_chart = df_chart[required_cols]
        
        # 格式化日期
        df_chart['日期'] = pd.to_datetime(df_chart['日期']).dt.strftime('%Y-%m-%d')
        
        # 确保数值列为浮点型
        for col in ['开盘', '最高', '最低', '收盘', '成交量']:
            df_chart[col] = pd.to_numeric(df_chart[col], errors='coerce')
        
        # 删除 NaN
        df_chart = df_chart.dropna()
        
        print(f"处理后列: {df_chart.columns.tolist()}")
        print(f"数据样本:\n{df_chart.head(3)}")
        print(f"数据类型:\n{df_chart.dtypes}")
        
        # 取最近100天测试
        df_test = df_chart.tail(100)
        
        # 绘制K线图
        chart = draw_pro_kline(df_test)
        output_file = f"test_{name}_kline.html"
        chart.render(output_file)
        print(f"✅ K线图生成成功: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 测试所有市场可视化\n")
    
    markets = [
        ("A股", load_a_share),
        ("港股", load_hk_share),
        ("美股", load_us_share),
    ]
    
    results = []
    for name, loader in markets:
        result = test_market_visualization(name, loader)
        results.append((name, result))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有市场可视化测试通过！")
        print("生成的文件:")
        print("  - test_A股_kline.html")
        print("  - test_港股_kline.html")
        print("  - test_美股_kline.html")
    else:
        print("\n⚠️  部分市场测试失败")
