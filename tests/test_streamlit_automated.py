"""
自动化测试 Streamlit 应用 - 简化版
"""
import asyncio
from playwright.async_api import async_playwright

async def test_app():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("📱 访问 Streamlit...")
        await page.goto('http://localhost:8501')
        await page.wait_for_timeout(5000)
        
        print("✅ 截图1: 初始页面")
        await page.screenshot(path='test_01_initial.png', full_page=True)
        
        # 勾选所有市场
        print("\n勾选所有市场...")
        await page.locator('text="A股 上证指数"').locator('..').locator('input').check()
        await page.wait_for_timeout(500)
        await page.locator('text="港股 腾讯"').locator('..').locator('input').check()
        await page.wait_for_timeout(500)
        await page.locator('text="美股 NVDA"').locator('..').locator('input').check()
        await page.wait_for_timeout(500)
        
        print("✅ 截图2: 已勾选市场")
        await page.screenshot(path='test_02_markets_selected.png', full_page=True)
        
        # 运行回测
        print("\n🚀 点击运行回测...")
        await page.locator('button:has-text("运行回测")').click()
        
        # 等待回测完成
        print("等待回测完成...")
        await page.wait_for_timeout(20000)
        
        print("✅ 截图3: A股结果")
        await page.screenshot(path='test_03_a_share.png', full_page=True)
        
        # 切换到港股
        print("\n切换到港股...")
        await page.locator('button:has-text("港股 腾讯")').click()
        await page.wait_for_timeout(2000)
        
        print("✅ 截图4: 港股结果")
        await page.screenshot(path='test_04_hk_share.png', full_page=True)
        
        # 切换到美股
        print("\n切换到美股...")
        await page.locator('button:has-text("美股 NVDA")').click()
        await page.wait_for_timeout(2000)
        
        print("✅ 截图5: 美股结果")
        await page.screenshot(path='test_05_us_share.png', full_page=True)
        
        # 切换到综合对比
        print("\n切换到综合对比...")
        await page.locator('button:has-text("综合对比")').click()
        await page.wait_for_timeout(2000)
        
        print("✅ 截图6: 综合对比")
        await page.screenshot(path='test_06_comparison.png', full_page=True)
        
        print("\n" + "="*60)
        print("✅ 测试完成！生成的截图:")
        print("  test_01_initial.png")
        print("  test_02_markets_selected.png")
        print("  test_03_a_share.png")
        print("  test_04_hk_share.png")
        print("  test_05_us_share.png")
        print("  test_06_comparison.png")
        print("="*60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_app())
