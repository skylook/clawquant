# ClawQuant 代码审查报告 - 严重问题汇总

**审查时间**: 2026-02-08
**审查工具**: Google Gemini
**代码版本**: feature/triple-ma 分支
**综合评分**: 4/10 (需要重大修复后才能投入使用)

---

## 🔴 严重问题 (Critical) - 共 4 项

### 1. 策略参数与市场规范严重不符

**位置**: `strategies/ma_cross_strategy.py` - `__init__` 方法

**问题描述**:
```python
default_params = {
    'fast_period': 10,  # ❌ 不符合任何市场规范
    'slow_period': 30,  # ❌ 不符合任何市场规范
}
```

代码默认值与策略设计文档要求严重不符：
- **A股要求**: 快线3天/慢线100天 → 代码使用10/30 ❌
- **港股要求**: 快线8天/慢线20天 → 代码使用10/30 ❌
- **美股要求**: 快线10天/慢线100天 → 代码使用10/30 ❌

**影响**: 策略在实际市场中无法达到预期效果，回测结果严重失真

**改进建议**:
```python
MARKET_PARAMS = {
    'A股': {'fast_period': 3, 'slow_period': 100},
    '港股': {'fast_period': 8, 'slow_period': 20},
    '美股': {'fast_period': 10, 'slow_period': 100},
}

def __init__(self, params: Dict[str, Any] = None, market: str = 'A股'):
    default_params = MARKET_PARAMS.get(market, MARKET_PARAMS['A股']).copy()
    # ... 其他参数合并逻辑
```

---

### 2. 潜在的未来数据泄露 (Look-ahead Bias)

**位置**: `strategies/ma_cross_strategy.py` - `generate_signals` 方法

**问题描述**:
```python
def generate_signals(self) -> Dict[str, Any]:
    fast_ma = self.fast_ma[0]  # 使用的是当前K线的MA值
    slow_ma = self.slow_ma[0]
```

在实盘交易中，当前K线收盘前无法确定MA值。若在盘中使用收盘价计算MA并生成信号，存在未来数据泄露。

**影响**: 回测结果过于乐观，实盘表现远低于预期

**改进建议**:
```python
def generate_signals(self) -> Dict[str, Any]:
    # 使用上一根K线的数据（lag 1）
    if len(self.fast_ma) < 2:
        return {'action': 'hold', 'strength': 0, 'reason': '数据不足'}
    
    fast_ma_prev = self.fast_ma[-1]  # 上一周期
    slow_ma_prev = self.slow_ma[-1]
    
    # 基于上一周期数据生成当前信号
```

---

### 3. 关键指标未定义/未初始化

**位置**: `strategies/ma_cross_strategy.py` - `__init__` 和 `generate_signals` 方法

**问题描述**:
```python
def generate_signals(self) -> Dict[str, Any]:
    trend_ok = not self.params_dict['use_trend_filter'] or \
        (hasattr(self, 'trend') and self.trend[0])
    volume_ok = not self.params_dict['use_volume_filter'] or \
        (hasattr(self, 'volume_ratio') and self.volume_ratio[0] > 1.0)
```

`self.trend`、`self.volume_ratio`、`self.crossover` 等关键指标在代码中未见定义/初始化。且使用 `hasattr` 静默处理缺失属性会导致逻辑错误。

**影响**: 运行时必然报错或产生错误信号

**改进建议**:
```python
def __init__(self, params: Dict[str, Any] = None):
    super().__init__(params)
    
    # 明确初始化指标
    self.fast_ma = bt.indicators.SMA(period=self.p.fast_period)
    self.slow_ma = bt.indicators.SMA(period=self.p.slow_period)
    self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
    
    if self.p.use_trend_filter:
        self.trend = bt.indicators.SMA(period=self.p.trend_period)
    
    if self.p.use_volume_filter:
        self.volume_ratio = bt.indicators.SMA(self.data.volume, period=20) / \
                           bt.indicators.SMA(self.data.volume, period=5)
```

---

### 4. 信号执行缺少 ATR 止损逻辑

**位置**: `strategies/ma_cross_strategy.py` - `generate_signals` 方法

**问题描述**:
代码中虽然定义了 ATR 止损参数：
```python
'use_atr_stop': True,
'atr_period': 14,
'atr_multiplier': 2.0
```

但在 `generate_signals` 方法中完全没有实现 ATR 止损逻辑。仅依赖金叉/死叉无法有效控制风险。

**影响**: 不符合策略设计文档的风险管理要求，可能导致大额亏损

**改进建议**:
```python
def generate_signals(self) -> Dict[str, Any]:
    # ... 现有逻辑 ...
    
    # ATR 止损检查
    if self.position.size > 0 and self.p.use_atr_stop:
        atr = self.atr[0] if hasattr(self, 'atr') else 0
        stop_price = self.position.price - self.p.atr_multiplier * atr
        
        if self.data.close[0] < stop_price:
            return {
                'action': 'sell', 
                'strength': 1.0, 
                'reason': f'ATR止损触发(价格{self.data.close[0]:.2f} < 止损线{stop_price:.2f})'
            }
```

---

## 📋 问题统计

| 问题级别 | 数量 | 状态 |
|---------|------|------|
| 严重 (Critical) | 4 | 待修复 |
| 中等 (Medium) | 7 | 待修复 |
| 轻微 (Low) | 4 | 建议修复 |

**总计**: 15 个问题

---

## 🎯 立即修复清单（上线前必须）

1. **按市场类型配置参数**，移除硬编码默认值
2. **正确初始化所有指标**（crossover、trend、volume_ratio、ATR）
3. **实现完整的 ATR 止损逻辑**
4. **添加数据长度充分性检查**（考虑所有指标周期）

---

## 📝 备注

**完整审查报告**: 包含在中等和轻微问题的详细分析，可在会话历史中找到。

**代码质量评分**:
- 功能完整性: 4/10
- 代码规范性: 6/10
- 架构合理性: 5/10
- 文档一致性: 3/10
- 风险控制: 2/10

**建议**: 在修复上述4个严重问题前，请勿将代码用于实盘交易。
