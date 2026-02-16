"""
完整页面验证 - 检查所有图表和数据
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        await page.goto('http://localhost:8501', wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # 勾选所有市场
        checkboxes = await page.locator('input[type="checkbox"]').all()
        for checkbox in checkboxes:
            if not await checkbox.is_checked():
                await checkbox.check()
                await page.wait_for_timeout(300)
        
        # 运行回测
        await page.locator('button:has-text("运行回测")').click()
        await page.wait_for_timeout(25000)
        
        # 测试每个标签页
        tabs = await page.locator('button[role="tab"]').all()
        
        for i, tab_name in enumerate(['A股', '港股', '美股', '综合对比']):
            print(f"\n{'='*60}")
            print(f"测试 {tab_name} 标签页")
            print('='*60)
            
            await tabs[i].click()
            await page.wait_for_timeout(2000)
            
            # 完整页面截图
            await page.screenshot(path=f'final_{tab_name}_full.png', full_page=True)
            print(f"✅ 完整截图: final_{tab_name}_full.png")
            
            # 检查元素
            if i < 3:  # 前三个是市场标签页
                # 滚动到资金曲线
                await page.evaluate("window.scrollTo(0, 800)")
                await page.wait_for_timeout(1000)
                await page.screenshot(path=f'final_{tab_name}_equity.png', full_page=False)
                print(f"✅ 资金曲线截图: final_{tab_name}_equity.png")
                
                # 滚动到交易记录
                await page.evaluate("window.scrollTo(0, 1400)")
                await page.wait_for_timeout(1000)
                await page.screenshot(path=f'final_{tab_name}_trades.png', full_page=False)
                print(f"✅ 交易记录截图: final_{tab_name}_trades.png")
            
            # 回到顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
