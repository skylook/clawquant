"""
可视化图表模块 - 使用 Pyecharts 绘制专业金融图表
"""

import pandas as pd
import pyecharts.options as opts
from pyecharts.charts import Bar, Grid, Kline, Line


def split_data(df: pd.DataFrame) -> tuple:
    """分割K线数据"""
    # 创建副本避免 SettingWithCopyWarning
    df = df.copy()
    
    x_data = df["日期"].astype(str).values.tolist()
    y_data = df[["开盘", "收盘", "最低", "最高"]].values.tolist()
    df_close = df["收盘"]
    
    df["index"] = df.index
    df["rise"] = df[["开盘", "收盘"]].apply(
        lambda x: 1 if x.iloc[0] > x.iloc[1] else -1, axis=1
    )
    y_vol = df[["index", "成交量", "rise"]].values.tolist()
    
    return x_data, y_data, df_close, y_vol


def calculate_ma(day_count: int, df: pd.Series) -> list:
    """计算移动平均线"""
    df_ma = df.rolling(day_count).mean().round(2).fillna("-")
    return df_ma.values.tolist()


def draw_pro_kline(df: pd.DataFrame) -> Grid:
    """绘制专业K线图（含均线和成交量）"""
    x_data, y_data, df_close, y_vol = split_data(df)
    
    # K线图
    kline = (
        Kline()
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="日K",
            y_axis=y_data,
            itemstyle_opts=opts.ItemStyleOpts(
                color="#ec0000",
                color0="#00da3c"
            ),
        )
        .set_global_opts(
            legend_opts=opts.LegendOpts(
                is_show=True,
                pos_bottom=10,
                pos_left="center"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=80,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="85%",
                    range_start=80,
                    range_end=100,
                ),
            ],
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True,
                    areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#00da3c"},
                    {"value": -1, "color": "#ec0000"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
        )
    )
    
    # 均线
    line = (
        Line()
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="MA5",
            y_axis=calculate_ma(5, df_close),
            is_smooth=True,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.7),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA10",
            y_axis=calculate_ma(10, df_close),
            is_smooth=True,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.7),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA20",
            y_axis=calculate_ma(20, df_close),
            is_smooth=True,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.7),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA30",
            y_axis=calculate_ma(30, df_close),
            is_smooth=True,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.7),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
    )
    
    # 成交量柱状图
    bar = (
        Bar()
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="成交量",
            y_axis=y_vol,
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                grid_index=1,
                boundary_gap=True,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                is_scale=True,
                split_number=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )
    
    # 组合K线和均线
    overlap_kline_line = kline.overlap(line)
    
    # 网格布局
    grid_chart = Grid(
        init_opts=opts.InitOpts(
            animation_opts=opts.AnimationOpts(animation=False),
        )
    )
    grid_chart.add(
        overlap_kline_line,
        grid_opts=opts.GridOpts(
            pos_left="10%",
            pos_right="8%",
            height="50%"
        ),
    )
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="10%",
            pos_right="8%",
            pos_top="63%",
            height="16%"
        ),
    )
    
    return grid_chart


def draw_result_bar(df: pd.DataFrame) -> Bar:
    """绘制回测结果对比柱状图"""
    x_data = df["market"].values.tolist()
    
    bar = (
        Bar()
        .add_xaxis(x_data)
        .add_yaxis(
            "总收益率 (%)",
            df["total_return"].values.tolist(),
            label_opts=opts.LabelOpts(position="top"),
        )
        .add_yaxis(
            "年化收益率 (%)",
            df["annual_return"].values.tolist(),
            label_opts=opts.LabelOpts(position="top"),
        )
        .add_yaxis(
            "最大回撤 (%)",
            df["max_drawdown"].values.tolist(),
            label_opts=opts.LabelOpts(position="top"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="多市场回测对比"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            legend_opts=opts.LegendOpts(pos_top="5%"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=-15)),
            yaxis_opts=opts.AxisOpts(name="百分比 (%)"),
        )
        .set_series_opts(
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="最大值"),
                    opts.MarkPointItem(type_="min", name="最小值"),
                ]
            ),
        )
    )
    
    return bar


def draw_equity_curve(equity_data, dates=None) -> Line:
    """
    绘制资金曲线
    
    Args:
        equity_data: 资金数据列表，可以是简单列表或字典列表
        dates: 日期列表（可选），如果提供则使用日期作为x轴
    """
    if not equity_data:
        return Line()
    
    # 处理不同格式的输入
    if isinstance(equity_data, list) and len(equity_data) > 0:
        if isinstance(equity_data[0], dict):
            # 格式: [{'date': ..., 'value': ...}, ...]
            x_data = [str(item['date'])[:10] if 'date' in item else i for i, item in enumerate(equity_data)]
            y_data = [item.get('value', 0) for item in equity_data]
        else:
            # 格式: [100000, 101000, ...]
            if dates:
                x_data = [str(d)[:10] for d in dates]
            else:
                x_data = [i for i in range(len(equity_data))]
            y_data = equity_data
    else:
        return Line()
    
    line = (
        Line()
        .add_xaxis(x_data)
        .add_yaxis(
            "资金曲线",
            y_data,
            is_smooth=True,
            areastyle_opts=opts.AreaStyleOpts(opacity=0.3),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="资金曲线"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            xaxis_opts=opts.AxisOpts(name="交易日"),
            yaxis_opts=opts.AxisOpts(name="资金 (元)"),
        )
    )
    
    return line
