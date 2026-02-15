"""
Triple Moving Average Crossover Strategy
Based on research: Three MA confirmation reduces false signals
Reference: QuantInsti 2025 - Moving Average Crossover Strategies
"""
import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class TripleMAStrategy(BaseStrategy):
    """
    三重均线交叉策略
    使用快/中/慢三条均线，形成双重确认机制
    - 买入：快线 > 中线 > 慢线（多头排列）
    - 卖出：快线 < 中线（趋势破坏）
    """

    def __init__(self, **kwargs):
        default_params = {
            'fast_period': 5,      # 快线
            'mid_period': 20,      # 中线
            'slow_period': 70,     # 慢线
            'volatility_filter': False,  # 是否启用波动率过滤
            'atr_threshold': 0.0,  # ATR阈值（0表示不过滤）
            'atr_period': 14,      # ATR周期
        }
        default_params.update(kwargs)
        super().__init__(default_params)

        self._init_triple_ma_strategy()

    def _init_triple_ma_strategy(self):
        """初始化三重均线策略特定指标"""
        params = self.params_dict

        # 三条均线
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['fast_period']
        )
        self.mid_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['mid_period']
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['slow_period']
        )

        # ATR（用于波动率过滤）
        if params['volatility_filter']:
            self.triple_atr = bt.indicators.ATR(
                self.data, period=params['atr_period']
            )
            self.atr_sma = bt.indicators.SimpleMovingAverage(
                self.triple_atr, period=20
            )

        # 交叉信号
        self.fast_mid_cross = bt.indicators.CrossOver(self.fast_ma, self.mid_ma)

    def validate_params(self) -> bool:
        fast = self.params_dict.get('fast_period', 5)
        mid = self.params_dict.get('mid_period', 20)
        slow = self.params_dict.get('slow_period', 70)
        return fast < mid < slow

    def generate_signals(self) -> Dict[str, Any]:
        """生成交易信号（bar-by-bar模式，兼容backtrader）"""
        signals = {}

        # 检查数据是否足够
        min_period = self.params_dict['slow_period']
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}

        # 获取当前值
        close = self.data.close[0]
        fast = self.fast_ma[0]
        mid = self.mid_ma[0]
        slow = self.slow_ma[0]

        # 波动率过滤
        if self.params_dict['volatility_filter'] and hasattr(self, 'triple_atr'):
            atr_val = self.triple_atr[0]
            atr_avg = self.atr_sma[0]
            threshold = self.params_dict.get('atr_threshold', 0.0)
            # 低波动时不交易
            if atr_avg > 0 and atr_val < atr_avg * 0.5:
                return {'action': 'hold', 'strength': 0, 'reason': '波动率过低，暂不交易'}

        # 判断排列状态
        bullish = fast > mid > slow
        bearish = fast < mid

        # 买入信号：多头排列形成
        if bullish and self.position.size == 0:
            # 计算信号强度（基于均线间距）
            spread = (fast - slow) / slow if slow > 0 else 0
            strength = min(abs(spread) * 100, 1.0)
            strength = max(strength, 0.3)

            signals['action'] = 'buy'
            signals['strength'] = strength
            signals['reason'] = f'三重均线多头排列: MA{self.params_dict["fast_period"]}>{self.params_dict["mid_period"]}>{self.params_dict["slow_period"]}'

        # 卖出信号：趋势破坏（快线跌破中线）
        elif bearish and self.position.size > 0:
            signals['action'] = 'sell'
            signals['strength'] = 0.9
            signals['reason'] = f'趋势破坏: MA{self.params_dict["fast_period"]}跌破MA{self.params_dict["mid_period"]}'

        # 持仓监控
        elif self.position.size > 0:
            if fast > mid:
                signals['action'] = 'hold'
                signals['strength'] = 0.7
                signals['reason'] = '快线仍在中线上方，继续持有'
            else:
                signals['action'] = 'sell'
                signals['strength'] = 0.8
                signals['reason'] = '均线排列转弱，平仓'

        # 空仓等待
        else:
            signals['action'] = 'hold'
            signals['strength'] = 0
            signals['reason'] = '等待三重均线多头排列'

        return signals

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = {
            'strategy_name': '三重均线交叉策略',
            'strategy_type': 'TRIPLE_MA',
            'description': '使用快/中/慢三条均线的双重确认趋势跟踪策略',
            'parameters': self.params_dict,
            'indicators': ['快速均线', '中速均线', '慢速均线', 'ATR(可选)'],
            'signal_type': '趋势跟踪',
            'risk_level': '中等'
        }

        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'fast_ma': float(self.fast_ma[0]) if hasattr(self, 'fast_ma') else None,
                'mid_ma': float(self.mid_ma[0]) if hasattr(self, 'mid_ma') else None,
                'slow_ma': float(self.slow_ma[0]) if hasattr(self, 'slow_ma') else None,
            }

        return info

    def get_param_ranges(self) -> Dict[str, Any]:
        """返回参数优化范围"""
        return {
            'fast_period': range(3, 15),
            'mid_period': range(10, 40),
            'slow_period': range(40, 100),
            'volatility_filter': [False, True],
            'atr_threshold': [0.0, 0.01, 0.02, 0.03]
        }


# ========== 策略参数优化配置 ==========

class TripleMAStrategyOptimizer:
    """三重均线策略优化器"""

    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """获取参数网格"""
        return {
            'fast_period': [3, 5, 8, 10, 13],
            'mid_period': [15, 20, 25, 30, 35],
            'slow_period': [50, 60, 70, 80, 90],
            'volatility_filter': [True, False],
        }

    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'fast_period': 5,
            'mid_period': 20,
            'slow_period': 70,
            'volatility_filter': False,
            'atr_threshold': 0.0,
            'atr_period': 14,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8
        }
