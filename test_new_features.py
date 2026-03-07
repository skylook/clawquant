"""
测试新功能
验证国际化数据获取、风险管理、新策略和监控功能
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.data_fetcher import DataFetcher
from utils.risk_manager import RiskManager
from strategies.base_strategy import StrategyFactory
from backtests.enhanced_backtest_engine import EnhancedBacktestEngine
from dashboard.real_time_monitor import RealTimeDashboard


def test_international_markets():
    """测试国际市场数据获取"""
    print("=== 测试国际市场数据获取 ===")
    
    fetcher = DataFetcher()
    
    # 测试A股数据获取
    print("\n1. 测试A股数据获取...")
    try:
        a_share_data = fetcher.fetch_stock_data(
            symbol="000001.SH",
            start_date="2024-01-01",
            end_date="2024-01-31",
            frequency="daily"
        )
        print(f"   A股数据获取成功: 形状 {a_share_data.shape}")
        print(f"   数据列: {a_share_data.columns.tolist()}")
    except Exception as e:
        print(f"   A股数据获取失败: {e}")
    
    # 测试港股数据获取（使用模拟）
    print("\n2. 测试港股数据获取...")
    try:
        hk_data = fetcher.fetch_stock_data(
            symbol="0005.HK",  # 汇丰控股
            start_date="2024-01-01",
            end_date="2024-01-31",
            frequency="daily"
        )
        print(f"   港股数据获取成功: 形状 {hk_data.shape}")
        print(f"   数据列: {hk_data.columns.tolist()}")
    except Exception as e:
        print(f"   港股数据获取失败: {e}")
    
    # 测试美股数据获取（使用模拟）
    print("\n3. 测试美股数据获取...")
    try:
        us_data = fetcher.fetch_stock_data(
            symbol="AAPL",  # 苹果公司
            start_date="2024-01-01",
            end_date="2024-01-31",
            frequency="daily"
        )
        print(f"   美股数据获取成功: 形状 {us_data.shape}")
        print(f"   数据列: {us_data.columns.tolist()}")
    except Exception as e:
        print(f"   美股数据获取失败: {e}")
    
    print("\n✓ 国际市场数据获取测试完成")


def test_risk_management():
    """测试风险管理功能"""
    print("\n=== 测试风险管理功能 ===")
    
    rm = RiskManager(initial_capital=100000, max_position_size=0.10)
    
    # 测试仓位计算
    print("\n1. 测试仓位计算...")
    try:
        shares, risk_details = rm.calculate_position_size(
            entry_price=100.0,
            stop_loss_price=95.0,
            signal_strength=0.8
        )
        print(f"   建议股数: {shares}")
        print(f"   风险详情: {risk_details}")
    except Exception as e:
        print(f"   仓位计算失败: {e}")
    
    # 测试凯利公式
    print("\n2. 测试凯利公式...")
    try:
        kelly_pct = rm.calculate_kelly_position_size(
            win_rate=0.6,
            avg_win=0.1,  # 10%平均盈利
            avg_loss=0.05  # 5%平均亏损
        )
        print(f"   凯利仓位比例: {kelly_pct:.4f} ({kelly_pct*100:.2f}%)")
    except Exception as e:
        print(f"   凯利公式计算失败: {e}")
    
    # 测试波动率仓位
    print("\n3. 测试波动率仓位...")
    try:
        vol_shares = rm.calculate_volatility_position_size(
            price=100.0,
            atr=2.0,
            volatility_target=0.15
        )
        print(f"   基于波动率的股数: {vol_shares}")
    except Exception as e:
        print(f"   波动率仓位计算失败: {e}")
    
    # 测试交易验证
    print("\n4. 测试交易验证...")
    try:
        validation = rm.validate_trade(
            entry_price=100.0,
            stop_loss_price=95.0,
            take_profit_price=110.0,
            direction='long'
        )
        print(f"   交易验证结果: {validation}")
    except Exception as e:
        print(f"   交易验证失败: {e}")
    
    # 获取风险指标
    print("\n5. 获取风险指标...")
    try:
        risk_metrics = rm.get_risk_metrics()
        print(f"   风险指标: {risk_metrics}")
    except Exception as e:
        print(f"   获取风险指标失败: {e}")
    
    print("\n✓ 风险管理功能测试完成")


def test_new_strategies():
    """测试新策略"""
    print("\n=== 测试新策略 ===")
    
    # 测试策略工厂是否能创建新策略
    available_strategies = StrategyFactory.get_available_strategies()
    print(f"\n可用策略: {available_strategies}")
    
    new_strategies = ['MOMENTUM', 'MEAN_REVERSION', 'BREAKOUT', 'TREND_FOLLOWING']
    for strategy_type in new_strategies:
        if strategy_type in available_strategies:
            print(f"   ✓ {strategy_type} 策略已注册")
        else:
            print(f"   ✗ {strategy_type} 策略未注册")
    
    # 测试创建新策略实例
    for strategy_type in new_strategies[:2]:  # 只测试前两个
        try:
            strategy = StrategyFactory.create_strategy(strategy_type)
            print(f"   ✓ {strategy_type} 策略实例创建成功")
        except Exception as e:
            print(f"   ✗ {strategy_type} 策略实例创建失败: {e}")
    
    print("\n✓ 新策略测试完成")


def test_enhanced_backtest():
    """测试增强版回测引擎"""
    print("\n=== 测试增强版回测引擎 ===")
    
    engine = EnhancedBacktestEngine()
    
    # 测试数据准备
    print("\n1. 测试数据准备...")
    try:
        data = engine.prepare_data(
            symbol="000001.SH",
            start_date="2024-01-01",
            end_date="2024-01-31",
            frequency="daily"
        )
        print(f"   数据准备成功: 形状 {data.shape}")
    except Exception as e:
        print(f"   数据准备失败: {e}")
    
    # 测试简单回测
    print("\n2. 测试简单回测...")
    try:
        result = engine.run_backtest(
            strategy_type='MA',
            params={'sma_period': 10, 'lma_period': 20},
            symbol='000001.SH',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        print(f"   回测成功!")
        print(f"   总收益率: {result['total_return']:.2%}")
        print(f"   性能指标: {result['performance'].keys()}")
        print(f"   风险指标: {result.get('risk_metrics', {}).keys()}")
    except Exception as e:
        print(f"   回测失败: {e}")
    
    print("\n✓ 增强版回测引擎测试完成")


def test_monitoring_dashboard():
    """测试监控仪表板"""
    print("\n=== 测试监控仪表板 ===")
    
    dashboard = RealTimeDashboard(refresh_interval=60)
    
    # 添加策略到监控
    sample_strategy = {
        'strategy_type': 'MA',
        'params': {'sma_period': 10, 'lma_period': 20},
        'symbol': '000001.SH'
    }
    
    dashboard.add_strategy_for_monitoring(sample_strategy)
    print(f"\n已添加策略到监控: {sample_strategy['strategy_type']}")
    
    # 获取仪表板状态
    status = dashboard.get_dashboard_status()
    print(f"\n仪表板状态: {status}")
    
    # 尝试导出数据
    try:
        export_path = dashboard.export_dashboard_data()
        print(f"\n✓ 仪表板数据导出成功: {export_path}")
    except Exception as e:
        print(f"\n✗ 仪表板数据导出失败: {e}")
    
    print("\n✓ 监控仪表板测试完成")


def main():
    """主测试函数"""
    print("开始测试 ClawQuant 新功能...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        test_international_markets()
        test_risk_management()
        test_new_strategies()
        test_enhanced_backtest()
        test_monitoring_dashboard()
        
        print("\n" + "="*50)
        print("✓ 所有测试完成！")
        print("="*50)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()