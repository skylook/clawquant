"""
UI 组件模块 - Streamlit 界面组件
"""

import streamlit as st
from datetime import date, datetime


def strategy_selector_ui():
    """策略选择器"""
    st.subheader("📊 策略选择")
    
    strategies = {
        "MA": "移动平均线策略",
        "MA_CROSS": "双均线交叉策略",
        "MACD": "MACD策略",
        "RSI": "RSI策略",
        "BOLL": "布林带策略",
        "TRIPLE_MA": "三均线策略",
        "DUAL_THRUST": "Dual Thrust策略",
        "KAMA": "KAMA策略",
        "TURTLE": "海龟交易策略"
    }
    
    strategy_name = st.selectbox(
        "选择策略",
        options=list(strategies.keys()),
        format_func=lambda x: f"{x} - {strategies[x]}"
    )
    
    st.markdown("---")
    st.subheader("⚙️ 策略参数")
    
    # 根据策略显示不同参数
    params = {}
    
    if strategy_name == "MA":
        params["ma_period"] = st.slider("均线周期", 5, 200, 20, 5)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
        params["take_profit_ratio"] = st.slider("止盈比例", 0.05, 0.50, 0.15, 0.05)
        params["max_position_size"] = st.slider("最大仓位", 0.1, 1.0, 0.8, 0.1)
    
    elif strategy_name == "MA_CROSS":
        params["fast_period"] = st.slider("快线周期", 3, 50, 10, 1)
        params["slow_period"] = st.slider("慢线周期", 10, 200, 100, 5)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
        params["take_profit_ratio"] = st.slider("止盈比例", 0.05, 0.50, 0.15, 0.05)
        params["max_position_size"] = st.slider("最大仓位", 0.1, 1.0, 0.8, 0.1)
    
    elif strategy_name == "MACD":
        params["fast_period"] = st.slider("快线周期", 5, 30, 12, 1)
        params["slow_period"] = st.slider("慢线周期", 15, 50, 26, 1)
        params["signal_period"] = st.slider("信号线周期", 5, 20, 9, 1)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
        params["take_profit_ratio"] = st.slider("止盈比例", 0.05, 0.50, 0.15, 0.05)
    
    elif strategy_name == "RSI":
        params["rsi_period"] = st.slider("RSI周期", 5, 30, 14, 1)
        params["rsi_lower"] = st.slider("超卖阈值", 10, 40, 30, 5)
        params["rsi_upper"] = st.slider("超买阈值", 60, 90, 70, 5)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
        params["take_profit_ratio"] = st.slider("止盈比例", 0.05, 0.50, 0.15, 0.05)
    
    elif strategy_name == "BOLL":
        params["period"] = st.slider("布林带周期", 10, 50, 20, 5)
        params["devfactor"] = st.slider("标准差倍数", 1.0, 3.0, 2.0, 0.1)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
        params["take_profit_ratio"] = st.slider("止盈比例", 0.05, 0.50, 0.15, 0.05)
    
    elif strategy_name == "TRIPLE_MA":
        params["fast_period"] = st.slider("快线周期", 3, 20, 5, 1)
        params["mid_period"] = st.slider("中线周期", 10, 50, 20, 5)
        params["slow_period"] = st.slider("慢线周期", 30, 200, 60, 5)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
        params["take_profit_ratio"] = st.slider("止盈比例", 0.05, 0.50, 0.15, 0.05)
    
    elif strategy_name == "DUAL_THRUST":
        params["k1"] = st.slider("K1系数", 0.1, 1.0, 0.5, 0.1)
        params["k2"] = st.slider("K2系数", 0.1, 1.0, 0.5, 0.1)
        params["period"] = st.slider("计算周期", 1, 10, 4, 1)
    
    elif strategy_name == "KAMA":
        params["period"] = st.slider("KAMA周期", 5, 50, 10, 5)
        params["fast"] = st.slider("快速EMA周期", 2, 10, 2, 1)
        params["slow"] = st.slider("慢速EMA周期", 10, 50, 30, 5)
        params["stop_loss_ratio"] = st.slider("止损比例", 0.01, 0.20, 0.05, 0.01)
    
    elif strategy_name == "TURTLE":
        params["entry_period"] = st.slider("入场周期", 10, 50, 20, 5)
        params["exit_period"] = st.slider("出场周期", 5, 30, 10, 5)
        params["atr_period"] = st.slider("ATR周期", 10, 30, 20, 5)
        params["risk_ratio"] = st.slider("风险比例", 0.01, 0.05, 0.02, 0.01)
    
    return strategy_name, params


def market_selector_ui():
    """市场选择器"""
    st.markdown("---")
    st.subheader("🌍 市场选择")
    
    markets = {
        "a_share": "A股 上证指数",
        "hk_share": "港股 腾讯",
        "us_nvda": "美股 NVDA"
    }
    
    selected_markets = []
    
    for key, name in markets.items():
        if st.checkbox(name, value=True, key=f"market_{key}"):
            selected_markets.append(key)
    
    return selected_markets


def backtest_params_ui():
    """回测参数配置"""
    st.markdown("---")
    st.subheader("💰 回测参数")
    
    config = {}
    
    config["initial_cash"] = st.number_input(
        "初始资金 (元)",
        min_value=10000,
        max_value=10000000,
        value=100000,
        step=10000
    )
    
    config["commission"] = st.number_input(
        "手续费率",
        min_value=0.0,
        max_value=0.01,
        value=0.001,
        step=0.0001,
        format="%.4f"
    )
    
    config["slippage"] = st.number_input(
        "滑点 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.1,
        step=0.1
    )
    
    return config


def display_results_table(results):
    """显示结果表格"""
    import pandas as pd
    
    data = []
    for r in results:
        data.append({
            "市场": r.get("market", ""),
            "总收益": f"{r.get('total_return', 0):.2f}%",
            "年化收益": f"{r.get('annual_return', 0):.2f}%",
            "夏普比率": f"{r.get('sharpe_ratio', 0):.2f}",
            "最大回撤": f"{r.get('max_drawdown', 0):.2f}%",
            "胜率": f"{r.get('win_rate', 0):.2f}%",
            "交易次数": r.get('trades', 0),
            "期末资产": f"¥{r.get('final_value', 0):,.0f}"
        })
    
    df = pd.DataFrame(data)
    st.dataframe(df, width='stretch', hide_index=True)
