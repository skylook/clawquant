"""
动量策略
基于价格动量的交易策略
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """动量策略"""
    
    params = (
        ('momentum_period', 20),      # 动量周期
        ('sma_period', 50),           # 均线周期
        ('atr_period', 14),           # ATR周期
        ('atr_multiplier', 2.0),      # ATR乘数
        ('signal_threshold', 0.02),   # 信号阈值
        ('exit_threshold', 0.01),     # 退出阈值
    )
    
    def __init__(self, params: Dict[str, Any] = None):
        """初始化动量策略"""
        super().__init__(params or {})
        
        # 获取参数
        self.momentum_period = self.params_dict.get('momentum_period', 20)
        self.sma_period = self.params_dict.get('sma_period', 50)
        self.atr_period = self.params_dict.get('atr_period', 14)
        self.atr_multiplier = self.params_dict.get('atr_multiplier', 2.0)
        self.signal_threshold = self.params_dict.get('signal_threshold', 0.02)
        self.exit_threshold = self.params_dict.get('exit_threshold', 0.01)
        
        # 创建指标
        self.momentum = bt.ind.Momentum(self.data.close, period=self.momentum_period)
        self.sma = bt.ind.SimpleMovingAverage(self.data.close, period=self.sma_period)
        self.atr = bt.ind.ATR(self.data, period=self.atr_period)
        
        # 记录关键指标
        self.last_momentum = 0
        
    def generate_signals(self):
        """生成交易信号"""
        # 检查数据长度
        if len(self.data) < max(self.momentum_period, self.sma_period):
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足'}
        
        current_close = self.data.close[0]
        current_momentum = self.momentum[0]
        current_sma = self.sma[0]
        current_atr = self.atr[0]
        
        # 计算动量强度
        momentum_strength = abs(current_momentum) / current_sma if current_sma != 0 else 0
        
        # 生成信号条件
        long_condition = (
            current_momentum > (self.signal_threshold * current_sma) and  # 动量为正且足够强
            current_close > current_sma and  # 价格在均线上方
            momentum_strength > 0.01  # 动量强度足够
        )
        
        short_condition = (
            current_momentum < (-self.signal_threshold * current_sma) and  # 动量为负且足够强
            current_close < current_sma and  # 价格在均线下方
            momentum_strength > 0.01  # 动量强度足够
        )
        
        # 持仓退出条件
        exit_condition = (
            hasattr(self, 'position') and 
            self.position.size != 0 and 
            (
                (self.position.size > 0 and current_momentum < (-self.exit_threshold * current_sma)) or  # 多头持仓遇到负动量
                (self.position.size < 0 and current_momentum > (self.exit_threshold * current_sma))     # 空头持仓遇到正动量
            )
        )
        
        # 信号强度计算
        signal_strength = min(1.0, momentum_strength * 10)  # 标准化到0-1
        
        if exit_condition:
            return {
                'action': 'sell',
                'strength': signal_strength,
                'reason': f'动量反转退出 (动量: {current_momentum:.2f})'
            }
        elif long_condition:
            return {
                'action': 'buy',
                'strength': signal_strength,
                'reason': f'强势看涨动量 (动量: {current_momentum:.2f}, 强度: {signal_strength:.2f})'
            }
        elif short_condition:
            return {
                'action': 'sell',  # 对于非做空环境，这可能意味着空头策略或不交易
                'strength': signal_strength,
                'reason': f'强势看跌动量 (动量: {current_momentum:.2f}, 强度: {signal_strength:.2f})'
            }
        else:
            return {
                'action': 'hold',
                'strength': 0.0,
                'reason': f'动量较弱或方向不明 (动量: {current_momentum:.2f})'
            }
    
    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈"""
        current_atr = self.atr[0] if len(self.atr) > 0 else 0.01 * entry_price
        
        # 基于ATR设置止损止盈
        atr_based_distance = current_atr * self.atr_multiplier
        
        self.stop_loss_price = entry_price - atr_based_distance if self.position.size > 0 else entry_price + atr_based_distance
        self.take_profit_price = entry_price + (atr_based_distance * 2) if self.position.size > 0 else entry_price - (atr_based_distance * 2)


