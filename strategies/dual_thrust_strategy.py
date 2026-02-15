"""
双轨突破策略 (Dual Thrust Strategy)
基于N日高低价区间的经典中国市场突破策略
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class DualThrustIndicator(bt.Indicator):
    """
    双轨突破指标

    计算公式:
        HH = 过去N日最高价的最大值
        LC = 过去N日收盘价的最小值
        HC = 过去N日收盘价的最大值
        LL = 过去N日最低价的最小值

        Range = max(HH - LC, HC - LL)
        Upper = 当日开盘价 + K1 * Range
        Lower = 当日开盘价 - K2 * Range
    """

    lines = ('upper', 'lower',)

    params = (
        ('lookback', 5),
        ('k1', 0.5),
        ('k2', 0.5),
    )

    def __init__(self):
        # 保证在lookback+1根K线之后才开始计算
        self.addminperiod(self.p.lookback + 1)

    def next(self):
        lookback = self.p.lookback

        # 从数据缓冲区获取过去lookback根K线（包含当前bar，newest first）
        highs = self.data.high.get(size=lookback)
        lows = self.data.low.get(size=lookback)
        closes = self.data.close.get(size=lookback)

        if len(highs) < lookback or len(lows) < lookback or len(closes) < lookback:
            return

        hh = max(highs)   # 过去N日最高价的最大值
        ll = min(lows)    # 过去N日最低价的最小值
        hc = max(closes)  # 过去N日收盘价的最大值
        lc = min(closes)  # 过去N日收盘价的最小值

        range_val = max(hh - lc, hc - ll)

        open_price = self.data.open[0]
        self.lines.upper[0] = open_price + self.p.k1 * range_val
        self.lines.lower[0] = open_price - self.p.k2 * range_val


class DualThrustStrategy(BaseStrategy):
    """
    双轨突破策略

    策略逻辑:
    1. 计算过去N日高低价区间 (Range)
    2. 以当日开盘价为基准, 向上扩展 K1*Range 为上轨, 向下扩展 K2*Range 为下轨
    3. 当日价格突破上轨时买入
    4. 当日价格跌破下轨时卖出
    5. 支持ATR动态止损和固定比例止盈止损
    """

    def __init__(self, **kwargs):
        """
        初始化双轨突破策略

        Args:
            lookback: 回望周期 (默认5天)
            k1: 上轨系数 (默认0.5)
            k2: 下轨系数 (默认0.5)
            use_atr_stop: 是否使用ATR止损 (默认True)
            atr_period: ATR计算周期 (默认14)
            atr_multiplier: ATR止损倍数 (默认2.0)
            stop_loss_ratio: 固定止损比例 (默认0.05)
            take_profit_ratio: 固定止盈比例 (默认0.15)
            max_position_size: 最大仓位比例 (默认0.8)
        """
        default_params = {
            'lookback': 5,
            'k1': 0.5,
            'k2': 0.5,
            'use_atr_stop': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.15,
            'max_position_size': 0.8,
        }

        default_params.update(kwargs)

        super().__init__(default_params)

        self._init_dual_thrust_strategy()

    def _init_dual_thrust_strategy(self):
        """初始化双轨突破策略特定指标"""
        params = self.params_dict

        # 双轨指标
        self.dual_thrust = DualThrustIndicator(
            self.data,
            lookback=params['lookback'],
            k1=params['k1'],
            k2=params['k2'],
        )

        # ATR指标（可选，用于动态止损）
        if params['use_atr_stop']:
            self.atr = bt.indicators.ATR(self.data, period=params['atr_period'])
        else:
            self.atr = None

        # 状态变量
        self.breakout_direction = None  # 'up' 或 'down'
        self.entry_upper = 0.0          # 入场时的上轨价格
        self.entry_lower = 0.0          # 入场时的下轨价格

    def generate_signals(self) -> Dict[str, Any]:
        """
        生成交易信号

        策略逻辑:
        1. 当收盘价突破上轨且无持仓 -> 买入
        2. 当收盘价跌破下轨且有持仓 -> 卖出
        3. 持仓期间监控ATR止损或价格回落
        """
        min_period = self.params_dict['lookback'] + 1
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足，等待预热'}

        # 防止指标尚未初始化完成
        if len(self.dual_thrust) == 0:
            return {'action': 'hold', 'strength': 0.0, 'reason': '指标预热中'}

        close = self.data.close[0]
        upper = self.dual_thrust.upper[0]
        lower = self.dual_thrust.lower[0]

        # 买入条件: 当日收盘价突破上轨且空仓
        if close > upper and self.position.size == 0:
            strength = self._calculate_breakout_strength(close, upper, lower, direction='up')
            self.breakout_direction = 'up'
            self.entry_upper = upper
            self.entry_lower = lower
            return {
                'action': 'buy',
                'strength': strength,
                'reason': (
                    f'价格突破上轨: 收盘价{close:.2f} > 上轨{upper:.2f}, '
                    f'突破幅度{(close - upper) / upper:.2%}'
                ),
            }

        # 卖出条件: 当日收盘价跌破下轨且持仓
        if close < lower and self.position.size > 0:
            self.breakout_direction = 'down'
            return {
                'action': 'sell',
                'strength': 1.0,
                'reason': (
                    f'价格跌破下轨: 收盘价{close:.2f} < 下轨{lower:.2f}, '
                    f'跌破幅度{(lower - close) / lower:.2%}'
                ),
            }

        # 持仓监控
        if self.position.size > 0:
            return self._monitor_long_position(close, upper, lower)

        # 空仓等待
        return {
            'action': 'hold',
            'strength': 0.0,
            'reason': f'等待突破: 上轨{upper:.2f}, 下轨{lower:.2f}, 当前{close:.2f}',
        }

    def _calculate_breakout_strength(
        self,
        close: float,
        upper: float,
        lower: float,
        direction: str,
    ) -> float:
        """
        计算突破信号强度

        基于价格偏离突破轨道的幅度，归一化到 [0.3, 1.0] 区间。
        """
        channel_width = upper - lower
        if channel_width <= 0:
            return 0.5

        if direction == 'up':
            # 突破上轨的距离相对于通道宽度
            breakout_dist = close - upper
        else:
            breakout_dist = lower - close

        # 突破幅度占通道宽度的比例，最大不超过50%
        ratio = min(breakout_dist / channel_width, 0.5)
        strength = 0.3 + ratio * 1.4  # 线性映射到 [0.3, 1.0]

        return min(max(strength, 0.3), 1.0)

    def _monitor_long_position(
        self,
        close: float,
        upper: float,
        lower: float,
    ) -> Dict[str, Any]:
        """监控多头持仓"""

        # ATR动态止损检查
        if self.params_dict['use_atr_stop'] and self.atr is not None and len(self.atr) > 0:
            atr_value = self.atr[0]
            atr_multiplier = self.params_dict['atr_multiplier']
            entry = self.position.price
            atr_stop_price = entry - atr_multiplier * atr_value

            if close < atr_stop_price:
                return {
                    'action': 'sell',
                    'strength': 0.9,
                    'reason': (
                        f'ATR止损触发: 价格{close:.2f} < 止损价{atr_stop_price:.2f} '
                        f'(入场{entry:.2f} - {atr_multiplier}×ATR{atr_value:.2f})'
                    ),
                }

        # 价格回落至入场时下轨附近，保守平仓
        if self.entry_lower > 0 and close < self.entry_lower:
            return {
                'action': 'sell',
                'strength': 0.8,
                'reason': (
                    f'价格回落至入场下轨: 收盘价{close:.2f} < 入场下轨{self.entry_lower:.2f}'
                ),
            }

        # 持仓正常，计算持有强度
        if self.entry_upper > 0:
            channel_width = self.entry_upper - self.entry_lower
            if channel_width > 0:
                hold_strength = min((close - self.entry_lower) / channel_width, 1.0)
                hold_strength = max(hold_strength, 0.5)
            else:
                hold_strength = 0.6
        else:
            hold_strength = 0.6

        return {
            'action': 'hold',
            'strength': hold_strength,
            'reason': f'双轨突破后持仓中: 当前{close:.2f}, 上轨{upper:.2f}, 下轨{lower:.2f}',
        }

    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈价格（重写基类方法，支持ATR动态止损）"""
        if self.params_dict['use_atr_stop'] and self.atr is not None and len(self.atr) > 0:
            atr_value = self.atr[0]
            atr_multiplier = self.params_dict['atr_multiplier']
            atr_stop = atr_multiplier * atr_value

            self.stop_loss_price = entry_price - atr_stop
            # 止盈使用2:1盈亏比
            self.take_profit_price = entry_price + 2.0 * atr_stop
        else:
            # 回退到固定比例止损止盈
            super()._set_stop_loss_take_profit(entry_price)

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = {
            'strategy_name': '双轨突破策略 (Dual Thrust)',
            'strategy_type': 'DUAL_THRUST',
            'description': (
                '基于过去N日高低价区间构建动态上下轨，'
                '价格突破上轨时买入，跌破下轨时卖出的经典突破策略'
            ),
            'parameters': self.params_dict,
            'indicators': ['DualThrustIndicator (上轨/下轨)', 'ATR (可选止损)'],
            'signal_type': '突破跟踪',
            'risk_level': '中高',
        }

        if len(self.data) > 0 and len(self.dual_thrust) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'open': float(self.data.open[0]),
                'upper': float(self.dual_thrust.upper[0]),
                'lower': float(self.dual_thrust.lower[0]),
                'breakout_direction': self.breakout_direction,
                'entry_upper': self.entry_upper,
                'entry_lower': self.entry_lower,
                'atr': float(self.atr[0]) if self.atr is not None and len(self.atr) > 0 else None,
            }

        return info


# ========== 策略参数优化配置 ==========

class DualThrustStrategyOptimizer:
    """双轨突破策略优化器"""

    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """
        获取参数优化网格

        覆盖不同市场环境下的参数组合:
        - lookback: 短期(3-5)适合波动较大的品种，中长期(10-20)适合趋势品种
        - k1/k2: 对称参数 (0.3-0.7) 控制突破灵敏度
        - atr_multiplier: 控制止损松紧度
        """
        return {
            'lookback': [3, 5, 8, 10, 15, 20],
            'k1': [0.3, 0.4, 0.5, 0.6, 0.7],
            'k2': [0.3, 0.4, 0.5, 0.6, 0.7],
            'use_atr_stop': [True, False],
            'atr_multiplier': [1.5, 2.0, 2.5, 3.0],
        }

    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'lookback': 5,
            'k1': 0.5,
            'k2': 0.5,
            'use_atr_stop': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.15,
            'max_position_size': 0.8,
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    print("测试双轨突破策略...")

    optimizer = DualThrustStrategyOptimizer()
    default_params = optimizer.get_default_params()
    print(f"默认参数: {default_params}")

    param_grid = optimizer.get_param_grid()
    print("\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")

    print("\n策略测试完成!")
