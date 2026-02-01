"""
策略参数配置
"""

from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class StrategyParams:
    """策略参数基类"""
    name: str
    description: str
    params: Dict[str, Any]

# ========== 各策略详细配置 ==========

class MAStrategyParams:
    """移动平均线策略参数"""
    
    @staticmethod
    def get_base_params() -> StrategyParams:
        return StrategyParams(
            name="MA",
            description="简单移动平均线策略：价格上穿均线买入，下穿均线卖出",
            params={
                "sma_period": 20,  # 短期均线周期
                "lma_period": 60,  # 长期均线周期
                "use_atr_stop": True,  # 是否使用ATR止损
                "atr_period": 14,  # ATR周期
                "atr_multiplier": 2.0,  # ATR倍数
            }
        )
    
    @staticmethod
    def get_param_grid() -> Dict[str, List]:
        """参数网格搜索范围"""
        return {
            "sma_period": [5, 10, 15, 20, 25, 30],
            "lma_period": [30, 40, 50, 60, 70, 80, 90, 100, 120],
            "atr_multiplier": [1.5, 2.0, 2.5, 3.0]
        }

class MACDStrategyParams:
    """MACD策略参数"""
    
    @staticmethod
    def get_base_params() -> StrategyParams:
        return StrategyParams(
            name="MACD",
            description="MACD指标策略：MACD金叉买入，死叉卖出",
            params={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "use_divergence": False,  # 是否使用背离信号
                "use_histogram": True,   # 是否使用柱状图信号
            }
        )
    
    @staticmethod
    def get_param_grid() -> Dict[str, List]:
        return {
            "fast_period": [8, 10, 12, 14, 16],
            "slow_period": [21, 24, 26, 28, 30],
            "signal_period": [7, 8, 9, 10, 11, 12]
        }

class RSIStrategyParams:
    """RSI策略参数"""
    
    @staticmethod
    def get_base_params() -> StrategyParams:
        return StrategyParams(
            name="RSI",
            description="RSI超买超卖策略：RSI低于超卖线买入，高于超买线卖出",
            params={
                "rsi_period": 14,
                "overbought": 70,
                "oversold": 30,
                "use_divergence": True,
                "exit_on_middle": False,  # 是否在50线退出
            }
        )
    
    @staticmethod
    def get_param_grid() -> Dict[str, List]:
        return {
            "rsi_period": [6, 9, 12, 14, 16, 20, 25],
            "overbought": [65, 70, 75, 80],
            "oversold": [20, 25, 30, 35]
        }

class BollingerStrategyParams:
    """布林带策略参数"""
    
    @staticmethod
    def get_base_params() -> StrategyParams:
        return StrategyParams(
            name="BOLL",
            description="布林带策略：价格触及下轨买入，触及上轨卖出",
            params={
                "period": 20,
                "devfactor": 2.0,
                "use_band_width": True,  # 是否使用带宽指标
                "use_percent_b": True,   # 是否使用%b指标
            }
        )
    
    @staticmethod
    def get_param_grid() -> Dict[str, List]:
        return {
            "period": [10, 15, 20, 25, 30],
            "devfactor": [1.5, 2.0, 2.5, 3.0]
        }

class MACrossStrategyParams:
    """双均线交叉策略参数"""
    
    @staticmethod
    def get_base_params() -> StrategyParams:
        return StrategyParams(
            name="MA_CROSS",
            description="双均线交叉策略：短期均线上穿长期均线买入，下穿卖出",
            params={
                "fast_period": 10,
                "slow_period": 30,
                "use_volume_filter": False,  # 是否使用成交量过滤
                "use_trend_filter": True,    # 是否使用趋势过滤
            }
        )
    
    @staticmethod
    def get_param_grid() -> Dict[str, List]:
        return {
            "fast_period": [3, 5, 8, 10, 13, 15, 18],
            "slow_period": [20, 25, 30, 35, 40, 45, 50, 60]
        }

# ========== 策略工厂配置 ==========

class StrategyFactoryConfig:
    """策略工厂配置"""
    
    @staticmethod
    def get_all_strategies() -> Dict[str, StrategyParams]:
        """获取所有策略的基础配置"""
        return {
            "MA": MAStrategyParams.get_base_params(),
            "MACD": MACDStrategyParams.get_base_params(),
            "RSI": RSIStrategyParams.get_base_params(),
            "BOLL": BollingerStrategyParams.get_base_params(),
            "MA_CROSS": MACrossStrategyParams.get_base_params(),
        }
    
    @staticmethod
    def get_all_param_grids() -> Dict[str, Dict[str, List]]:
        """获取所有策略的参数网格"""
        return {
            "MA": MAStrategyParams.get_param_grid(),
            "MACD": MACDStrategyParams.get_param_grid(),
            "RSI": RSIStrategyParams.get_param_grid(),
            "BOLL": BollingerStrategyParams.get_param_grid(),
            "MA_CROSS": MACrossStrategyParams.get_param_grid(),
        }
    
    @staticmethod
    def get_strategy_descriptions() -> Dict[str, str]:
        """获取策略描述"""
        return {
            "MA": "移动平均线策略：价格上穿均线时买入，下穿均线时卖出",
            "MACD": "MACD策略：MACD线上穿信号线时买入，下穿信号线时卖出",
            "RSI": "RSI策略：RSI低于超卖线时买入，高于超买线时卖出",
            "BOLL": "布林带策略：价格触及下轨时买入，触及上轨时卖出",
            "MA_CROSS": "双均线交叉策略：短期均线上穿长期均线时买入，下穿时卖出",
        }

# ========== 导出配置 ==========

# 策略配置实例
MA_PARAMS = MAStrategyParams()
MACD_PARAMS = MACDStrategyParams()
RSI_PARAMS = RSIStrategyParams()
BOLL_PARAMS = BollingerStrategyParams()
MA_CROSS_PARAMS = MACrossStrategyParams()

# 工厂配置实例
STRATEGY_FACTORY = StrategyFactoryConfig()

if __name__ == "__main__":
    # 测试配置
    print("策略配置测试:")
    print("-" * 40)
    
    strategies = STRATEGY_FACTORY.get_all_strategies()
    for name, params in strategies.items():
        print(f"{name}: {params.description}")
        print(f"  基础参数: {params.params}")
        print()