"""
调试脚本 - 检查回测结果中的数据结构
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import run_multimarket_backtest as rmb

print("="*60)
print("测试 A股")
print("="*60)
df_a, sym_a, start_a, end_a = rmb.load_a_share()
result_a = rmb.run_backtest(df_a, sym_a, "MA_CROSS", {})
print(f"A股 result keys: {result_a.keys()}")
print(f"A股 df 存在: {'df' in result_a}")
if 'df' in result_a:
    print(f"A股 df 类型: {type(result_a['df'])}")
    print(f"A股 df 是否为空: {result_a['df'] is None or result_a['df'].empty}")
    if result_a['df'] is not None and not result_a['df'].empty:
        print(f"A股 df 列: {list(result_a['df'].columns)}")
        print(f"A股 df 形状: {result_a['df'].shape}")
        print(f"A股 df 前3行:\n{result_a['df'].head(3)}")

print("\n" + "="*60)
print("测试 港股")
print("="*60)
df_hk, sym_hk, start_hk, end_hk = rmb.load_hk_share()
result_hk = rmb.run_backtest(df_hk, sym_hk, "MA_CROSS", {})
print(f"港股 result keys: {result_hk.keys()}")
print(f"港股 df 存在: {'df' in result_hk}")
if 'df' in result_hk:
    print(f"港股 df 类型: {type(result_hk['df'])}")
    print(f"港股 df 是否为空: {result_hk['df'] is None or result_hk['df'].empty}")
    if result_hk['df'] is not None and not result_hk['df'].empty:
        print(f"港股 df 列: {list(result_hk['df'].columns)}")
        print(f"港股 df 形状: {result_hk['df'].shape}")
        print(f"港股 df 前3行:\n{result_hk['df'].head(3)}")

print("\n" + "="*60)
print("测试 美股")
print("="*60)
df_us, sym_us, start_us, end_us = rmb.load_us_share()
result_us = rmb.run_backtest(df_us, sym_us, "MA_CROSS", {})
print(f"美股 result keys: {result_us.keys()}")
print(f"美股 df 存在: {'df' in result_us}")
if 'df' in result_us:
    print(f"美股 df 类型: {type(result_us['df'])}")
    print(f"美股 df 是否为空: {result_us['df'] is None or result_us['df'].empty}")
    if result_us['df'] is not None and not result_us['df'].empty:
        print(f"美股 df 列: {list(result_us['df'].columns)}")
        print(f"美股 df 形状: {result_us['df'].shape}")
        print(f"美股 df 前3行:\n{result_us['df'].head(3)}")

print("\n" + "="*60)
print("检查 equity_curve_detailed")
print("="*60)
for name, result in [("A股", result_a), ("港股", result_hk), ("美股", result_us)]:
    if 'equity_curve_detailed' in result:
        ec = result['equity_curve_detailed']
        print(f"{name} equity_curve_detailed 长度: {len(ec)}")
        if len(ec) > 0:
            print(f"{name} 第一条: {ec[0]}")
            print(f"{name} 最后一条: {ec[-1]}")
    else:
        print(f"{name} 缺少 equity_curve_detailed")
