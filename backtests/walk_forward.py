"""
Walk-Forward Optimization Module

Implements rolling-window walk-forward analysis to assess strategy
robustness and prevent in-sample overfitting.

The core idea is simple: if a strategy is genuinely predictive,
parameters optimized on one period should continue to perform on an
unseen out-of-sample period.  The "walk-forward efficiency" ratio
(OOS Sharpe / IS Sharpe) is the primary diagnostic: values above 0.5
suggest the strategy generalises reasonably well.

Typical usage
-------------
>>> from backtests.walk_forward import WalkForwardOptimizer
>>> wfo = WalkForwardOptimizer()
>>> result = wfo.run_walk_forward(
...     strategy_type="MA",
...     param_grid={"sma_period": [5, 10, 20], "lma_period": [20, 30, 60]},
...     symbol="000001.SH",
...     start_date="2015-01-01",
...     end_date="2024-01-01",
...     train_months=12,
...     test_months=3,
...     step_months=3,
... )
>>> print(wfo.get_summary())
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from loguru import logger

from backtests.backtest_engine import BacktestEngine
from backtests.optimizer import StrategyOptimizer
from config.settings import OPTIMIZATION_RESULTS_DIR


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert an arbitrary value to float, returning *default* on failure."""
    try:
        if value is None:
            return default
        f = float(value)
        return f if np.isfinite(f) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class WalkForwardOptimizer:
    """
    Rolling-window walk-forward optimisation.

    Parameters
    ----------
    backtest_engine : BacktestEngine, optional
        Shared engine instance.  A new one is created if not supplied.
    strategy_optimizer : StrategyOptimizer, optional
        Shared optimizer instance.  A new one is created if not supplied.
    """

    def __init__(
        self,
        backtest_engine: Optional[BacktestEngine] = None,
        strategy_optimizer: Optional[StrategyOptimizer] = None,
    ) -> None:
        self.backtest_engine: BacktestEngine = backtest_engine or BacktestEngine()
        self.strategy_optimizer: StrategyOptimizer = (
            strategy_optimizer or StrategyOptimizer(self.backtest_engine)
        )

        # Populated after run_walk_forward completes
        self._last_result: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_walk_forward(
        self,
        strategy_type: str,
        param_grid: Dict[str, List],
        symbol: str,
        start_date: str,
        end_date: str,
        train_months: int = 12,
        test_months: int = 3,
        step_months: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute a rolling walk-forward analysis.

        For every rolling window the optimizer finds the best parameter
        combination on the *training* sub-period (in-sample / IS), then
        evaluates those parameters on the immediately following *test*
        sub-period (out-of-sample / OOS).

        Parameters
        ----------
        strategy_type : str
            Registered strategy identifier (e.g. ``"MA"``, ``"MACD"``).
        param_grid : Dict[str, List]
            Parameter search space passed verbatim to
            :meth:`StrategyOptimizer.grid_search`.
        symbol : str
            Market symbol, e.g. ``"000001.SH"``.
        start_date : str
            Overall analysis start date, ``"YYYY-MM-DD"``.
        end_date : str
            Overall analysis end date, ``"YYYY-MM-DD"``.
        train_months : int
            Length of each in-sample training window in calendar months.
        test_months : int
            Length of each out-of-sample test window in calendar months.
        step_months : int
            Number of months to advance the window at each step.  Setting
            ``step_months == test_months`` gives non-overlapping OOS periods.

        Returns
        -------
        Dict[str, Any]
            Keys:

            * ``windows``             – per-window detail (list of dicts)
            * ``oos_aggregated``      – aggregated OOS statistics
            * ``walk_forward_efficiency`` – OOS Sharpe / IS Sharpe ratio
            * ``strategy_type``       – echoed back
            * ``param_grid``          – echoed back
            * ``symbol``              – echoed back
            * ``date_range``          – ``(start_date, end_date)``
            * ``config``              – window sizing used
            * ``result_dir``          – directory where artefacts are saved
            * ``timestamp``           – ISO timestamp
        """
        logger.info(
            f"Starting walk-forward optimisation | strategy={strategy_type} "
            f"symbol={symbol} period={start_date}~{end_date} "
            f"train={train_months}m test={test_months}m step={step_months}m"
        )

        windows = self._generate_windows(
            start_date, end_date, train_months, test_months, step_months
        )

        if not windows:
            msg = (
                f"No valid windows generated for "
                f"{start_date}~{end_date} with "
                f"train={train_months}m + test={test_months}m"
            )
            logger.error(msg)
            raise ValueError(msg)

        logger.info(f"Generated {len(windows)} walk-forward windows")

        window_results: List[Dict[str, Any]] = []
        oos_results: List[Dict[str, Any]] = []

        for idx, window in enumerate(windows, start=1):
            logger.info(
                f"Window {idx}/{len(windows)} | "
                f"train={window['train_start']}~{window['train_end']} "
                f"test={window['test_start']}~{window['test_end']}"
            )

            window_result = self._process_window(
                idx=idx,
                window=window,
                strategy_type=strategy_type,
                param_grid=param_grid,
                symbol=symbol,
            )
            window_results.append(window_result)

            if window_result.get("oos_performance"):
                oos_results.append(window_result["oos_performance"])

        # Aggregate OOS results
        oos_aggregated = self._aggregate_oos_results(oos_results)

        # Walk-forward efficiency = OOS Sharpe / IS Sharpe
        avg_is_sharpe = np.mean(
            [
                _safe_float(w.get("is_performance", {}).get("sharpe_ratio"))
                for w in window_results
                if w.get("is_performance")
            ]
        ) if window_results else 0.0

        avg_oos_sharpe = _safe_float(oos_aggregated.get("avg_sharpe_ratio"))
        wfe = (
            avg_oos_sharpe / avg_is_sharpe
            if avg_is_sharpe and avg_is_sharpe != 0
            else None
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = self._save_results(
            strategy_type=strategy_type,
            window_results=window_results,
            oos_aggregated=oos_aggregated,
            wfe=wfe,
            timestamp=timestamp,
        )

        result = {
            "windows": window_results,
            "oos_aggregated": oos_aggregated,
            "walk_forward_efficiency": wfe,
            "strategy_type": strategy_type,
            "param_grid": param_grid,
            "symbol": symbol,
            "date_range": (start_date, end_date),
            "config": {
                "train_months": train_months,
                "test_months": test_months,
                "step_months": step_months,
            },
            "result_dir": result_dir,
            "timestamp": timestamp,
        }

        self._last_result = result

        logger.info(
            f"Walk-forward complete | windows={len(window_results)} "
            f"OOS_sharpe={avg_oos_sharpe:.4f} "
            f"IS_sharpe={avg_is_sharpe:.4f} "
            f"WFE={wfe:.4f if wfe is not None else 'N/A'}"
        )

        return result

    # ------------------------------------------------------------------
    # Window generation
    # ------------------------------------------------------------------

    def _generate_windows(
        self,
        start_date: str,
        end_date: str,
        train_months: int,
        test_months: int,
        step_months: int,
    ) -> List[Dict[str, str]]:
        """
        Build the list of (train_start, train_end, test_start, test_end) windows.

        Parameters
        ----------
        start_date, end_date : str
            Overall date range in ``"YYYY-MM-DD"`` format.
        train_months, test_months, step_months : int
            Window sizing.

        Returns
        -------
        List[Dict[str, str]]
            Each element has keys
            ``train_start``, ``train_end``, ``test_start``, ``test_end``.
        """
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
        dt_step = relativedelta(months=step_months)
        dt_train = relativedelta(months=train_months)
        dt_test = relativedelta(months=test_months)

        windows: List[Dict[str, str]] = []
        train_start = dt_start

        while True:
            train_end = train_start + dt_train
            test_start = train_end
            test_end = test_start + dt_test

            # Stop once the test window exceeds the overall end
            if test_end > dt_end:
                break

            windows.append(
                {
                    "train_start": train_start.strftime("%Y-%m-%d"),
                    "train_end": train_end.strftime("%Y-%m-%d"),
                    "test_start": test_start.strftime("%Y-%m-%d"),
                    "test_end": test_end.strftime("%Y-%m-%d"),
                }
            )

            train_start = train_start + dt_step

        return windows

    # ------------------------------------------------------------------
    # Window processing
    # ------------------------------------------------------------------

    def _process_window(
        self,
        idx: int,
        window: Dict[str, str],
        strategy_type: str,
        param_grid: Dict[str, List],
        symbol: str,
    ) -> Dict[str, Any]:
        """
        Optimise on the training period, then evaluate on the test period.

        Returns a dict with keys: ``window_index``, ``window``,
        ``best_params``, ``is_performance``, ``oos_performance``, ``error``.
        """
        result: Dict[str, Any] = {
            "window_index": idx,
            "window": window,
            "best_params": None,
            "is_performance": None,
            "oos_performance": None,
            "error": None,
        }

        try:
            # --- In-sample optimisation ---
            logger.debug(
                f"Window {idx}: grid_search {window['train_start']}~{window['train_end']}"
            )
            opt_result = self.strategy_optimizer.grid_search(
                strategy_type=strategy_type,
                param_grid=param_grid,
                symbol=symbol,
                start_date=window["train_start"],
                end_date=window["train_end"],
            )

            if not opt_result or "best_params" not in opt_result:
                logger.warning(f"Window {idx}: optimisation returned no best_params")
                result["error"] = "optimisation_no_result"
                return result

            best_params = opt_result["best_params"]
            is_performance = opt_result.get("best_performance", {})

            result["best_params"] = best_params
            result["is_performance"] = is_performance

            logger.debug(
                f"Window {idx}: best IS params={best_params} "
                f"IS sharpe={_safe_float(is_performance.get('sharpe_ratio')):.4f}"
            )

            # --- Out-of-sample evaluation ---
            logger.debug(
                f"Window {idx}: OOS backtest {window['test_start']}~{window['test_end']}"
            )
            oos_backtest = self.backtest_engine.run_backtest(
                strategy_type=strategy_type,
                params=best_params,
                symbol=symbol,
                start_date=window["test_start"],
                end_date=window["test_end"],
            )

            oos_performance = oos_backtest.get("performance", {})
            result["oos_performance"] = oos_performance

            logger.info(
                f"Window {idx} done | "
                f"IS sharpe={_safe_float(is_performance.get('sharpe_ratio')):.4f} "
                f"OOS sharpe={_safe_float(oos_performance.get('sharpe_ratio')):.4f} "
                f"OOS return={_safe_float(oos_performance.get('total_return')):.4f}"
            )

        except Exception as exc:
            logger.error(f"Window {idx} failed: {exc}", exc_info=True)
            result["error"] = str(exc)

        return result

    # ------------------------------------------------------------------
    # OOS aggregation
    # ------------------------------------------------------------------

    def _aggregate_oos_results(self, oos_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute combined out-of-sample performance statistics.

        Parameters
        ----------
        oos_results : List[Dict[str, Any]]
            One dict per window containing the OOS ``performance`` dict.

        Returns
        -------
        Dict[str, Any]
            Aggregated metrics including averages, standard deviations,
            consistency ratio, and the raw per-window data.
        """
        if not oos_results:
            return {
                "window_count": 0,
                "avg_total_return": None,
                "avg_sharpe_ratio": None,
                "avg_max_drawdown": None,
                "avg_win_rate": None,
                "std_total_return": None,
                "std_sharpe_ratio": None,
                "positive_return_ratio": None,
                "consistency_ratio": None,
                "raw_results": [],
            }

        def _collect(key: str) -> List[float]:
            return [
                _safe_float(r.get(key))
                for r in oos_results
                if r.get(key) is not None
            ]

        returns = _collect("total_return")
        sharpes = _collect("sharpe_ratio")
        drawdowns = _collect("max_drawdown")
        win_rates = _collect("win_rate")

        # Consistency: fraction of OOS windows with positive return
        positive_return_ratio = (
            sum(1 for r in returns if r > 0) / len(returns)
            if returns
            else None
        )

        # Consistency ratio: fraction of windows with sharpe > 0
        consistency_ratio = (
            sum(1 for s in sharpes if s > 0) / len(sharpes)
            if sharpes
            else None
        )

        aggregated: Dict[str, Any] = {
            "window_count": len(oos_results),
            "avg_total_return": float(np.mean(returns)) if returns else None,
            "avg_sharpe_ratio": float(np.mean(sharpes)) if sharpes else None,
            "avg_max_drawdown": float(np.mean(drawdowns)) if drawdowns else None,
            "avg_win_rate": float(np.mean(win_rates)) if win_rates else None,
            "std_total_return": float(np.std(returns)) if returns else None,
            "std_sharpe_ratio": float(np.std(sharpes)) if sharpes else None,
            "positive_return_ratio": positive_return_ratio,
            "consistency_ratio": consistency_ratio,
            "raw_results": oos_results,
        }

        logger.info(
            f"OOS aggregation | windows={len(oos_results)} "
            f"avg_return={aggregated['avg_total_return']:.4f if aggregated['avg_total_return'] is not None else 'N/A'} "
            f"avg_sharpe={aggregated['avg_sharpe_ratio']:.4f if aggregated['avg_sharpe_ratio'] is not None else 'N/A'} "
            f"consistency={consistency_ratio:.2f if consistency_ratio is not None else 'N/A'}"
        )

        return aggregated

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a human-readable summary of the most recent walk-forward run.

        Returns
        -------
        Dict[str, Any]
            Condensed result suitable for logging or serialisation.
            Returns an empty dict if no analysis has been run yet.
        """
        if not self._last_result:
            return {}

        result = self._last_result
        oos = result.get("oos_aggregated", {})
        wfe = result.get("walk_forward_efficiency")

        # Interpret WFE
        if wfe is None:
            wfe_interpretation = "N/A (insufficient data)"
        elif wfe >= 0.7:
            wfe_interpretation = "Excellent (>= 0.70) – strong out-of-sample persistence"
        elif wfe >= 0.5:
            wfe_interpretation = "Acceptable (>= 0.50) – moderate generalisation"
        elif wfe >= 0.3:
            wfe_interpretation = "Weak (0.30-0.50) – likely overfitted; use with caution"
        else:
            wfe_interpretation = "Poor (< 0.30) – parameters do not generalise; avoid live use"

        summary: Dict[str, Any] = {
            "strategy_type": result.get("strategy_type"),
            "symbol": result.get("symbol"),
            "date_range": result.get("date_range"),
            "config": result.get("config"),
            "total_windows": len(result.get("windows", [])),
            "successful_windows": sum(
                1
                for w in result.get("windows", [])
                if w.get("oos_performance") is not None and w.get("error") is None
            ),
            "oos_avg_return": oos.get("avg_total_return"),
            "oos_avg_sharpe": oos.get("avg_sharpe_ratio"),
            "oos_avg_drawdown": oos.get("avg_max_drawdown"),
            "oos_consistency_ratio": oos.get("consistency_ratio"),
            "oos_positive_return_ratio": oos.get("positive_return_ratio"),
            "walk_forward_efficiency": wfe,
            "wfe_interpretation": wfe_interpretation,
            "result_dir": result.get("result_dir"),
            "timestamp": result.get("timestamp"),
        }

        return summary

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_results(
        self,
        strategy_type: str,
        window_results: List[Dict[str, Any]],
        oos_aggregated: Dict[str, Any],
        wfe: Optional[float],
        timestamp: str,
    ) -> str:
        """
        Persist walk-forward results to ``OPTIMIZATION_RESULTS_DIR``.

        Returns the path to the created result directory.
        """
        result_dir = os.path.join(
            OPTIMIZATION_RESULTS_DIR,
            f"walk_forward_{strategy_type}_{timestamp}",
        )

        try:
            os.makedirs(result_dir, exist_ok=True)

            # --- Per-window CSV ---
            rows = []
            for w in window_results:
                row: Dict[str, Any] = {
                    "window_index": w["window_index"],
                    "train_start": w["window"]["train_start"],
                    "train_end": w["window"]["train_end"],
                    "test_start": w["window"]["test_start"],
                    "test_end": w["window"]["test_end"],
                    "best_params": json.dumps(w.get("best_params") or {}),
                    "error": w.get("error"),
                }

                # IS metrics
                is_perf = w.get("is_performance") or {}
                for metric in ("total_return", "sharpe_ratio", "max_drawdown", "win_rate"):
                    row[f"is_{metric}"] = is_perf.get(metric)

                # OOS metrics
                oos_perf = w.get("oos_performance") or {}
                for metric in ("total_return", "sharpe_ratio", "max_drawdown", "win_rate"):
                    row[f"oos_{metric}"] = oos_perf.get(metric)

                rows.append(row)

            windows_df = pd.DataFrame(rows)
            windows_csv = os.path.join(result_dir, "window_results.csv")
            windows_df.to_csv(windows_csv, index=False)

            # --- OOS aggregated JSON ---
            oos_json_path = os.path.join(result_dir, "oos_aggregated.json")
            # Remove raw_results from JSON save (can be large)
            oos_save = {k: v for k, v in oos_aggregated.items() if k != "raw_results"}
            with open(oos_json_path, "w", encoding="utf-8") as fh:
                json.dump(oos_save, fh, indent=2, ensure_ascii=False, default=str)

            # --- Summary text ---
            summary_path = os.path.join(result_dir, "summary.txt")
            with open(summary_path, "w", encoding="utf-8") as fh:
                fh.write(f"Walk-Forward Optimisation Summary\n")
                fh.write("=" * 60 + "\n")
                fh.write(f"Strategy       : {strategy_type}\n")
                fh.write(f"Timestamp      : {timestamp}\n")
                fh.write(f"Total windows  : {len(window_results)}\n")
                fh.write(
                    f"Successful     : "
                    f"{sum(1 for w in window_results if not w.get('error'))}\n"
                )
                fh.write("\nOOS Aggregated Metrics\n")
                fh.write("-" * 40 + "\n")
                for key, value in oos_save.items():
                    fh.write(f"  {key}: {value}\n")
                fh.write("\n")
                fh.write(
                    f"Walk-Forward Efficiency (OOS/IS Sharpe): "
                    f"{wfe:.4f if wfe is not None else 'N/A'}\n"
                )

            logger.info(f"Walk-forward results saved to: {result_dir}")

        except Exception as exc:
            logger.warning(f"Could not save walk-forward results: {exc}")

        return result_dir
