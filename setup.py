"""
ClawQuant 安装脚本
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    
    if sys.version_info < (3, 8):
        print(f"错误: 需要Python 3.8或更高版本，当前版本: {sys.version}")
        return False
    
    print(f"Python版本: {sys.version} ✓")
    return True


def check_dependencies():
    """检查依赖"""
    print("\n检查依赖...")
    
    required_packages = [
        'backtrader',
        'pandas',
        'numpy',
        'matplotlib',
        'seaborn',
        'akshare',
        'tushare',
        'scipy',
        'scikit-learn',
        'loguru',
        'colorama',
        'pyyaml',
        'python-dotenv',
        'tqdm',
        'joblib'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  {package}: 已安装 ✓")
        except ImportError:
            missing_packages.append(package)
            print(f"  {package}: 未安装 ✗")
    
    return missing_packages


def install_dependencies(missing_packages):
    """安装缺失的依赖"""
    if not missing_packages:
        print("\n所有依赖已安装 ✓")
        return True
    
    print(f"\n安装缺失的依赖 ({len(missing_packages)}个)...")
    
    try:
        # 使用pip安装
        cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
        subprocess.check_call(cmd)
        
        print("依赖安装完成 ✓")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}")
        return False


def install_system_dependencies():
    """安装系统依赖"""
    print("\n检查系统依赖...")
    
    system = platform.system().lower()
    
    if system == 'linux':
        # 检查并安装Linux依赖
        try:
            # 检查是否已安装必要的系统工具
            required_tools = ['curl', 'wget', 'git', 'tmux']
            missing_tools = []
            
            for tool in required_tools:
                result = subprocess.run(['which', tool], capture_output=True, text=True)
                if result.returncode != 0:
                    missing_tools.append(tool)
                    print(f"  {tool}: 未安装 ✗")
                else:
                    print(f"  {tool}: 已安装 ✓")
            
            if missing_tools:
                print(f"\n需要安装系统工具: {', '.join(missing_tools)}")
                print("请使用系统包管理器安装，例如:")
                print("  Ubuntu/Debian: sudo apt-get install " + " ".join(missing_tools))
                print("  CentOS/RHEL: sudo yum install " + " ".join(missing_tools))
                print("  Arch: sudo pacman -S " + " ".join(missing_tools))
        
        except Exception as e:
            print(f"检查系统工具时出错: {e}")
    
    elif system == 'darwin':  # macOS
        print("macOS系统依赖检查...")
        # 可以添加Homebrew检查等
    
    elif system == 'windows':
        print("Windows系统依赖检查...")
        # 可以添加Windows特定检查
    
    return True


def create_directories():
    """创建必要的目录"""
    print("\n创建项目目录...")
    
    base_dir = Path(__file__).parent
    directories = [
        'data/raw',
        'data/processed',
        'data/cache',
        'results/backtest_results',
        'results/optimization_results',
        'results/best_strategies',
        'results/final_configuration',
        'logs'
    ]
    
    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  创建: {dir_path} ✓")
    
    return True


def create_config_file():
    """创建配置文件"""
    print("\n创建配置文件...")
    
    config_template = """# ClawQuant 配置文件
# 可以根据需要修改这些配置

# 交易配置
TRADING_CONFIG = {
    # 回测时间范围
    'BACKTEST_START_DATE': '2020-01-01',
    'BACKTEST_END_DATE': '2024-01-01',
    
    # 验证时间范围
    'VALIDATION_START_DATE': '2024-01-01',
    'VALIDATION_END_DATE': '2024-12-31',
    
    # 初始资金
    'INITIAL_CASH': 100000.0,
    
    # 手续费和滑点
    'COMMISSION': 0.0003,  # 0.03%
    'SLIPPAGE': 0.0001,    # 0.01%
    
    # 交易品种
    'SYMBOL': '000001.SH',  # 上证指数
    'SYMBOL_NAME': '上证指数',
    
    # 数据频率
    'FREQUENCY': 'daily',  # daily, weekly, monthly
    
    # 风险控制
    'MAX_POSITION_SIZE': 0.8,   # 最大仓位 80%
    'STOP_LOSS_RATIO': 0.05,    # 止损比例 5%
    'TAKE_PROFIT_RATIO': 0.10   # 止盈比例 10%
}

# 策略配置
STRATEGY_CONFIG = {
    # 要测试的策略类型
    'STRATEGY_TYPES': [
        'MA',      # 移动平均线策略
        'MACD',    # MACD策略
        'RSI',     # RSI策略
        'BOLL',    # 布林带策略
        'MA_CROSS' # 双均线交叉策略
    ],
    
    # 优化参数
    'OPTIMIZATION_METHOD': 'grid_search',  # grid_search, random_search
    'MAX_OPTIMIZATION_ITERATIONS': 100
}

# 回测配置
BACKTEST_CONFIG = {
    # 绩效指标权重（用于策略排序）
    'METRIC_WEIGHTS': {
        'sharpe_ratio': 0.25,      # 夏普比率
        'total_return': 0.20,      # 总收益率
        'max_drawdown': -0.25,     # 最大回撤（负权重表示越小越好）
        'win_rate': 0.15,          # 胜率
        'profit_factor': 0.15      # 盈亏比
    }
}

