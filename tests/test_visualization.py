"""
测试可视化模块 - 验证 K 线图绘制功能
"""

import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from web.charts import draw_pro_kline, draw_equity_curve, draw_result_bar

def test_kline_chart():
    """测试 K 线图绘制"""
    print("=" * 60)
    print("测试 K 线图绘制功能")
    print("=" * 60)
    
    # 加载测试数据
    try:
        df = pd.read_csv("data/raw/000001.SH_daily_2020-01-01_2024-01-01.csv")
        print(f"✅ 成功加载数据: {len(df)} 行")
        print(f"原始列名: {list(df.columns)}")
        
        # 转换为中文列名
        df['date'] = pd.to_datetime(df['date'])
        df_chart = df.rename(columns={
            'date': '日期',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量'
        })
        
        # 格式化日期
        df_chart['日期'] = df_chart['日期'].dt.strftime('%Y-%m-%d')
        
        # 只保留需要的列
        df_chart = df_chart[['日期', '开盘', '最高', '最低', '收盘', '成交量']]
        
        # 取最近 100 天数据
        df_chart = df_chart.tail(100)
        
        print(f"转换后列名: {list(df_chart.columns)}")
        print(f"数据样本:\n{df_chart.head()}")
        
        # 绘制 K 线图
        print("\n开始绘制 K 线图...")
        chart = draw_pro_kline(df_chart)
        print("✅ K 线图绘制成功！")
        
        # 保存为 HTML
        output_path = "test_kline.html"
        chart.render(output_path)
        print(f"✅ K 线图已保存到: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_equity_curve():
    """测试资金曲线图"""
    print("\n" + "=" * 60)
    print("测试资金曲线图绘制功能")
    print("=" * 60)
    
    try:
        # 模拟资金曲线数据
        equity_data = [100000 + i * 500 for i in range(100)]
        
        print(f"生成测试数据: {len(equity_data)} 个点")
        
        # 绘制资金曲线
        chart = draw_equity_curve(equity_data)
        print("✅ 资金曲线图绘制成功！")
        
        # 保存为 HTML
        output_path = "test_equity.html"
        chart.render(output_path)
        print(f"✅ 资金曲线图已保存到: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_result_bar():
    """测试对比柱状图"""
    print("\n" + "=" * 60)
    print("测试对比柱状图绘制功能")
    print("=" * 60)
    
    try:
        # 模拟对比数据
        data = {
            'market': ['A股', '港股', '美股'],
            'total_return': [15.5, 22.3, 35.8],
            'annual_return': [12.3, 18.5, 28.2],
            'max_drawdown': [8.5, 12.3, 15.6]
        }
        df = pd.DataFrame(data)
        
        print(f"生成测试数据:\n{df}")
        
        # 绘制对比图
        chart = draw_result_bar(df)
        print("✅ 对比柱状图绘制成功！")
        
        # 保存为 HTML
        output_path = "test_comparison.html"
        chart.render(output_path)
        print(f"✅ 对比柱状图已保存到: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 开始测试可视化模块\n")
    
    results = []
    results.append(("K线图", test_kline_chart()))
    results.append(("资金曲线图", test_equity_curve()))
    results.append(("对比柱状图", test_result_bar()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！可视化模块工作正常。")
        print("\n下一步：运行 streamlit run web/streamlit_app.py 启动完整应用")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")
