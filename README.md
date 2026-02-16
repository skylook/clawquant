# ClawQuant — 量化回测平台

基于 Backtrader 的多市场量化策略回测系统，支持 A股 / 港股 / 美股，内置 WebUI 可视化平台与交互式 K 线图。

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 WebUI（推荐）
python web/app.py
# 浏览器访问 http://localhost:8888

# 3. 或直接命令行回测
python run_multimarket_backtest.py
```

---

## WebUI 使用说明

### 启动

```bash
python web/app.py
# → http://localhost:8888
```

### 四个 Tab 功能

| Tab | 功能描述 |
|-----|---------|
| **概览 Dashboard** | 最新回测汇总：市场卡片、权益曲线、收益/夏普对比图 |
| **运行回测** | 配置策略 + 参数 → 一键运行三市场回测 → 交互式 K 线图 |
| **市场对比** | 多维雷达图、风险/收益散点图 |
| **交易记录** | 逐笔交易明细表格、盈亏分布图 |

### 运行回测 + 查看 K 线图（Step by Step）

1. 切换到 **「运行回测」** Tab
2. 选择策略（默认 `MA_CROSS`）并填写参数
3. 勾选目标市场（A股 / 港股 / 美股），点击 **▶ 运行回测**
4. 等待完成（三市场顺序执行，约需 10–30 秒）
5. 点击任意市场结果卡片（带「点击查看K线」提示）
6. 页面下方加载 **Plotly 交互式 K 线图**，包含：
   - OHLC 蜡烛图（悬停显示 open/high/low/close/volume）
   - 策略指标线（MA、信号线等，由 backtrader-plotly 自动生成）
   - 买卖点三角标记（悬停显示时间与信号原因）
   - 成交量柱状图（子图）
   - 组合价值曲线（子图）
7. 点击其他市场卡片切换 K 线图

> **注意**：K 线图数据缓存在服务器内存中，重启服务后需重新运行回测。

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 主页面 |
| `GET` | `/api/strategies` | 可用策略及默认参数 |
| `GET` | `/api/results` | 历史回测结果列表 |
| `GET` | `/api/results/latest` | 最新回测结果 |
| `POST` | `/api/backtest` | 运行回测（同步） |
| `GET` | `/api/chart/{run_id}/{market_key}` | 懒加载单市场 K 线 JSON |

---

## 命令行回测

```bash
# 三市场批量回测（A股/港股/美股）
python run_multimarket_backtest.py

# 单市场回测（通过 main.py 流水线）
python main.py --mode backtest --symbol 000001.SH --start-date 2020-01-01 --end-date 2024-01-01

# 参数优化
python main.py --mode optimize

