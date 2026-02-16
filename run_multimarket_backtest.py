"""
三市场回测脚本 (A股 / 港股 / 美股)
直接读取本地 CSV，跳过网络获取，使用 MA_CROSS 策略最优参数回测
"""

import sys
import os
import json
from pathlib import Path
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime

# 锚定项目根目录（无论从哪个 cwd 调用都能正确找到 data/）
ROOT = Path(__file__).resolve().parent

# ──────────────────────────────────────────────
# 1. 数据加载
# ──────────────────────────────────────────────

def load_a_share():
    """加载 A 股上证指数数据"""
    path = ROOT / "data/raw/000001.SH_daily_2020-01-01_2024-01-01.csv"
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df, "000001.SH", "2020-01-02", "2023-12-29"


def load_hk_share():
    """加载港股腾讯数据"""
    path = ROOT / "data/raw/0700.HK_daily_2014-2025.csv"
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    # 注意：原始数据列顺序是 open, close, high, low，需要重新排列
    df = df.rename(columns={'high': 'high_temp', 'close': 'close_temp'})
    df['high'] = df['high_temp']
    df['close'] = df['close_temp']
    df = df.set_index('date').sort_index()
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df, "0700.HK", str(df.index[0].date()), str(df.index[-1].date())


def load_us_share():
    """
    加载美股 NVDA 数据
    原始文件有 3 行 header:
      Price,Close,High,Low,Open,Volume
      Ticker,NVDA,NVDA,NVDA,NVDA,NVDA
      Date,,,,,
    实际数据从第 4 行开始，Price 列是日期索引
    """
    path = ROOT / "data/raw/NVDA_daily_2014-2025.csv"
    df = pd.read_csv(path, skiprows=[1, 2], index_col=0)
    df.index.name = 'date'
    df.index = pd.to_datetime(df.index)
    # 原列名: Close, High, Low, Open, Volume (大写)
    df.columns = [c.lower() for c in df.columns]
    # 列顺序: close, high, low, open, volume → 补齐
    df = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric, errors='coerce')
    df = df.dropna()
    df = df.sort_index()
    # 同时保存清洗后的文件供后续使用
    clean_path = ROOT / "data/raw/NVDA_daily_2014-2025_clean.csv"
    df.to_csv(clean_path)
    print(f"  [NVDA] 清洗后数据已保存: {clean_path}")
    return df, "NVDA", str(df.index[0].date()), str(df.index[-1].date())


