# ClawQuant - OpenClaw量化交易策略优化系统

## 项目概述
基于OpenClaw的自动化量化策略生成、回测和优化系统。系统会自动生成多种策略，通过回测找到最优策略。

## 文件结构
```
Develop/clawquant/
├── README.md                    # 项目说明
├── main.py                      # 主程序入口
├── requirements.txt             # 依赖包
├── config/                      # 配置文件
│   ├── __init__.py
│   ├── settings.py             # 全局配置
│   └── strategy_config.py      # 策略参数配置
├── data/                        # 数据目录
│   ├── raw/                    # 原始数据
│   ├── processed/              # 处理后的数据
│   └── cache/                  # 缓存数据
├── strategies/                  # 策略模块
│   ├── __init__.py
│   ├── base_strategy.py        # 策略基类
│   ├── ma_strategy.py          # 均线策略
│   ├── macd_strategy.py        # MACD策略
│   ├── rsi_strategy.py         # RSI策略
│   ├── bollinger_strategy.py   # 布林带策略
│   ├── ma_cross_strategy.py    # 双均线交叉策略
│   └── strategy_factory.py     # 策略工厂
├── backtests/                   # 回测模块
│   ├── __init__.py
│   ├── backtest_engine.py      # 回测引擎
│   ├── analyzer.py             # 回测结果分析
│   └── optimizer.py            # 策略优化器
├── results/                     # 结果目录
│   ├── backtest_results/       # 回测结果
│   ├── optimization_results/   # 优化结果
│   └── best_strategies/        # 最优策略
└── utils/                       # 工具模块
    ├── __init__.py
    ├── data_fetcher.py         # 数据获取
    ├── data_processor.py       # 数据处理
    ├── logger.py               # 日志工具
    └── visualizer.py           # 可视化工具
```

## 功能特点
1. **策略自动生成**：基于模板生成多种技术指标策略
2. **批量回测**：并行运行多个策略回测
3. **参数优化**：自动搜索最优参数组合
4. **结果分析**：全面的绩效指标评估
5. **策略筛选**：基于风险调整收益选择最优策略
6. **多策略支持**：支持MA、MACD、RSI、BOLL、MA_CROSS等多种策略
7. **实时数据验证**：支持A股实时数据验证

## 使用方法

### 命令行回测

```bash
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python main.py

# 运行特定功能
python main.py --mode backtest      # 只运行回测
python main.py --mode optimize      # 只运行优化
python main.py --mode full          # 完整流程（默认）

# 三市场批量回测（A股/港股/美股，结果保存到 results/backtest_results/）
python run_multimarket_backtest.py
```

---

## WebUI 可视化平台

### 快速启动

```bash
# 1. 安装 Web 依赖（首次执行）
pip install -r requirements.txt
pip install backtrader-plotly       # K线图依赖

# 2. 启动 Web 服务
python web/app.py

# 浏览器访问
open http://localhost:8888
```

### 功能说明

| Tab | 功能 |
|-----|------|
| 概览 Dashboard | 最新回测汇总：市场卡片、权益曲线、收益/夏普对比图 |
| 运行回测 | 配置策略参数 → 一键运行三市场回测 → **交互式 K 线图** |
| 市场对比 | 多维雷达图、风险/收益散点图 |
| 交易记录 | 各市场逐笔交易明细、盈亏分布图 |

### 运行回测 + 查看 K 线图

1. 切换到 **「运行回测」** Tab
2. 选择策略（默认 `MA_CROSS`）并填写参数
3. 勾选目标市场（A股 / 港股 / 美股），点击 **▶ 运行回测**
4. 等待完成后，点击任意市场结果卡片
5. 页面下方出现该市场的 **Plotly 交互式 K 线图**，包含：
   - OHLC 蜡烛图（悬停显示 open/high/low/close/volume）
   - 策略指标线（MA、信号线等）
   - 买卖点三角标记（▲买入 / ▼卖出，悬停显示时间与信号原因）
   - 成交量柱状图（子图）
   - 组合价值曲线（子图）
6. 点击其他市场卡片可切换 K 线图

> **注意**：K 线图数据缓存在服务器内存中，重启服务后需重新运行回测才可查看。

### 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI + uvicorn（端口 8888）|
| K 线生成 | backtrader-plotly（backtrader 原生绘图流水线）|
| 前端图表 | Plotly.js（K线）+ Chart.js（权益/雷达/散点）|
| 前端交互 | Alpine.js + Tailwind CSS + Flowbite |

---

## 当前进展
- [x] 基础框架搭建
- [x] 数据获取模块实现
- [x] MA策略实现
- [x] MACD策略实现
- [x] RSI策略实现
- [x] BOLL策略实现
- [x] MA_CROSS策略实现
- [x] TRIPLE_MA / DUAL_THRUST / KAMA / TURTLE 策略实现
- [x] 回测引擎开发
- [x] 参数优化功能实现
- [x] 走势前向验证（Walk-Forward Optimization）
- [x] 实盘数据验证
- [x] 性能分析工具
- [x] 完整回测流程
- [x] WebUI 可视化平台（FastAPI + Alpine.js）
- [x] 交互式 K 线图（backtrader-plotly + Plotly.js）
- [ ] 风险管理模块
- [ ] 实盘交易接口

## 策略类型
1. **MA策略**: 基于移动平均线的趋势跟踪策略
2. **MACD策略**: 基于MACD指标的趋势和动量策略
3. **RSI策略**: 基于相对强弱指数的超买超卖策略
4. **BOLL策略**: 基于布林带的均值回归策略
5. **MA_CROSS策略**: 基于双移动平均线交叉的策略

## 最新成果
- 成功回测A股上证指数(000001.SH) 2014-2024年数据
- 默认策略(MA20, MA60): 总收益1.23%, 夏普比率0.050, 最大回撤-11.70%
- 优化后策略: 总收益61.38%, 夏普比率0.537, 最大回撤-9.82%
- 最优参数: fast_period: 5, slow_period: 70

## 性能指标
- 总收益率(Total Return)
- 年化收益率(Annual Return)
- 夏普比率(Sharpe Ratio)
- 最大回撤(Max Drawdown)
- 胜率(Win Rate)
- 盈亏比(Profit Factor)
- 交易次数(Number of Trades)

## 配置说明
在`config/settings.py`中可配置：
- 交易参数(初始资金、手续费率等)
- 回测参数(回测时间段、评估指标权重)
- 数据参数(缓存设置、数据源选择)
- 优化参数(参数搜索范围、优化目标权重)

## 数据源
- 默认使用akshare获取A股数据
- 备选tushare作为数据源
- 支持缓存机制提高数据访问效率

## 输出结果
系统会在`results/`目录下生成：
1. 各策略回测报告（CSV格式）
2. 策略绩效对比图表
3. 最优策略代码和配置
4. 详细的分析报告

## 注意事项
1. 回测结果仅供参考，实盘交易需谨慎
2. 注意过拟合风险，避免在历史数据上过度优化
3. 定期更新市场数据，确保策略有效性