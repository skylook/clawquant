# ClawQuant 系统架构文档

## 系统概述

**ClawQuant** 是一个跨市场量化交易系统，支持A股、港股、美股三大市场的策略回测和交易执行。

## 核心架构

### 1. 数据层 (Data Layer)

```
data/
├── raw/           # 原始数据
│   ├── 000001.SH_daily_2014-2025.csv
│   ├── 0700.HK_daily_2014-2025.csv
│   └── NVDA_daily_2014-2025.csv
├── processed/     # 清洗后数据
└── cache/         # 数据缓存
```

**数据源**:
- A股: Tushare API
- 港股: AKShare (Yahoo Finance备用)
- 美股: Yahoo Finance (yfinance)

**数据格式**:
| 字段 | 类型 | 说明 |
|------|------|------|
| date | datetime | 交易日期 |
| open | float | 开盘价 |
| high | float | 最高价 |
| low | float | 最低价 |
| close | float | 收盘价 |
| volume | int | 成交量 |

### 2. 策略层 (Strategy Layer)

```python
strategies/
├── base_strategy.py      # 策略基类
├── ma_strategy.py        # 均线策略
├── ma_cross_strategy.py  # 双均线交叉
├── macd_strategy.py      # MACD策略
├── rsi_strategy.py       # RSI策略
├── bollinger_strategy.py # 布林带
└── triple_ma_strategy.py # 三重均线(已废弃)
```

**设计模式**: 策略模式 (Strategy Pattern)
- 统一接口: `generate_signals()`
- 易于扩展: 继承`BaseStrategy`
- 参数配置: 通过`config/strategy_config.py`

### 3. 回测层 (Backtest Layer)

**核心组件**:
```python
backtests/
├── backtest_engine.py   # 回测引擎
├── optimizer.py         # 参数优化器
└── analyzer.py          # 结果分析器
```

**回测流程**:
1. 加载数据 → 2. 生成信号 → 3. 计算持仓 → 4. 计算收益 → 5. 评估指标

**评价指标**:
- Total Return (总收益率)
- Sharpe Ratio (夏普比率)
- Max Drawdown (最大回撤)
- Trade Count (交易次数)

### 4. 配置层 (Config Layer)

```python
config/
├── settings.py           # 全局设置
└── strategy_config.py    # 策略参数配置
```

**参数管理**:
- 基础参数 (base params)
- 参数网格 (param grid for optimization)
- 策略工厂 (strategy factory)

### 5. 实验层 (Experiment Layer)

```
experiments/
├── exp_20250207_triple_ma.md              # 废弃实验
├── exp_20250207_parameter_optimization.json
├── exp_20250207_strategy_comparison_a股.json
└── exp_20250207_final_report.md           # 最终报告
```

## 核心模块详解

### 策略基类 (BaseStrategy)

```python
class BaseStrategy:
    def __init__(self, params: Dict[str, Any]):
        self.params = params
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        pass
        
    def validate_params(self) -> bool:
        """验证参数有效性"""
        pass
        
    def get_param_ranges(self) -> Dict[str, Any]:
        """返回参数优化范围"""
        pass
```

### 双均线策略实现

```python
def ma_cross_strategy(df, fast=5, slow=70):
    # 计算均线
    df['fast_ma'] = df['close'].rolling(window=fast).mean()
    df['slow_ma'] = df['close'].rolling(window=slow).mean()
    
    # 生成信号
    df['signal'] = 0
    df.loc[df['fast_ma'] > df['slow_ma'], 'signal'] = 1
    
    # 持仓 (滞后一期，避免未来数据)
    df['position'] = df['signal'].shift(1).fillna(0)
    
    # 计算收益
    df['returns'] = df['close'].pct_change()
    df['strategy_returns'] = df['position'] * df['returns']
    
    return df
```

## 数据流

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │───▶│  Strategy   │───▶│  Backtest   │───▶│  Metrics    │
│   Source    │    │   Engine    │    │   Engine    │    │  Analysis   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                 │                   │                  │
      ▼                 ▼                   ▼                  ▼
 raw CSV files    signal generation   returns calc      sharpe/max dd
```

## 关键设计决策

### 1. 为什么放弃Triple MA?

**原始设计**:
```python
# 买入: 快线>中线>慢线
# 卖出: 快线<中线
```

**问题**:
- 卖出条件过于敏感
- 交易次数翻倍(90+次 vs 50次)
- 错失趋势行情

**结论**: 简单双均线最优

### 2. 参数设计原则

**A股 (3/100)**:
- 超短快线: 捕捉快速启动
- 超慢慢线: 过滤频繁震荡

**港股 (8/20)**:
- 中短周期: 适应互联网股波动
- 相对敏感: 捕捉腾讯趋势

**美股 (10/100)**:
- 中线信号: 避免噪音
- 超长慢线: 持有大趋势

### 3. 为什么选择日线数据?

**优势**:
- 趋势清晰，噪音较少
- 计算成本低
- 实盘可执行性好

**劣势**:
- 信号滞后
- 无法捕捉日内波动
- 隔夜风险

**决策**: 日线是趋势跟踪的最佳平衡

## 性能指标

### 当前系统性能
- **回测速度**: ~2秒/策略/标的
- **数据加载**: ~1秒/文件
- **参数优化**: ~30秒/市场 (6x8=48组参数)

### 优化空间
- [ ] 向量化计算优化
- [ ] Numba加速
- [ ] 并行计算

## 安全性和可靠性

### 数据质量检查
- 空值处理 (fillna)
- 日期对齐 (resample)
- 价格合理性 (high>=low)

### 避免过拟合
- 参数空间限制
- 样本外验证预留
- 经济逻辑优先

### 版本控制
- Git分支管理
- 实验记录可追溯
- 结果可复现

## 扩展性设计

### 新增策略
1. 继承`BaseStrategy`
2. 实现`generate_signals()`
3. 在`strategy_config.py`注册
4. 参数优化自动生效

### 新增数据源
1. 实现`DataFetcher`接口
2. 标准化输出格式
3. 自动缓存支持

## Git 工作流

```
main
├── feature/triple-ma        # 已废弃，可删除
│   ├── docs/STRATEGY_DESIGN.md   
│   ├── docs/ARCHITECTURE.md
│   └── experiments/
└── feature/volatility-filter  # 待开发
```

## 已知限制

1. **无实盘接口**: 仅支持回测
2. **单标的测试**: 未测试多标的组合
3. **未考虑滑点**: 理想化执行
4. **固定手续费**: 未按交易所差异化

## 未来路线图

### v1.1 (建议)
- [ ] ATR波动率过滤
- [ ] 动态止损机制
- [ ] 多标的回测

### v1.2 (建议)
- [ ] 实盘接口对接
- [ ] 实时数据流
- [ ] Web Dashboard

### v2.0 (研究)
- [ ] 机器学习策略
- [ ] 多因子模型
- [ ] 组合优化

---
**文档更新**: 2026-02-08  
**版本**: v1.0  
**Git Commit**: caa37c9
