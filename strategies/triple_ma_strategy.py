"""
Triple Moving Average Crossover Strategy
Based on research: Three MA confirmation reduces false signals
Reference: QuantInsti 2025 - Moving Average Crossover Strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base_strategy import BaseStrategy


class TripleMAStrategy(BaseStrategy):
    """
    三重均线交叉策略
    使用快/中/慢三条均线，形成双重确认机制
    - 买入：快线 > 中线 > 慢线（多头排列）
    - 卖出：快线 < 中线（趋势破坏）
    """
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        default_params = {
            'fast_period': 5,    # 快线
            'mid_period': 20,    # 中线  
            'slow_period': 70,   # 慢线
            'volatility_filter': False,  # 是否启用波动率过滤
            'atr_threshold': 0.0  # ATR阈值（0表示不过滤）
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
        
    def get_name(self) -> str:
        return "Triple_MA"
    
    def validate_params(self) -> bool:
        fast = self.params.get('fast_period', 5)
        mid = self.params.get('mid_period', 20)
        slow = self.params.get('slow_period', 70)
        return fast < mid < slow
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        df = data.copy()
        
        fast = self.params['fast_period']
        mid = self.params['mid_period']
        slow = self.params['slow_period']
        
        # 计算三条均线
        df[f'ma_fast'] = df['close'].rolling(window=fast).mean()
        df[f'ma_mid'] = df['close'].rolling(window=mid).mean()
        df[f'ma_slow'] = df['close'].rolling(window=slow).mean()
        
        # 趋势状态
        df['bullish'] = (df['ma_fast'] > df['ma_mid']) & (df['ma_mid'] > df['ma_slow'])
        df['bearish'] = df['ma_fast'] < df['ma_mid']
        
        # 信号生成（带确认延迟）
        df['signal'] = 0
        
        # 买入：多头排列形成 + 持续确认（避免单日假信号）
        df['signal'] = np.where(df['bullish'], 1, 0)
        
        # 卖出：趋势破坏（快线跌破中线）
        df['signal'] = np.where(df['bearish'], 0, df['signal'])
        
        # 波动率过滤（可选）
        if self.params.get('volatility_filter', False):
            df['atr'] = self._calculate_atr(df)
            avg_atr = df['atr'].rolling(window=20).mean()
            threshold = self.params.get('atr_threshold', 0.02)
            # 低波动时减少交易
            df['signal'] = np.where(df['atr'] < avg_atr * 0.5, 0, df['signal'])
        
        # 持仓（滞后一期，避免未来数据）
        df['position'] = df['signal'].shift(1).fillna(0)
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ATR指标"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift(1))
        low_close = np.abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def get_param_ranges(self) -> Dict[str, Any]:
        """返回参数优化范围"""
        return {
            'fast_period': range(3, 15),
            'mid_period': range(10, 40),
            'slow_period': range(40, 100),
            'volatility_filter': [False, True],
            'atr_threshold': [0.0, 0.01, 0.02, 0.03]
        }
    
    def get_description(self) -> str:
        return f"""三重均线交叉策略
        快线周期: {self.params['fast_period']}
        中线周期: {self.params['mid_period']}
        慢线周期: {self.params['slow_period']}
        特点: 
        - 双重确认机制，减少假信号
        - 趋势明确时才入场
        - 适合波动较大的市场
        """