# 完整流程（数据获取 → 回测 → 优化 → 分析）
python main.py --mode full
```

---

## 项目结构

```
clawquant/
├── main.py                      # CLI 主入口（backtest / optimize / full）
├── run_multimarket_backtest.py  # 三市场批量回测脚本
├── requirements.txt
├── CLAUDE.md                    # Claude Code 项目指引
│
├── web/                         # WebUI（FastAPI）
│   ├── app.py                   # FastAPI 后端，端口 8888
│   └── templates/
│       └── index.html           # 前端（Alpine.js + Tailwind + Plotly.js + Chart.js）
│
├── strategies/                  # 策略层
│   ├── base_strategy.py         # BaseStrategy 基类 + StrategyFactory 注册表
│   ├── ma_strategy.py           # MA 均线策略
│   ├── macd_strategy.py         # MACD 策略
│   ├── rsi_strategy.py          # RSI 策略
│   ├── bollinger_strategy.py    # 布林带策略
│   ├── ma_cross_strategy.py     # 双均线交叉策略（主力策略）
│   ├── triple_ma_strategy.py    # 三均线策略
│   ├── dual_thrust_strategy.py  # Dual Thrust 策略
│   ├── kama_strategy.py         # KAMA 自适应均线策略
│   └── turtle_strategy.py       # 海龟交易策略
│
├── backtests/                   # 回测引擎层
│   ├── backtest_engine.py       # BacktestEngine（封装 bt.Cerebro）
│   ├── analyzer.py              # BacktestAnalyzer（Sharpe/Sortino/Omega/Calmar）
│   ├── optimizer.py             # StrategyOptimizer（网格/随机搜索）
│   └── walk_forward.py          # WalkForwardOptimizer（滚动 IS/OOS 验证）
│
├── config/
│   ├── settings.py              # 全局配置（交易参数、数据源）
│   └── strategy_config.py       # 各策略默认参数和优化网格
│
├── utils/
│   ├── data_fetcher.py          # DataFetcher（Tushare/AKShare/yfinance，24h缓存）
│   ├── data_processor.py        # DataProcessor（OHLCV 校验、TA-Lib特征）
│   └── logger.py                # 日志（10MB轮转，30天保留）
│
├── data/
│   ├── raw/                     # 原始行情 CSV
│   ├── processed/               # 处理后数据
│   └── cache/                   # DataFetcher 24h 缓存（pickle）
│
├── results/
│   ├── backtest_results/        # 回测结果（timestamped CSV）
│   ├── optimization_results/    # 优化结果
│   └── best_strategies/         # 最优策略配置
│
├── docs/                        # 设计文档
│   ├── ARCHITECTURE.md
│   └── STRATEGY_DESIGN.md
│
├── tests/                       # 测试脚本
│   ├── test_ma_strategy.py
│   ├── test_real_data.py
│   ├── test_tushare.py
│   └── ...
│
└── debug/                       # 调试脚本与临时产物
    ├── debug_chart_rendering.py
    ├── debug_results.py
    └── ...
```

---

## 策略列表

| 策略 ID | 类名 | 描述 |
|---------|------|------|
| `MA` | `MAStrategy` | 单均线趋势跟踪 |
| `MACD` | `MACDStrategy` | MACD 趋势 + 动量 |
| `RSI` | `RSIStrategy` | RSI 超买超卖 |
| `BOLL` | `BollingerStrategy` | 布林带均值回归 |
| `MA_CROSS` | `MACrossStrategy` | 双均线交叉（主力，跨市场验证最优）|
| `TRIPLE_MA` | `TripleMAStrategy` | 三均线趋势过滤 |
| `DUAL_THRUST` | `DualThrustStrategy` | Dual Thrust 突破 |
| `KAMA` | `KAMAStrategy` | KAMA 自适应均线 |
| `TURTLE` | `TurtleStrategy` | 海龟交易（N日突破）|

---

## 技术栈

| 层 | 技术 |
|----|------|
| 回测引擎 | Backtrader 1.9.78 |
| 数据获取 | AKShare / Tushare / yfinance |
| 技术指标 | TA-Lib |
| WebUI 后端 | FastAPI + uvicorn（端口 8888）|
| K 线图生成 | backtrader-plotly（Backtrader 原生绘图流水线）|
| 前端图表 | Plotly.js（K线）+ Chart.js（权益/雷达/散点）|
| 前端框架 | Alpine.js + Tailwind CSS + Flowbite |

---

## 关键配置

`config/settings.py` 中可调整：
- 初始资金（默认 100,000）、手续费（默认 0.03%）、滑点（0.01%）
- 主测试标的（默认 `000001.SH`）、回测区间（2020-01-01 ~ 2024-01-01）

---

## 输出说明

| 目录 | 内容 |
|------|------|
| `results/backtest_results/` | 每次回测生成 `comparison.csv`（多市场对比）|
| `results/optimization_results/` | 参数优化结果 CSV + JSON |
| `results/optimization_results/walk_forward_*/` | 走势前向验证报告（WFE 指标）|
| `logs/clawquant.log` | 运行日志（10MB 轮转，30天保留）|

---

## 注意事项

- 回测结果仅供研究参考，不构成投资建议
- 注意过拟合风险，建议配合走势前向验证（Walk-Forward）评估策略稳健性
- K 线图缓存在内存中，服务重启后需重新运行回测
