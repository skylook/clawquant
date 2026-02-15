"""
移动平均线策略
基于简单移动平均线的趋势跟踪策略
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class MAStrategy(BaseStrategy):
    """移动平均线策略"""
    
    def __init__(self, **kwargs):
        """
        初始化移动平均线策略
        
        Args:
            params: 策略参数
        """
        # 默认参数
        default_params = {
            'sma_period': 20,      # 短期均线周期
            'lma_period': 60,      # 长期均线周期
            'use_atr_stop': True,  # 是否使用ATR止损
            'atr_period': 14,      # ATR周期
            'atr_multiplier': 2.0, # ATR倍数
            'trend_filter': True,  # 是否使用趋势过滤
            'volume_filter': False # 是否使用成交量过滤
        }
        
        # 合并参数
        default_params.update(kwargs)
        
        super().__init__(default_params)
        
        # 策略特定初始化
        self._init_ma_strategy()
    
    def _init_ma_strategy(self):
        """初始化MA策略特定指标"""
        params = self.params_dict
        
        # 移动平均线
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['sma_period']
        )
        
        self.lma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=params['lma_period']
        )
        
        # 均线差值
        self.ma_diff = self.sma - self.lma
        
        # 均线交叉信号
        self.crossover = bt.indicators.CrossOver(self.sma, self.lma)
        
        # 趋势指标
        if params['trend_filter']:
            self.trend_sma = bt.indicators.SimpleMovingAverage(
                self.data.close, period=200
            )
            self.trend = self.data.close > self.trend_sma
        
        # 成交量指标（可选）
        if params['volume_filter'] and hasattr(self.data, 'volume'):
            self.volume_sma = bt.indicators.SimpleMovingAverage(
                self.data.volume, period=20
            )
            self.volume_ratio = self.data.volume / self.volume_sma
        
        # ATR止损（可选）
        if params['use_atr_stop']:
            self.atr = bt.indicators.ATR(self.data, period=params['atr_period'])
    
    def generate_signals(self) -> Dict[str, Any]:
        """
        生成交易信号
        
        策略逻辑：
        1. 短期均线上穿长期均线 -> 买入信号
        2. 短期均线下穿长期均线 -> 卖出信号
        3. 使用趋势过滤（价格在200日均线上方才做多）
        4. 使用成交量过滤（成交量高于均线才交易）
        """
        signals = {}
        
        # 检查数据是否足够
        if len(self.data) < max(self.params_dict['lma_period'], 200):
            return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}
        
        # 获取当前值
        close = self.data.close[0]
        sma = self.sma[0]
        lma = self.lma[0]
        
        # 趋势过滤
        trend_ok = True
        if self.params_dict['trend_filter']:
            trend_ok = self.trend[0] if hasattr(self, 'trend') else True
        
        # 成交量过滤
        volume_ok = True
        if self.params_dict['volume_filter'] and hasattr(self, 'volume_ratio'):
            volume_ok = self.volume_ratio[0] > 1.0
        
        # 生成信号
        if trend_ok and volume_ok:
            # 买入信号：短期均线上穿长期均线
            if self.crossover[0] == 1:  # 上穿
                signals['action'] = 'buy'
                signals['strength'] = self._calculate_signal_strength()
                signals['reason'] = f'MA金叉: SMA{self.params_dict["sma_period"]}上穿LMA{self.params_dict["lma_period"]}'
            
            # 卖出信号：短期均线下穿长期均线
            elif self.crossover[0] == -1:  # 下穿
                signals['action'] = 'sell'
                signals['strength'] = 1.0
                signals['reason'] = f'MA死叉: SMA{self.params_dict["sma_period"]}下穿LMA{self.params_dict["lma_period"]}'
            
            # 持仓监控
            elif self.position.size > 0:
                # 检查是否应该持有
                if sma > lma:
                    signals['action'] = 'hold'
                    signals['strength'] = 0.7
                    signals['reason'] = '趋势向上，继续持有'
                else:
                    signals['action'] = 'sell'
                    signals['strength'] = 0.8
                    signals['reason'] = '趋势转弱，平仓'
            
            # 空仓等待
            else:
                signals['action'] = 'hold'
                signals['strength'] = 0
                signals['reason'] = '等待信号'
        
        else:
            # 过滤条件不满足
            if self.position.size > 0:
                # 如果持仓但趋势变坏，考虑平仓
                if not trend_ok:
                    signals['action'] = 'sell'
                    signals['strength'] = 0.9
                    signals['reason'] = '趋势变坏，强制平仓'
                else:
                    signals['action'] = 'hold'
                    signals['strength'] = 0.5
                    signals['reason'] = '持仓中，过滤条件检查'
            else:
                signals['action'] = 'hold'
                signals['strength'] = 0
                signals['reason'] = '过滤条件不满足，等待'
        
        return signals
    
    def _calculate_signal_strength(self) -> float:
        """计算信号强度"""
        # 基于均线距离和角度计算信号强度
        ma_diff = self.ma_diff[0]
        ma_diff_pct = abs(ma_diff) / self.data.close[0]
        
        # 标准化到0-1范围
        strength = min(ma_diff_pct * 100, 1.0)
        
        # 考虑趋势强度
        if hasattr(self, 'trend') and self.trend[0]:
            strength *= 1.2  # 趋势向上时增强信号
        
        # 考虑成交量
        if hasattr(self, 'volume_ratio'):
            volume_strength = min(self.volume_ratio[0] / 2.0, 1.0)
            strength = (strength + volume_strength) / 2
        
        return min(max(strength, 0.1), 1.0)  # 限制在0.1-1.0之间
    
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
            'strategy_name': '移动平均线策略',
            'strategy_type': 'MA',
            'description': '基于双均线交叉的趋势跟踪策略',
            'parameters': self.params_dict,
            'indicators': ['SMA', 'LMA', 'ATR(可选)', 'Volume(可选)'],
            'signal_type': '趋势跟踪',
            'risk_level': '中等'
        }
        
        # 添加当前指标值
        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'sma': float(self.sma[0]) if hasattr(self, 'sma') else None,
                'lma': float(self.lma[0]) if hasattr(self, 'lma') else None,
                'ma_diff': float(self.ma_diff[0]) if hasattr(self, 'ma_diff') else None,
                'trend': bool(self.trend[0]) if hasattr(self, 'trend') else None
            }
        
        return info


# ========== 策略参数优化配置 ==========

class MAStrategyOptimizer:
    """MA策略优化器"""
    
    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """获取参数网格"""
        return {
            'sma_period': [5, 10, 15, 20, 25, 30],
            'lma_period': [30, 40, 50, 60, 70, 80, 90, 100, 120],
            'use_atr_stop': [True, False],
            'atr_multiplier': [1.5, 2.0, 2.5, 3.0],
            'trend_filter': [True, False]
        }
    
    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'sma_period': 20,
            'lma_period': 60,
            'use_atr_stop': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'trend_filter': True,
            'volume_filter': False,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试MA策略
    print("测试移动平均线策略...")
    
    # 创建策略实例
    params = {
        'sma_period': 10,
        'lma_period': 30,
        'use_atr_stop': True
    }
    
    strategy = MAStrategy(params)
    
    # 获取策略信息
    info = strategy.get_strategy_info()
    print(f"策略名称: {info['strategy_name']}")
    print(f"策略描述: {info['description']}")
    print(f"策略参数: {info['parameters']}")
    
    # 获取优化器配置
    optimizer = MAStrategyOptimizer()
    param_grid = optimizer.get_param_grid()
    print(f"\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    print("\n策略测试完成!")