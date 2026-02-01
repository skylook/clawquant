"""
策略优化器模块
用于优化策略参数
"""

import itertools
import random
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from config.settings import STRATEGY, BACKTEST_RESULTS_DIR, OPTIMIZATION_RESULTS_DIR
from backtests.backtest_engine import BacktestEngine
from utils.logger import log_optimization_result


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self, backtest_engine: BacktestEngine = None):
        """
        初始化策略优化器
        
        Args:
            backtest_engine: 回测引擎实例
        """
        self.backtest_engine = backtest_engine or BacktestEngine()
        self.optimization_results = {}
    
    def grid_search(self, strategy_type: str, param_grid: Dict[str, List],
                   symbol: str = None, start_date: str = None,
                   end_date: str = None, max_iterations: int = None) -> Dict[str, Any]:
        """
        网格搜索优化
        
        Args:
            strategy_type: 策略类型
            param_grid: 参数网格
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            max_iterations: 最大迭代次数
            
        Returns:
            优化结果
        """
        logger.info(f"开始网格搜索优化: {strategy_type}")
        logger.info(f"参数网格: {param_grid}")
        
        # 计算总组合数
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        total_combinations = np.prod([len(vals) for vals in param_values])
        
        # 限制最大迭代次数
        if max_iterations is None:
            max_iterations = STRATEGY.MAX_OPTIMIZATION_ITERATIONS
        
        if total_combinations > max_iterations:
            logger.warning(f"总组合数 {total_combinations} 超过最大迭代次数 {max_iterations}")
            logger.info(f"将进行随机采样")
            return self.random_search(strategy_type, param_grid, symbol, start_date, end_date, max_iterations)
        
        # 生成所有参数组合
        all_combinations = list(itertools.product(*param_values))
        
        # 运行优化
        results = self._evaluate_parameter_combinations(
            strategy_type, param_names, all_combinations,
            symbol, start_date, end_date
        )
        
        # 分析结果
        optimization_result = self._analyze_optimization_results(
            strategy_type, param_names, results
        )
        
        # 保存结果
        self._save_optimization_result(strategy_type, optimization_result)
        
        return optimization_result
    
    def random_search(self, strategy_type: str, param_grid: Dict[str, List],
                     symbol: str = None, start_date: str = None,
                     end_date: str = None, max_iterations: int = None) -> Dict[str, Any]:
        """
        随机搜索优化
        
        Args:
            strategy_type: 策略类型
            param_grid: 参数网格
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            max_iterations: 最大迭代次数
            
        Returns:
            优化结果
        """
        logger.info(f"开始随机搜索优化: {strategy_type}")
        
        if max_iterations is None:
            max_iterations = STRATEGY.MAX_OPTIMIZATION_ITERATIONS
        
        param_names = list(param_grid.keys())
        
        # 生成随机参数组合
        random_combinations = []
        for _ in range(max_iterations):
            combination = []
            for param_name in param_names:
                values = param_grid[param_name]
                combination.append(random.choice(values))
            random_combinations.append(combination)
        
        # 运行优化
        results = self._evaluate_parameter_combinations(
            strategy_type, param_names, random_combinations,
            symbol, start_date, end_date
        )
        
        # 分析结果
        optimization_result = self._analyze_optimization_results(
            strategy_type, param_names, results
        )
        
        # 保存结果
        self._save_optimization_result(strategy_type, optimization_result)
        
        return optimization_result
    
    def _evaluate_parameter_combinations(self, strategy_type: str,
                                        param_names: List[str],
                                        combinations: List[Tuple],
                                        symbol: str, start_date: str,
                                        end_date: str) -> List[Dict[str, Any]]:
        """
        评估参数组合
        
        Args:
            strategy_type: 策略类型
            param_names: 参数名称列表
            combinations: 参数组合列表
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            评估结果列表
        """
        results = []
        total_combinations = len(combinations)
        
        logger.info(f"开始评估 {total_combinations} 个参数组合")
        
        for i, combination in enumerate(combinations, 1):
            # 创建参数字典
            params = dict(zip(param_names, combination))
            
            logger.info(f"评估进度: {i}/{total_combinations}")
            logger.info(f"参数: {params}")
            
            try:
                # 运行回测
                result = self.backtest_engine.run_backtest(
                    strategy_type=strategy_type,
                    params=params,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # 计算综合得分
                score = self.backtest_engine._calculate_strategy_score(result['performance'])
                
                # 保存结果
                eval_result = {
                    'params': params,
                    'performance': result['performance'],
                    'score': score,
                    'total_return': result['total_return'],
                    'final_value': result['final_value']
                }
                
                results.append(eval_result)
                
                logger.info(f"评估完成，得分: {score:.4f}")
            
            except Exception as e:
                logger.error(f"参数组合评估失败: {params}, 错误: {e}")
        
        return results
    
    def _analyze_optimization_results(self, strategy_type: str,
                                     param_names: List[str],
                                     results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析优化结果
        
        Args:
            strategy_type: 策略类型
            param_names: 参数名称列表
            results: 评估结果列表
            
        Returns:
            优化分析结果
        """
        if not results:
            logger.warning("没有有效的优化结果")
            return {}
        
        # 提取分数
        scores = [result['score'] for result in results]
        
        # 找到最佳结果
        best_idx = np.argmax(scores)
        best_result = results[best_idx]
        
        # 分析参数敏感性
        param_sensitivity = self._analyze_parameter_sensitivity(param_names, results)
        
        # 创建优化结果
        optimization_result = {
            'strategy_type': strategy_type,
            'best_params': best_result['params'],
            'best_score': best_result['score'],
            'best_performance': best_result['performance'],
            'total_results': len(results),
            'score_stats': {
                'mean': np.mean(scores),
                'std': np.std(scores),
                'min': np.min(scores),
                'max': np.max(scores)
            },
            'param_sensitivity': param_sensitivity,
            'all_results': results
        }
        
        # 记录优化结果
        log_optimization_result(
            best_params=best_result['params'],
            best_score=best_result['score'],
            strategy_name=f"{strategy_type}策略",
            iteration=len(results)
        )
        
        logger.info(f"优化完成，找到最佳参数: {best_result['params']}")
        logger.info(f"最佳得分: {best_result['score']:.4f}")
        
        return optimization_result
    
    def _analyze_parameter_sensitivity(self, param_names: List[str],
                                      results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析参数敏感性
        
        Args:
            param_names: 参数名称列表
            results: 评估结果列表
            
        Returns:
            参数敏感性分析
        """
        sensitivity = {}
        
        for param_name in param_names:
            # 按参数值分组
            param_values = {}
            
            for result in results:
                param_value = result['params'][param_name]
                score = result['score']
                
                if param_value not in param_values:
                    param_values[param_value] = []
                
                param_values[param_value].append(score)
            
            # 计算每个参数值的平均得分
            value_stats = {}
            for value, scores in param_values.items():
                value_stats[value] = {
                    'mean_score': np.mean(scores),
                    'std_score': np.std(scores),
                    'count': len(scores)
                }
            
            # 找到最佳参数值
            best_value = None
            best_score = -float('inf')
            
            for value, stats in value_stats.items():
                if stats['mean_score'] > best_score:
                    best_score = stats['mean_score']
                    best_value = value
            
            sensitivity[param_name] = {
                'value_stats': value_stats,
                'best_value': best_value,
                'best_score': best_score,
                'sensitivity': len(value_stats) > 1  # 是否对参数敏感
            }
        
        return sensitivity
    
    def _save_optimization_result(self, strategy_type: str,
                                 optimization_result: Dict[str, Any]):
        """
        保存优化结果
        
        Args:
            strategy_type: 策略类型
            optimization_result: 优化结果
        """
        try:
            # 创建优化结果目录
            os.makedirs(OPTIMIZATION_RESULTS_DIR, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_dir = os.path.join(OPTIMIZATION_RESULTS_DIR, f"{strategy_type}_{timestamp}")
            os.makedirs(result_dir, exist_ok=True)
            
            # 保存最佳参数
            best_params = optimization_result['best_params']
            param_file = os.path.join(result_dir, "best_params.txt")
            
            with open(param_file, 'w', encoding='utf-8') as f:
                f.write(f"策略类型: {strategy_type}\n")
                f.write(f"优化时间: {timestamp}\n")
                f.write(f"最佳得分: {optimization_result['best_score']:.4f}\n")
                f.write(f"最佳参数:\n")
                for param, value in best_params.items():
                    f.write(f"  {param}: {value}\n")
            
            # 保存性能指标
            perf_file = os.path.join(result_dir, "best_performance.csv")
            perf_df = pd.DataFrame([optimization_result['best_performance']])
            perf_df.to_csv(perf_file, index=False)
            
            # 保存所有结果
            all_results = optimization_result['all_results']
            if all_results:
                # 提取关键信息
                results_data = []
                for result in all_results:
                    row = {
                        'score': result['score'],
                        'total_return': result['total_return']
                    }
                    
                    # 添加参数
                    for param, value in result['params'].items():
                        row[param] = value
                    
                    # 添加性能指标
                    for metric, value in result['performance'].items():
                        if metric not in row:  # 避免重复
                            row[metric] = value
                    
                    results_data.append(row)
                
                results_df = pd.DataFrame(results_data)
                results_file = os.path.join(result_dir, "all_results.csv")
                results_df.to_csv(results_file, index=False)
            
            # 保存参数敏感性分析
            sensitivity = optimization_result['param_sensitivity']
            if sensitivity:
                sens_file = os.path.join(result_dir, "parameter_sensitivity.txt")
                
                with open(sens_file, 'w', encoding='utf-8') as f:
                    f.write("参数敏感性分析:\n")
                    f.write("=" * 50 + "\n")
                    
                    for param_name, sens_info in sensitivity.items():
                        f.write(f"\n参数: {param_name}\n")
                        f.write(f"最佳值: {sens_info['best_value']}\n")
                        f.write(f"最佳得分: {sens_info['best_score']:.4f}\n")
                        f.write(f"是否敏感: {'是' if sens_info['sensitivity'] else '否'}\n")
                        
                        if sens_info['value_stats']:
                            f.write("各值表现:\n")
                            for value, stats in sens_info['value_stats'].items():
                                f.write(f"  {value}: 平均得分={stats['mean_score']:.4f}, "
                                       f"标准差={stats['std_score']:.4f}, "
                                       f"样本数={stats['count']}\n")
            
            # 保存到优化结果字典
            result_key = f"{strategy_type}_{timestamp}"
            self.optimization_results[result_key] = optimization_result
            
            logger.info(f"优化结果已保存: {result_dir}")
        
        except Exception as e:
            logger.warning(f"保存优化结果失败: {e}")
    
    def optimize_multiple_strategies(self, strategies_config: List[Dict[str, Any]],
                                    symbol: str = None, start_date: str = None,
                                    end_date: str = None) -> Dict[str, Any]:
        """
        优化多个策略
        
        Args:
            strategies_config: 策略配置列表
            symbol: 交易品种
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            多策略优化结果
        """
        logger.info(f"开始优化多个策略，共 {len(strategies_config)} 个策略")
        
        all_optimization_results = {}
        
        for i, config in enumerate(strategies_config, 1):
            strategy_type = config.get('strategy_type')
            param_grid = config.get('param_grid', {})
            optimization_method = config.get('method', 'grid_search')
            max_iterations = config.get('max_iterations')
            
            logger.info(f"优化进度: {i}/{len(strategies_config)} - {strategy_type}")
            
            try:
                if optimization_method == 'grid_search':
                    result = self.grid_search(
                        strategy_type, param_grid, symbol, start_date, end_date, max_iterations
                    )
                elif optimization_method == 'random_search':
                    result = self.random_search(
                        strategy_type, param_grid, symbol, start_date, end_date, max_iterations
                    )
                else:
                    logger.warning(f"未知的优化方法: {optimization_method}，使用网格搜索")
                    result = self.grid_search(
                        strategy_type, param_grid, symbol, start_date, end_date, max_iterations
                    )
                
                all_optimization_results[strategy_type] = result
            
            except Exception as e:
                logger.error(f"策略 {strategy_type} 优化失败: {e}")
        
        # 比较不同策略的优化结果
        strategy_comparison = self._compare_optimized_strategies(all_optimization_results)
        
        # 保存多策略优化结果
        self._save_multi_strategy_results(all_optimization_results, strategy_comparison)
        
        logger.info(f"多策略优化完成，共成功 {len(all_optimization_results)} 个策略")
        
        return {
            'optimization_results': all_optimization_results,
            'strategy_comparison': strategy_comparison,
            'best_strategy_overall': strategy_comparison.get('best_strategy')
        }
    
    def _compare_optimized_strategies(self, optimization_results: Dict[str, Any]) -> Dict[str, Any]:
        """比较优化后的策略"""
        comparison = {
            'strategies': [],
            'best_strategy': None
        }
        
        try:
            best_score = -float('inf')
            best_strategy = None
            
            for strategy_type, result in optimization_results.items():
                strategy_info = {
                    'strategy_type': strategy_type,
                    'best_params': result['best_params'],
                    'best_score': result['best_score'],
                    'best_performance': result['best_performance']
                }
                
                comparison['strategies'].append(strategy_info)
                
                # 更新最佳策略
                if result['best_score'] > best_score:
                    best_score = result['best_score']
                    best_strategy = strategy_info
            
            # 设置最佳策略
            if best_strategy:
                comparison['best_strategy'] = best_strategy
                
                logger.info(f"总体最佳策略: {best_strategy['strategy_type']}")
                logger.info(f"最佳参数: {best_strategy['best_params']}")
                logger.info(f"最佳得分: {best_score:.4f}")
        
        except Exception as e:
            logger.warning(f"策略比较失败: {e}")
        
        return comparison
    
    def _save_multi_strategy_results(self, optimization_results: Dict[str, Any],
                                    strategy_comparison: Dict[str, Any]):
        """保存多策略优化结果"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            multi_dir = os.path.join(OPTIMIZATION_RESULTS_DIR, f"multi_strategy_{timestamp}")
            os.makedirs(multi_dir, exist_ok=True)
            
            # 保存每个策略的优化结果
            for strategy_type, result in optimization_results.items():
                strategy_dir = os.path.join(multi_dir, strategy_type)
                os.makedirs(strategy_dir, exist_ok=True)
                
                # 保存最佳参数
                param_file = os.path.join(strategy_dir, "best_params.txt")
                with open(param_file, 'w', encoding='utf-8') as f:
                    f.write(f"策略类型: {strategy_type}\n")
                    f.write(f"最佳得分: {result['best_score']:.4f}\n")
                    f.write(f"最佳参数:\n")
                    for param, value in result['best_params'].items():
                        f.write(f"  {param}: {value}\n")
            
            # 保存策略比较结果
            if strategy_comparison['strategies']:
                comp_file = os.path.join(multi_dir, "strategy_comparison.csv")
                
                comp_data = []
                for strategy in strategy_comparison['strategies']:
                    row = {
                        'strategy_type': strategy['strategy_type'],
                        'best_score': strategy['best_score']
                    }
                    
                    # 添加性能指标
                    for metric, value in strategy['best_performance'].items():
                        row[metric] = value
                    
                    comp_data.append(row)
                
                comp_df = pd.DataFrame(comp_data)
                comp_df.to_csv(comp_file, index=False)
            
            # 保存总体最佳策略
            if strategy_comparison['best_strategy']:
                best_strategy = strategy_comparison['best_strategy']
                best_file = os.path.join(multi_dir, "best_strategy_overall.txt")
                
                with open(best_file, 'w', encoding='utf-8') as f:
                    f.write(f"总体最佳策略: {best_strategy['strategy_type']}\n")
                    f.write(f"最佳得分: {best_strategy['best_score']:.4f}\n")
                    f.write(f"最佳参数:\n")
                    for param, value in best_strategy['best_params'].items():
                        f.write(f"  {param}: {value}\n")
                    f.write(f"性能指标:\n")
                    for metric, value in best_strategy['best_performance'].items():
                        f.write(f"  {metric}: {value}\n")
            
            logger.info(f"多策略优化结果已保存: {multi_dir}")
        
        except Exception as e:
            logger.warning(f"保存多策略优化结果失败: {e}")
    
    def get_best_optimized_strategy(self) -> Optional[Dict[str, Any]]:
        """获取最佳优化策略"""
        if not self.optimization_results:
            return None
        
        best_key = None
        best_score = -float('inf')
        
        for key, result in self.optimization_results.items():
            if result['best_score'] > best_score:
                best_score = result['best_score']
                best_key = key
        
        if best_key:
            return self.optimization_results[best_key]
        
        return None


# ========== 使用示例 ==========
if __name__ == "__main__":
    import os
    
    # 测试优化器
    print("测试策略优化器...")
    
    # 创建优化器
    optimizer = StrategyOptimizer()
    
    # 测试参数网格
    param_grid = {
        'sma_period': [5, 10, 20],
        'lma_period': [20, 30, 60],
        'stop_loss_ratio': [0.03, 0.05]
    }
    
    print(f"参数网格: {param_grid}")
    print(f"总组合数: {len(list(itertools.product(*param_grid.values())))}")
    
    # 测试网格搜索（小规模）
    print("\n测试网格搜索优化...")
    
    try:
        result = optimizer.grid_search(
            strategy_type='MA',
            param_grid=param_grid,
            symbol='000001.SH',
            start_date='2023-01-01',
            end_date='2023-12-31',
            max_iterations=10  # 限制迭代次数
        )
        
        if result:
            print(f"优化完成!")
            print(f"最佳参数: {result['best_params']}")
            print(f"最佳得分: {result['best_score']:.4f}")
            print(f"总结果数: {result['total_results']}")
    
    except Exception as e:
        print(f"优化失败: {e}")
    
    print("\n优化器测试完成!")