"""
KAMA (Kaufman Adaptive Moving Average) Strategy
Based on Perry Kaufman's adaptive moving average algorithm.

KAMA adapts its speed to market noise:
- In trending markets: fast response (low noise, high ER)
- In choppy markets: slow response (high noise, low ER)

Algorithm:
1. Efficiency Ratio (ER) = |close - close[n]| / sum(|close[i] - close[i-1]| for i in 1..n)
2. Smoothing Constant (SC) = (ER * (fast_sc - slow_sc) + slow_sc)^2
   - fast_sc = 2 / (fast + 1), fast=2 (typical)
   - slow_sc = 2 / (slow + 1), slow=30 (typical)
3. KAMA[t] = KAMA[t-1] + SC * (close[t] - KAMA[t-1])
"""

import backtrader as bt
import numpy as np
from typing import Dict, Any
from loguru import logger

from strategies.base_strategy import BaseStrategy


class KAMAIndicator(bt.Indicator):
    """
    Kaufman Adaptive Moving Average custom backtrader indicator.

    Lines:
        kama: The adaptive moving average line.

    Params:
        period (int): Lookback period for Efficiency Ratio calculation. Default: 10.
        fast (int): Fast EMA period (high ER / trending). Default: 2.
        slow (int): Slow EMA period (low ER / sideways). Default: 30.

    Example::

        kama = KAMAIndicator(data.close, period=10, fast=2, slow=30)
        current_kama = kama.kama[0]
    """

    lines = ('kama',)
    params = (
        ('period', 10),
        ('fast', 2),
        ('slow', 30),
    )

    def __init__(self):
        # Require period+1 bars before producing output.
        # +1 because we need period bars of price-changes (|p[i]-p[i-1]|),
        # which requires period+1 raw prices.
        self.addminperiod(self.p.period + 1)

        # Pre-compute smoothing-constant bounds (computed once at init time)
        self._fast_sc = 2.0 / (self.p.fast + 1.0)
        self._slow_sc = 2.0 / (self.p.slow + 1.0)

        # Running KAMA state; seeded on the very first valid bar in nextstart()
        self._kama_prev = float('nan')

    def nextstart(self):
        """
        Called exactly once on the first bar where minperiod is satisfied.
        Seeds KAMA to the current close price so the very first output bar
        carries a meaningful value rather than NaN.

        Inside a bt.Indicator that was passed data.close, self.data IS the
        close line - so self.data[0] gives the current bar's close price.
        """
        self._kama_prev = self.data[0]
        self.lines.kama[0] = self._kama_prev

    def next(self):
        """
        Compute KAMA for the current bar.

        Inside a bt.Indicator created with ``KAMAIndicator(data.close, ...)``,
        ``self.data`` IS the close line.  Therefore:

        - ``self.data[0]``              -> close price of the current bar
        - ``self.data[-period]``        -> close price period bars ago
        - ``self.data.get(size=n)``     -> list of the last n close prices,
                                           ordered oldest-first (index 0 is
                                           oldest, index -1 is most recent)
        """
        period = self.p.period

        # get(size=period+1) returns a list:
        #   [close_{t-period}, ..., close_{t-1}, close_{t}]
        # i.e. oldest price first, newest price last.
        closes = self.data.get(size=period + 1)

        if len(closes) < period + 1:
            # Guard: carry forward the previous KAMA value
            self.lines.kama[0] = self._kama_prev
            return

        close_now = closes[-1]    # close[0]      - current bar
        close_n_ago = closes[0]   # close[-period] - period bars ago

        # --- Efficiency Ratio (ER) ---
        # Net directional move over the period
        direction = abs(close_now - close_n_ago)

        # Total path length (sum of absolute single-bar moves)
        volatility = sum(abs(closes[i] - closes[i - 1]) for i in range(1, len(closes)))

        er = 0.0 if volatility == 0.0 else direction / volatility
        er = max(0.0, min(1.0, er))   # clamp to [0, 1] for numerical safety

        # --- Smoothing Constant (SC) ---
        sc = (er * (self._fast_sc - self._slow_sc) + self._slow_sc) ** 2

        # --- KAMA update ---
        # Safety seed in case nextstart was somehow skipped
        if np.isnan(self._kama_prev):
            self._kama_prev = close_now

        kama_now = self._kama_prev + sc * (close_now - self._kama_prev)

        self.lines.kama[0] = kama_now
        self._kama_prev = kama_now


