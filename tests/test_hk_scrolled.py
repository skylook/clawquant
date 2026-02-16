"""
测试港股标签页并滚动查看完整内容
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
        
        # 切换到港股标签
        tabs = await page.locator('button[role="tab"]').all()
        await tabs[1].click()
        await page.wait_for_timeout(3000)
        
        # 滚动并截图
        print("港股标签页 - 顶部")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path='hk_top.png', full_page=False)
        
        print("港股标签页 - 中部")
        await page.evaluate("window.scrollTo(0, 800)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path='hk_middle.png', full_page=False)
        
        print("港股标签页 - 底部")
        await page.evaluate("window.scrollTo(0, 1600)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path='hk_bottom.png', full_page=False)
        
        print("港股标签页 - 完整页面")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        await page.screenshot(path='hk_complete.png', full_page=True)
        
        # 检查 iframe 内容
        iframes = await page.locator('iframe').all()
        print(f"\niframe 数量: {len(iframes)}")
        
        for i, iframe in enumerate(iframes[:3]):  # 只检查前3个
            try:
                frame = await iframe.content_frame()
                if frame:
                    html = await frame.content()
                    print(f"iframe {i+1} 内容长度: {len(html)} 字符")
                    if 'echarts' in html.lower():
                        print(f"  ✅ iframe {i+1} 包含 echarts")
            except Exception as e:
                print(f"  ❌ iframe {i+1} 无法访问: {e}")
        
        print("\n✅ 截图完成")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
