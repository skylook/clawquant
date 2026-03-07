"""
风险管理模块
提供多种风险管理和资金管理算法
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger


class RiskManager:
    """风险管理器"""
    
    def __init__(self, initial_capital: float = 100000.0, max_position_size: float = 0.10):
        """
        初始化风险管理者
        
        Args:
            initial_capital: 初始资本
            max_position_size: 最大仓位比例（默认10%）
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_position_size = max_position_size
        self.max_drawdown = 0.20  # 最大回撤限制20%
        
        # 交易统计
        self.trades = []
        self.daily_returns = []
        self.portfolio_values = [initial_capital]
        
    def calculate_position_size(self, 
                              entry_price: float, 
                              stop_loss_price: float,
                              signal_strength: float = 1.0,
                              volatility: Optional[float] = None,
                              account_risk_pct: float = 0.02) -> tuple[int, Dict[str, float]]:
        """
        计算仓位大小（基于风险）
        
        Args:
            entry_price: 入场价格
            stop_loss_price: 止损价格
            signal_strength: 信号强度 (0-1)
            volatility: 波动率（如果提供，用于波动率调整）
            account_risk_pct: 账户风险百分比（默认2%）
            
        Returns:
            (股数, 风险详情)
        """
        # 计算风险金额（账户风险百分比）
        risk_amount = self.current_capital * account_risk_pct * signal_strength
        
        # 计算每单位的风险（入场价与止损价差）
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0:
            # 如果止损价无效，使用ATR或其他方法估计风险
            risk_per_share = entry_price * 0.02  # 默认2%的风险
        
        # 计算理论股数
        shares = risk_amount / risk_per_share
        
        # 应用最大仓位限制
        max_shares_by_capital = (self.current_capital * self.max_position_size) / entry_price
        shares = min(shares, max_shares_by_capital)
        
        # 考虑波动率调整（如果提供）
        if volatility and volatility > 0:
            # 波动率越高，仓位越小
            volatility_adjustment = max(0.5, min(1.5, 1.0 / (1.0 + volatility)))
            shares *= volatility_adjustment
        
        # 取整到百股（A股规则）或最小单位
        shares = int(shares / 100) * 100  # A股以100股为单位
        shares = max(shares, 100)  # 至少100股
        
        # 计算实际投入资金
        invested_amount = shares * entry_price
        
        risk_details = {
            'risk_amount': risk_amount,
            'risk_per_share': risk_per_share,
            'theoretical_shares': risk_amount / risk_per_share,
            'adjusted_shares': shares,
            'invested_amount': invested_amount,
            'capital_percentage': invested_amount / self.current_capital
        }
        
        return shares, risk_details
    
    def calculate_kelly_position_size(self, 
                                   win_rate: float, 
                                   avg_win: float, 
                                   avg_loss: float,
                                   kelly_fraction: float = 0.25) -> float:
        """
        使用凯利公式计算仓位大小
        
        Args:
            win_rate: 胜率
            avg_win: 平均盈利幅度
            avg_loss: 平均亏损幅度
            kelly_fraction: 凯利分数（通常使用1/4到1/2以降低风险）
            
        Returns:
            仓位比例
        """
        # 凯利公式: f = (bp - q) / b
        # b = 赔率 (平均盈利/平均亏损)
        # p = 胜率
        # q = 1 - 胜率
        
        if avg_loss == 0:
            return self.max_position_size
        
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p
        
        kelly_percentage = (b * p - q) / b
        
        # 应用凯利分数并限制在合理范围内
        adjusted_percentage = max(0, min(self.max_position_size, kelly_percentage * kelly_fraction))
        
        return adjusted_percentage
    
    def calculate_volatility_position_size(self,
                                        price: float,
                                        atr: float,
                                        volatility_target: float = 0.15,
                                        capital: float = None) -> int:
        """
        基于波动率的目标仓位计算
        
        Args:
            price: 当前价格
            atr: 平均真实波幅
            volatility_target: 波动率目标（年化15%）
            capital: 可用资金（如果不提供，使用当前资金）
            
        Returns:
            股票数量
        """
        if capital is None:
            capital = self.current_capital
        
        if atr <= 0:
            atr = price * 0.02  # 默认ATR
        
        # 计算基于ATR的头寸规模
        # 波动性越高，仓位越小
        atr_risk = price / atr
        position_value = (capital * volatility_target) / atr_risk
        
        # 计算股数
        shares = position_value / price
        shares = int(shares / 100) * 100  # 整百股
        shares = max(shares, 100)
        
        return shares
    
    def check_drawdown_limit(self, current_equity: float) -> bool:
        """
        检查是否超过最大回撤限制
        
        Args:
            current_equity: 当前权益
            
        Returns:
            是否允许继续交易
        """
        peak_equity = max(self.portfolio_values) if self.portfolio_values else self.initial_capital
        drawdown = (peak_equity - current_equity) / peak_equity
        
        return drawdown <= self.max_drawdown
    
    def update_portfolio_value(self, current_value: float):
        """更新投资组合价值"""
        self.current_capital = current_value
        self.portfolio_values.append(current_value)
        
        # 计算日收益率
        if len(self.portfolio_values) > 1:
            daily_return = (current_value - self.portfolio_values[-2]) / self.portfolio_values[-2]
            self.daily_returns.append(daily_return)
    
    def calculate_var(self, confidence_level: float = 0.95) -> float:
        """
        计算VaR（风险价值）
        
        Args:
            confidence_level: 置信水平
            
        Returns:
            VaR值
        """
        if len(self.daily_returns) < 30:
            return 0.0  # 数据不足
        
        # 计算分位数
        var_percentile = np.percentile(self.daily_returns, (1 - confidence_level) * 100)
        var_value = abs(var_percentile) * self.current_capital
        
        return var_value
    
    def calculate_max_position_for_var(self, var_limit: float, confidence_level: float = 0.95) -> float:
        """
        基于VaR限制计算最大仓位
        
        Args:
            var_limit: VaR限制
            confidence_level: 置信水平
            
        Returns:
            最大仓位比例
        """
        var_current = self.calculate_var(confidence_level)
        
        if var_current <= 0:
            return self.max_position_size
        
        # 计算应调整的比例
        adjustment_factor = var_limit / var_current
        max_position = min(self.max_position_size, adjustment_factor)
        
        return max_position
    
    def validate_trade(self, 
                      entry_price: float, 
                      stop_loss_price: float, 
                      take_profit_price: float,
                      direction: str = 'long') -> Dict[str, Any]:
        """
        验证交易的有效性
        
        Args:
            entry_price: 入场价格
            stop_loss_price: 止损价格
            take_profit_price: 止盈价格
            direction: 方向 ('long' 或 'short')
            
        Returns:
            验证结果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'risk_reward_ratio': 0.0
        }
        
        # 检查价格逻辑
        if direction == 'long':
            # 多头：止盈 > 入场 > 止损
            if take_profit_price <= entry_price:
                validation_result['valid'] = False
                validation_result['errors'].append(f"止盈价格({take_profit_price})必须大于入场价格({entry_price})")
            
            if entry_price <= stop_loss_price:
                validation_result['valid'] = False
                validation_result['errors'].append(f"入场价格({entry_price})必须大于止损价格({stop_loss_price})")
            
            # 计算风险回报比
            if entry_price != stop_loss_price:
                risk = abs(entry_price - stop_loss_price)
                reward = abs(take_profit_price - entry_price)
                validation_result['risk_reward_ratio'] = reward / risk
            else:
                validation_result['risk_reward_ratio'] = 0.0
                
        elif direction == 'short':
            # 空头：止盈 < 入场 < 止损
            if take_profit_price >= entry_price:
                validation_result['valid'] = False
                validation_result['errors'].append(f"止盈价格({take_profit_price})必须小于入场价格({entry_price})")
            
            if entry_price >= stop_loss_price:
                validation_result['valid'] = False
                validation_result['errors'].append(f"入场价格({entry_price})必须小于止损价格({stop_loss_price})")
            
            # 计算风险回报比
            if stop_loss_price != entry_price:
                risk = abs(stop_loss_price - entry_price)
                reward = abs(entry_price - take_profit_price)
                validation_result['risk_reward_ratio'] = reward / risk
            else:
                validation_result['risk_reward_ratio'] = 0.0
        
        # 检查风险回报比是否合理
        if validation_result['risk_reward_ratio'] < 1.0:
            validation_result['warnings'].append(f"风险回报比较低({validation_result['risk_reward_ratio']:.2f}:1)")
        
        # 检查最大回撤限制
        if not self.check_drawdown_limit(self.current_capital):
            validation_result['valid'] = False
            validation_result['errors'].append(f"超出最大回撤限制({self.max_drawdown*100:.1f}%)")
        
        return validation_result
    
    def get_risk_metrics(self) -> Dict[str, float]:
        """获取风险指标"""
        if len(self.daily_returns) < 2:
            return {
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'var_95': 0.0,
                'current_drawdown': 0.0
            }
        
        returns_array = np.array(self.daily_returns)
        
        # 波动率（年化）
        volatility = np.std(returns_array) * np.sqrt(252)
        
        # 夏普比率（假设无风险利率为3%）
        excess_return = np.mean(returns_array) * 252 - 0.03
        sharpe_ratio = excess_return / volatility if volatility != 0 else 0.0
        
        # 最大回撤
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        # 当前回撤
        if len(cumulative_returns) > 0:
            current_drawdown = abs(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
        else:
            current_drawdown = 0.0
        
        # VaR 95%
        var_95 = self.calculate_var(0.95)
        
        return {
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'var_95': var_95,
            'total_trades': len(self.trades)
        }


class PositionSizer:
    """仓位计算器"""
    
    @staticmethod
    def fixed_percentage_sizer(capital: float, percentage: float, price: float) -> int:
        """固定百分比仓位计算"""
        amount = capital * percentage
        shares = amount / price
        shares = int(shares / 100) * 100  # 整百股
        return max(shares, 100)
    
    @staticmethod
    def fixed_amount_sizer(capital: float, fixed_amount: float, price: float) -> int:
        """固定金额仓位计算"""
        shares = fixed_amount / price
        shares = int(shares / 100) * 100  # 整百股
        return max(shares, 100)
    
    @staticmethod
    def volatility_fixed_sizer(capital: float, price: float, atr: float, 
                             risk_per_share: float, max_percentage: float = 0.10) -> int:
        """基于波动率的固定风险仓位计算"""
        risk_amount = capital * max_percentage
        shares = risk_amount / risk_per_share
        shares = int(shares / 100) * 100
        return max(shares, 100)


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试风险管理器
    print("测试风险管理模块...")
    
    rm = RiskManager(initial_capital=100000, max_position_size=0.10)
    
    # 测试仓位计算
    entry_price = 100.0
    stop_loss_price = 95.0
    signal_strength = 0.8
    
    shares, risk_details = rm.calculate_position_size(
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        signal_strength=signal_strength
    )
    
    print(f"入场价格: {entry_price}")
    print(f"止损价格: {stop_loss_price}")
    print(f"建议股数: {shares}")
    print(f"风险详情: {risk_details}")
    
    # 测试凯利公式
    kelly_pct = rm.calculate_kelly_position_size(
        win_rate=0.6,
        avg_win=0.1,  # 10%平均盈利
        avg_loss=0.05  # 5%平均亏损
    )
    print(f"凯利仓位比例: {kelly_pct:.4f}")
    
    # 测试验证功能
    validation = rm.validate_trade(
        entry_price=100.0,
        stop_loss_price=95.0,
        take_profit_price=110.0,
        direction='long'
    )
    
    print(f"交易验证结果: {validation}")