class KAMAStrategy(BaseStrategy):
    """
    KAMA-based adaptive trend-following strategy.

    Entry logic:
        Buy  when close crosses above KAMA (close[0] > kama[0] and close[-1] <= kama[-1])
             AND trend filter passes (close > long-period SMA, if enabled).
        Sell when close crosses below KAMA OR ATR stop-loss is triggered.
        Hold otherwise, with ATR stop monitoring active.

    Default parameters::

        period=10, fast=2, slow=30
        use_trend_filter=True, trend_period=200
        use_atr_stop=True, atr_period=14, atr_multiplier=2.0

    Example::

        strategy = KAMAStrategy(period=10, fast=2, slow=30, use_trend_filter=True)
    """

    def __init__(self, **kwargs):
        """
        Initialise KAMA strategy.

        Args:
            **kwargs: Override any default parameter by name.
        """
        default_params: Dict[str, Any] = {
            'period': 10,              # KAMA efficiency-ratio lookback
            'fast': 2,                 # Fast EMA constant (high ER)
            'slow': 30,                # Slow EMA constant (low ER)
            'use_trend_filter': True,  # Only buy when price > trend SMA
            'trend_period': 200,       # Long-period SMA for trend filter
            'use_atr_stop': True,      # ATR-based trailing stop
            'atr_period': 14,          # ATR lookback
            'atr_multiplier': 2.0,     # ATR multiplier for stop distance
        }

        default_params.update(kwargs)
        super().__init__(default_params)

        self._init_kama_strategy()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_kama_strategy(self):
        """Initialise all KAMA-specific indicators."""
        params = self.params_dict

        # Primary KAMA indicator
        self.kama = KAMAIndicator(
            self.data.close,
            period=params['period'],
            fast=params['fast'],
            slow=params['slow'],
        )

        # Trend filter: long-period SMA (optional)
        if params['use_trend_filter']:
            self.trend_sma = bt.indicators.SimpleMovingAverage(
                self.data.close,
                period=params['trend_period'],
            )
        else:
            self.trend_sma = None

        # ATR for dynamic stop-loss (optional)
        if params['use_atr_stop']:
            self.kama_atr = bt.indicators.ATR(
                self.data,
                period=params['atr_period'],
            )
        else:
            self.kama_atr = None

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(self) -> Dict[str, Any]:
        """
        Generate a trading signal for the current bar.

        Returns:
            Dict with keys:
                'action'   - 'buy', 'sell', or 'hold'
                'strength' - float in [0.0, 1.0]
                'reason'   - human-readable description
        """
        params = self.params_dict

        # Guard: ensure enough bars have elapsed
        min_period = max(
            params['period'] + 1,
            params['trend_period'] if params['use_trend_filter'] else 0,
            params['atr_period'] if params['use_atr_stop'] else 0,
        )
        if len(self.data) < min_period:
            return {'action': 'hold', 'strength': 0.0, 'reason': '数据不足'}

        # Guard: KAMA must have produced at least two values
        if len(self.kama) < 2:
            return {'action': 'hold', 'strength': 0.0, 'reason': 'KAMA指标未就绪'}

        close_now = self.data.close[0]
        close_prev = self.data.close[-1]
        kama_now = self.kama.kama[0]
        kama_prev = self.kama.kama[-1]

        # ------------------------------------------------------------------
        # Trend filter
        # ------------------------------------------------------------------
        trend_ok = True
        if params['use_trend_filter'] and self.trend_sma is not None:
            if len(self.trend_sma) > 0:
                trend_ok = close_now > self.trend_sma[0]

        # ------------------------------------------------------------------
        # Cross detection
        # ------------------------------------------------------------------
        crossed_above = (close_now > kama_now) and (close_prev <= kama_prev)
        crossed_below = (close_now < kama_now) and (close_prev >= kama_prev)

        # ------------------------------------------------------------------
        # ATR stop-loss check (for existing position)
        # ------------------------------------------------------------------
        if self.position.size > 0 and params['use_atr_stop'] and self.kama_atr is not None:
            if len(self.kama_atr) > 0:
                atr_value = self.kama_atr[0]
                stop_price = self.position.price - params['atr_multiplier'] * atr_value
                if close_now < stop_price:
                    return {
                        'action': 'sell',
                        'strength': 1.0,
                        'reason': (
                            f'ATR止损触发: 价格{close_now:.2f} < '
                            f'止损价{stop_price:.2f} '
                            f'(入场价{self.position.price:.2f} - '
                            f'{params["atr_multiplier"]}x ATR{atr_value:.2f})'
                        ),
                    }

        # ------------------------------------------------------------------
        # Entry: close crosses above KAMA with trend confirmation
        # ------------------------------------------------------------------
        if crossed_above and self.position.size == 0:
            if trend_ok:
                strength = self._calculate_kama_signal_strength(
                    close_now, kama_now
                )
                return {
                    'action': 'buy',
                    'strength': strength,
                    'reason': (
                        f'价格上穿KAMA: close({close_now:.2f}) > '
                        f'KAMA({kama_now:.2f})'
                        + (' [趋势确认]' if params['use_trend_filter'] else '')
                    ),
                }
            else:
                return {
                    'action': 'hold',
                    'strength': 0.0,
                    'reason': (
                        f'价格上穿KAMA但趋势过滤未通过: '
                        f'close({close_now:.2f}) < '
                        f'趋势均线({self.trend_sma[0]:.2f})'
                    ),
                }

        # ------------------------------------------------------------------
        # Exit: close crosses below KAMA
        # ------------------------------------------------------------------
        if crossed_below and self.position.size > 0:
            return {
                'action': 'sell',
                'strength': 0.9,
                'reason': (
                    f'价格下穿KAMA: close({close_now:.2f}) < '
                    f'KAMA({kama_now:.2f})'
                ),
            }

        # ------------------------------------------------------------------
        # Hold logic: monitor open position
        # ------------------------------------------------------------------
        if self.position.size > 0:
            return self._monitor_kama_position(close_now, kama_now)

        # ------------------------------------------------------------------
        # Default: wait for entry
        # ------------------------------------------------------------------
        return {
            'action': 'hold',
            'strength': 0.0,
            'reason': '等待价格上穿KAMA',
        }

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _calculate_kama_signal_strength(
        self, close: float, kama: float
    ) -> float:
        """
        Compute buy-signal strength from the distance between close and KAMA.

        Args:
            close: Current closing price.
            kama:  Current KAMA value.

        Returns:
            Signal strength in [0.3, 1.0].
        """
        if kama == 0.0:
            return 0.5

        distance_pct = (close - kama) / kama

        # Normalise: every 1 % gap = 0.1 strength unit
        strength = min(distance_pct * 10.0, 1.0)

        # Trend alignment bonus
        if (
            self.params_dict['use_trend_filter']
            and self.trend_sma is not None
            and len(self.trend_sma) > 0
            and close > self.trend_sma[0]
        ):
            strength = min(strength * 1.2, 1.0)

        return max(round(strength, 4), 0.3)

    def _monitor_kama_position(
        self, close: float, kama: float
    ) -> Dict[str, Any]:
        """
        Monitor an open long position and decide whether to hold.

        Args:
            close: Current closing price.
            kama:  Current KAMA value.

        Returns:
            Signal dict.
        """
        if close > kama:
            gap_pct = (close - kama) / kama if kama != 0.0 else 0.0
            hold_strength = min(0.5 + gap_pct * 5.0, 0.9)
            return {
                'action': 'hold',
                'strength': hold_strength,
                'reason': (
                    f'持仓中: close({close:.2f}) 在KAMA({kama:.2f})上方, '
                    f'距离{gap_pct:.2%}'
                ),
            }
        # close <= kama but has not crossed below yet (equal)
        return {
            'action': 'hold',
            'strength': 0.4,
            'reason': (
                f'持仓观察: close({close:.2f}) 接近KAMA({kama:.2f})'
            ),
        }

    # ------------------------------------------------------------------
    # Risk management override
    # ------------------------------------------------------------------

    def _set_stop_loss_take_profit(self, entry_price: float):
        """
        Override base-class method to use ATR-based stop-loss.

        When use_atr_stop is True, the stop distance is
        atr_multiplier * ATR and take-profit is 2x that distance
        (1:2 risk/reward ratio).

        Args:
            entry_price: Price at which the position was opened.
        """
        params = self.params_dict
        if params['use_atr_stop'] and self.kama_atr is not None and len(self.kama_atr) > 0:
            atr_value = self.kama_atr[0]
            atr_stop = params['atr_multiplier'] * atr_value
            self.stop_loss_price = entry_price - atr_stop
            self.take_profit_price = entry_price + 2.0 * atr_stop  # 1:2 R:R
        else:
            super()._set_stop_loss_take_profit(entry_price)

    # ------------------------------------------------------------------
    # Strategy metadata
    # ------------------------------------------------------------------

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Return a summary dict of this strategy's metadata and live values.

        Returns:
            Dict containing strategy name, type, description, parameters,
            indicator names, and (if data is available) current indicator values.
        """
        info: Dict[str, Any] = {
            'strategy_name': 'KAMA自适应移动平均策略',
            'strategy_type': 'KAMA',
            'description': (
                'Kaufman自适应移动平均线策略 - '
                '在趋势市场中快速响应，在震荡市场中缓慢响应'
            ),
            'parameters': self.params_dict,
            'indicators': [
                'KAMA (Kaufman Adaptive Moving Average)',
                '趋势SMA (可选)',
                'ATR止损 (可选)',
            ],
            'signal_type': '趋势跟踪 + 自适应',
            'risk_level': '中等',
        }

        if len(self.data) > 0 and len(self.kama) > 0:
            info['current_values'] = {
                'close': float(self.data.close[0]),
                'kama': float(self.kama.kama[0]),
                'trend_sma': (
                    float(self.trend_sma[0])
                    if self.trend_sma is not None and len(self.trend_sma) > 0
                    else None
                ),
                'atr': (
                    float(self.kama_atr[0])
                    if self.kama_atr is not None and len(self.kama_atr) > 0
                    else None
                ),
                'position_size': int(self.position.size),
                'entry_price': float(self.entry_price),
            }

        return info


# ==========================================================================
# Strategy parameter optimisation configuration
# ==========================================================================


class KAMAStrategyOptimizer:
    """Parameter grid and defaults for KAMAStrategy optimisation."""

    @staticmethod
    def get_param_grid() -> Dict[str, list]:
        """
        Return a grid of parameters to sweep during optimisation.

        Returns:
            Dict mapping parameter names to lists of candidate values.
        """
        return {
            'period': [5, 8, 10, 12, 15, 20],
            'fast': [2, 3],
            'slow': [20, 25, 30],
            'use_trend_filter': [True, False],
            'trend_period': [100, 150, 200],
            'use_atr_stop': [True, False],
            'atr_multiplier': [1.5, 2.0, 2.5, 3.0],
        }

    @staticmethod
    def get_default_params() -> Dict[str, Any]:
        """
        Return the recommended default parameters for live trading.

        Returns:
            Dict of parameter name -> value.
        """
        return {
            'period': 10,
            'fast': 2,
            'slow': 30,
            'use_trend_filter': True,
            'trend_period': 200,
            'use_atr_stop': True,
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'stop_loss_ratio': 0.05,
            'take_profit_ratio': 0.10,
            'max_position_size': 0.8,
        }


# ==========================================================================
# Smoke-test entry point
# ==========================================================================

if __name__ == "__main__":
    print("KAMA策略模块加载成功")
    print("KAMAIndicator: 自适应移动平均线指标")
    print("KAMAStrategy: 基于KAMA的趋势跟踪策略")

    optimizer = KAMAStrategyOptimizer()
    param_grid = optimizer.get_param_grid()
    print("\n参数优化网格:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")

    default = optimizer.get_default_params()
    print("\n默认参数:")
    for k, v in default.items():
        print(f"  {k}: {v}")
