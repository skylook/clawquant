"""
日志工具模块
"""

import os
import sys
import pandas as pd
from loguru import logger
from datetime import datetime

from config.settings import PROJECT_ROOT, SYSTEM


def setup_logger(log_level: str = None, log_file: str = None):
    """
    设置日志配置
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径
    """
    # 使用配置中的默认值
    if log_level is None:
        log_level = SYSTEM.LOG_LEVEL
    
    if log_file is None:
        log_file = SYSTEM.LOG_FILE
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)
    
    # 移除默认的处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 添加文件处理器
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",  # 日志文件大小达到10MB时轮转
        retention="30 days",  # 保留30天的日志
        compression="zip"  # 压缩旧日志
    )
    
    # 添加错误日志单独文件
    error_log_file = log_file.replace('.log', '_error.log')
    logger.add(
        error_log_file,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="5 MB",
        retention="60 days",
        compression="zip"
    )
    
    logger.info(f"日志系统初始化完成，级别: {log_level}")
    logger.info(f"日志文件: {log_file}")
    
    return logger


def log_performance(metrics: dict, strategy_name: str, params: dict = None):
    """
    记录策略性能
    
    Args:
        metrics: 性能指标字典
        strategy_name: 策略名称
        params: 策略参数
    """
    logger.info(f"策略性能报告 - {strategy_name}")
    logger.info("-" * 50)
    
    if params:
        logger.info(f"参数配置: {params}")
    
    # 记录关键指标
    key_metrics = [
        ('总收益率', 'total_return'),
        ('年化收益率', 'annual_return'),
        ('夏普比率', 'sharpe_ratio'),
        ('最大回撤', 'max_drawdown'),
        ('胜率', 'win_rate'),
        ('交易次数', 'trades_count'),
        ('盈亏比', 'profit_factor')
    ]
    
    for display_name, metric_key in key_metrics:
        if metric_key in metrics:
            value = metrics[metric_key]
            if isinstance(value, float):
                logger.info(f"{display_name}: {value:.4f}")
            else:
                logger.info(f"{display_name}: {value}")
    
    logger.info("-" * 50)


def log_optimization_result(best_params: dict, best_score: float, 
                           strategy_name: str, iteration: int = None):
    """
    记录优化结果
    
    Args:
        best_params: 最优参数
        best_score: 最优分数
        strategy_name: 策略名称
        iteration: 迭代次数
    """
    if iteration:
        logger.info(f"优化迭代 {iteration} - {strategy_name}")
    
    logger.info(f"找到最优参数: {best_params}")
    logger.info(f"最优分数: {best_score:.6f}")
    
    # 保存优化结果到文件
    opt_result_dir = os.path.join(PROJECT_ROOT, "results", "optimization_results")
    os.makedirs(opt_result_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = os.path.join(opt_result_dir, f"{strategy_name}_opt_{timestamp}.txt")
    
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(f"策略: {strategy_name}\n")
        f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"最优分数: {best_score:.6f}\n")
        f.write(f"最优参数:\n")
        for key, value in best_params.items():
            f.write(f"  {key}: {value}\n")
    
    logger.info(f"优化结果已保存: {result_file}")


def log_data_info(data: pd.DataFrame, data_name: str):
    """
    记录数据信息
    
    Args:
        data: 数据DataFrame
        data_name: 数据名称
    """
    logger.info(f"数据信息 - {data_name}")
    logger.info(f"数据形状: {data.shape}")
    logger.info(f"时间范围: {data.index[0]} 到 {data.index[-1]}")
    logger.info(f"数据列: {list(data.columns)}")
    
    # 统计信息
    if 'close' in data.columns:
        logger.info(f"收盘价统计:")
        logger.info(f"  最小值: {data['close'].min():.2f}")
        logger.info(f"  最大值: {data['close'].max():.2f}")
        logger.info(f"  平均值: {data['close'].mean():.2f}")
        logger.info(f"  标准差: {data['close'].std():.2f}")
    
    # 缺失值统计
    missing_count = data.isnull().sum().sum()
    if missing_count > 0:
        logger.warning(f"数据中存在缺失值: {missing_count} 个")
    
    logger.info("-" * 50)


def log_strategy_generation(strategy_type: str, params: dict, 
                           code_snippet: str = None):
    """
    记录策略生成过程
    
    Args:
        strategy_type: 策略类型
        params: 生成参数
        code_snippet: 生成的代码片段
    """
    logger.info(f"生成策略: {strategy_type}")
    logger.info(f"参数: {params}")
    
    if code_snippet:
        # 只记录代码的前几行
        lines = code_snippet.split('\n')[:10]
        logger.info("生成代码片段:")
        for line in lines:
            logger.info(f"  {line}")
        if len(code_snippet.split('\n')) > 10:
            line_count = len(code_snippet.split('\n'))
            logger.info(f"  ... (共 {line_count} 行)")
    
    logger.info("-" * 30)


def log_backtest_progress(current: int, total: int, strategy_name: str):
    """
    记录回测进度
    
    Args:
        current: 当前进度
        total: 总进度
        strategy_name: 策略名称
    """
    progress = (current / total) * 100
    logger.debug(f"回测进度: {strategy_name} - {current}/{total} ({progress:.1f}%)")


# 初始化日志系统
logger = setup_logger()

if __name__ == "__main__":
    # 测试日志系统
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    # 测试性能记录
    sample_metrics = {
        'total_return': 0.3567,
        'annual_return': 0.1254,
        'sharpe_ratio': 1.2345,
        'max_drawdown': -0.1567,
        'win_rate': 0.5567,
        'trades_count': 123,
        'profit_factor': 1.7890
    }
    
    log_performance(sample_metrics, "测试策略", {"param1": 10, "param2": 20})
    
    # 测试优化结果记录
    log_optimization_result(
        best_params={"fast_period": 12, "slow_period": 26},
        best_score=0.8567,
        strategy_name="MACD策略",
        iteration=50
    )