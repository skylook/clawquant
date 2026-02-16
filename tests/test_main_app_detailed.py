"""
详细测试主应用 - 截图并检查每个标签页
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # 先停止测试服务器，启动主应用
        import subprocess
        subprocess.run(['pkill', '-f', 'streamlit'])
        await asyncio.sleep(3)
        
        # 启动主应用
        subprocess.Popen(
            ['streamlit', 'run', 'web/streamlit_app.py', '--server.port', '8501'],
            cwd='/Users/skylook/Develop/clawquant',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        await asyncio.sleep(10)
        
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1200})
        
        print("访问主应用...")
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
        await page.wait_for_timeout(25000)
        
        # 检查 A股标签页
        print("\n=== A股标签页 ===")
        tabs = await page.locator('button[role="tab"]').all()
        await tabs[0].click()
        await page.wait_for_timeout(3000)
        
        # 检查元素
        k_line_count = await page.locator('text="K线图与均线"').count()
        equity_count = await page.locator('text="资金曲线"').count()
        iframe_count = len(await page.locator('iframe').all())
        
        print(f"K线图标题: {k_line_count}")
        print(f"资金曲线标题: {equity_count}")
        print(f"iframe数量: {iframe_count}")
        
        await page.screenshot(path='main_app_a_share.png', full_page=True)
        print("✅ 截图: main_app_a_share.png")
        
        # 检查港股标签页
        print("\n=== 港股标签页 ===")
        await tabs[1].click()
        await page.wait_for_timeout(3000)
        
        k_line_count = await page.locator('text="K线图与均线"').count()
        equity_count = await page.locator('text="资金曲线"').count()
        iframe_count = len(await page.locator('iframe').all())
        
        print(f"K线图标题: {k_line_count}")
        print(f"资金曲线标题: {equity_count}")
        print(f"iframe数量: {iframe_count}")
        
        # 检查是否有警告信息
        warnings = await page.locator('[data-testid="stAlert"]').all()
        print(f"警告数量: {len(warnings)}")
        for i, warning in enumerate(warnings):
            text = await warning.inner_text()
            print(f"  警告{i+1}: {text}")
        
        await page.screenshot(path='main_app_hk_share.png', full_page=True)
        print("✅ 截图: main_app_hk_share.png")
        
        # 检查美股标签页
        print("\n=== 美股标签页 ===")
        await tabs[2].click()
        await page.wait_for_timeout(3000)
        
        k_line_count = await page.locator('text="K线图与均线"').count()
        equity_count = await page.locator('text="资金曲线"').count()
        iframe_count = len(await page.locator('iframe').all())
        
        print(f"K线图标题: {k_line_count}")
        print(f"资金曲线标题: {equity_count}")
        print(f"iframe数量: {iframe_count}")
        
        warnings = await page.locator('[data-testid="stAlert"]').all()
        print(f"警告数量: {len(warnings)}")
        for i, warning in enumerate(warnings):
            text = await warning.inner_text()
            print(f"  警告{i+1}: {text}")
        
        await page.screenshot(path='main_app_us_share.png', full_page=True)
        print("✅ 截图: main_app_us_share.png")
        
        print("\n✅ 测试完成！")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
