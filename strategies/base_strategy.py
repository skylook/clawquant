"""
策略基类
所有量化策略的基类
"""

import backtrader as bt
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from loguru import logger

from config.settings import TRADING


class BaseStrategy(bt.Strategy):
    """策略基类"""
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化策略
        
        Args:
            params: 策略参数
        """
        super().__init__()
        
        # 策略参数
        self.params_dict = params or {}
        
        # 交易统计
        self.trade_count = 0
        self.win_count = 0
        self.loss_count = 0
        self.total_pnl = 0.0
        
        # 持仓状态
        self.position_size = 0
        self.entry_price = 0.0
        
        # 风险控制
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0
        
        # 指标缓存
        self.indicators = {}
        
        # 日志记录
        self.log_entries = []
        
        # 初始化策略
        self._init_strategy()
    
    def _validate_params(self):
        """验证策略参数合理性（子类可重写以添加特定验证）"""
        params = self.params_dict

        # 验证风险控制参数
        stop_loss = params.get('stop_loss_ratio', 0)
        if stop_loss < 0 or stop_loss > 1:
            logger.warning(f"stop_loss_ratio={stop_loss} 不在合理范围(0,1)，使用默认值")
            params['stop_loss_ratio'] = TRADING.STOP_LOSS_RATIO

        take_profit = params.get('take_profit_ratio', 0)
        if take_profit < 0 or take_profit > 10:
            logger.warning(f"take_profit_ratio={take_profit} 不在合理范围(0,10)，使用默认值")
            params['take_profit_ratio'] = TRADING.TAKE_PROFIT_RATIO

        max_pos = params.get('max_position_size', 0)
        if max_pos <= 0 or max_pos > 1:
            logger.warning(f"max_position_size={max_pos} 不在合理范围(0,1]，使用默认值")
            params['max_position_size'] = TRADING.MAX_POSITION_SIZE

        # 验证均线周期参数（通用）
        for fast_key, slow_key in [('fast_period', 'slow_period'), ('sma_period', 'lma_period'), ('sma_short', 'sma_long')]:
            if fast_key in params and slow_key in params:
                if params[fast_key] >= params[slow_key]:
                    logger.warning(f"{fast_key}={params[fast_key]} >= {slow_key}={params[slow_key]}，快线周期应小于慢线周期")

        # 验证ATR风险比例参数
        if 'atr_risk_pct' in params:
            atr_risk_pct = params['atr_risk_pct']
            if atr_risk_pct < 0.001 or atr_risk_pct > 0.1:
                logger.warning(f"atr_risk_pct={atr_risk_pct} 不在合理范围[0.001, 0.1]，使用默认值0.01")
                params['atr_risk_pct'] = 0.01

    def _init_strategy(self):
        """初始化策略（子类可以重写）"""
        # 验证参数
        self._validate_params()

        # 设置风险控制参数
        self.stop_loss_ratio = self.params_dict.get('stop_loss_ratio', TRADING.STOP_LOSS_RATIO)
        self.take_profit_ratio = self.params_dict.get('take_profit_ratio', TRADING.TAKE_PROFIT_RATIO)
        self.max_position_size = self.params_dict.get('max_position_size', TRADING.MAX_POSITION_SIZE)

        # ATR仓位管理参数
        self.use_atr_sizing = self.params_dict.get('use_atr_sizing', False)
        self.atr_risk_pct = self.params_dict.get('atr_risk_pct', 0.01)

        # 添加基础指标
        self._add_base_indicators()
    
    def _add_base_indicators(self):
        """添加基础指标"""
        # 简单移动平均线
        self.sma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, 
            period=self.params_dict.get('sma_short', 10)
        )
        
        self.sma_long = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params_dict.get('sma_long', 30)
        )
        
        # ATR（用于止损）
        self.atr = bt.indicators.ATR(self.data, period=14)
    
    def generate_signals(self):
        """
        生成交易信号（子类应该重写此方法）
        
        返回: 信号字典
            - 'action': 'buy', 'sell', 'hold'
            - 'strength': 信号强度 (0-1)
            - 'reason': 信号原因
        """
        # 默认返回持有信号
        return {'action': 'hold', 'strength': 0.0, 'reason': '未定义信号逻辑'}
    
    def next(self):
        """
        每个bar执行一次的策略逻辑
        """
        # 检查是否有持仓
        has_position = self.position.size != 0
        
        # 生成交易信号
        signals = self.generate_signals()
        
        if not signals:
            return
        
        action = signals.get('action', 'hold')
        strength = signals.get('strength', 0.5)
        reason = signals.get('reason', '')
        
        # 执行交易
        if action == 'buy' and not has_position:
            self._execute_buy(strength, reason)
        elif action == 'sell' and has_position:
            self._execute_sell(strength, reason)
        elif action == 'hold':
            self._monitor_position()
        
        # 检查止损止盈
        self._check_stop_loss_take_profit()
    
    def _execute_buy(self, strength: float, reason: str):
        """执行买入操作"""
        # 计算仓位大小（基于信号强度）
        position_size = self._calculate_position_size(strength)
        
        # 计算买入价格（考虑滑点）
        price = self.data.close[0] * (1 + TRADING.SLIPPAGE)
        
        # 执行买入
        self.buy(size=position_size)
        
        # 记录交易
        self.entry_price = price
        self.position_size = position_size
        
        # 设置止损止盈
        self._set_stop_loss_take_profit(price)
        
        # 记录日志
        self.log_trade('BUY', price, position_size, reason)
    
    def _execute_sell(self, strength: float, reason: str):
        """执行卖出操作"""
        # 计算卖出价格（考虑滑点）
        price = self.data.close[0] * (1 - TRADING.SLIPPAGE)
        
        # 执行卖出
        self.sell(size=self.position.size)
        
        # 保存卖出数量（在重置前）
        sold_size = self.position_size

        # 计算盈亏
        pnl = (price - self.entry_price) * sold_size
        self.total_pnl += pnl

        # 更新统计
        self.trade_count += 1
        if pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1

        # 重置持仓状态
        self.position_size = 0
        self.entry_price = 0.0
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0

        # 记录日志
        self.log_trade('SELL', price, sold_size, reason, pnl)
    
    def _calculate_atr_position_size(self, signal_strength: float) -> float:
        """
        ATR-based position sizing (turtle/van tharp style).

        Risk amount = account_value * atr_risk_pct * signal_strength
        Dollar risk per share = current ATR value
        Shares = risk_amount / atr_value, rounded down to nearest 100 (A-share lot size)

        Falls back to 2% of price when the ATR indicator is unavailable or zero.
        """
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.atr_risk_pct * signal_strength

        # Use ATR indicator if available
        if hasattr(self, 'atr') and self.atr is not None and len(self.atr) > 0:
            atr_val = self.atr[0]
        else:
            # Fallback: estimate ATR as 2% of price
            atr_val = self.data.close[0] * 0.02

        if atr_val <= 0:
            return 100  # minimum position

        position_size = risk_amount / atr_val
        position_size = int(position_size / 100) * 100  # A股100股单位
        return max(position_size, 100)

    def _calculate_position_size(self, signal_strength: float) -> float:
        """计算仓位大小，支持固定比例和ATR两种模式"""
        if self.use_atr_sizing:
            return self._calculate_atr_position_size(signal_strength)

        # 基于凯利公式的简化版本（固定比例模式）
        account_value = self.broker.getvalue()

        # 基础仓位（最大仓位 * 信号强度）
        base_size = account_value * self.max_position_size * signal_strength

        # 考虑风险调整
        risk_adjusted_size = base_size * (1 - self.stop_loss_ratio)

        # 转换为股票数量（假设股价为当前价格）
        price = self.data.close[0]
        position_size = risk_adjusted_size / price

        # 取整
        position_size = int(position_size / 100) * 100  # A股以100股为单位

        return max(position_size, 100)  # 至少100股
    
    def _set_stop_loss_take_profit(self, entry_price: float):
        """设置止损止盈价格"""
        self.stop_loss_price = entry_price * (1 - self.stop_loss_ratio)
        self.take_profit_price = entry_price * (1 + self.take_profit_ratio)
    
    def _check_stop_loss_take_profit(self):
        """检查止损止盈"""
        if self.position_size == 0:
            return
        
        current_price = self.data.close[0]
        
        # 检查止损
        if current_price <= self.stop_loss_price:
            self._execute_sell(1.0, '触发止损')
            return
        
        # 检查止盈
        if current_price >= self.take_profit_price:
            self._execute_sell(1.0, '触发止盈')
            return
    
    def _monitor_position(self):
        """监控持仓"""
        # 这里可以添加持仓监控逻辑
        # 例如：移动止损、分批止盈等
        pass
    
    def log_trade(self, action: str, price: float, size: float, 
                 reason: str, pnl: float = 0.0):
        """记录交易日志"""
        log_entry = {
            'datetime': self.data.datetime.datetime(),
            'action': action,
            'price': price,
            'size': size,
            'reason': reason,
            'pnl': pnl,
            'portfolio_value': self.broker.getvalue()
        }
        
        self.log_entries.append(log_entry)
        
        # 输出到控制台
        logger.info(f"{log_entry['datetime']} | {action} | "
                   f"价格: {price:.2f} | 数量: {size} | "
                   f"原因: {reason} | 盈亏: {pnl:.2f}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        # 基础指标
        total_return = self.broker.getvalue() / TRADING.INITIAL_CASH - 1
        
        # 计算年化收益率
        days = len(self.data) / 252  # 假设252个交易日
        annual_return = (1 + total_return) ** (1 / days) - 1 if days > 0 else 0
        
        # 计算胜率
        win_rate = self.win_count / self.trade_count if self.trade_count > 0 else 0
        
        # 计算平均盈亏比
        # 这里简化处理，实际需要更复杂的计算
        
        metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'trade_count': self.trade_count,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'final_portfolio_value': self.broker.getvalue()
        }
        
        return metrics
    
    def get_trade_logs(self) -> pd.DataFrame:
        """获取交易日志"""
        return pd.DataFrame(self.log_entries)
    
    def notify_trade(self, trade):
        """交易通知（backtrader回调）"""
        if trade.isclosed:
            logger.info(f"交易关闭: 盈亏 = {trade.pnl:.2f}, 佣金 = {trade.commission:.2f}")
    
    def notify_order(self, order):
        """订单通知（backtrader回调）"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受
            return
        
        if order.status in [order.Completed]:
            # 订单完成
            if order.isbuy():
                logger.info(f"买入完成: 价格 = {order.executed.price:.2f}, "
                           f"数量 = {order.executed.size}, 成本 = {order.executed.value:.2f}, "
                           f"佣金 = {order.executed.comm:.2f}")
            else:  # Sell
                logger.info(f"卖出完成: 价格 = {order.executed.price:.2f}, "
                           f"数量 = {order.executed.size}, 成本 = {order.executed.value:.2f}, "
                           f"佣金 = {order.executed.comm:.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单取消/保证金不足/被拒绝
            logger.warning(f"订单状态: {order.getstatusname()}")
    
    def stop(self):
        """策略停止时调用"""
        logger.info(f"策略运行结束")
        logger.info(f"最终资产: {self.broker.getvalue():.2f}")
        logger.info(f"总交易次数: {self.trade_count}")
        logger.info(f"盈利次数: {self.win_count}, 亏损次数: {self.loss_count}")
        logger.info(f"总盈亏: {self.total_pnl:.2f}")


class StrategyFactory:
    """策略工厂"""
    
    STRATEGY_MAP = {
        'MA': 'strategies.ma_strategy.MAStrategy',
        'MACD': 'strategies.macd_strategy.MACDStrategy',
        'RSI': 'strategies.rsi_strategy.RSIStrategy',
        'BOLL': 'strategies.bollinger_strategy.BollingerStrategy',
        'MA_CROSS': 'strategies.ma_cross_strategy.MACrossStrategy',
        'TRIPLE_MA': 'strategies.triple_ma_strategy.TripleMAStrategy',
        'DUAL_THRUST': 'strategies.dual_thrust_strategy.DualThrustStrategy',
        'KAMA': 'strategies.kama_strategy.KAMAStrategy',
        'TURTLE': 'strategies.turtle_strategy.TurtleStrategy',
    }
    
    @staticmethod
    def get_strategy_class(strategy_type: str):
        """
        获取策略类（用于backtrader addstrategy）
        
        Args:
            strategy_type: 策略类型
            
        Returns:
            策略类
        """
        if strategy_type == 'MA':
            from strategies.ma_strategy import MAStrategy
            return MAStrategy
        elif strategy_type == 'MACD':
            from strategies.macd_strategy import MACDStrategy
            return MACDStrategy
        elif strategy_type == 'RSI':
            from strategies.rsi_strategy import RSIStrategy
            return RSIStrategy
        elif strategy_type == 'BOLL':
            from strategies.bollinger_strategy import BollingerStrategy
            return BollingerStrategy
        elif strategy_type == 'MA_CROSS':
            from strategies.ma_cross_strategy import MACrossStrategy
            return MACrossStrategy
        elif strategy_type == 'TRIPLE_MA':
            from strategies.triple_ma_strategy import TripleMAStrategy
            return TripleMAStrategy
        elif strategy_type == 'DUAL_THRUST':
            from strategies.dual_thrust_strategy import DualThrustStrategy
            return DualThrustStrategy
        elif strategy_type == 'KAMA':
            from strategies.kama_strategy import KAMAStrategy
            return KAMAStrategy
        elif strategy_type == 'TURTLE':
            from strategies.turtle_strategy import TurtleStrategy
            return TurtleStrategy
        else:
            raise ValueError(f"未知的策略类型: {strategy_type}")
    
    @staticmethod
    def create_strategy(strategy_type: str, params: Dict[str, Any] = None) -> BaseStrategy:
        """
        创建策略实例（用于测试）
        
        Args:
            strategy_type: 策略类型
            params: 策略参数
            
        Returns:
            策略实例
        """
        strategy_class = StrategyFactory.get_strategy_class(strategy_type)
        return strategy_class(params)
    
    @staticmethod
    def get_available_strategies() -> List[str]:
        """获取可用的策略类型"""
        return ['MA', 'MACD', 'RSI', 'BOLL', 'MA_CROSS', 'TRIPLE_MA', 'DUAL_THRUST', 'KAMA', 'TURTLE']
    
    @staticmethod
    def get_default_params(strategy_type: str) -> Dict[str, Any]:
        """获取策略的默认参数"""
        default_params = {
            'MA': {
                'sma_period': 20,
                'lma_period': 60,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.10
            },
            'MACD': {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.10
            },
            'RSI': {
                'rsi_period': 14,
                'overbought': 70,
                'oversold': 30,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.10
            },
            'BOLL': {
                'period': 20,
                'devfactor': 2.0,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.10
            },
            'MA_CROSS': {
                'fast_period': 10,
                'slow_period': 30,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.10
            },
            'TRIPLE_MA': {
                'fast_period': 5,
                'mid_period': 20,
                'slow_period': 70,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.10
            },
            'DUAL_THRUST': {
                'lookback': 5,
                'k1': 0.5,
                'k2': 0.5,
                'use_atr_stop': True,
                'atr_period': 14,
                'atr_multiplier': 2.0,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.15,
                'max_position_size': 0.8,
            },
            'TURTLE': {
                'entry_period': 20,
                'exit_period': 10,
                'atr_period': 20,
                'risk_per_unit': 0.01,
                'use_pyramiding': False,
                'max_units': 4,
                'stop_loss_atr_multiplier': 2.0,
                'stop_loss_ratio': 0.05,
                'take_profit_ratio': 0.20,
                'max_position_size': 0.8,
            },
            'KAMA': {
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
        }
        
        return default_params.get(strategy_type, {})


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试策略基类
    print("测试策略基类...")
    
    # 创建模拟数据
    data = bt.feeds.PandasData(
        dataname=pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [105, 106, 107, 108, 109],
            'low': [95, 96, 97, 98, 99],
            'close': [102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
    )
    
    # 创建策略实例
    strategy = BaseStrategy(params={'sma_short': 5, 'sma_long': 10})
    
    print(f"策略类型: {type(strategy).__name__}")
    print(f"策略参数: {strategy.params_dict}")
    
    # 测试策略工厂
    print("\n测试策略工厂...")
    available = StrategyFactory.get_available_strategies()
    print(f"可用策略: {available}")
    
    for strategy_type in available[:2]:  # 只测试前两种
        default_params = StrategyFactory.get_default_params(strategy_type)
        print(f"{strategy_type} 默认参数: {default_params}")