# ──────────────────────────────────────────────
# 2. 回测执行
# ──────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, symbol: str, strategy_type: str,
                 params: dict, initial_cash: float = 100_000) -> dict:
    """
    直接用 Cerebro 跑回测，不经过 DataFetcher
    返回值包含 equity_curve 和 trade_log 供 WebUI 使用
    """
    from strategies.base_strategy import StrategyFactory

    # 用于记录每日权益的容器（通过闭包传给 Observer）
    class _EquityRecorder:
        def __init__(self):
            self.dates = []
            self.values = []

    recorder = _EquityRecorder()

    class DailyEquityObserver(bt.Observer):
        lines = ('portfolio_value',)
        plotinfo = dict(plot=False)

        def next(self):
            dt = self._owner.data.datetime.date(0)
            val = self._owner.broker.getvalue()
            recorder.dates.append(str(dt))
            recorder.values.append(round(val, 2))
            self.lines.portfolio_value[0] = val

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.0003)
    cerebro.broker.set_slippage_perc(0.0001)

    data_feed = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='open', high='high', low='low',
        close='close', volume='volume',
        openinterest=None
    )
    cerebro.adddata(data_feed)

    strategy_class = StrategyFactory.get_strategy_class(strategy_type)
    cerebro.addstrategy(strategy_class, **params)

    cerebro.addobserver(DailyEquityObserver)

    cerebro.addanalyzer(bt.analyzers.Returns,     _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio,  _name='sharpe', riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.DrawDown,     _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    results = cerebro.run()
    strat = results[0]

    # 生成 Plotly 图表（backtrader 原生绘图流水线）
    chart_json = None
    try:
        from backtrader_plotly.plotter import BacktraderPlotly
        from backtrader_plotly.scheme import PlotScheme
        scheme = PlotScheme(decimal_places=4, max_legend_text_width=16)
        bt_figs = cerebro.plot(BacktraderPlotly(show=False, scheme=scheme))
        if bt_figs and bt_figs[0]:
            chart_json = json.loads(bt_figs[0][0].to_json())
    except Exception:
        chart_json = None  # 降级：不影响主流程

    # 提取指标
    final_value = cerebro.broker.getvalue()
    total_return = (final_value / initial_cash) - 1

    ret_ana  = strat.analyzers.returns.get_analysis()
    sharpe_ana = strat.analyzers.sharpe.get_analysis()
    dd_ana   = strat.analyzers.drawdown.get_analysis()
    trade_ana = strat.analyzers.trades.get_analysis()

    annual_return = ret_ana.get('rnorm100', 0) / 100 if ret_ana.get('rnorm100') else 0
    sharpe  = sharpe_ana.get('sharperatio', None)
    max_dd  = dd_ana.get('max', {}).drawdown if 'max' in dd_ana else 0

    total_trades = trade_ana.get('total', {}).get('total', 0)
    won_trades   = trade_ana.get('won', {}).get('total', 0)
    win_rate = won_trades / total_trades if total_trades > 0 else 0

    won_pnl  = trade_ana.get('won',  {}).get('pnl', {}).get('total', 0)
    lost_pnl = abs(trade_ana.get('lost', {}).get('pnl', {}).get('total', 0) or 0)
    profit_factor = won_pnl / lost_pnl if lost_pnl > 0 else float('inf')

    # 构建权益曲线（来自 DailyEquityObserver）
    # 返回两种格式：详细版（带日期）和简单版（仅数值）
    equity_curve_detailed = [
        {'date': d, 'value': v}
        for d, v in zip(recorder.dates, recorder.values)
    ]
    equity_curve = [v for v in recorder.values]  # 简单数值列表供图表使用

    # 构建交易日志（来自 BaseStrategy.log_entries）
    entries = getattr(strat, 'log_entries', [])
    trade_log = [
        {
            'date': str(e['datetime'].date()) if hasattr(e['datetime'], 'date') else str(e['datetime'])[:10],
            'action': e.get('action', ''),
            'price': round(float(e.get('price', 0)), 4),
            'size': int(e.get('size', 0)),
            'reason': e.get('reason', ''),
            'pnl': round(float(e.get('pnl', 0)), 2),
        }
        for e in entries
    ]

    return {
        'symbol':        symbol,
        'strategy':      strategy_type,
        'params':        params,
        'initial_cash':  initial_cash,
        'final_value':   final_value,
        'total_return':  total_return * 100,  # 转换为百分比
        'annual_return': annual_return * 100,  # 转换为百分比
        'sharpe_ratio':  sharpe,
        'max_drawdown':  max_dd,
        'trades':        total_trades,
        'win_rate':      win_rate * 100,  # 转换为百分比
        'profit_factor': profit_factor,
        'equity_curve':  equity_curve,
        'equity_curve_detailed': equity_curve_detailed,
        'trade_log':     trade_log,
        'chart_json':    chart_json,
    }


# ──────────────────────────────────────────────
# 3. 主函数
# ──────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  三市场 MA_CROSS 策略回测")
    print("=" * 65)

    # 市场配置：(加载函数, 最优参数)
    # 参数来自 docs/STRATEGY_DESIGN.md 的跨市场最优参数
    markets = [
        {
            'name': 'A股 000001.SH',
            'loader': load_a_share,
            'strategy': 'MA_CROSS',
            'params': {
                'fast_period': 3,
                'slow_period': 100,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.15,
                'max_position_size': 0.8,
            },
        },
        {
            'name': '港股 0700.HK',
            'loader': load_hk_share,
            'strategy': 'MA_CROSS',
            'params': {
                'fast_period': 8,
                'slow_period': 20,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.15,
                'max_position_size': 0.8,
            },
        },
        {
            'name': '美股 NVDA',
            'loader': load_us_share,
            'strategy': 'MA_CROSS',
            'params': {
                'fast_period': 10,
                'slow_period': 100,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.20,
                'max_position_size': 0.8,
            },
        },
    ]

    all_results = []

    for mkt in markets:
        print(f"\n{'─'*65}")
        print(f"  加载数据: {mkt['name']}")
        try:
            df, symbol, start, end = mkt['loader']()
            print(f"  行数: {len(df)}  |  日期: {start} ~ {end}")
            print(f"  运行回测 [{mkt['strategy']}] 参数: {mkt['params']}")

            result = run_backtest(df, symbol, mkt['strategy'], mkt['params'])
            result['market_name'] = mkt['name']
            all_results.append(result)

            sharpe_str = f"{result['sharpe_ratio']:.3f}" if result['sharpe_ratio'] is not None else "N/A"
            print(f"  ✓ 完成  |  总收益: {result['total_return']:+.2%}"
                  f"  |  年化: {result['annual_return']:+.2%}"
                  f"  |  夏普: {sharpe_str}"
                  f"  |  回撤: {result['max_drawdown']:.2f}%")

        except Exception as e:
            print(f"  ✗ 失败: {e}")
            import traceback; traceback.print_exc()

    # ── 汇总表格 ──
    if all_results:
        print(f"\n{'='*65}")
        print("  回测汇总")
        print(f"{'='*65}")
        print(f"{'市场':<16} {'总收益':>10} {'年化收益':>10} {'夏普比率':>10} "
              f"{'最大回撤':>10} {'胜率':>8} {'交易次数':>8}")
        print(f"{'─'*65}")

        for r in all_results:
            sharpe_str = f"{r['sharpe_ratio']:.3f}" if r['sharpe_ratio'] is not None else "  N/A"
            print(
                f"{r['market_name']:<16} "
                f"{r['total_return']:>+9.2%} "
                f"{r['annual_return']:>+9.2%} "
                f"{sharpe_str:>10} "
                f"{r['max_drawdown']:>9.2f}% "
                f"{r['win_rate']:>7.1%} "
                f"{r['trades']:>8}"
            )

        print(f"{'='*65}")

        # 保存结果
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_dir = f"results/backtest_results/multimarket_{ts}"
        os.makedirs(out_dir, exist_ok=True)
        rows = []
        for r in all_results:
            rows.append({
                '市场':   r['market_name'],
                '总收益': f"{r['total_return']:+.4f}",
                '年化收益': f"{r['annual_return']:+.4f}",
                '夏普比率': r['sharpe_ratio'],
                '最大回撤%': r['max_drawdown'],
                '胜率': f"{r['win_rate']:.4f}",
                '交易次数': r['trades'],
                '期末资产': r['final_value'],
            })
        out_file = f"{out_dir}/comparison.csv"
        pd.DataFrame(rows).to_csv(out_file, index=False, encoding='utf-8-sig')
        print(f"\n  结果已保存: {out_file}")


if __name__ == '__main__':
    main()
