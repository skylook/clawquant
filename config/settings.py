"""
量化交易系统全局配置
"""

import os
from datetime import datetime

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# 结果目录
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
BACKTEST_RESULTS_DIR = os.path.join(RESULTS_DIR, "backtest_results")
OPTIMIZATION_RESULTS_DIR = os.path.join(RESULTS_DIR, "optimization_results")
BEST_STRATEGIES_DIR = os.path.join(RESULTS_DIR, "best_strategies")

# 策略目录
STRATEGIES_DIR = os.path.join(PROJECT_ROOT, "strategies")

# 创建必要的目录
for directory in [
    RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_DIR,
    BACKTEST_RESULTS_DIR, OPTIMIZATION_RESULTS_DIR, BEST_STRATEGIES_DIR
]:
    os.makedirs(directory, exist_ok=True)

# ========== 交易配置 ==========
class TradingConfig:
    """交易相关配置"""
    
    # 回测时间范围
    BACKTEST_START_DATE = "2020-01-01"
    BACKTEST_END_DATE = "2024-01-01"
    
    # 测试时间范围（用于验证）
    VALIDATION_START_DATE = "2024-01-01"
    VALIDATION_END_DATE = "2024-12-31"
    
    # 初始资金
    INITIAL_CASH = 100000.0
    
    # 手续费设置
    COMMISSION = 0.0003  # 0.03% 手续费
    SLIPPAGE = 0.0001    # 0.01% 滑点
    
    # 交易品种
    SYMBOL = "000001.SH"  # 上证指数
    SYMBOL_NAME = "上证指数"
    
    # 数据频率
    FREQUENCY = "daily"  # daily, weekly, monthly
    
    # 风险控制
    MAX_POSITION_SIZE = 0.8  # 最大仓位 80%
    STOP_LOSS_RATIO = 0.05   # 止损比例 5%
    TAKE_PROFIT_RATIO = 0.10 # 止盈比例 10%

# ========== 策略配置 ==========
class StrategyConfig:
    """策略相关配置"""
    
    # 策略列表（要测试的策略类型）
    STRATEGY_TYPES = [
        "MA",      # 移动平均线策略
        "MACD",    # MACD策略
        "RSI",     # RSI策略
        "BOLL",    # 布林带策略
        "MA_CROSS" # 双均线交叉策略
    ]
    
    # 各策略的参数搜索范围
    PARAM_RANGES = {
        "MA": {
            "sma_period": [5, 10, 20, 30, 60],
            "lma_period": [20, 30, 60, 120]
        },
        "MACD": {
            "fast_period": [8, 12, 16],
            "slow_period": [21, 26, 30],
            "signal_period": [7, 9, 12]
        },
        "RSI": {
            "rsi_period": [6, 14, 21],
            "overbought": [70, 75, 80],
            "oversold": [20, 25, 30]
        },
        "BOLL": {
            "period": [10, 20, 30],
            "devfactor": [1.5, 2.0, 2.5]
        },
        "MA_CROSS": {
            "fast_period": [5, 10, 20],
            "slow_period": [20, 30, 60]
        }
    }
    
    # 优化参数
    OPTIMIZATION_METHOD = "grid_search"  # grid_search, random_search, bayesian
    MAX_OPTIMIZATION_ITERATIONS = 100  # 最大优化迭代次数

# ========== 回测配置 ==========
class BacktestConfig:
    """回测相关配置"""
    
    # 回测引擎
    BACKTEST_ENGINE = "backtrader"
    
    # 绩效指标
    METRICS = [
        "total_return",          # 总收益率
        "annual_return",         # 年化收益率
        "sharpe_ratio",         # 夏普比率
        "max_drawdown",         # 最大回撤
        "win_rate",             # 胜率
        "profit_factor",        # 盈亏比
        "calmar_ratio",         # 卡玛比率
        "sortino_ratio",        # 索提诺比率
        "volatility",           # 波动率
        "trades_count"          # 交易次数
    ]
    
    # 权重配置（用于策略排序）
    METRIC_WEIGHTS = {
        "sharpe_ratio": 0.25,
        "total_return": 0.20,
        "max_drawdown": -0.25,  # 负权重表示越小越好
        "win_rate": 0.15,
        "profit_factor": 0.15
    }

# ========== 系统配置 ==========
class SystemConfig:
    """系统配置"""
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FILE = os.path.join(PROJECT_ROOT, "logs", "clawquant.log")
    
    # 并行处理
    USE_PARALLEL = True
    MAX_WORKERS = 4
    
    # 缓存配置
    USE_CACHE = True
    CACHE_EXPIRE_HOURS = 24

# ========== 实例化配置 ==========
TRADING = TradingConfig()
STRATEGY = StrategyConfig()
BACKTEST = BacktestConfig()
SYSTEM = SystemConfig()

# 当前运行模式
CURRENT_MODE = "full"  # full, backtest, optimize

def print_config_summary():
    """打印配置摘要"""
    print("=" * 60)
    print("ClawQuant 量化交易系统配置")
    print("=" * 60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"数据目录: {DATA_DIR}")
    print(f"结果目录: {RESULTS_DIR}")
    print(f"回测时间: {TRADING.BACKTEST_START_DATE} 到 {TRADING.BACKTEST_END_DATE}")
    print(f"交易品种: {TRADING.SYMBOL_NAME} ({TRADING.SYMBOL})")
    print(f"初始资金: {TRADING.INITIAL_CASH:,.2f}")
    print(f"测试策略: {', '.join(STRATEGY.STRATEGY_TYPES)}")
    print("=" * 60)

if __name__ == "__main__":
    print_config_summary()