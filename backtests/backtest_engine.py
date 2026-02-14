"""
回测引擎模块
基于Backtrader的回测引擎
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import os
from datetime import datetime
from loguru import logger

from config.settings import TRADING, BACKTEST, SYSTEM, BACKTEST_RESULTS_DIR
from strategies.base_strategy import BaseStrategy, StrategyFactory
from utils.data_fetcher import DataFetcher
from utils.data_processor import DataProcessor
from utils.logger import log_performance


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_cash: float = None, commission: float = None):
        """
        初始化回测引擎
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
        """
        self.initial_cash = initial_cash or TRADING.INITIAL_CASH
        self.commission = commission or TRADING.COMMISSION
        
        # 数据获取和处理工具
        self.data_fetcher = DataFetcher(use_cache=SYSTEM.USE_CACHE)
        self.data_processor = DataProcessor()
        
        # 回测结果
        self.results = {}
        self.performance_metrics = {}
    
    def prepare_data(self, symbol: str, start_date: str, end_date: str,
                    frequency: str = "daily") -> pd.DataFrame:
        """
        准备回测数据
        
        Args:
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            处理后的数据
        """
        logger.info(f"准备回测数据: {symbol} ({start_date} 到 {end_date})")
        
        # 获取原始数据
        raw_data = self.data_fetcher.fetch_stock_data(
            symbol, start_date, end_date, frequency
        )
        
        # 处理数据
        processed_data = self.data_processor.process_raw_data(raw_data, symbol)
        
        return processed_data
    
    def create_cerebro(self) -> bt.Cerebro:
        """
        创建Backtrader引擎
        
        Returns:
            Cerebro实例
        """
        cerebro = bt.Cerebro()
        
        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)
        
        # 设置手续费
        cerebro.broker.setcommission(commission=self.commission)
        
        # 设置滑点
        cerebro.broker.set_slippage_perc(TRADING.SLIPPAGE)
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        return cerebro
    
    def run_backtest(self, strategy_type: str, params: Dict[str, Any],
                    symbol: str = None, start_date: str = None,
                    end_date: str = None, frequency: str = "daily") -> Dict[str, Any]:
        """
        运行单个策略回测
        
        Args:
            strategy_type: 策略类型
            params: 策略参数
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            回测结果
        """
        # 使用默认值
        symbol = symbol or TRADING.SYMBOL
        start_date = start_date or TRADING.BACKTEST_START_DATE
        end_date = end_date or TRADING.BACKTEST_END_DATE
        
        logger.info(f"开始回测: {strategy_type}")
        logger.info(f"参数: {params}")
        logger.info(f"品种: {symbol}, 时间: {start_date} 到 {end_date}")
        
        try:
            # 准备数据
            data_df = self.prepare_data(symbol, start_date, end_date, frequency)
            
            # 创建Backtrader数据源
            data = bt.feeds.PandasData(
                dataname=data_df,
                datetime=None,  # 使用索引作为日期
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=None
            )
            
            # 创建回测引擎
            cerebro = self.create_cerebro()
            
            # 添加数据
            cerebro.adddata(data)
            
            # 添加策略 - 使用策略类并传递参数
            strategy_class = StrategyFactory.get_strategy_class(strategy_type)
            cerebro.addstrategy(strategy_class, **params)
            
            # 运行回测
            logger.info(f"初始资金: {cerebro.broker.getvalue():.2f}")
            results = cerebro.run()
            
            # 获取回测结果
            strategy_result = results[0]
            
            # 提取分析结果
            performance = self._extract_performance_metrics(strategy_result)
            
            # 记录交易日志
            trade_logs = self._extract_trade_logs(strategy_result)
            
            # 保存结果
            result_key = f"{strategy_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.results[result_key] = {
                'strategy_type': strategy_type,
                'params': params,
                'performance': performance,
                'trade_logs': trade_logs,
                'final_value': cerebro.broker.getvalue(),
                'total_return': (cerebro.broker.getvalue() / self.initial_cash) - 1
            }
            
            # 记录性能
            self.performance_metrics[result_key] = performance
            
            # 输出性能报告
            log_performance(performance, f"{strategy_type}策略", params)
            
            # 保存详细结果到文件
            self._save_backtest_result(result_key)
            
            logger.info(f"回测完成: {strategy_type}")
            logger.info(f"最终资产: {cerebro.broker.getvalue():.2f}")
            logger.info(f"总收益率: {performance.get('total_return', 0):.2%}")
            
            return self.results[result_key]
            
        except Exception as e:
            logger.error(f"回测失败: {strategy_type}, 错误: {e}")
            raise
    
    def _extract_performance_metrics(self, strategy_result) -> Dict[str, Any]:
        """提取性能指标"""
        metrics = {}
        
        try:
            # 总收益率
            returns_analyzer = strategy_result.analyzers.returns.get_analysis()
            if 'rtot' in returns_analyzer:
                metrics['total_return'] = returns_analyzer['rtot']
            
            # 年化收益率
            if 'rnorm100' in returns_analyzer:
                metrics['annual_return'] = returns_analyzer['rnorm100'] / 100
            
            # 夏普比率
            sharpe_analyzer = strategy_result.analyzers.sharpe.get_analysis()
            if 'sharperatio' in sharpe_analyzer:
                metrics['sharpe_ratio'] = sharpe_analyzer['sharperatio']
            
            # 最大回撤
            drawdown_analyzer = strategy_result.analyzers.drawdown.get_analysis()
            if 'max' in drawdown_analyzer:
                metrics['max_drawdown'] = drawdown_analyzer['max'].drawdown
                metrics['max_drawdown_period'] = str(drawdown_analyzer['max'].len)
            
            # 交易分析
            trade_analyzer = strategy_result.analyzers.trades.get_analysis()
            
            # 总交易次数
            if 'total' in trade_analyzer:
                metrics['trades_count'] = trade_analyzer['total']['total']
                
                # 盈利交易
                if 'won' in trade_analyzer:
                    metrics['win_count'] = trade_analyzer['won']['total']
                    metrics['win_rate'] = trade_analyzer['won']['total'] / trade_analyzer['total']['total'] if trade_analyzer['total']['total'] > 0 else 0
                
                # 亏损交易
                if 'lost' in trade_analyzer:
                    metrics['loss_count'] = trade_analyzer['lost']['total']
                
                # 盈亏比
                if 'won' in trade_analyzer and 'lost' in trade_analyzer:
                    total_won = trade_analyzer['won']['pnl']['total']
                    total_lost = abs(trade_analyzer['lost']['pnl']['total'])
                    metrics['profit_factor'] = total_won / total_lost if total_lost > 0 else float('inf')
            
            # VWR（波动率调整收益率）
            vwr_analyzer = strategy_result.analyzers.vwr.get_analysis()
            if 'vwr' in vwr_analyzer:
                metrics['vwr'] = vwr_analyzer['vwr']
            
            # SQN（系统质量指标）
            sqn_analyzer = strategy_result.analyzers.sqn.get_analysis()
            if 'sqn' in sqn_analyzer:
                metrics['sqn'] = sqn_analyzer['sqn']
            
            # 从策略实例获取额外指标
            if hasattr(strategy_result, 'trade_count'):
                metrics['trade_count'] = strategy_result.trade_count
            
            if hasattr(strategy_result, 'win_count'):
                metrics['win_count'] = strategy_result.win_count
            
            if hasattr(strategy_result, 'loss_count'):
                metrics['loss_count'] = strategy_result.loss_count
            
            if hasattr(strategy_result, 'total_pnl'):
                metrics['total_pnl'] = strategy_result.total_pnl
        
        except Exception as e:
            logger.warning(f"提取性能指标失败: {e}")
        
        return metrics
    
    def _extract_trade_logs(self, strategy_result) -> pd.DataFrame:
        """提取交易日志"""
        try:
            if hasattr(strategy_result, 'log_entries') and strategy_result.log_entries:
                logs_df = pd.DataFrame(strategy_result.log_entries)
                
                # 转换日期列
                if 'datetime' in logs_df.columns:
                    logs_df['datetime'] = pd.to_datetime(logs_df['datetime'])
                
                return logs_df
            
            # 尝试从策略中获取交易日志
            if hasattr(strategy_result, 'get_trade_logs'):
                return strategy_result.get_trade_logs()
        
        except Exception as e:
            logger.warning(f"提取交易日志失败: {e}")
        
        return pd.DataFrame()
    
    def _save_backtest_result(self, result_key: str):
        """保存回测结果到文件"""
        try:
            result = self.results[result_key]
            
            # 创建结果目录
            os.makedirs(BACKTEST_RESULTS_DIR, exist_ok=True)
            
            # 保存性能指标
            perf_file = os.path.join(BACKTEST_RESULTS_DIR, f"{result_key}_performance.csv")
            perf_df = pd.DataFrame([result['performance']])
            perf_df.to_csv(perf_file, index=False)
            
            # 保存交易日志
            if not result['trade_logs'].empty:
                trade_file = os.path.join(BACKTEST_RESULTS_DIR, f"{result_key}_trades.csv")
                result['trade_logs'].to_csv(trade_file, index=False)
            
            # 保存汇总信息
            summary = {
                'strategy_type': result['strategy_type'],
                'params': str(result['params']),
                'final_value': result['final_value'],
                'total_return': result['total_return'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            summary_file = os.path.join(BACKTEST_RESULTS_DIR, f"{result_key}_summary.txt")
            with open(summary_file, 'w', encoding='utf-8') as f:
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")
            
            logger.info(f"回测结果已保存: {result_key}")
        
        except Exception as e:
            logger.warning(f"保存回测结果失败: {e}")
    
    def run_batch_backtest(self, strategies_config: List[Dict[str, Any]],
                          symbol: str = None, start_date: str = None,
                          end_date: str = None, frequency: str = "daily") -> Dict[str, Any]:
        """
        运行批量回测
        
        Args:
            strategies_config: 策略配置列表
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            批量回测结果
        """
        logger.info(f"开始批量回测，共 {len(strategies_config)} 个策略")
        
        batch_results = {}
        
        for i, config in enumerate(strategies_config, 1):
            strategy_type = config.get('strategy_type')
            params = config.get('params', {})
            
            logger.info(f"回测进度: {i}/{len(strategies_config)} - {strategy_type}")
            
            try:
                result = self.run_backtest(
                    strategy_type, params, symbol, start_date, end_date, frequency
                )
                
                batch_results[f"{strategy_type}_{i}"] = result
            
            except Exception as e:
                logger.error(f"策略 {strategy_type} 回测失败: {e}")
        
        # 比较策略性能
        comparison = self._compare_strategies(batch_results)
        
        # 保存批量回测结果
        self._save_batch_results(batch_results, comparison)
        
        logger.info(f"批量回测完成，共成功 {len(batch_results)} 个策略")
        
        return {
            'batch_results': batch_results,
            'comparison': comparison,
            'best_strategy': comparison.get('best_strategy')
        }
    
    def _compare_strategies(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """比较策略性能"""
        comparison = {
            'strategies': [],
            'metrics_summary': {},
            'best_strategy': None
        }
        
        try:
            best_score = -float('inf')
            best_strategy = None
            
            for key, result in batch_results.items():
                strategy_info = {
                    'key': key,
                    'strategy_type': result['strategy_type'],
                    'params': result['params'],
                    'performance': result['performance']
                }
                
                comparison['strategies'].append(strategy_info)
                
                # 计算综合得分
                score = self._calculate_strategy_score(result['performance'])
                strategy_info['score'] = score
                
                # 更新最佳策略
                if score > best_score:
                    best_score = score
                    best_strategy = strategy_info
            
            # 设置最佳策略
            if best_strategy:
                comparison['best_strategy'] = best_strategy
                
                logger.info(f"最佳策略: {best_strategy['strategy_type']}")
                logger.info(f"最佳参数: {best_strategy['params']}")
                logger.info(f"最佳得分: {best_score:.4f}")
            
            # 计算指标统计
            metrics_summary = {}
            for metric in ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']:
                values = []
                for strategy in comparison['strategies']:
                    if metric in strategy['performance']:
                        values.append(strategy['performance'][metric])
                
                if values:
                    metrics_summary[metric] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'min': np.min(values),
                        'max': np.max(values)
                    }
            
            comparison['metrics_summary'] = metrics_summary
        
        except Exception as e:
            logger.warning(f"策略比较失败: {e}")
        
        return comparison
    
    def _calculate_strategy_score(self, performance: Dict[str, Any]) -> float:
        """计算策略综合得分"""
        score = 0
        
        try:
            # 使用配置的权重
            for metric, weight in BACKTEST.METRIC_WEIGHTS.items():
                if metric in performance:
                    value = performance[metric]
                    
                    # 处理负权重（越小越好）
                    if weight < 0:
                        # 对于回撤等负向指标，取绝对值
                        if metric == 'max_drawdown':
                            value = abs(value)
                        else:
                            value = -value
                    
                    score += value * abs(weight)
        
        except Exception as e:
            logger.warning(f"计算策略得分失败: {e}")
        
        return score
    
    def _save_batch_results(self, batch_results: Dict[str, Any], comparison: Dict[str, Any]):
        """保存批量回测结果"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            batch_dir = os.path.join(BACKTEST_RESULTS_DIR, f"batch_{timestamp}")
            os.makedirs(batch_dir, exist_ok=True)
            
            # 保存每个策略的结果
            for key, result in batch_results.items():
                strategy_dir = os.path.join(batch_dir, key)
                os.makedirs(strategy_dir, exist_ok=True)
                
                # 保存性能指标
                perf_file = os.path.join(strategy_dir, "performance.csv")
                perf_df = pd.DataFrame([result['performance']])
                perf_df.to_csv(perf_file, index=False)
                
                # 保存参数
                param_file = os.path.join(strategy_dir, "params.txt")
                with open(param_file, 'w', encoding='utf-8') as f:
                    for param, value in result['params'].items():
                        f.write(f"{param}: {value}\n")
            
            # 保存比较结果
            comp_file = os.path.join(batch_dir, "comparison.csv")
            
            # 提取比较数据
            comp_data = []
            for strategy in comparison['strategies']:
                row = {
                    'strategy': strategy['strategy_type'],
                    'score': strategy['score']
                }
                
                # 添加性能指标
                for metric, value in strategy['performance'].items():
                    row[metric] = value
                
                comp_data.append(row)
            
            comp_df = pd.DataFrame(comp_data)
            comp_df.to_csv(comp_file, index=False)
            
            # 保存最佳策略信息
            if comparison['best_strategy']:
                best_file = os.path.join(batch_dir, "best_strategy.txt")
                with open(best_file, 'w', encoding='utf-8') as f:
                    best = comparison['best_strategy']
                    f.write(f"最佳策略: {best['strategy_type']}\n")
                    f.write(f"综合得分: {best['score']:.4f}\n")
                    f.write(f"参数配置:\n")
                    for param, value in best['params'].items():
                        f.write(f"  {param}: {value}\n")
                    f.write(f"性能指标:\n")
                    for metric, value in best['performance'].items():
                        f.write(f"  {metric}: {value}\n")
            
            logger.info(f"批量回测结果已保存: {batch_dir}")
        
        except Exception as e:
            logger.warning(f"保存批量回测结果失败: {e}")
    
    def get_best_strategy(self) -> Optional[Dict[str, Any]]:
        """获取最佳策略"""
        if not self.results:
            return None
        
        best_key = None
        best_score = -float('inf')
        
        for key, result in self.results.items():
            score = self._calculate_strategy_score(result['performance'])
            if score > best_score:
                best_score = score
                best_key = key
        
        if best_key:
            return self.results[best_key]
        
        return None


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试回测引擎
    print("测试回测引擎...")
    
    # 创建回测引擎
    engine = BacktestEngine()
    
    # 测试数据准备
    print("测试数据准备...")
    data = engine.prepare_data(
        symbol="000001.SH",
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    
    print(f"数据形状: {data.shape}")
    print(f"数据列: {data.columns.tolist()}")
    print(f"数据时间范围: {data.index[0]} 到 {data.index[-1]}")
    
    # 测试单个策略回测
    print("\n测试单个策略回测...")
    test_params = {
        'sma_period': 10,
        'lma_period': 30,
        'stop_loss_ratio': 0.05
    }
    
    try:
        result = engine.run_backtest(
            strategy_type='MA',
            params=test_params,
            symbol='000001.SH',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        
        print(f"回测成功!")
        print(f"总收益率: {result['total_return']:.2%}")
        print(f"交易次数: {result['performance'].get('trades_count', 0)}")
    
    except Exception as e:
        print(f"回测失败: {e}")
    
    print("\n回测引擎测试完成!")