class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""
    
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('bb_period', 20),
        ('bb_devfactor', 2.0),
        ('sma_period', 50),
    )
    
    def __init__(self, params: Dict[str, Any] = None):
        """初始化均值回归策略"""
        super().__init__(params or {})
        
        # 获取参数
        self.rsi_period = self.params_dict.get('rsi_period', 14)
        self.rsi_oversold = self.params_dict.get('rsi_oversold', 30)
        self.rsi_overbought = self.params_dict.get('rsi_overbought', 70)
        self.bb_period = self.params_dict.get('bb_period', 20)
        self.bb_devfactor = self.params_dict.get('bb_devfactor', 2.0)
        self.sma_period = self.params_dict.get('sma_period', 50)
        
        # 创建指标
        self.rsi = bt.ind.RSI(self.data.close, period=self.rsi_period)
        self.bbands = bt.ind.BollingerBands(self.data.close, period=self.bb_period, devfactor=self.bb_devfactor)
        self.sma = bt.ind.SimpleMovingAverage(self.data.close, period=self.sma_period)
        
    def generate_signals(self):
        """生成交易信号"""
        if len(self.data) < max(self.rsi_period, self.bb_period, self.sma_period):
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足'}
        
        current_close = self.data.close[0]
        current_rsi = self.rsi[0]
        current_sma = self.sma[0]
        
        # 检查是否触及布林带
        bb_top = self.bbands.top[0]
        bb_bottom = self.bbands.bot[0]
        
        # 均值回归买入信号：RSI超卖 + 价格接近布林带下轨
        long_signal = (
            current_rsi < self.rsi_oversold and  # RSI超卖
            current_close <= bb_bottom * 1.02 and  # 接近布林带下轨
            current_close < current_sma  # 价格低于均线（可能反弹）
        )
        
        # 均值回归卖出信号：RSI超买 + 价格接近布林带上轨
        short_signal = (
            current_rsi > self.rsi_overbought and  # RSI超买
            current_close >= bb_top * 0.98 and  # 接近布林带上轨
            current_close > current_sma  # 价格高于均线（可能回落）
        )
        
        # 计算信号强度
        rsi_strength = 1.0 - min(1.0, abs(current_rsi - 50) / 50)  # RSI距离中性值的强度
        
        if long_signal:
            strength = min(1.0, (self.rsi_oversold - current_rsi) / self.rsi_oversold + 0.2)
            return {
                'action': 'buy',
                'strength': strength,
                'reason': f'均值回归买入 (RSI: {current_rsi:.2f}, 价格: {current_close:.2f})'
            }
        elif short_signal:
            strength = min(1.0, (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought) + 0.2)
            return {
                'action': 'sell',
                'strength': strength,
                'reason': f'均值回归卖出 (RSI: {current_rsi:.2f}, 价格: {current_close:.2f})'
            }
        else:
            return {
                'action': 'hold',
                'strength': 0.0,
                'reason': f'未满足均值回归条件 (RSI: {current_rsi:.2f}, 位置: {current_close:.2f})'
            }
    
    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈"""
        # 均值回归策略使用较小的止损幅度
        self.stop_loss_price = entry_price * 0.97 if self.position.size > 0 else entry_price * 1.03  # 3%止损
        self.take_profit_price = entry_price * 1.08 if self.position.size > 0 else entry_price * 0.92  # 8%止盈


class BreakoutStrategy(BaseStrategy):
    """突破策略"""
    
    params = (
        ('atr_period', 14),
        ('atr_multiplier', 2.0),
        ('lookback_period', 20),  # 回看周期
        ('confirmation_period', 3),  # 确认周期
    )
    
    def __init__(self, params: Dict[str, Any] = None):
        """初始化突破策略"""
        super().__init__(params or {})
        
        # 获取参数
        self.atr_period = self.params_dict.get('atr_period', 14)
        self.atr_multiplier = self.params_dict.get('atr_multiplier', 2.0)
        self.lookback_period = self.params_dict.get('lookback_period', 20)
        self.confirmation_period = self.params_dict.get('confirmation_period', 3)
        
        # 创建指标
        self.atr = bt.ind.ATR(self.data, period=self.atr_period)
        
        # 计算高低点
        self.highest_high = bt.ind.Highest(self.data.high, period=self.lookback_period)
        self.lowest_low = bt.ind.Lowest(self.data.low, period=self.lookback_period)
        
    def generate_signals(self):
        """生成交易信号"""
        if len(self.data) < self.lookback_period:
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足'}
        
        current_close = self.data.close[0]
        current_high = self.data.high[0]
        current_low = self.data.low[0]
        
        highest_20d = self.highest_high[0]
        lowest_20d = self.lowest_low[0]
        
        # 突破上轨（多头信号）
        breakout_up = current_close > highest_20d
        breakdown_down = current_close < lowest_20d
        
        # 计算最近几个周期的确认信号
        recent_breakout = False
        recent_breakdown = False
        
        if len(self.data) >= self.confirmation_period:
            closes = [self.data.close[i] for i in range(-self.confirmation_period+1, 1)]
            highs = [self.data.high[i] for i in range(-self.confirmation_period+1, 1)]
            lows = [self.data.low[i] for i in range(-self.confirmation_period+1, 1)]
            
            # 检查最近几根K线是否持续在新高/新低之上/之下
            recent_breakout = all(close > highest_20d for close in closes[-2:])  # 最近2根K线确认
            recent_breakdown = all(close < lowest_20d for close in closes[-2:])
        
        # 信号强度基于突破幅度和ATR
        current_atr = self.atr[0] if len(self.atr) > 0 else 0.01 * current_close
        breakout_strength = max(0, (current_close - highest_20d) / current_atr) / 10  # 标准化到0-1
        breakdown_strength = max(0, (lowest_20d - current_close) / current_atr) / 10
        
        if recent_breakout:
            return {
                'action': 'buy',
                'strength': min(1.0, breakout_strength),
                'reason': f'向上突破 (突破幅度: {current_close - highest_20d:.2f})'
            }
        elif recent_breakdown:
            return {
                'action': 'sell',
                'strength': min(1.0, breakdown_strength),
                'reason': f'向下突破 (突破幅度: {lowest_20d - current_close:.2f})'
            }
        else:
            return {
                'action': 'hold',
                'strength': 0.0,
                'reason': f'未发生有效突破 (当前: {current_close:.2f}, 高点: {highest_20d:.2f}, 低点: {lowest_20d:.2f})'
            }
    
    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈"""
        current_atr = self.atr[0] if len(self.atr) > 0 else 0.01 * entry_price
        
        # 突破策略使用ATR为基础的止损止盈
        atr_distance = current_atr * self.atr_multiplier
        
        self.stop_loss_price = entry_price - atr_distance if self.position.size > 0 else entry_price + atr_distance
        self.take_profit_price = entry_price + (atr_distance * 3) if self.position.size > 0 else entry_price - (atr_distance * 3)


