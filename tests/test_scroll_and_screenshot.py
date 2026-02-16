"""
测试滚动并截图 - 检查图表是否在页面下方
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("访问 Streamlit...")
        await page.goto('http://localhost:8501', wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        print("勾选所有市场...")
        checkboxes = await page.locator('input[type="checkbox"]').all()
        for checkbox in checkboxes:
            if not await checkbox.is_checked():
                await checkbox.check()
                await page.wait_for_timeout(300)
        
        print("运行回测...")
        await page.locator('button:has-text("运行回测")').click()
        await page.wait_for_timeout(20000)
        
        # 切换到港股标签
        print("\n切换到港股标签...")
        tabs = await page.locator('button[role="tab"]').all()
        if len(tabs) > 1:
            await tabs[1].click()
            await page.wait_for_timeout(3000)
            
            # 滚动页面查看所有内容
            print("滚动页面...")
            await page.evaluate("window.scrollTo(0, 500)")
            await page.wait_for_timeout(1000)
            
            await page.screenshot(path='hk_scrolled_500.png', full_page=False)
            print("✅ 截图: hk_scrolled_500.png")
            
            await page.evaluate("window.scrollTo(0, 1000)")
            await page.wait_for_timeout(1000)
            
            await page.screenshot(path='hk_scrolled_1000.png', full_page=False)
            print("✅ 截图: hk_scrolled_1000.png")
            
            # 完整页面截图
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)
            await page.screenshot(path='hk_full_page.png', full_page=True)
            print("✅ 截图: hk_full_page.png (完整页面)")
            
            # 检查页面元素
            print("\n检查页面元素...")
            k_line_header = await page.locator('text="K线图与均线"').count()
            equity_header = await page.locator('text="资金曲线"').count()
            trade_header = await page.locator('text="交易记录"').count()
            
            print(f"K线图标题数量: {k_line_header}")
            print(f"资金曲线标题数量: {equity_header}")
            print(f"交易记录标题数量: {trade_header}")
            
            # 检查是否有 iframe (pyecharts 图表通常在 iframe 中)
            iframes = await page.locator('iframe').all()
            print(f"iframe 数量: {len(iframes)}")
            
            # 检查是否有错误消息
            warnings = await page.locator('[data-testid="stAlert"]').all()
            print(f"警告/错误消息数量: {len(warnings)}")
            if len(warnings) > 0:
                for i, warning in enumerate(warnings):
                    text = await warning.inner_text()
                    print(f"  警告 {i+1}: {text[:100]}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
