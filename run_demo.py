#!/usr/bin/env python3
"""
ClawQuant 演示脚本
一键运行所有新功能演示
"""

import sys
import os

def main():
    """主函数"""
    print("🔍 ClawQuant 新功能演示启动器")
    print("="*50)
    
    # 获取项目路径
    project_dir = os.path.dirname(os.path.abspath(__file__))
    demo_script = os.path.join(project_dir, "demo_new_features.py")
    
    if not os.path.exists(demo_script):
        print(f"❌ 演示脚本不存在: {demo_script}")
        return 1
    
    print(f"📁 项目路径: {project_dir}")
    print(f"🎬 运行演示脚本: {demo_script}")
    print("-" * 50)
    
    # 运行演示
    import subprocess
    try:
        result = subprocess.run([sys.executable, demo_script], 
                              cwd=project_dir, 
                              capture_output=True, 
                              text=True)
        
        print(result.stdout)
        if result.stderr:
            print("⚠️  标准错误输出:")
            print(result.stderr)
        
        print(f"\n✅ 演示完成，返回码: {result.returncode}")
        return result.returncode
        
    except Exception as e:
        print(f"❌ 运行演示时出错: {e}")
        return 1

if __name__ == "__main__":
    exit(main())