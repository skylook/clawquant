"""
RSI策略
基于相对强弱指数的超买超卖策略
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, **kwargs):
        """
        初始化RSI策略
        
        Args:
            params: 策略参数
        """
        # 默认参数
        default_params = {
            'rsi_period': 14,        # RSI计算周期
            'overbought': 70,        # 超买线
            'oversold': 30,          # 超卖线
            'use_divergence': True,  # 是否使用背离信号
            'exit_on_middle': False, # 是否在50线退出
            'use_confirmation': True,# 是否使用确认信号
            'smooth_rsi': False,     # 是否平滑RSI
            'smooth_period': 3,      # 平滑周期
        }
        
        # 合并参数
        # 合并参数
        default_params.update(kwargs)
        
        super().__init__(default_params)
        
        # 策略特定初始化
        self._init_rsi_strategy()
    
    def _init_rsi_strategy(self):
        """初始化RSI策略特定指标"""
        params = self.params_dict
        
        # RSI指标
        self.rsi = bt.indicators.RelativeStrengthIndex(
            self.data.close, period=params['rsi_period']
        )
        
        # 平滑RSI（可选）
        if params['smooth_rsi']:
            self.rsi_smooth = bt.indicators.SimpleMovingAverage(
                self.rsi, period=params['smooth_period']
            )
            self.rsi_to_use = self.rsi_smooth
        else:
            self.rsi_to_use = self.rsi
        
        # 超买超卖线
        self.overbought_line = bt.indicators.Constant(params['overbought'], plot=False)
        self.oversold_line = bt.indicators.Constant(params['oversold'], plot=False)
        self.middle_line = bt.indicators.Constant(50, plot=False)
        
        # 交叉信号
        self.overbought_cross = bt.indicators.CrossOver(self.rsi_to_use, self.overbought_line)
        self.oversold_cross = bt.indicators.CrossOver(self.rsi_to_use, self.oversold_line)
        self.middle_cross_up = bt.indicators.CrossOver(self.rsi_to_use, self.middle_line)
        self.middle_cross_down = bt.indicators.CrossOver(self.middle_line, self.rsi_to_use)
        
        # 趋势过滤
        self.trend_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=50
        )
        self.trend = self.data.close > self.trend_sma
        
        # 记录历史RSI和价格用于背离检测
        self.rsi_history = []
        self.price_history = []
        
        # 状态变量
        self.oversold_triggered = False
        self.overbought_triggered = False
        self.last_signal = None
    
    def generate_signals(self) -> Dict[str, Any]:
        """
        生成交易信号
        
        策略逻辑：
        1. RSI低于超卖线 -> 买入信号
        2. RSI高于超买线 -> 卖出信号
        3. RSI从超卖区回到50以上 -> 确认买入
        4. RSI从超买区回到50以下 -> 确认卖出
        5. 背离信号 -> 反转信号
        """
        signals = {}
        
        # 检查数据是否足够
        min_period = max(self.params_dict['rsi_period'], 50)
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}
        
        # 获取当前值
        rsi_val = self.rsi_to_use[0]
        close_val = self.data.close[0]
        
        # 更新历史记录
        self._update_history(rsi_val, close_val)
        
        # 趋势过滤
        trend_ok = self.trend[0]
        
        # 更新触发状态
        self._update_trigger_states(rsi_val)
        
        # 生成信号
        if trend_ok or not self.params_dict['use_confirmation']:
            # 主要信号：超买超卖
            signals.update(self._generate_overbought_oversold_signals(rsi_val))
            
            # 确认信号（可选）
            if self.params_dict['use_confirmation']:
                signals.update(self._generate_confirmation_signals(rsi_val))
            
            # 背离信号（可选）
            if self.params_dict['use_divergence']:
                signals.update(self._generate_divergence_signals())
            
            # 中间线退出（可选）
            if self.params_dict['exit_on_middle'] and self.position.size > 0:
                signals.update(self._generate_middle_exit_signals(rsi_val))
        
        else:
            # 趋势向下，谨慎操作
            signals.update(self._generate_trend_down_signals(rsi_val))
        
        # 如果没有信号，返回默认
        if not signals:
            signals = {
                'action': 'hold',
                'strength': 0,
                'reason': '等待RSI信号'
            }
        
        # 记录最后信号
        if signals['action'] != 'hold':
            self.last_signal = signals
        
        return signals
    
    def _update_history(self, rsi_val: float, price: float):
        """更新历史记录"""
        self.rsi_history.append(rsi_val)
        self.price_history.append(price)
        
        # 只保留最近100个值
        if len(self.rsi_history) > 100:
            self.rsi_history.pop(0)
            self.price_history.pop(0)
    
    def _update_trigger_states(self, rsi_val: float):
        """更新触发状态"""
        params = self.params_dict
        
        # 检查是否触发超卖
        if rsi_val <= params['oversold']:
            self.oversold_triggered = True
        elif rsi_val >= params['oversold'] + 5:  # 离开超卖区一定距离
            self.oversold_triggered = False
        
        # 检查是否触发超买
        if rsi_val >= params['overbought']:
            self.overbought_triggered = True
        elif rsi_val <= params['overbought'] - 5:  # 离开超买区一定距离
            self.overbought_triggered = False
    
    def _generate_overbought_oversold_signals(self, rsi_val: float) -> Dict[str, Any]:
        """生成超买超卖信号"""
        signals = {}
        params = self.params_dict
        
        # 超卖买入信号
        if rsi_val <= params['oversold']:
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = self._calculate_oversold_strength(rsi_val)
                signals['reason'] = f'RSI超卖: {rsi_val:.1f} ≤ {params["oversold"]}'
        
        # 超买卖出信号
        elif rsi_val >= params['overbought']:
            if self.position.size > 0:
                signals['action'] = 'sell'
                signals['strength'] = self._calculate_overbought_strength(rsi_val)
                signals['reason'] = f'RSI超买: {rsi_val:.1f} ≥ {params["overbought"]}'
        
        return signals
    
    def _generate_confirmation_signals(self, rsi_val: float) -> Dict[str, Any]:
        """生成确认信号"""
        signals = {}
        
        # 超卖后确认买入：RSI从超卖区回到50以上
        if self.oversold_triggered and rsi_val > 50:
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = 0.7
                signals['reason'] = 'RSI从超卖区回到50以上，确认买入'
                self.oversold_triggered = False
        
        # 超买后确认卖出：RSI从超买区回到50以下
        elif self.overbought_triggered and rsi_val < 50:
            if self.position.size > 0:
                signals['action'] = 'sell'
                signals['strength'] = 0.7
                signals['reason'] = 'RSI从超买区回到50以下，确认卖出'
                self.overbought_triggered = False
        
        return signals
    
    def _generate_divergence_signals(self) -> Dict[str, Any]:
        """生成背离信号"""
        signals = {}
        
        if len(self.rsi_history) < 20 or len(self.price_history) < 20:
            return signals
        
        # 检测顶背离：价格创新高，RSI未创新高
        recent_prices = self.price_history[-10:]
        recent_rsi = self.rsi_history[-10:]
        
        price_max_idx = np.argmax(recent_prices)
        rsi_max_idx = np.argmax(recent_rsi)
        
        if price_max_idx == len(recent_prices) - 1:  # 价格刚创新高
            if rsi_max_idx != len(recent_rsi) - 1:  # RSI未创新高
                if self.position.size > 0:
                    signals['action'] = 'sell'
                    signals['strength'] = 0.9
                    signals['reason'] = '顶背离，价格新高但RSI未新高'
        
        # 检测底背离：价格创新低，RSI未创新低
        price_min_idx = np.argmin(recent_prices)
        rsi_min_idx = np.argmin(recent_rsi)
        
        if price_min_idx == len(recent_prices) - 1:  # 价格刚创新低
            if rsi_min_idx != len(recent_rsi) - 1:  # RSI未创新低
                if self.position.size == 0:
                    signals['action'] = 'buy'
                    signals['strength'] = 0.9
                    signals['reason'] = '底背离，价格新低但RSI未新低'
        
        return signals
    
    def _generate_middle_exit_signals(self, rsi_val: float) -> Dict[str, Any]:
        """生成中间线退出信号"""
        signals = {}
        
        # 买入后，RSI跌破50线时退出
        if self.middle_cross_down[0] == 1:  # RSI从上方跌破50
            if self.position.size > 0 and self.last_signal and self.last_signal['action'] == 'buy':
                signals['action'] = 'sell'
                signals['strength'] = 0.6
                signals['reason'] = 'RSI跌破50线，退出多头'
        
        return signals
    
    def _generate_trend_down_signals(self, rsi_val: float) -> Dict[str, Any]:
        """趋势向下时的信号"""
        signals = {}
        
        # 趋势向下时，只在超卖时考虑买入
        if rsi_val <= self.params_dict['oversold']:
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = 0.5  # 降低信号强度
                signals['reason'] = '趋势向下，但RSI超卖，谨慎买入'
        
        # 如果有持仓，考虑在反弹时卖出
        elif self.position.size > 0 and rsi_val >= 60:
            signals['action'] = 'sell'
            signals['strength'] = 0.8
            signals['reason'] = '趋势向下，反弹时保护利润'
        
        return signals
    
    def _calculate_oversold_strength(self, rsi_val: float) -> float:
        """计算超卖信号强度"""
        params = self.params_dict
        
        # RSI越低，信号越强
        oversold_level = params['oversold']
        strength = (oversold_level - rsi_val) / oversold_level
        
        # 限制在0.3-1.0之间
        return max(min(strength, 1.0), 0.3)
    
    def _calculate_overbought_strength(self, rsi_val: float) -> float:
        """计算超买信号强度"""
        params = self.params_dict
        
        # RSI越高，信号越强
        overbought_level = params['overbought']
        max_rsi = 100  # RSI最大值
        strength = (rsi_val - overbought_level) / (max_rsi - overbought_level)
        
        # 限制在0.3-1.0之间
        return max(min(strength, 1.0), 0.3)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = {
            'strategy_name': 'RSI策略',
            'strategy_type': 'RSI',
            'description': '基于相对强弱指数的超买超卖策略',
            'parameters': self.params_dict,
            'indicators': ['RSI', '超买线', '超卖线', '50线'],
            'signal_type': '反转',
            'risk_level': '中等'
        }
        
        # 添加当前指标值
        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'rsi': float(self.rsi_to_use[0]) if hasattr(self, 'rsi_to_use') else None,
                'trend': bool(self.trend[0]) if hasattr(self, 'trend') else None,
                'oversold_triggered': self.oversold_triggered,
                'overbought_triggered': self.overbought_triggered
            }
        
        return info


# ========== 策略参数优化配置 ==========

class RSIStrategyOptimizer:
    """RSI策略优化器"""
    
    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """获取参数网格"""
        return {
            'rsi_period': [6, 9, 12, 14, 16, 20, 25],
            'overbought': [65, 70, 75, 80],
            'oversold': [20, 25, 30, 35],
            'use_divergence': [True, False],
            'exit_on_middle': [True, False],
            'use_confirmation': [True, False],
            'smooth_rsi': [True, False]
        }
    
    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'rsi_period': 14,
            'overbought': 70,
            'oversold': 30,
            'use_divergence': True,
            'exit_on_middle': False,
            'use_confirmation': True,
            'smooth_rsi': False,
            'smooth_period': 3,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试RSI策略
    print("测试RSI策略...")
    
    # 创建策略实例
    params = {
        'rsi_period': 14,
        'overbought': 70,
        'oversold': 30,
        'use_divergence': True
    }
    
    strategy = RSIStrategy(params)
    
    # 获取策略信息
    info = strategy.get_strategy_info()
    print(f"策略名称: {info['strategy_name']}")
    print(f"策略描述: {info['description']}")
    print(f"策略参数: {info['parameters']}")
    
    # 获取优化器配置
    optimizer = RSIStrategyOptimizer()
    param_grid = optimizer.get_param_grid()
    print(f"\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    print("\n策略测试完成!")