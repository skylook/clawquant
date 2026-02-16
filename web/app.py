"""
ClawQuant WebUI — FastAPI 后端
运行: cd /path/to/clawquant && python web/app.py
访问: http://localhost:8888
"""

import os
import sys
import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# 将项目根目录加入 sys.path，使 strategies 等模块可导入
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="ClawQuant WebUI", version="1.0.0")

# Jinja2 模板目录
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# 全局任务状态存储（内存中，重启丢失）
_tasks: Dict[str, Dict] = {}
_tasks_lock = threading.Lock()

# K线图缓存（内存中，重启丢失）{run_id: {market_key: chart_json}}
_chart_cache: Dict[str, Dict[str, Any]] = {}

# ──────────────────────────────────────────────
# 辅助：扫描结果目录
# ──────────────────────────────────────────────

RESULTS_DIR = ROOT / "results" / "backtest_results"


def _scan_results() -> List[Dict]:
    """扫描 results/backtest_results/ 目录，返回历史运行列表"""
    runs = []
    if not RESULTS_DIR.exists():
        return runs
    for d in sorted(RESULTS_DIR.iterdir(), reverse=True):
        csv_path = d / "comparison.csv"
        if csv_path.exists():
            runs.append({
                "run_id": d.name,
                "path": str(csv_path),
                "timestamp": d.name.split("_", 1)[-1] if "_" in d.name else d.name,
            })
    return runs


def _read_comparison_csv(csv_path: str) -> List[Dict]:
    """读取 comparison.csv，返回结构化 JSON"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    records = []
    for _, row in df.iterrows():
        def _f(v):
            try:
                return float(str(v).replace("+", "").replace("%", ""))
            except Exception:
                return 0.0

        records.append({
            "market": row.get("市场", ""),
            "total_return": _f(row.get("总收益", 0)),
            "annual_return": _f(row.get("年化收益", 0)),
            "sharpe_ratio": _f(row.get("夏普比率", 0)),
            "max_drawdown": _f(row.get("最大回撤%", 0)),
            "win_rate": _f(row.get("胜率", 0)),
            "trades": int(_f(row.get("交易次数", 0))),
            "final_value": _f(row.get("期末资产", 100000)),
            "equity_curve": [],
            "trade_log": [],
        })
    return records


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

class BacktestRequest(BaseModel):
    strategy: str = "MA_CROSS"
    params: Dict[str, Any] = {}
    markets: List[str] = ["a_share", "hk_share", "us_nvda"]


# ──────────────────────────────────────────────
# 路由
# ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """返回主页面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/strategies")
async def get_strategies():
    """返回可用策略列表及各市场默认参数"""
    strategies = [
        "MA", "MACD", "RSI", "BOLL", "MA_CROSS",
        "TRIPLE_MA", "DUAL_THRUST", "KAMA", "TURTLE"
    ]
    default_params = {
        "MA_CROSS": {
            "a_share":  {"fast_period": 3,  "slow_period": 100, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.15, "max_position_size": 0.8},
            "hk_share": {"fast_period": 8,  "slow_period": 20,  "stop_loss_ratio": 0.05, "take_profit_ratio": 0.15, "max_position_size": 0.8},
            "us_nvda":  {"fast_period": 10, "slow_period": 100, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.20, "max_position_size": 0.8},
        },
        "MA": {
            "a_share":  {"ma_period": 20, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.15, "max_position_size": 0.8},
            "hk_share": {"ma_period": 20, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.15, "max_position_size": 0.8},
            "us_nvda":  {"ma_period": 20, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.20, "max_position_size": 0.8},
        },
    }
    return {"strategies": strategies, "default_params": default_params}


@app.get("/api/results")
async def get_results():
    """扫描 results/ 目录，返回历史运行列表"""
    runs = _scan_results()
    return {"runs": runs, "count": len(runs)}