class TrendFollowingStrategy(BaseStrategy):
    """趋势跟踪策略"""
    
    params = (
        ('fast_ema_period', 10),
        ('slow_ema_period', 21),
        ('atr_period', 14),
        ('atr_multiplier', 3.0),
    )
    
    def __init__(self, params: Dict[str, Any] = None):
        """初始化趋势跟踪策略"""
        super().__init__(params or {})
        
        # 获取参数
        self.fast_ema_period = self.params_dict.get('fast_ema_period', 10)
        self.slow_ema_period = self.params_dict.get('slow_ema_period', 21)
        self.atr_period = self.params_dict.get('atr_period', 14)
        self.atr_multiplier = self.params_dict.get('atr_multiplier', 3.0)
        
        # 创建指标
        self.fast_ema = bt.ind.ExponentialMovingAverage(self.data.close, period=self.fast_ema_period)
        self.slow_ema = bt.ind.ExponentialMovingAverage(self.data.close, period=self.slow_ema_period)
        self.atr = bt.ind.ATR(self.data, period=self.atr_period)
        
    def generate_signals(self):
        """生成交易信号"""
        if len(self.data) < max(self.fast_ema_period, self.slow_ema_period):
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足'}
        
        current_close = self.data.close[0]
        fast_ema_val = self.fast_ema[0]
        slow_ema_val = self.slow_ema[0]
        
        # 趋势判断：快线上穿慢线为多头趋势，快线下穿慢线为空头趋势
        golden_cross = fast_ema_val > slow_ema_val and self.fast_ema[-1] <= self.slow_ema[-1]  # 金叉
        death_cross = fast_ema_val < slow_ema_val and self.fast_ema[-1] >= self.slow_ema[-1]   # 死叉
        
        # 趋势强度
        trend_strength = abs(fast_ema_val - slow_ema_val) / current_close
        
        if golden_cross:
            return {
                'action': 'buy',
                'strength': min(1.0, trend_strength * 5),
                'reason': f'趋势跟踪买入 (金叉, 强度: {trend_strength:.3f})'
            }
        elif death_cross:
            return {
                'action': 'sell',
                'strength': min(1.0, trend_strength * 5),
                'reason': f'趋势跟踪卖出 (死叉, 强度: {trend_strength:.3f})'
            }
        else:
            return {
                'action': 'hold',
                'strength': 0.0,
                'reason': f'趋势不明 (快线: {fast_ema_val:.2f}, 慢线: {slow_ema_val:.2f})'
            }
    
    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈"""
        current_atr = self.atr[0] if len(self.atr) > 0 else 0.01 * entry_price
        
        # 趋势跟踪策略使用追踪止损
        atr_distance = current_atr * self.atr_multiplier
        
        self.stop_loss_price = entry_price - atr_distance if self.position.size > 0 else entry_price + atr_distance
        self.take_profit_price = entry_price + (atr_distance * 2) if self.position.size > 0 else entry_price - (atr_distance * 2)


# ========== 策略工厂扩展 ==========
def register_new_strategies(strategy_factory_class):
    """注册新的策略到策略工厂"""
    original_create_strategy = strategy_factory_class.create_strategy
    
    def new_create_strategy(strategy_type: str, params: Dict[str, Any] = None):
        """扩展的创建策略方法"""
        if strategy_type == 'MOMENTUM':
            from strategies.momentum_strategy import MomentumStrategy
            return MomentumStrategy(params)
        elif strategy_type == 'MEAN_REVERSION':
            from strategies.momentum_strategy import MeanReversionStrategy
            return MeanReversionStrategy(params)
        elif strategy_type == 'BREAKOUT':
            from strategies.momentum_strategy import BreakoutStrategy
            return BreakoutStrategy(params)
        elif strategy_type == 'TREND_FOLLOWING':
            from strategies.momentum_strategy import TrendFollowingStrategy
            return TrendFollowingStrategy(params)
        else:
            # 调用原始方法
            return original_create_strategy(strategy_type, params)
    
    # 替换创建策略方法
    strategy_factory_class.create_strategy = staticmethod(new_create_strategy)
    
    # 扩展获取可用策略列表的方法
    original_get_available = strategy_factory_class.get_available_strategies
    
    def new_get_available_strategies():
        original_strategies = original_get_available()
        new_strategies = ['MOMENTUM', 'MEAN_REVERSION', 'BREAKOUT', 'TREND_FOLLOWING']
        return original_strategies + new_strategies
    
    strategy_factory_class.get_available_strategies = staticmethod(new_get_available_strategies)


if __name__ == "__main__":
    # 测试策略
    print("测试新增策略...")
    
    # 这里可以添加测试代码来验证策略功能
    print("策略模块加载成功")