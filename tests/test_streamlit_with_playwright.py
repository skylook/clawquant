"""
使用 Playwright 测试 Streamlit 应用并截图验证
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_streamlit_app():
    """测试 Streamlit 应用的所有功能"""
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        print("📱 打开 Streamlit 应用...")
        await page.goto('http://localhost:8501')
        await page.wait_for_timeout(3000)
        
        # 截图1: 初始页面
        await page.screenshot(path='screenshot_01_initial.png', full_page=True)
        print("✅ 截图1: 初始页面")
        
        # 选择策略
        print("\n🔧 配置回测参数...")
        await page.wait_for_timeout(2000)
        
        # 勾选所有市场
        print("勾选所有市场...")
        markets = ['A股 上证指数', '港股 腾讯', '美股 NVDA']
        for market in markets:
            checkbox = page.locator(f'text="{market}"').locator('..').locator('input[type="checkbox"]')
            if not await checkbox.is_checked():
                await checkbox.check()
                await page.wait_for_timeout(500)
        
        # 截图2: 配置完成
        await page.screenshot(path='screenshot_02_configured.png', full_page=True)
        print("✅ 截图2: 配置完成")
        
        # 点击运行回测
        print("\n🚀 运行回测...")
        run_button = page.locator('button:has-text("运行回测")')
        await run_button.click()
        
        # 等待回测完成
        print("等待回测完成...")
        await page.wait_for_timeout(15000)
        
        # 截图3: A股结果
        await page.screenshot(path='screenshot_03_a_share_results.png', full_page=True)
        print("✅ 截图3: A股结果页面")
        
        # 切换到港股标签
        print("\n📊 切换到港股标签...")
        hk_tab = page.locator('button:has-text("港股 腾讯")')
        await hk_tab.click()
        await page.wait_for_timeout(2000)
        
        # 截图4: 港股结果
        await page.screenshot(path='screenshot_04_hk_share_results.png', full_page=True)
        print("✅ 截图4: 港股结果页面")
        
        # 切换到美股标签
        print("\n📊 切换到美股标签...")
        us_tab = page.locator('button:has-text("美股 NVDA")')
        await us_tab.click()
        await page.wait_for_timeout(2000)
        
        # 截图5: 美股结果
        await page.screenshot(path='screenshot_05_us_share_results.png', full_page=True)
        print("✅ 截图5: 美股结果页面")
        
        # 切换到综合对比标签
        print("\n📊 切换到综合对比标签...")
        comparison_tab = page.locator('button:has-text("综合对比")')
        await comparison_tab.click()
        await page.wait_for_timeout(2000)
        
        # 截图6: 综合对比
        await page.screenshot(path='screenshot_06_comparison.png', full_page=True)
        print("✅ 截图6: 综合对比页面")
        
        print("\n" + "="*60)
        print("测试完成！生成的截图:")
        print("  1. screenshot_01_initial.png - 初始页面")
        print("  2. screenshot_02_configured.png - 配置完成")
        print("  3. screenshot_03_a_share_results.png - A股结果")
        print("  4. screenshot_04_hk_share_results.png - 港股结果")
        print("  5. screenshot_05_us_share_results.png - 美股结果")
        print("  6. screenshot_06_comparison.png - 综合对比")
        print("="*60)
        
        await browser.close()

if __name__ == "__main__":
    print("🚀 开始测试 Streamlit 应用\n")
    asyncio.run(test_streamlit_app())
