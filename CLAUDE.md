# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline (data fetch → backtest → optimize → analyze)
python main.py --mode full

# Run backtest only
python main.py --mode backtest --symbol 000001.SH --start-date 2020-01-01 --end-date 2024-01-01

# Run parameter optimization only
python main.py --mode optimize

# Run analysis on existing results
python main.py --mode analyze

# Syntax-check a modified file
python -m py_compile strategies/some_strategy.py

# Check all strategy files at once
python -c "
import ast, pathlib
for f in pathlib.Path('strategies').glob('*.py'):
    try: ast.parse(f.read_text()); print(f'{f.name}: OK')
    except SyntaxError as e: print(f'{f.name}: ERROR {e}')
"

# Verify StrategyFactory registration
python -c "from strategies.base_strategy import StrategyFactory; print(StrategyFactory.get_available_strategies())"

# Ad-hoc test scripts (no pytest setup)
python simple_test.py
python test_ma_strategy.py
```

## Architecture

ClawQuant is a Backtrader-based quantitative backtesting system with 5 layers:

### Data Flow
```
DataFetcher (Tushare/AKShare/yfinance)
  → DataProcessor (validate, clean, align)
    → BacktestEngine (runs backtrader Cerebro)
      → StrategyOptimizer (grid search over params)
        → BacktestAnalyzer (metrics, Sortino, Omega ratio)
          → WalkForwardOptimizer (OOS validation)
```

### Entry Point
`main.py` contains the `ClawQuant` orchestrator class. It wires together all layers based on `--mode`. The four modes (`full`, `backtest`, `optimize`, `analyze`) call into `BacktestEngine`, `StrategyOptimizer`, and `BacktestAnalyzer` in sequence.

### Strategy Layer (`strategies/`)
All strategies extend `BaseStrategy(bt.Strategy)` and must implement `generate_signals() -> Dict[str, Any]` returning `{'action': 'buy'|'sell'|'hold', 'strength': float, 'reason': str}`.

The standard `__init__` pattern for every strategy:
```python
def __init__(self, **kwargs):
    default_params = {'param': value, ...}
    default_params.update(kwargs)
    super().__init__(default_params)
    self._init_<name>_strategy()   # sets up bt.indicators here
```

`BaseStrategy._init_strategy()` sets up shared risk controls (`stop_loss_ratio`, `take_profit_ratio`, `max_position_size`), ATR-based position sizing (`use_atr_sizing`, `atr_risk_pct`), and calls `_validate_params()`.

**Available strategies** (registered in `StrategyFactory`): `MA`, `MACD`, `RSI`, `BOLL`, `MA_CROSS`, `TRIPLE_MA`, `DUAL_THRUST`, `KAMA`, `TURTLE`. `MA_CROSS` is the primary/best-performing strategy.

### StrategyFactory (`strategies/base_strategy.py`)
Registry with lazy imports. To add a new strategy:
1. Create `strategies/<name>_strategy.py` with `class XStrategy(BaseStrategy)`
2. Add to `STRATEGY_MAP`, `get_strategy_class()`, `get_available_strategies()`, and `get_default_params()` in `StrategyFactory`
3. Add params to `config/strategy_config.py`

### Backtest Layer (`backtests/`)
- `BacktestEngine` — wraps `bt.Cerebro`, feeds data, runs the strategy, returns a `results` dict
- `StrategyOptimizer` — grid search or random search over a param grid; calls `BacktestEngine` repeatedly
- `BacktestAnalyzer` — computes Sharpe, Sortino (true downside-deviation based), Calmar, Omega ratio, max drawdown; `_calculate_risk_metrics()` pulls `daily_returns` from `performance` dict for Omega
- `WalkForwardOptimizer` — rolling train/test windows; computes Walk-Forward Efficiency (WFE = OOS Sharpe / IS Sharpe; ≥0.70 excellent, ≥0.50 acceptable)

### Configuration (`config/`)
- `config/settings.py` — global singleton objects `TRADING`, `STRATEGY`, `BACKTEST`, `SYSTEM`; primary symbol is `000001.SH`, dates `2020-01-01` to `2024-01-01`, commission `0.03%`
- `config/strategy_config.py` — per-strategy `get_base_params()` and `get_param_grid()` used by the optimizer

### Data Layer (`utils/`)
- `DataFetcher` — tries Tushare first, falls back to AKShare/yfinance; caches to `data/cache/` for 24 hours (pickle)
- `DataProcessor` — validates OHLCV integrity, adds technical features; `_add_price_patterns()` uses TA-Lib candlestick patterns

### Outputs
- Logs: `logs/clawquant.log` (10 MB rotation, 30-day retention)
- Backtest results: `results/backtest_results/`
- Optimization results: `results/optimization_results/`
- Walk-forward results: `results/optimization_results/walk_forward_<strategy>_<timestamp>/` (CSV + JSON + TXT)
- Best strategy config: `results/final_configuration/best_strategy_<timestamp>.json`

## Key Conventions

**Backtrader indexing**: `[0]` = current bar (already closed, no lookahead), `[-1]` = previous bar. All strategies use `[0]` for current values; Turtle uses `[-1]` on channel indicators intentionally to avoid lookahead.

**Custom `bt.Indicator` subclasses**: When a `bt.Indicator` receives `data.close` as input, `self.data` IS the close line (not the feed). Use `self.data[0]` for current value and `self.data.get(size=n)` for lookback — not `self.data.close.get(...)`. Seed with `nextstart()` (not `onceover()`).

**ATR position sizing** (opt-in): Pass `use_atr_sizing=True, atr_risk_pct=0.01` in params. Sizing formula: `shares = (account * atr_risk_pct * signal_strength) / ATR`, rounded to nearest 100 (A-share lot size).

**Bollinger divide-by-zero**: Never compute `(close - bb_bot) / (bb_top - bb_bot)` as a `bt.Indicator` expression. Use runtime method `_safe_price_position()` with `abs(bb_range) < 1e-10` guard.
