"""
海龟交易策略
基于Richard Dennis和William Eckhardt的经典海龟系统

系统1: 20日唐奇安通道突破（默认）
系统2: 55日唐奇安通道突破（可选）
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class TurtleStrategy(BaseStrategy):
    """海龟交易策略"""

    def __init__(self, **kwargs):
        """
        初始化海龟交易策略

        Args:
            entry_period: 入场唐奇安通道周期（系统1默认20，系统2用55）
            exit_period: 出场唐奇安通道周期（默认10）
            atr_period: ATR计算周期（默认20）
            risk_per_unit: 每个单位承担的账户风险比例（默认1%）
            use_pyramiding: 是否启用加仓（默认False）
            max_units: 最大加仓次数（默认4）
            stop_loss_atr_multiplier: ATR止损倍数（默认2.0）
            stop_loss_ratio: 固定止损比例（默认5%）
            take_profit_ratio: 止盈比例（默认20%）
            max_position_size: 最大仓位比例（默认0.8）
        """
        # 默认参数
        default_params = {
            'entry_period': 20,          # 入场通道周期（系统1: 20，系统2: 55）
            'exit_period': 10,           # 出场通道周期
            'atr_period': 20,            # ATR周期
            'risk_per_unit': 0.01,       # 每单位风险（账户的1%）
            'use_pyramiding': False,     # 是否启用加仓
            'max_units': 4,              # 最大加仓次数
            'stop_loss_atr_multiplier': 2.0,  # ATR止损倍数
            'stop_loss_ratio': 0.05,     # 固定止损比例（兜底）
            'take_profit_ratio': 0.20,   # 止盈比例
            'max_position_size': 0.8,    # 最大仓位比例
        }

        # 合并参数
        default_params.update(kwargs)

        super().__init__(default_params)

        # 策略特定初始化
        self._init_turtle_strategy()

    def _init_turtle_strategy(self):
        """初始化海龟策略特定指标和状态"""
        params = self.params_dict

        # 入场唐奇安通道（系统1: 20日高点，系统1退出: 10日低点）
        self.entry_high = bt.indicators.Highest(
            self.data.high, period=params['entry_period']
        )
        self.entry_low = bt.indicators.Lowest(
            self.data.low, period=params['entry_period']
        )

        # 出场唐奇安通道（10日低点用于多头平仓，10日高点用于空头平仓）
        self.exit_low = bt.indicators.Lowest(
            self.data.low, period=params['exit_period']
        )
        self.exit_high = bt.indicators.Highest(
            self.data.high, period=params['exit_period']
        )

        # ATR（用于仓位计算和止损）
        self.turtle_atr = bt.indicators.ATR(
            self.data, period=params['atr_period']
        )

        # 海龟策略状态变量
        self.units_held = 0           # 当前持有的单位数
        self.last_add_price = 0.0    # 最后一次加仓价格

    def _calculate_position_size(self, signal_strength: float) -> float:
        """
        基于ATR的海龟仓位计算（Unit sizing）

        海龟规则: Unit = (账户价值 * risk_per_unit) / (ATR * 价格)
        这样每个Unit的风险等于账户的risk_per_unit比例

        Args:
            signal_strength: 信号强度（0-1），海龟系统中不直接使用

        Returns:
            计算出的仓位数量（股数）
        """
        params = self.params_dict
        broker_value = self.broker.getvalue()
        close = self.data.close[0]

        # 检查ATR是否有效
        if len(self.turtle_atr) == 0 or self.turtle_atr[0] <= 0 or close <= 0:
            # 回退到基类方法
            logger.warning("ATR无效，回退到基类仓位计算")
            return super()._calculate_position_size(signal_strength)

        atr_value = self.turtle_atr[0]
        risk_per_unit = params['risk_per_unit']
        max_position_size = params['max_position_size']

        # 海龟Unit计算: 风险资金 / ATR波动额
        # 单位价格风险 = ATR（以价格表示的1N波动）
        # 单位股数 = 账户价值 * risk_per_unit / ATR
        unit_size = (broker_value * risk_per_unit) / (atr_value * close) * close
        # 更准确: 单位持仓额 = broker_value * risk_per_unit / atr_pct
        # atr_pct = atr_value / close
        # unit_value = broker_value * risk_per_unit / (atr_value / close)
        # unit_shares = unit_value / close = broker_value * risk_per_unit / atr_value
        unit_shares = (broker_value * risk_per_unit) / atr_value

        # 最大仓位限制（账户价值的max_position_size）
        max_shares = (broker_value * max_position_size) / close

        # 取两者较小值
        position_size = min(unit_shares, max_shares)

        # 取整为100股的整数倍（A股交易单位）
        position_size = int(position_size / 100) * 100

        return max(position_size, 100)  # 至少100股

    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈价格（重写基类，使用ATR动态止损）"""
        params = self.params_dict

        if len(self.turtle_atr) > 0 and self.turtle_atr[0] > 0:
            atr_value = self.turtle_atr[0]
            atr_multiplier = params['stop_loss_atr_multiplier']
            # ATR止损: 入场价 - 2N
            self.stop_loss_price = entry_price - atr_multiplier * atr_value
            # 止盈使用固定比例（海龟系统靠通道出场，这里提供兜底止盈）
            self.take_profit_price = entry_price * (1 + params['take_profit_ratio'])
        else:
            # 回退到固定比例止损
            super()._set_stop_loss_take_profit(entry_price)

    def generate_signals(self) -> Dict[str, Any]:
        """
        生成海龟交易信号

        信号逻辑:
        1. 买入信号: 收盘价突破前一日20日最高价（避免前瞻偏差）
        2. 卖出信号（平仓）: 收盘价跌破前一日10日最低价
        3. ATR止损: 当前价格低于 (入场价 - 2*ATR)
        4. 加仓（可选）: 价格每上涨0.5N时加仓，最多4个单位

        Returns:
            包含 action/strength/reason 的信号字典
        """
        params = self.params_dict
        min_period = max(params['entry_period'], params['exit_period'], params['atr_period'])

        # 检查数据是否足够
        if len(self.data) < min_period + 1:
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足，等待指标预热'}

        # 获取当前数据（使用[0]为当前bar）
        close = self.data.close[0]

        # 使用[-1]获取前一个bar的通道值，避免前瞻偏差
        # entry_high[-1] 是前一根bar的20日最高价
        prev_entry_high = self.entry_high[-1]
        prev_exit_low = self.exit_low[-1]

        # 当前ATR值
        atr_value = self.turtle_atr[0] if len(self.turtle_atr) > 0 else 0.0

        # 当前持仓状态
        has_position = self.position.size > 0

        # ========== 持仓状态: 检查出场信号 ==========
        if has_position:
            return self._generate_exit_signals(close, prev_exit_low, atr_value)

        # ========== 空仓状态: 检查入场信号 ==========
        return self._generate_entry_signals(close, prev_entry_high, atr_value)

    def _generate_entry_signals(
        self,
        close: float,
        prev_entry_high: float,
        atr_value: float
    ) -> Dict[str, Any]:
        """
        生成入场信号

        海龟规则: 收盘价突破前一日N日最高价时买入

        Args:
            close: 当前收盘价
            prev_entry_high: 前一日入场通道高点
            atr_value: 当前ATR值

        Returns:
            信号字典
        """
        params = self.params_dict

        # 突破入场信号（避免前瞻：使用前一根bar的高点）
        if close > prev_entry_high and prev_entry_high > 0:
            # 计算信号强度（突破幅度越大信号越强）
            breakout_pct = (close - prev_entry_high) / prev_entry_high if prev_entry_high > 0 else 0
            strength = min(0.5 + breakout_pct * 50, 1.0)  # 基础0.5，突破幅度加成

            # 初始化加仓状态
            self.units_held = 1
            self.last_add_price = close

            logger.debug(
                f"海龟入场信号: 收盘价 {close:.2f} > {params['entry_period']}日高点 {prev_entry_high:.2f}"
            )

            return {
                'action': 'buy',
                'strength': strength,
                'reason': (
                    f"唐奇安通道突破: 收盘{close:.2f} > {params['entry_period']}日高点{prev_entry_high:.2f}"
                    f"（突破幅度 {breakout_pct:.2%}）"
                )
            }

        # 加仓逻辑（仅在已有持仓时触发，但此函数只在空仓时调用，此处保留逻辑完整性）
        return {
            'action': 'hold',
            'strength': 0.0,
            'reason': f'等待突破 {params["entry_period"]}日高点 {prev_entry_high:.2f}'
        }

    def _generate_exit_signals(
        self,
        close: float,
        prev_exit_low: float,
        atr_value: float
    ) -> Dict[str, Any]:
        """
        生成出场信号

        出场逻辑（按优先级）:
        1. ATR止损: 价格低于 入场价 - 2*ATR
        2. 唐奇安出场: 价格跌破10日最低价
        3. 加仓检查（如启用）

        Args:
            close: 当前收盘价
            prev_exit_low: 前一日出场通道低点
            atr_value: 当前ATR值

        Returns:
            信号字典
        """
        params = self.params_dict
        entry_price = self.entry_price  # 由基类 _execute_buy 设置

        # ========== ATR止损检查（最高优先级）==========
        if entry_price > 0 and atr_value > 0:
            atr_stop_price = entry_price - params['stop_loss_atr_multiplier'] * atr_value
            if close < atr_stop_price:
                logger.debug(
                    f"海龟ATR止损: 收盘价 {close:.2f} < 止损价 {atr_stop_price:.2f}"
                    f"（入场价 {entry_price:.2f} - {params['stop_loss_atr_multiplier']}N）"
                )
                self.units_held = 0
                self.last_add_price = 0.0
                return {
                    'action': 'sell',
                    'strength': 1.0,
                    'reason': (
                        f"ATR止损: 价格{close:.2f} < 止损价{atr_stop_price:.2f}"
                        f"（入场价{entry_price:.2f} - {params['stop_loss_atr_multiplier']}N）"
                    )
                }

        # ========== 唐奇安通道出场信号 ==========
        if close < prev_exit_low and prev_exit_low > 0:
            logger.debug(
                f"海龟通道出场: 收盘价 {close:.2f} < {params['exit_period']}日低点 {prev_exit_low:.2f}"
            )
            self.units_held = 0
            self.last_add_price = 0.0
            return {
                'action': 'sell',
                'strength': 1.0,
                'reason': (
                    f"唐奇安通道出场: 收盘{close:.2f} < {params['exit_period']}日低点{prev_exit_low:.2f}"
                )
            }

        # ========== 加仓检查（可选）==========
        if params['use_pyramiding'] and self.units_held < params['max_units']:
            pyramid_signal = self._check_pyramid_signal(close, atr_value)
            if pyramid_signal['action'] == 'buy':
                return pyramid_signal

        # ========== 持续持仓 ==========
        return {
            'action': 'hold',
            'strength': 0.5,
            'reason': (
                f"持仓中: 收盘{close:.2f}，出场线{prev_exit_low:.2f}"
                f"，当前单位数: {self.units_held}"
            )
        }

    def _check_pyramid_signal(self, close: float, atr_value: float) -> Dict[str, Any]:
        """
        检查加仓条件

        海龟加仓规则: 价格每上涨0.5N时加仓，最多4个单位

        Args:
            close: 当前收盘价
            atr_value: 当前ATR值

        Returns:
            信号字典（'buy'为加仓，'hold'为不加仓）
        """
        params = self.params_dict

        # 检查是否满足加仓条件
        if (
            self.last_add_price > 0
            and atr_value > 0
            and close > self.last_add_price + 0.5 * atr_value
        ):
            self.units_held += 1
            self.last_add_price = close

            logger.debug(
                f"海龟加仓: 第{self.units_held}单位，"
                f"价格{close:.2f}，上次加仓价{self.last_add_price:.2f}"
            )

            return {
                'action': 'buy',
                'strength': 0.8,
                'reason': (
                    f"加仓: 第{self.units_held}单位"
                    f"（价格{close:.2f} > 上次加仓价 + 0.5N）"
                )
            }

        return {
            'action': 'hold',
            'strength': 0.5,
            'reason': f'加仓条件未满足（当前: {self.units_held}单位）'
        }

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        params = self.params_dict
        info = {
            'strategy_name': '海龟交易策略',
            'strategy_type': 'TURTLE',
            'description': (
                '基于Richard Dennis/William Eckhardt的经典海龟系统。'
                f'使用{params["entry_period"]}日唐奇安通道入场，'
                f'{params["exit_period"]}日通道出场，'
                f'ATR动态止损，风险每单位{params["risk_per_unit"]*100:.1f}%。'
            ),
            'parameters': params,
            'indicators': [
                f'{params["entry_period"]}日唐奇安入场通道',
                f'{params["exit_period"]}日唐奇安出场通道',
                f'{params["atr_period"]}日ATR',
            ],
            'signal_type': '趋势跟踪（通道突破）',
            'risk_level': '中低（ATR动态止损）',
            'pyramiding': '启用' if params['use_pyramiding'] else '禁用',
            'max_units': params['max_units'],
        }

        # 添加当前指标值
        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'entry_high': float(self.entry_high[0]) if len(self.entry_high) > 0 else None,
                'entry_low': float(self.entry_low[0]) if len(self.entry_low) > 0 else None,
                'exit_low': float(self.exit_low[0]) if len(self.exit_low) > 0 else None,
                'exit_high': float(self.exit_high[0]) if len(self.exit_high) > 0 else None,
                'atr': float(self.turtle_atr[0]) if len(self.turtle_atr) > 0 else None,
                'units_held': self.units_held,
                'last_add_price': self.last_add_price,
                'entry_price': self.entry_price,
            }

        return info