@app.get("/api/results/latest")
async def get_latest_results():
    """读取最新 comparison.csv，返回 JSON"""
    runs = _scan_results()
    if not runs:
        return {"results": [], "run_id": None, "message": "暂无历史回测结果"}
    latest = runs[0]
    try:
        records = _read_comparison_csv(latest["path"])
        return {"results": records, "run_id": latest["run_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取结果失败: {e}")


@app.post("/api/backtest")
async def run_backtest_api(req: BacktestRequest):
    """
    同步运行回测，返回完整结果 JSON。
    在生产环境中建议改为异步任务，这里为简单起见使用同步执行。
    """
    import run_multimarket_backtest as rmb

    # 市场配置映射
    market_loaders = {
        "a_share":  (rmb.load_a_share,  "000001.SH", "A股 000001.SH"),
        "hk_share": (rmb.load_hk_share, "0700.HK",   "港股 0700.HK"),
        "us_nvda":  (rmb.load_us_share, "NVDA",       "美股 NVDA"),
    }

    # 各市场默认参数
    default_params_map = {
        "MA_CROSS": {
            "a_share":  {"fast_period": 3,  "slow_period": 100, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.15, "max_position_size": 0.8},
            "hk_share": {"fast_period": 8,  "slow_period": 20,  "stop_loss_ratio": 0.05, "take_profit_ratio": 0.15, "max_position_size": 0.8},
            "us_nvda":  {"fast_period": 10, "slow_period": 100, "stop_loss_ratio": 0.05, "take_profit_ratio": 0.20, "max_position_size": 0.8},
        },
    }

    # 清洗 float('inf')/NaN：FastAPI/Starlette JSONResponse 使用 allow_nan=False，
    # 含 NaN/Inf 的 dict 直接返回会触发 ValueError → 500。
    # chart_json 也必须经过此函数再存入缓存。
    def _sanitize(obj):
        if isinstance(obj, float):
            if obj == float('inf') or obj == float('-inf') or obj != obj:
                return None
            return obj
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(i) for i in obj]
        return obj

    results = []
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    for market_key in req.markets:
        if market_key not in market_loaders:
            continue

        loader_fn, symbol, market_name = market_loaders[market_key]

        # 合并参数：默认 → 用户覆盖
        base_params = (
            default_params_map.get(req.strategy, {}).get(market_key, {})
        )
        merged_params = {**base_params, **req.params}

        try:
            df, sym, start, end = loader_fn()
            result = rmb.run_backtest(df, sym, req.strategy, merged_params)
            result["market"] = market_name
            result["market_key"] = market_key
            # 缓存 chart_json（不放入响应体，保持响应轻量）
            # backtrader-plotly 在指标预热期会产生 NaN，必须先清洗
            chart_json = result.pop("chart_json", None)
            if chart_json is not None:
                if run_id not in _chart_cache:
                    # 保留最近 20 次运行，超出时删除最旧的条目（防止内存泄漏）
                    if len(_chart_cache) >= 20:
                        oldest = next(iter(_chart_cache))
                        del _chart_cache[oldest]
                    _chart_cache[run_id] = {}
                _chart_cache[run_id][market_key] = _sanitize(chart_json)
            results.append(result)
        except Exception as e:
            results.append({
                "market": market_name,
                "market_key": market_key,
                "error": str(e),
                "total_return": 0,
                "annual_return": 0,
                "sharpe_ratio": None,
                "max_drawdown": 0,
                "win_rate": 0,
                "trades": 0,
                "final_value": 0,
                "equity_curve": [],
                "trade_log": [],
            })

    return _sanitize({"results": results, "run_id": run_id})


@app.get("/api/chart/{run_id}/{market_key}")
async def get_chart(run_id: str, market_key: str):
    """按需返回单市场 K线 Plotly 图表 JSON（懒加载）"""
    chart = _chart_cache.get(run_id, {}).get(market_key)
    if chart is None:
        raise HTTPException(status_code=404, detail="K线图暂不可用（服务重启后缓存清除，请重新运行回测）")
    return chart


# ──────────────────────────────────────────────
# 启动
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  ClawQuant WebUI")
    print("  访问: http://localhost:8888")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8888, reload=False)
