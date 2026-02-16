"""
可视化图表模块 - 使用 Plotly 绘制专业金融图表
替代 Pyecharts，解决标签页渲染问题
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def draw_kline_with_ma(df: pd.DataFrame) -> go.Figure:
    """
    绘制K线图（含均线和成交量）
    
    Args:
        df: DataFrame，必须包含列：日期, 开盘, 最高, 最低, 收盘, 成交量
    
    Returns:
        Plotly Figure 对象
    """
    # 计算移动平均线
    df = df.copy()
    df['MA5'] = df['收盘'].rolling(window=5).mean()
    df['MA10'] = df['收盘'].rolling(window=10).mean()
    df['MA20'] = df['收盘'].rolling(window=20).mean()
    df['MA30'] = df['收盘'].rolling(window=30).mean()
    
    # 创建子图：上方K线图 + 均线，下方成交量
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('K线图与均线', '成交量')
    )
    
    # K线图
    fig.add_trace(
        go.Candlestick(
            x=df['日期'],
            open=df['开盘'],
            high=df['最高'],
            low=df['最低'],
            close=df['收盘'],
            name='K线',
            increasing_line_color='#ec0000',  # 红涨
            decreasing_line_color='#00da3c',  # 绿跌
            increasing_fillcolor='#ec0000',
            decreasing_fillcolor='#00da3c',
        ),
        row=1, col=1
    )
    
    # 添加均线
    ma_colors = {
        'MA5': '#1f77b4',
        'MA10': '#ff7f0e', 
        'MA20': '#2ca02c',
        'MA30': '#d62728'
    }
    
    for ma_name, color in ma_colors.items():
        fig.add_trace(
            go.Scatter(
                x=df['日期'],
                y=df[ma_name],
                name=ma_name,
                line=dict(color=color, width=1.5),
                mode='lines'
            ),
            row=1, col=1
        )
    
    # 成交量柱状图（红涨绿跌）
    colors = ['#ec0000' if close >= open_ else '#00da3c' 
              for close, open_ in zip(df['收盘'], df['开盘'])]
    
    fig.add_trace(
        go.Bar(
            x=df['日期'],
            y=df['成交量'],
            name='成交量',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # 更新布局
    fig.update_layout(
        title=None,
        xaxis_rangeslider_visible=False,
        height=700,
        hovermode='x unified',
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    # 更新 x 轴
    fig.update_xaxes(
        title_text="日期",
        row=2, col=1,
        rangeslider_visible=False
    )
    
    # 更新 y 轴
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    return fig


def draw_equity_curve(equity_data, dates=None) -> go.Figure:
    """
    绘制资金曲线
    
    Args:
        equity_data: 资金数据，可以是：
            - 列表: [100000, 101000, ...]
            - 字典列表: [{'date': '2020-01-01', 'value': 100000}, ...]
        dates: 日期列表（可选），当 equity_data 是简单列表时使用
    
    Returns:
        Plotly Figure 对象
    """
    if not equity_data:
        return go.Figure()
    
    # 处理不同格式的输入
    if isinstance(equity_data, list) and len(equity_data) > 0:
        if isinstance(equity_data[0], dict):
            # 格式: [{'date': ..., 'value': ...}, ...]
            x_data = [item.get('date', i) for i, item in enumerate(equity_data)]
            y_data = [item.get('value', 0) for item in equity_data]
        else:
            # 格式: [100000, 101000, ...]
            if dates:
                x_data = dates
            else:
                x_data = list(range(len(equity_data)))
            y_data = equity_data
    else:
        return go.Figure()
    
    # 创建图表
    fig = go.Figure()
    
    # 添加资金曲线
    fig.add_trace(
        go.Scatter(
            x=x_data,
            y=y_data,
            mode='lines',
            name='资金曲线',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.2)'
        )
    )
    
    # 更新布局
    fig.update_layout(
        title=None,
        xaxis_title="日期",
        yaxis_title="资金 (元)",
        height=400,
        hovermode='x unified',
        template='plotly_white',
        margin=dict(l=50, r=50, t=30, b=50)
    )
    
    return fig


def draw_comparison_bar(df: pd.DataFrame) -> go.Figure:
    """
    绘制回测结果对比柱状图
    
    Args:
        df: DataFrame，包含列：market, total_return, annual_return 等
    
    Returns:
        Plotly Figure 对象
    """
    fig = go.Figure()
    
    # 添加总收益率
    fig.add_trace(
        go.Bar(
            name='总收益率 (%)',
            x=df['market'],
            y=df['total_return'],
            marker_color='#1f77b4',
            text=df['total_return'].round(2),
            textposition='outside'
        )
    )
    
    # 添加年化收益率
    fig.add_trace(
        go.Bar(
            name='年化收益率 (%)',
            x=df['market'],
            y=df['annual_return'],
            marker_color='#ff7f0e',
            text=df['annual_return'].round(2),
            textposition='outside'
        )
    )
    
    # 更新布局
    fig.update_layout(
        title=None,
        xaxis_title="市场",
        yaxis_title="收益率 (%)",
        barmode='group',
        height=400,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig
