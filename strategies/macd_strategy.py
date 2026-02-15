"""
MACD策略
基于MACD指标的趋势和动量策略
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD策略"""
    
    def __init__(self, **kwargs):
        """
        初始化MACD策略
        
        Args:
            params: 策略参数
        """
        # 默认参数
        default_params = {
            'fast_period': 12,      # 快速EMA周期
            'slow_period': 26,      # 慢速EMA周期
            'signal_period': 9,     # 信号线周期
            'use_divergence': False, # 是否使用背离信号
            'use_histogram': True,  # 是否使用柱状图信号
            'use_zero_cross': True, # 是否使用零轴交叉
            'smooth_type': 'ema',   # 平滑类型: 'ema' 或 'sma'
        }
        
        # 合并参数
        default_params.update(kwargs)
        
        super().__init__(default_params)
        
        # 策略特定初始化
        self._init_macd_strategy()
    
    def _init_macd_strategy(self):
        """初始化MACD策略特定指标"""
        params = self.params_dict
        
        # MACD指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=params['fast_period'],
            period_me2=params['slow_period'],
            period_signal=params['signal_period']
        )
        
        # MACD线
        self.macd_line = self.macd.macd
        
        # 信号线
        self.signal_line = self.macd.signal
        
        # 柱状图
        self.macd_hist = self.macd.macd - self.macd.signal
        
        # 零轴
        self.zero_line = bt.indicators.Constant(0, plot=False)
        
        # 交叉信号
        self.macd_cross = bt.indicators.CrossOver(self.macd_line, self.signal_line)
        self.zero_cross = bt.indicators.CrossOver(self.macd_line, self.zero_line)
        
        # 趋势过滤（可选）
        self.trend_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=50
        )
        self.trend = self.data.close > self.trend_sma
        
        # 记录历史MACD值用于背离检测
        self.macd_history = []
        self.price_history = []
    
    def generate_signals(self) -> Dict[str, Any]:
        """
        生成交易信号
        
        策略逻辑：
        1. MACD线上穿信号线 -> 买入信号
        2. MACD线下穿信号线 -> 卖出信号
        3. MACD线上穿零轴 -> 加强买入信号
        4. MACD线下穿零轴 -> 加强卖出信号
        5. 柱状图变化 -> 动量信号
        """
        signals = {}
        
        # 检查数据是否足够
        min_period = max(self.params_dict['slow_period'], 50)
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}
        
        # 获取当前值
        macd_val = self.macd_line[0]
        signal_val = self.signal_line[0]
        hist_val = self.macd_hist[0]
        
        # 更新历史记录（用于背离检测）
        self._update_history(macd_val, self.data.close[0])
        
        # 趋势过滤
        trend_ok = self.trend[0]
        
        # 生成信号
        if trend_ok:
            # 主要信号：MACD交叉
            if self.macd_cross[0] == 1:  # MACD上穿信号线
                signals['action'] = 'buy'
                signals['strength'] = self._calculate_cross_strength(macd_val, signal_val)
                signals['reason'] = f'MACD金叉: {self.params_dict["fast_period"]}/{self.params_dict["slow_period"]}/{self.params_dict["signal_period"]}'

                # 如果同时上穿零轴，增强信号
                if self.zero_cross[0] == 1:
                    signals['strength'] = min(signals['strength'] * 1.5, 1.0)
                    signals['reason'] += ' + 零轴上穿'

            elif self.macd_cross[0] == -1:  # MACD下穿信号线
                signals['action'] = 'sell'
                signals['strength'] = 1.0
                signals['reason'] = f'MACD死叉: {self.params_dict["fast_period"]}/{self.params_dict["slow_period"]}/{self.params_dict["signal_period"]}'

                # 如果同时下穿零轴，增强信号
                if self.zero_cross[0] == -1:
                    signals['strength'] = 1.0
                    signals['reason'] += ' + 零轴下穿'

            else:
                # 无交叉信号时，组合检查柱状图和背离信号
                hist_signals = {}
                div_signals = {}

                if self.params_dict['use_histogram']:
                    hist_signals = self._generate_histogram_signals(hist_val)

                if self.params_dict['use_divergence']:
                    div_signals = self._generate_divergence_signals()

                # 优先使用背离信号（更强），其次柱状图信号
                if div_signals.get('action') in ('buy', 'sell'):
                    signals.update(div_signals)
                    # 如果柱状图信号方向一致，增强强度
                    if hist_signals.get('action') == div_signals['action']:
                        signals['strength'] = min(signals['strength'] * 1.2, 1.0)
                        signals['reason'] += ' + 柱状图确认'
                elif hist_signals.get('action') in ('buy', 'sell'):
                    signals.update(hist_signals)
                elif self.position.size > 0:
                    signals.update(self._monitor_position(macd_val, signal_val))
                else:
                    signals['action'] = 'hold'
                    signals['strength'] = 0
                    signals['reason'] = '等待MACD信号'
        
        else:
            # 趋势向下，只考虑卖出或观望
            if self.position.size > 0:
                signals['action'] = 'sell'
                signals['strength'] = 0.8
                signals['reason'] = '趋势向下，保护利润'
            else:
                signals['action'] = 'hold'
                signals['strength'] = 0
                signals['reason'] = '趋势向下，观望'
        
        return signals
    
    def _update_history(self, macd_val: float, price: float):
        """更新历史记录"""
        self.macd_history.append(macd_val)
        self.price_history.append(price)
        
        # 只保留最近100个值
        if len(self.macd_history) > 100:
            self.macd_history.pop(0)
            self.price_history.pop(0)
    
    def _calculate_cross_strength(self, macd_val: float, signal_val: float) -> float:
        """计算交叉信号强度"""
        # 基于MACD和信号线的距离
        distance = abs(macd_val - signal_val)
        
        # 标准化（假设典型MACD值范围）
        typical_range = 0.02  # 调整这个值基于实际数据
        strength = min(distance / typical_range, 1.0)
        
        # 考虑柱状图变化
        if hasattr(self, 'macd_hist'):
            hist_change = abs(self.macd_hist[0] - self.macd_hist[-1])
            hist_strength = min(hist_change / 0.01, 1.0)
            strength = (strength + hist_strength) / 2
        
        return max(strength, 0.3)  # 最小强度0.3
    
    def _generate_histogram_signals(self, hist_val: float) -> Dict[str, Any]:
        """生成柱状图信号"""
        signals = {}
        
        if len(self.macd_hist) < 3:
            return signals
        
        # 柱状图变化方向
        hist_prev = self.macd_hist[-1]
        hist_prev2 = self.macd_hist[-2]
        
        # 柱状图由负转正（动量转强）
        if hist_prev < 0 and hist_val > 0:
            if self.position.size == 0:
                signals['action'] = 'buy'
                signals['strength'] = 0.6
                signals['reason'] = 'MACD柱状图转正'
        
        # 柱状图由正转负（动量转弱）
        elif hist_prev > 0 and hist_val < 0:
            if self.position.size > 0:
                signals['action'] = 'sell'
                signals['strength'] = 0.7
                signals['reason'] = 'MACD柱状图转负'
        
        # 柱状图加速（动量增强）
        elif abs(hist_val) > abs(hist_prev) > abs(hist_prev2):
            if hist_val > 0 and self.position.size > 0:
                signals['action'] = 'hold'
                signals['strength'] = 0.8
                signals['reason'] = 'MACD柱状图加速向上'
            elif hist_val < 0 and self.position.size == 0:
                signals['action'] = 'hold'
                signals['strength'] = 0
                signals['reason'] = 'MACD柱状图加速向下，观望'
        
        return signals
    
    def _generate_divergence_signals(self) -> Dict[str, Any]:
        """生成背离信号"""
        signals = {}
        
        if len(self.macd_history) < 20 or len(self.price_history) < 20:
            return signals
        
        # 检测顶背离：价格创新高，MACD未创新高
        recent_prices = self.price_history[-10:]
        recent_macd = self.macd_history[-10:]
        
        price_max_idx = np.argmax(recent_prices)
        macd_max_idx = np.argmax(recent_macd)
        
        if price_max_idx == len(recent_prices) - 1:  # 价格刚创新高
            if macd_max_idx != len(recent_macd) - 1:  # MACD未创新高
                if self.position.size > 0:
                    signals['action'] = 'sell'
                    signals['strength'] = 0.9
                    signals['reason'] = '顶背离，价格新高但MACD未新高'
        
        # 检测底背离：价格创新低，MACD未创新低
        price_min_idx = np.argmin(recent_prices)
        macd_min_idx = np.argmin(recent_macd)
        
        if price_min_idx == len(recent_prices) - 1:  # 价格刚创新低
            if macd_min_idx != len(recent_macd) - 1:  # MACD未创新低
                if self.position.size == 0:
                    signals['action'] = 'buy'
                    signals['strength'] = 0.9
                    signals['reason'] = '底背离，价格新低但MACD未新低'
        
        return signals
    
    def _monitor_position(self, macd_val: float, signal_val: float) -> Dict[str, Any]:
        """监控持仓"""
        signals = {}
        
        # 检查MACD是否仍然在信号线上方
        if macd_val > signal_val:
            # 计算持仓强度
            strength = self._calculate_cross_strength(macd_val, signal_val)
            signals['action'] = 'hold'
            signals['strength'] = strength
            signals['reason'] = 'MACD仍在信号线上方，继续持有'
        else:
            # MACD跌破信号线，考虑平仓
            signals['action'] = 'sell'
            signals['strength'] = 0.8
            signals['reason'] = 'MACD跌破信号线，平仓'
        
        return signals
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        info = {
            'strategy_name': 'MACD策略',
            'strategy_type': 'MACD',
            'description': '基于MACD指标的趋势和动量策略',
            'parameters': self.params_dict,
            'indicators': ['MACD线', '信号线', '柱状图', '零轴'],
            'signal_type': '趋势+动量',
            'risk_level': '中等'
        }
        
        # 添加当前指标值
        if len(self.data) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'macd_line': float(self.macd_line[0]) if hasattr(self, 'macd_line') else None,
                'signal_line': float(self.signal_line[0]) if hasattr(self, 'signal_line') else None,
                'macd_hist': float(self.macd_hist[0]) if hasattr(self, 'macd_hist') else None,
                'trend': bool(self.trend[0]) if hasattr(self, 'trend') else None
            }
        
        return info


# ========== 策略参数优化配置 ==========

class MACDStrategyOptimizer:
    """MACD策略优化器"""
    
    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """获取参数网格"""
        return {
            'fast_period': [8, 10, 12, 14, 16],
            'slow_period': [21, 24, 26, 28, 30],
            'signal_period': [7, 8, 9, 10, 11, 12],
            'use_divergence': [True, False],
            'use_histogram': [True, False],
            'use_zero_cross': [True, False]
        }
    
    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """获取默认参数"""
        return {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'use_divergence': False,
            'use_histogram': True,
            'use_zero_cross': True,
            'smooth_type': 'ema',
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8
        }


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试MACD策略
    print("测试MACD策略...")
    
    # 创建策略实例
    params = {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
        'use_histogram': True
    }
    
    strategy = MACDStrategy(params)
    
    # 获取策略信息
    info = strategy.get_strategy_info()
    print(f"策略名称: {info['strategy_name']}")
    print(f"策略描述: {info['description']}")
    print(f"策略参数: {info['parameters']}")
    
    # 获取优化器配置
    optimizer = MACDStrategyOptimizer()
    param_grid = optimizer.get_param_grid()
    print(f"\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    
    print("\n策略测试完成!")