# 系统配置
SYSTEM_CONFIG = {
    # 日志配置
    'LOG_LEVEL': 'INFO',
    
    # 并行处理
    'USE_PARALLEL': True,
    'MAX_WORKERS': 4,
    
    # 缓存配置
    'USE_CACHE': True,
    'CACHE_EXPIRE_HOURS': 24
}
"""
    
    config_file = Path(__file__).parent / 'config' / 'user_config.py'
    
    if not config_file.exists():
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_template)
        
        print(f"  创建: config/user_config.py ✓")
        print(f"  注意: 请根据需求修改配置文件")
    else:
        print(f"  配置文件已存在: config/user_config.py ✓")
    
    return True


def setup_environment():
    """设置环境"""
    print("\n设置环境...")
    
    # 创建.env文件（如果需要）
    env_file = Path(__file__).parent / '.env'
    
    if not env_file.exists():
        env_template = """# ClawQuant 环境变量
# 在这里设置API密钥和其他环境变量

# 数据API密钥（可选）
# TUSHARE_TOKEN=your_tushare_token_here
# AKSHARE_NO_PROXY=true

# AI API密钥（用于未来扩展）
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here
# GEMINI_API_KEY=your_gemini_key_here

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/clawquant.log
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_template)
        
        print(f"  创建: .env ✓")
        print(f"  注意: 请根据需要设置API密钥")
    else:
        print(f"  环境文件已存在: .env ✓")
    
    return True


def test_installation():
    """测试安装"""
    print("\n测试安装...")
    
    try:
        # 测试导入主要模块
        test_code = """
import sys
sys.path.insert(0, '.')

try:
    from config.settings import TRADING, STRATEGY, BACKTEST, SYSTEM
    from strategies.base_strategy import BaseStrategy
    from backtests.backtest_engine import BacktestEngine
    from backtests.optimizer import StrategyOptimizer
    from backtests.analyzer import BacktestAnalyzer
    
    print("✓ 所有模块导入成功")
    
    # 测试配置
    print(f"✓ 交易品种: {TRADING.SYMBOL}")
    print(f"✓ 策略类型: {', '.join(STRATEGY.STRATEGY_TYPES)}")
    print(f"✓ 初始资金: {TRADING.INITIAL_CASH:,.2f}")
    
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
"""
        
        result = subprocess.run(
            [sys.executable, "-c", test_code],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(result.stdout)
            print("安装测试通过 ✓")
            return True
        else:
            print("安装测试失败:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return False


def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 60)
    print("ClawQuant 量化交易系统安装完成!")
    print("=" * 60)
    
    project_dir = Path(__file__).parent
    
    print(f"\n📁 项目目录: {project_dir}")
    print("\n🚀 快速开始:")
    print("  1. 进入项目目录:")
    print(f"     cd {project_dir}")
    print("  2. 运行完整量化流程:")
    print("     python main.py --mode full")
    print("  3. 或只运行回测:")
    print("     python main.py --mode backtest")
    print("  4. 或只运行优化:")
    print("     python main.py --mode optimize")
    
    print("\n⚙️  配置选项:")
    print("  --symbol: 设置交易品种，如 --symbol 000001.SH")
    print("  --start-date: 设置开始日期，如 --start-date 2023-01-01")
    print("  --end-date: 设置结束日期，如 --end-date 2023-12-31")
    print("  --initial-cash: 设置初始资金，如 --initial-cash 100000")
    
    print("\n📊 结果查看:")
    print(f"  回测结果: {project_dir}/results/backtest_results/")
    print(f"  优化结果: {project_dir}/results/optimization_results/")
    print(f"  最佳策略: {project_dir}/results/best_strategies/")
    print(f"  最终配置: {project_dir}/results/final_configuration/")
    
    print("\n🔧 自定义配置:")
    print(f"  1. 编辑配置文件: {project_dir}/config/user_config.py")
    print(f"  2. 设置环境变量: {project_dir}/.env")
    print(f"  3. 修改策略参数: {project_dir}/config/strategy_config.py")
    
    print("\n📚 文档:")
    print(f"  项目说明: {project_dir}/README.md")
    print("  策略文档: strategies/ 目录下的各个策略文件")
    
    print("\n" + "=" * 60)
    print("开始你的量化交易之旅吧! 🚀")
    print("=" * 60)


def main():
    """主安装函数"""
    print("=" * 60)
    print("ClawQuant 量化交易系统安装程序")
    print("=" * 60)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查依赖
    missing_packages = check_dependencies()
    
    # 安装缺失的依赖
    if missing_packages:
        if not install_dependencies(missing_packages):
            print("\n⚠️  依赖安装失败，请手动安装:")
            print(f"   pip install {' '.join(missing_packages)}")
            sys.exit(1)
    
    # 安装系统依赖
    install_system_dependencies()
    
    # 创建目录
    if not create_directories():
        sys.exit(1)
    
    # 创建配置文件
    if not create_config_file():
        sys.exit(1)
    
    # 设置环境
    if not setup_environment():
        sys.exit(1)
    
    # 测试安装
    if not test_installation():
        print("\n⚠️  安装测试失败，但系统可能仍然可用")
        print("  请检查错误信息并手动修复")
    
    # 显示使用说明
    show_usage()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())