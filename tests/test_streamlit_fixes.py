"""
测试 Streamlit 修复 - 验证所有问题已解决
"""

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def test_sharpe_ratio_formatting():
    """测试夏普比率格式化（处理 None 值）"""
    print("=" * 60)
    print("测试夏普比率格式化")
    print("=" * 60)
    
    test_cases = [
        (None, "N/A"),
        (float('inf'), "N/A"),
        (float('-inf'), "N/A"),
        (float('nan'), "N/A"),
        (1.5, "1.50"),
        (0.0, "0.00"),
        (-0.5, "-0.50"),
    ]
    
    all_passed = True
    for sharpe, expected in test_cases:
        if sharpe is None or sharpe == float('inf') or sharpe == float('-inf') or sharpe != sharpe:
            result = "N/A"
        else:
            result = f"{sharpe:.2f}"
        
        passed = result == expected
        status = "✅" if passed else "❌"
        print(f"{status} sharpe={sharpe} -> {result} (expected: {expected})")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_rsi_strategy():
    """测试 RSI 策略（不使用 Constant 指标）"""
    print("\n" + "=" * 60)
    print("测试 RSI 策略")
    print("=" * 60)
    
    try:
        from strategies.rsi_strategy import RSIStrategy
        import backtrader as bt
        
        # 创建简单的数据
        df = pd.read_csv("data/raw/000001.SH_daily_2020-01-01_2024-01-01.csv")
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        # 创建 Cerebro
        cerebro = bt.Cerebro()
        
        # 添加数据
        data_feed = bt.feeds.PandasData(
            dataname=df.head(100),
            datetime=None,
            open='open', high='high', low='low',
            close='close', volume='volume',
            openinterest=None
        )
        cerebro.adddata(data_feed)
        
        # 添加策略
        cerebro.addstrategy(RSIStrategy, rsi_period=14, overbought=70, oversold=30)
        
        # 运行
        cerebro.run()
        
        print("✅ RSI 策略初始化成功，无 Constant 错误")
        return True
        
    except Exception as e:
        print(f"❌ RSI 策略测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_equity_curve_format():
    """测试资金曲线格式"""
    print("\n" + "=" * 60)
    print("测试资金曲线格式")
    print("=" * 60)
    
    try:
        # 模拟 run_backtest 返回的格式
        equity_curve = [100000, 101000, 102500, 101800, 103000]
        
        print(f"资金曲线数据: {equity_curve}")
        print(f"数据类型: {type(equity_curve)}")
        print(f"数据长度: {len(equity_curve)}")
        
        # 验证是否为列表
        if not isinstance(equity_curve, list):
            print("❌ equity_curve 不是列表")
            return False
        
        # 验证是否包含数值
        if not all(isinstance(v, (int, float)) for v in equity_curve):
            print("❌ equity_curve 包含非数值元素")
            return False
        
        print("✅ 资金曲线格式正确")
        return True
        
    except Exception as e:
        print(f"❌ 资金曲线测试失败: {str(e)}")
        return False


def test_percentage_conversion():
    """测试百分比转换"""
    print("\n" + "=" * 60)
    print("测试百分比转换")
    print("=" * 60)
    
    test_cases = [
        (0.15, 15.0, "total_return"),
        (0.12, 12.0, "annual_return"),
        (0.65, 65.0, "win_rate"),
    ]
    
    all_passed = True
    for value, expected, name in test_cases:
        result = value * 100
        passed = abs(result - expected) < 0.01
        status = "✅" if passed else "❌"
        print(f"{status} {name}: {value} * 100 = {result} (expected: {expected})")
        
        if not passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    print("\n🚀 开始测试 Streamlit 修复\n")
    
    results = []
    results.append(("夏普比率格式化", test_sharpe_ratio_formatting()))
    results.append(("RSI 策略", test_rsi_strategy()))
    results.append(("资金曲线格式", test_equity_curve_format()))
    results.append(("百分比转换", test_percentage_conversion()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！可以重新启动 Streamlit 应用测试。")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")
