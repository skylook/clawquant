"""
简化的 Playwright 自动化测试
"""
import asyncio
import time
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        print("启动浏览器...")
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1200})
        page = await context.new_page()
        
        print("\n1. 访问 Streamlit 应用...")
        await page.goto('http://localhost:8501', wait_until='networkidle')
        await page.wait_for_timeout(5000)
        await page.screenshot(path='screenshot_01_initial.png', full_page=True)
        print("✅ 截图保存: screenshot_01_initial.png")
        
        print("\n2. 勾选所有市场...")
        # 使用更可靠的选择器
        checkboxes = await page.locator('input[type="checkbox"]').all()
        print(f"找到 {len(checkboxes)} 个复选框")
        for i, checkbox in enumerate(checkboxes):
            if not await checkbox.is_checked():
                await checkbox.check()
                print(f"  勾选复选框 {i+1}")
                await page.wait_for_timeout(500)
        
        await page.screenshot(path='screenshot_02_markets_selected.png', full_page=True)
        print("✅ 截图保存: screenshot_02_markets_selected.png")
        
        print("\n3. 点击运行回测...")
        run_btn = page.locator('button:has-text("运行回测")')
        await run_btn.click()
        print("等待回测完成 (20秒)...")
        await page.wait_for_timeout(20000)
        
        await page.screenshot(path='screenshot_03_after_backtest.png', full_page=True)
        print("✅ 截图保存: screenshot_03_after_backtest.png")
        
        print("\n4. 检查 A股 标签页...")
        tabs = await page.locator('button[role="tab"]').all()
        print(f"找到 {len(tabs)} 个标签页")
        if len(tabs) > 0:
            await tabs[0].click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshot_04_a_share.png', full_page=True)
            print("✅ 截图保存: screenshot_04_a_share.png")
        
        print("\n5. 检查 港股 标签页...")
        if len(tabs) > 1:
            await tabs[1].click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshot_05_hk_share.png', full_page=True)
            print("✅ 截图保存: screenshot_05_hk_share.png")
        
        print("\n6. 检查 美股 标签页...")
        if len(tabs) > 2:
            await tabs[2].click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshot_06_us_share.png', full_page=True)
            print("✅ 截图保存: screenshot_06_us_share.png")
        
        print("\n7. 检查 综合对比 标签页...")
        if len(tabs) > 3:
            await tabs[3].click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path='screenshot_07_comparison.png', full_page=True)
            print("✅ 截图保存: screenshot_07_comparison.png")
        
        print("\n" + "="*60)
        print("✅ 测试完成！已生成所有截图")
        print("="*60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
