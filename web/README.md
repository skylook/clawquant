# ClawQuant WebUI 可视化系统

## 概述

ClawQuant 提供两种 Web 可视化方案：

1. **Streamlit + Pyecharts**（推荐）- 专业金融图表，交互性强
2. **FastAPI + Plotly** - RESTful API，适合集成

## 方案一：Streamlit + Pyecharts（推荐）

### 特点

- ✅ **专业K线图** - 支持蜡烛图、均线、成交量
- ✅ **交互式界面** - 直观的参数配置和结果展示
- ✅ **实时回测** - 点击运行即可查看结果
- ✅ **多市场对比** - 同时展示多个市场的回测结果
- ✅ **历史记录** - 查看历史回测记录

### 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 启动应用

```bash
streamlit run web/streamlit_app.py
```

#### 3. 访问界面

浏览器自动打开 `http://localhost:8501`

### 使用说明

#### 侧边栏配置

1. **策略选择** - 选择回测策略（MA、MA_CROSS、MACD等）
2. **策略参数** - 调整策略参数（周期、止损止盈等）
3. **市场选择** - 选择要回测的市场（A股、港股、美股）
4. **回测参数** - 设置初始资金、手续费等

#### 主界面功能

1. **K线图** - 显示价格走势、均线和成交量
2. **资金曲线** - 展示账户资金变化
3. **交易记录** - 查看详细的买卖记录
4. **多市场对比** - 对比不同市场的表现

### 可视化图表

#### 1. 专业K线图

- 蜡烛图（红涨绿跌）
- MA5/MA10/MA20/MA30 均线
- 成交量柱状图
- 数据缩放和拖拽
- 十字光标

#### 2. 资金曲线图

- 平滑曲线展示
- 面积填充
- 交互式提示

#### 3. 对比柱状图

- 多市场收益对比
- 最大值/最小值标记
- 交互式图例

### 支持的策略

| 策略 | 说明 | 参数 |
|------|------|------|
| MA | 移动平均线策略 | ma_period, stop_loss_ratio, take_profit_ratio |
| MA_CROSS | 双均线交叉策略 | fast_period, slow_period, stop_loss_ratio |
| MACD | MACD策略 | fast_period, slow_period, signal_period |
| RSI | RSI策略 | rsi_period, rsi_lower, rsi_upper |
| BOLL | 布林带策略 | period, devfactor |
| TRIPLE_MA | 三均线策略 | fast_period, mid_period, slow_period |
| DUAL_THRUST | Dual Thrust策略 | k1, k2, period |
| KAMA | KAMA策略 | period, fast, slow |
| TURTLE | 海龟交易策略 | entry_period, exit_period, atr_period |

### 文件结构

```
web/
├── streamlit_app.py      # Streamlit 主应用
├── charts.py             # Pyecharts 图表模块
├── ui_components.py      # UI 组件模块
├── app.py               # FastAPI 应用（备选）
├── templates/           # FastAPI 模板
└── README.md            # 本文档
```

## 方案二：FastAPI + Plotly

### 启动方式

```bash
python web/app.py
```

访问 `http://localhost:8888`

### API 端点

- `GET /` - 主页面
- `GET /api/strategies` - 获取策略列表
- `GET /api/results` - 获取历史结果
- `GET /api/results/latest` - 获取最新结果
- `POST /api/backtest` - 运行回测
- `GET /api/chart/{run_id}/{market_key}` - 获取K线图

## 对比

| 特性 | Streamlit + Pyecharts | FastAPI + Plotly |
|------|---------------------|------------------|
| 易用性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 图表质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 交互性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| API支持 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 部署难度 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 适用场景 | 本地分析、演示 | 生产环境、集成 |

## 技术栈

### Streamlit 方案

- **Streamlit** - Web 应用框架
- **Pyecharts** - 专业图表库
- **streamlit-echarts** - Streamlit + Echarts 集成

### FastAPI 方案

- **FastAPI** - 高性能 Web 框架
- **Plotly** - 交互式图表库
- **Jinja2** - 模板引擎

## 常见问题

### Q: 如何切换到 Streamlit 方案？

A: 直接运行 `streamlit run web/streamlit_app.py` 即可。

### Q: 两种方案可以同时运行吗？

A: 可以，它们使用不同的端口（8501 和 8888）。

### Q: 如何添加新的策略？

A: 在 `ui_components.py` 的 `strategy_selector_ui()` 函数中添加策略配置。

### Q: 图表不显示怎么办？

A: 检查数据格式，确保包含 "日期"、"开盘"、"收盘"、"最高"、"最低"、"成交量" 列。

### Q: 如何自定义图表样式？

A: 修改 `charts.py` 中的 Pyecharts 配置选项。

## 参考项目

本可视化系统参考了以下优秀开源项目：

- [stock-backtrader-web-app](https://github.com/chenwr727/stock-backtrader-web-app) - Streamlit + Backtrader 回测应用

## 贡献

欢迎提交 Issue 和 Pull Request！
