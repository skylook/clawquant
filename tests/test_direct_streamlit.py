"""
直接测试 Streamlit 显示 - 最小化测试
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from streamlit_echarts import st_pyecharts
import run_multimarket_backtest as rmb
from web.charts import draw_pro_kline, draw_equity_curve
import pandas as pd

st.title("测试港股图表显示")

# 加载港股数据并运行回测
df_hk, sym_hk, start_hk, end_hk = rmb.load_hk_share()
result_hk = rmb.run_backtest(df_hk, sym_hk, "MA_CROSS", {})

# 添加 df
df_for_chart = df_hk.copy().reset_index()
result_hk["df"] = df_for_chart

st.write(f"df 存在: {'df' in result_hk}")
st.write(f"df 形状: {result_hk['df'].shape}")
st.write(f"df 列: {list(result_hk['df'].columns)}")

# 尝试显示K线图
st.subheader("📈 K线图测试")

try:
    df = result_hk["df"].copy()
    
    # 列名映射
    column_mapping = {
        'date': '日期', 'open': '开盘', 'high': '最高',
        'low': '最低', 'close': '收盘', 'volume': '成交量'
    }
    df_chart = df.rename(columns=column_mapping)
    
    # 只保留需要的列
    required_cols = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
    df_chart = df_chart[required_cols]
    
    # 数据类型转换
    df_chart['日期'] = pd.to_datetime(df_chart['日期']).dt.strftime('%Y-%m-%d')
    for col in ['开盘', '最高', '最低', '收盘', '成交量']:
        df_chart[col] = pd.to_numeric(df_chart[col], errors='coerce')
    
    df_chart = df_chart.dropna()
    
    st.write(f"清理后数据形状: {df_chart.shape}")
    
    if len(df_chart) > 0:
        kline_chart = draw_pro_kline(df_chart)
        st.write(f"图表类型: {type(kline_chart)}")
        st_pyecharts(kline_chart, height="600px")
        st.success("✅ K线图显示成功！")
    else:
        st.error("❌ 数据为空")
        
except Exception as e:
    st.error(f"❌ 错误: {e}")
    import traceback
    st.code(traceback.format_exc())

# 测试资金曲线
st.subheader("💰 资金曲线测试")

try:
    if 'equity_curve_detailed' in result_hk:
        ec = result_hk['equity_curve_detailed']
        st.write(f"equity_curve_detailed 长度: {len(ec)}")
        
        equity_chart = draw_equity_curve(ec)
        st.write(f"图表类型: {type(equity_chart)}")
        st_pyecharts(equity_chart, height="400px")
        st.success("✅ 资金曲线显示成功！")
    else:
        st.error("❌ 缺少 equity_curve_detailed")
        
except Exception as e:
    st.error(f"❌ 错误: {e}")
    import traceback
    st.code(traceback.format_exc())
