"""
双均线交叉策略
基于短期和长期均线交叉的趋势跟踪策略
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class MACrossStrategy(BaseStrategy):
    """双均线交叉策略"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化双均线交叉策略
        
        Args:
            params: 策略参数
        """
        # 默认参数
        default_params = {
            'fast_period': 10,       # 快速均线周期
            'slow_period': 30,       # 慢速均线周期
            'use_volume_filter': False, # 是否使用成交量过滤
            'use_trend_filter': True,   # 是否使用趋势过滤
            'trend_period': 200,     # 趋势过滤周期
            'use_atr_stop': True,    # 是否使用ATR止损
            'atr_period': 14,        # ATR周期
            'atr_multiplier': 2.0,   # ATR倍数
        }
        
        # 合并参数
        if params:
            default_params.update(params)
        
        super().__init__(default_params)
        
        # 策略特定初始化
        self._init_ma_cross_strategy()
    
    def _init_ma_cross_strategy(self):
        """初始化双均线交叉策略特定指标"""
        params = self.params_dict
        
        # 快速均线
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['fast_period']
        )
        
        # 慢速均线
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['slow_period']
        )
        
        # 均线差值
        self.ma_diff = self.fast_ma - self.slow_ma
        
        # 交叉信号
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # 趋势过滤（可选）
        if params['use_trend_filter']:
            self.trend_ma = bt.indicators.SimpleMovingAverage(
                self.data.close, period=params['trend_period']
            )
            self.trend = self.data.close > self.trend_ma
        
        # 成交量过滤（可选）
        if params['use_volume_filter'] and hasattr(self.data, 'volume'):
            self.volume_sma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=20
            )
            self.volume_ratio = self.data.volume / self.volume_sma
        
        # ATR止损（可选）
        if params['use_atr_stop']:
            self.atr = bt.indicators.ATR(self.data, period=params['atr_period'])
        
        # 状态变量
        self.cross_direction = None  # 'golden' 或 'death'
        self.entry_cross = False     # 是否在交叉时入场
    
    def generate_signals(self) -> Dict[str, Any]:
        """
        生成交易信号
        
        策略逻辑：
        1. 快速均线上穿慢速均线 -> 买入信号（金叉）
        2. 快速均线下穿慢速均线 -> 卖出信号（死叉）
        3. 使用趋势过滤（价格在长期均线上方才做多）
        4. 使用成交量过滤（成交量高于均线才交易）
        """
        signals = {}
        
        # 检查数据是否足够
        min_period = max(self.params_dict['slow_period'], 
                        self.params_dict.get('trend_period', 200))
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}
        
        # 获取当前值
        close = self.data.close[0]
        fast_ma = self.fast_ma[0]
        slow_ma = self.slow_ma[0]
        
        # 趋势过滤
        trend_ok = True
        if self.params_dict['use_trend_filter']:
            trend_ok = self.trend[0] if hasattr(self, 'trend') else True
        
        # 成交量过滤
        volume_ok = True
        if self.params_dict['use_volume_filter'] and hasattr(self, 'volume_ratio'):
            volume_ok = self.volume_ratio[0] > 1.0
        
        # 生成信号
        if trend_ok and volume_ok:
            # 金叉买入信号
            if self.crossover[0] == 1:  # 快速均线上穿慢速均线
                self.cross_direction = 'golden'
                self.entry_cross = True
                
                if self.position.size == 0:
                    signals['action'] = 'buy'
                    signals['strength'] = self._calculate_golden_cross_strength(fast_ma, slow_ma)
                    signals['reason'] = f'均线金叉: {params["fast_period"]}上穿{params["slow_period"]}'
            
            # 死叉卖出信号
            elif self.crossover[0] == -1:  # 快速均线下穿慢速均线
                self.cross_direction = 'death'
                self.entry_cross = True
                
                if self.position.size > 0:
                    signals['action'] = 'sell'
                    signals['strength'] = 1.0
                    signals['reason'] = f'均线死叉: {params["fast_period"]}下穿{params["slow_period"]}'
            
            # 持仓监控
            elif self.position.size > 0:
                signals.update(self._monitor_long_position(fast_ma, slow_ma, close))
            
            # 空仓等待
            else:
                signals['action'] = 'hold'
                signals['strength'] = 0
                signals['reason'] = '等待均线交叉信号'
        
        else:
            # 过滤条件不满足
            signals.update(self._generate_filtered_signals(close, fast_ma, slow_ma))
        
        return signals
    
    def _calculate_golden_cross_strength(self, fast_ma: float, slow_ma: float) -> float:
        """计算金叉信号强度"""
        # 基于均线距离和角度
        ma_distance = fast_ma - slow_ma
        distance_pct = abs(ma_distance) / slow_ma
        
        # 标准化到0-1范围
        strength = min(distance_pct * 100, 1.0)
        
        # 考虑趋势强度
        if hasattr(self, 'trend') and self.trend[0]:
            strength *= 1.2  # 趋势向上时增强信号
        
        # 考虑成交量
        if hasattr(self, 'volume_ratio'):
            volume_strength = min(self.volume_ratio[0] / 2.0, 1.0)
            strength = (strength + volume_strength) / 2
        
        return min(max(strength, 0.3), 1.0)  # 限制在0.3-1.0之间
    
    def _monitor_long_position(self, fast_ma: float, slow_ma: float, 
                              close: float) -> Dict[str, Any]:
        """监控多头持仓"""
        signals = {}
        
        # 检查均线排列
        if fast_ma > slow_ma:
            # 均线多头排列，继续持有
            ma_diff_pct = (fast_ma - slow_ma) / slow_ma
            strength = min(ma_diff_pct * 200, 0.9)  # 基于均线距离计算强度
            
            signals['action'] = 'hold'
            signals['strength'] = max(strength, 0.5)
            signals['reason'] = f'均线多头排列，距离: {ma_diff_pct:.2%}'
        
        else:
            # 均线空头排列或纠缠，考虑平仓
            signals['action'] = 'sell'
            signals['strength'] = 0.8
            signals['reason'] = '均线空头排列，平仓'
        
        return signals
    
    def _generate_filtered_signals(self, close: float, fast_ma: float, 
                                  slow_ma: float) -> Dict[str, Any]:
        """生成过滤条件下的信号"""
        signals = {}
        
        # 检查当前持仓
        if self.position.size > 0:
            # 有持仓但过滤条件不满足
            
            # 如果趋势变坏，强制平仓
            if self.params_dict['use_trend_filter'] and hasattr(self, 'trend') and not self.trend[0]:
                signals['action'] = 'sell'
                signals['strength'] = 0.9
                signals['reason'] = '趋势变坏，强制平仓'
            
            # 如果成交量不足但趋势还在，谨慎持有
            elif self.params_dict['use_volume_filter'] and hasattr(self, 'volume_ratio') and self.volume_ratio[0] < 0.8:
                signals['action'] = 'hold'
                signals['strength'] = 0.4
                signals['reason'] = '成交量不足但趋势仍在，谨慎持有'
            
            else:
                signals['action'] = 'hold'
                signals['strength'] = 0.6
                signals['reason'] = '过滤条件检查中'
        
        else:
            # 空仓，等待条件满足
            signals['action'] = 'hold'
            signals['strength'] = 0
            signals['reason'] = '等待过滤条件满足'
        
        return signals
    
    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈价格（重写基类方法）"""
        if self.params_dict['use_atr_stop'] and hasattr(self, 'atr'):
            # 使用ATR动态止损
            atr_value = self.atr[0]
            atr_stop = self.params_dict['atr_multiplier'] * atr_value
            
            self.stop_loss_price = entry_price - atr_stop
            self.take_profit_price = entry_price + 2 * atr_stop  # 盈亏比2:1
        else:
            # 使用固定比例止损止盈
            super()._set_stop_loss_take_profit(entry_price)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = {
            'strategy_name': '双均线交叉策略',
            'strategy_type': 'MA_CROSS',
            'description': '基于短期和长期均线交叉的趋势跟踪策略',
            'parameters': self.params_dict,
            'indicators': ['快速均线', '慢速均线', '交叉信号', 'ATR(可选)'],
            'signal_type': '趋势跟踪',
            'risk_level': '中等'
        }
        
        # 添加当前指标值
        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'fast_ma': float(self.fast_ma[0]) if hasattr(self, 'fast_ma') else None,
                'slow_ma': float(self.slow_ma[0]) if hasattr(self, 'slow_ma') else None,
                'ma_diff': float(self.ma_diff[0]) if hasattr(self, 'ma_diff') else None,
                'trend': bool(self.trend[0]) if hasattr(self, 'trend') else None,
                'cross_direction': self.cross_direction,
                'entry_cross': self.entry_cross
            }
        
        return info


