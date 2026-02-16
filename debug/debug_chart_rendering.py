"""
调试图表渲染 - 检查为什么港美股没有显示图表
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from web.charts import draw_pro_kline, draw_equity_curve
import run_multimarket_backtest as rmb

print("="*60)
print("测试港股图表生成")
print("="*60)

# 加载港股数据
df_hk, sym_hk, start_hk, end_hk = rmb.load_hk_share()
result_hk = rmb.run_backtest(df_hk, sym_hk, "MA_CROSS", {})

# 模拟 streamlit_app.py 的处理流程
df_for_chart = df_hk.copy().reset_index()
result_hk["df"] = df_for_chart

print(f"\n1. df 是否存在: {'df' in result_hk}")
print(f"2. df 类型: {type(result_hk['df'])}")
print(f"3. df 是否为空: {result_hk['df'].empty}")
print(f"4. df 列: {list(result_hk['df'].columns)}")
print(f"5. df 形状: {result_hk['df'].shape}")
print(f"6. df 前3行:\n{result_hk['df'].head(3)}")

# 尝试生成K线图
print("\n" + "="*60)
print("尝试生成K线图")
print("="*60)

df = result_hk["df"].copy()

# 重置索引
if df.index.name == 'date' or 'date' in str(df.index.name).lower():
    df = df.reset_index()
    print("已重置索引")

print(f"\n重置后的列: {list(df.columns)}")

# 列名映射
column_mapping = {
    'date': '日期', 'Date': '日期', 'DATE': '日期',
    'open': '开盘', 'Open': '开盘', 'OPEN': '开盘',
    'high': '最高', 'High': '最高', 'HIGH': '最高',
    'low': '最低', 'Low': '最低', 'LOW': '最低',
    'close': '收盘', 'Close': '收盘', 'CLOSE': '收盘',
    'volume': '成交量', 'Volume': '成交量', 'VOLUME': '成交量'
}

df_chart = df.rename(columns=column_mapping)
print(f"映射后的列: {list(df_chart.columns)}")

# 检查必需列
required_cols = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
missing_cols = [col for col in required_cols if col not in df_chart.columns]
if missing_cols:
    print(f"\n❌ 缺少列: {missing_cols}")
else:
    print(f"\n✅ 所有必需列都存在")
    
    # 只保留需要的列
    df_chart = df_chart[required_cols]
    
    # 确保日期格式
    df_chart['日期'] = pd.to_datetime(df_chart['日期']).dt.strftime('%Y-%m-%d')
    
    # 确保数值列为浮点型
    for col in ['开盘', '最高', '最低', '收盘', '成交量']:
        df_chart[col] = pd.to_numeric(df_chart[col], errors='coerce')
    
    # 删除 NaN
    df_chart = df_chart.dropna()
    
    print(f"清理后的数据形状: {df_chart.shape}")
    print(f"清理后的前3行:\n{df_chart.head(3)}")
    
    if len(df_chart) > 0:
        try:
            kline_chart = draw_pro_kline(df_chart)
            print("\n✅ K线图生成成功！")
            print(f"图表类型: {type(kline_chart)}")
        except Exception as e:
            print(f"\n❌ K线图生成失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ 数据清理后为空")

# 测试资金曲线
print("\n" + "="*60)
print("测试资金曲线生成")
print("="*60)

if 'equity_curve_detailed' in result_hk:
    ec = result_hk['equity_curve_detailed']
    print(f"equity_curve_detailed 长度: {len(ec)}")
    print(f"第一条: {ec[0]}")
    print(f"最后一条: {ec[-1]}")
    
    try:
        equity_chart = draw_equity_curve(ec)
        print("\n✅ 资金曲线生成成功！")
        print(f"图表类型: {type(equity_chart)}")
    except Exception as e:
        print(f"\n❌ 资金曲线生成失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ 缺少 equity_curve_detailed")
