"""
布林带策略
基于布林带的价格通道策略
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class BollingerStrategy(BaseStrategy):
    """布林带策略"""
    
    def __init__(self, **kwargs):
        """
        初始化布林带策略
        
        Args:
            params: 策略参数
        """
        # 默认参数
        default_params = {
            'period': 20,           # 布林带周期
            'devfactor': 2.0,       # 标准差倍数
            'use_band_width': True, # 是否使用带宽指标
            'use_percent_b': True,  # 是否使用%b指标
            'squeeze_threshold': 0.1, # 挤压阈值
            'band_touch_threshold': 0.95, # 触及边界阈值
            'exit_on_middle': True, # 是否在中轨退出
        }
        
        # 合并参数
        default_params.update(kwargs)
        
        super().__init__(default_params)
        
        # 策略特定初始化
        self._init_bollinger_strategy()
    
    def _init_bollinger_strategy(self):
        """初始化布林带策略特定指标"""
        params = self.params_dict
        
        # 布林带指标
        self.bollinger = bt.indicators.BollingerBands(
            self.data.close,
            period=params['period'],
            devfactor=params['devfactor']
        )
        
        # 布林带上下轨和中轨
        self.bb_top = self.bollinger.top
        self.bb_bot = self.bollinger.bot
        self.bb_mid = self.bollinger.mid
        
        # 价格位置（相对于布林带）- 运行时通过 _safe_price_position() 获取以避免除零
        
        # 带宽指标（可选）
        if params['use_band_width']:
            self.band_width = (self.bb_top - self.bb_bot) / self.bb_mid
        
        # %b指标（可选）
        if params['use_percent_b']:
            self.percent_b = (self.data.close - self.bb_bot) / (self.bb_top - self.bb_bot)
        
        # 趋势过滤
        self.trend_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=50
        )
        self.trend = self.data.close > self.trend_sma
        
        # 成交量确认（可选）
        if hasattr(self.data, 'volume'):
            self.volume_sma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=20
            )
            self.volume_ratio = self.data.volume / self.volume_sma
        
        # 状态变量
        self.squeeze_detected = False
        self.last_touch = None  # 'top' 或 'bot'

    def _safe_price_position(self) -> float:
        """计算价格在布林带中的位置，带除零保护"""
        bb_range = self.bb_top[0] - self.bb_bot[0]
        if abs(bb_range) < 1e-10:
            return 0.5  # 布林带挤压时返回中间值
        return (self.data.close[0] - self.bb_bot[0]) / bb_range

    def generate_signals(self) -> Dict[str, Any]:
        """
        生成交易信号
        
        策略逻辑：
        1. 价格触及下轨 -> 买入信号
        2. 价格触及上轨 -> 卖出信号
        3. 布林带挤压 -> 突破预警
        4. 价格回到中轨 -> 部分退出
        5. 带宽变化 -> 动量信号
        """
        signals = {}
        
        # 检查数据是否足够
        min_period = max(self.params_dict['period'], 50)
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}
        
        # 获取当前值
        close = self.data.close[0]
        bb_top = self.bb_top[0]
        bb_bot = self.bb_bot[0]
        bb_mid = self.bb_mid[0]
        
        # 计算价格位置
        price_pos = self._safe_price_position()
        
        # 检测布林带挤压
        self._detect_squeeze()
        
        # 检测边界触及
        touch_signal = self._detect_band_touch(close, bb_top, bb_bot, price_pos)
        
        # 趋势过滤
        trend_ok = self.trend[0]
        
        # 生成信号
        if trend_ok:
            # 边界触及信号
            if touch_signal:
                signals.update(touch_signal)
            
            # 挤压突破信号
            elif self.squeeze_detected:
                signals.update(self._generate_squeeze_breakout_signals(close, bb_mid))
            
            # 中轨退出信号（可选）
            elif self.params_dict['exit_on_middle']:
                signals.update(self._generate_middle_exit_signals(close, bb_mid))
            
            # 持仓监控
            elif self.position.size > 0:
                signals.update(self._monitor_position(close, bb_top, bb_bot, bb_mid))
            
            # 空仓等待
            else:
                signals['action'] = 'hold'
                signals['strength'] = 0
                signals['reason'] = '等待布林带信号'
        
        else:
            # 趋势向下，谨慎操作
            signals.update(self._generate_trend_down_signals(close, bb_bot, bb_top))
        
        return signals
    
    def _detect_squeeze(self):
        """检测布林带挤压"""
        if not self.params_dict['use_band_width']:
            return
        
        if len(self.band_width) < 2:
            return
        
        # 检查带宽是否低于阈值
        current_width = self.band_width[0]
        prev_width = self.band_width[-1]
        threshold = self.params_dict['squeeze_threshold']
        
        if current_width < threshold and prev_width < threshold:
            self.squeeze_detected = True
        elif current_width > threshold * 1.5:
            self.squeeze_detected = False
    
    def _detect_band_touch(self, close: float, bb_top: float, 
                          bb_bot: float, price_pos: float) -> Dict[str, Any]:
        """检测边界触及"""
        signals = {}
        threshold = self.params_dict['band_touch_threshold']
        
        # 触及下轨（超卖）
        if price_pos <= (1 - threshold):
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = self._calculate_bot_touch_strength(close, bb_bot)
                signals['reason'] = f'触及布林带下轨，价格位置: {price_pos:.3f}'
                self.last_touch = 'bot'
        
        # 触及上轨（超买）
        elif price_pos >= threshold:
            if self.position.size > 0:
                signals['action'] = 'sell'
                signals['strength'] = self._calculate_top_touch_strength(close, bb_top)
                signals['reason'] = f'触及布林带上轨，价格位置: {price_pos:.3f}'
                self.last_touch = 'top'
        
        return signals
    
    def _generate_squeeze_breakout_signals(self, close: float, bb_mid: float) -> Dict[str, Any]:
        """生成挤压突破信号"""
        signals = {}
        
        if not self.squeeze_detected:
            return signals
        
        # 向上突破
        if close > bb_mid:
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = 0.6
                signals['reason'] = '布林带挤压后向上突破'
                self.squeeze_detected = False
        
        # 向下跌破
        elif close < bb_mid:
            if self.position.size > 0:
                signals['action'] = 'sell'
                signals['strength'] = 0.6
                signals['reason'] = '布林带挤压后向下跌破'
                self.squeeze_detected = False
        
        return signals
    
    def _generate_middle_exit_signals(self, close: float, bb_mid: float) -> Dict[str, Any]:
        """生成中轨退出信号"""
        signals = {}
        
        if self.position.size == 0:
            return signals
        
        # 检查价格是否回到中轨附近
        mid_distance = abs(close - bb_mid) / bb_mid
        
        if mid_distance < 0.02:  # 2%以内
            signals['action'] = 'sell'
            signals['strength'] = 0.5
            signals['reason'] = '价格回到布林带中轨，部分退出'
        
        return signals
    
    def _monitor_position(self, close: float, bb_top: float, 
                         bb_bot: float, bb_mid: float) -> Dict[str, Any]:
        """监控持仓"""
        signals = {}
        price_pos = self._safe_price_position()
        
        # 检查是否应该继续持有
        if self.last_touch == 'bot':  # 从下轨买入
            # 如果价格还在中轨以下，继续持有
            if close < bb_mid:
                signals['action'] = 'hold'
                signals['strength'] = 0.7
                signals['reason'] = f'价格仍在布林带下半部，位置: {price_pos:.3f}'
            else:
                # 价格已到上半部，考虑部分退出
                signals['action'] = 'sell'
                signals['strength'] = 0.6
                signals['reason'] = f'价格到达布林带上半部，位置: {price_pos:.3f}'
        
        return signals
    
    def _generate_trend_down_signals(self, close: float, 
                                    bb_bot: float, bb_top: float) -> Dict[str, Any]:
        """趋势向下时的信号"""
        signals = {}
        
        price_pos = self._safe_price_position()
        threshold = self.params_dict['band_touch_threshold']
        
        # 趋势向下时，只在极端超卖时考虑买入
        if price_pos <= (1 - threshold * 1.1):  # 更严格的条件
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = 0.4  # 降低信号强度
                signals['reason'] = '趋势向下，但极端超卖，谨慎买入'
        
        # 如果有持仓，在触及上轨时卖出
        elif price_pos >= threshold and self.position.size > 0:
            signals['action'] = 'sell'
            signals['strength'] = 0.8
            signals['reason'] = '趋势向下，触及上轨时保护利润'
        
        else:
            signals['action'] = 'hold'
            signals['strength'] = 0
            signals['reason'] = '趋势向下，观望'
        
        return signals
    
    def _calculate_bot_touch_strength(self, close: float, bb_bot: float) -> float:
        """计算下轨触及信号强度"""
        # 价格低于下轨越多，信号越强
        if close < bb_bot:
            penetration = (bb_bot - close) / bb_bot
            strength = min(penetration * 100, 1.0)
        else:
            # 价格在下轨之上但接近
            distance = (close - bb_bot) / bb_bot
            strength = max(1.0 - distance * 100, 0.3)
        
        # 考虑成交量确认
        if hasattr(self, 'volume_ratio'):
            volume_strength = min(self.volume_ratio[0] / 2.0, 1.0)
            strength = (strength + volume_strength) / 2
        
        return max(min(strength, 1.0), 0.3)
    
    def _calculate_top_touch_strength(self, close: float, bb_top: float) -> float:
        """计算上轨触及信号强度"""
        # 价格高于上轨越多，信号越强
        if close > bb_top:
            penetration = (close - bb_top) / bb_top
            strength = min(penetration * 100, 1.0)
        else:
            # 价格在上轨之下但接近
            distance = (bb_top - close) / bb_top
            strength = max(1.0 - distance * 100, 0.3)
        
        # 考虑成交量确认
        if hasattr(self, 'volume_ratio'):
            volume_strength = min(self.volume_ratio[0] / 2.0, 1.0)
            strength = (strength + volume_strength) / 2
        
        return max(min(strength, 1.0), 0.3)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = {
            'strategy_name': '布林带策略',
            'strategy_type': 'BOLL',
            'description': '基于布林带的价格通道策略',
            'parameters': self.params_dict,
            'indicators': ['布林带上轨', '布林带中轨', '布林带下轨', '带宽', '%b(可选)'],
            'signal_type': '通道交易',
            'risk_level': '中等'
        }
        
        # 添加当前指标值
        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'bb_top': float(self.bb_top[0]) if hasattr(self, 'bb_top') else None,
                'bb_mid': float(self.bb_mid[0]) if hasattr(self, 'bb_mid') else None,
                'bb_bot': float(self.bb_bot[0]) if hasattr(self, 'bb_bot') else None,
                'price_position': float(self._safe_price_position()),
                'trend': bool(self.trend[0]) if hasattr(self, 'trend') else None,
                'squeeze_detected': self.squeeze_detected,
                'last_touch': self.last_touch
            }
        
        return info


# ========== 策略参数优化配置 ==========

class BollingerStrategyOptimizer:
    """布林带策略优化器"""
    
    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """获取参数网格"""
        return {
            'period': [10, 15, 20, 25, 30],
            'devfactor': [1.5, 2.0, 2.5, 3.0],
            'use_band_width': [True, False],
            'use_percent_b': [True, False],
            'squeeze_threshold': [0.05, 0.1, 0.15, 0.2],
            'band_touch_threshold': [0.9, 0.95, 0.98],
            'exit_on_middle': [True, False]
        }
    
    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'period': 20,
            'devfactor': 2.0,
            'use_band_width': True,
            'use_percent_b': True,
            'squeeze_threshold': 0.1,
            'band_touch_threshold': 0.95,
            'exit_on_middle': True,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试布林带策略
    print("测试布林带策略...")
    
    # 创建策略实例
    params = {
        'period': 20,
        'devfactor': 2.0,
        'use_band_width': True,
        'use_percent_b': True
    }
    
    strategy = BollingerStrategy(params)
    
    # 获取策略信息
    info = strategy.get_strategy_info()
    print(f"策略名称: {info['strategy_name']}")
    print(f"策略描述: {info['description']}")
    print(f"策略参数: {info['parameters']}")
    
    # 获取优化器配置
    optimizer = BollingerStrategyOptimizer()
    param_grid = optimizer.get_param_grid()
    print(f"\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    print("\n策略测试完成!")