# ========== 策略参数优化配置 ==========

class MACrossStrategyOptimizer:
    """双均线交叉策略优化器"""
    
    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """获取参数网格"""
        return {
            'fast_period': [3, 5, 8, 10, 13, 15, 18, 20],
            'slow_period': [20, 25, 30, 35, 40, 45, 50, 60],
            'use_volume_filter': [True, False],
            'use_trend_filter': [True, False],
            'use_atr_stop': [True, False],
            'atr_multiplier': [1.5, 2.0, 2.5, 3.0]
        }
    
    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'fast_period': 10,
            'slow_period': 30,
            'use_volume_filter': False,
            'use_trend_filter': True,
            'trend_period': 200,
            'use_atr_stop': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试双均线交叉策略
    print("测试双均线交叉策略...")
    
    # 创建策略实例
    params = {
        'fast_period': 10,
        'slow_period': 30,
        'use_trend_filter': True,
        'use_atr_stop': True
    }
    
    strategy = MACrossStrategy(params)
    
    # 获取策略信息
    info = strategy.get_strategy_info()
    print(f"策略名称: {info['strategy_name']}")
    print(f"策略描述: {info['description']}")
    print(f"策略参数: {info['parameters']}")
    
    # 获取优化器配置
    optimizer = MACrossStrategyOptimizer()
    param_grid = optimizer.get_param_grid()
    print(f"\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    print("\n策略测试完成!")