# ========== 策略参数优化配置 ==========

class TurtleStrategyOptimizer:
    """海龟交易策略优化器"""

    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """
        获取参数网格

        Returns:
            各参数的候选值列表
        """
        return {
            # 系统1: entry_period=20, 系统2: entry_period=55
            'entry_period': [20, 30, 40, 55],
            'exit_period': [10, 15, 20],
            'atr_period': [14, 20],
            'risk_per_unit': [0.005, 0.01, 0.02],
            'use_pyramiding': [True, False],
            'max_units': [2, 4],
            'stop_loss_atr_multiplier': [1.5, 2.0, 2.5],
        }

    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """
        获取默认参数（系统1配置）

        Returns:
            默认参数字典
        """
        return {
            'entry_period': 20,
            'exit_period': 10,
            'atr_period': 20,
            'risk_per_unit': 0.01,
            'use_pyramiding': False,
            'max_units': 4,
            'stop_loss_atr_multiplier': 2.0,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.20,
            'max_position_size': 0.8,
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试海龟策略
    print("测试海龟交易策略...")

    # 获取优化器配置
    optimizer = TurtleStrategyOptimizer()
    default_params = optimizer.get_default_params()
    param_grid = optimizer.get_param_grid()

    print(f"默认参数: {default_params}")
    print(f"\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")

    print("\n策略测试完成!")
