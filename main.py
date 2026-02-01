"""
ClawQuant 量化交易系统主程序
自动生成、回测、优化和选择最佳策略
"""

import os
import sys
import argparse
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    TRADING, STRATEGY, BACKTEST, SYSTEM,
    PROJECT_ROOT, print_config_summary
)
from config.strategy_config import STRATEGY_FACTORY
from utils.data_fetcher import DataFetcher
from utils.data_processor import DataProcessor
from utils.logger import setup_logger, log_performance, log_optimization_result
from backtests.backtest_engine import BacktestEngine
from backtests.optimizer import StrategyOptimizer
from backtests.analyzer import BacktestAnalyzer


class ClawQuant:
    """ClawQuant量化交易系统主类"""
    
    def __init__(self, mode: str = "full"):
        """
        初始化ClawQuant系统
        
        Args:
            mode: 运行模式 (full, backtest, optimize, analyze)
        """
        self.mode = mode
        
        # 初始化日志
        self.logger = setup_logger()
        
        # 初始化组件
        self.data_fetcher = DataFetcher(use_cache=SYSTEM.USE_CACHE)
        self.data_processor = DataProcessor()
        self.backtest_engine = BacktestEngine()
        self.optimizer = StrategyOptimizer(self.backtest_engine)
        self.analyzer = BacktestAnalyzer()
        
        # 运行结果
        self.results = {}
        self.optimization_results = {}
        self.best_strategy = None
        
        self.logger.info(f"ClawQuant 量化交易系统初始化完成")
        self.logger.info(f"运行模式: {mode}")
    
    def prepare_data(self) -> Dict[str, Any]:
        """准备数据"""
        self.logger.info("开始准备数据...")
        
        try:
            # 获取数据
            data = self.data_fetcher.fetch_stock_data(
                symbol=TRADING.SYMBOL,
                start_date=TRADING.BACKTEST_START_DATE,
                end_date=TRADING.BACKTEST_END_DATE,
                frequency=TRADING.FREQUENCY
            )
            
            # 处理数据
            processed_data = self.data_processor.process_raw_data(data, TRADING.SYMBOL)
            
            self.logger.info(f"数据准备完成，共 {len(processed_data)} 条记录")
            
            return {
                'raw_data': data,
                'processed_data': processed_data,
                'symbol': TRADING.SYMBOL,
                'start_date': TRADING.BACKTEST_START_DATE,
                'end_date': TRADING.BACKTEST_END_DATE
            }
        
        except Exception as e:
            self.logger.error(f"数据准备失败: {e}")
            raise
    
    def generate_strategies(self) -> List[Dict[str, Any]]:
        """生成策略配置"""
        self.logger.info("生成策略配置...")
        
        strategies = []
        
        # 获取所有策略类型
        strategy_types = STRATEGY.STRATEGY_TYPES
        
        for strategy_type in strategy_types:
            # 获取默认参数
            default_params = STRATEGY_FACTORY.get_all_strategies().get(strategy_type)
            
            if default_params:
                strategy_config = {
                    'strategy_type': strategy_type,
                    'params': default_params.params,
                    'description': default_params.description
                }
                strategies.append(strategy_config)
                
                self.logger.info(f"生成策略: {strategy_type}")
                self.logger.info(f"  描述: {default_params.description}")
                self.logger.info(f"  参数: {default_params.params}")
        
        self.logger.info(f"共生成 {len(strategies)} 个策略配置")
        
        return strategies
    
    def run_backtests(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行批量回测"""
        self.logger.info("开始批量回测...")
        
        # 准备回测配置
        backtest_configs = []
        for strategy in strategies:
            config = {
                'strategy_type': strategy['strategy_type'],
                'params': strategy['params']
            }
            backtest_configs.append(config)
        
        # 运行批量回测
        batch_results = self.backtest_engine.run_batch_backtest(
            strategies_config=backtest_configs,
            symbol=TRADING.SYMBOL,
            start_date=TRADING.BACKTEST_START_DATE,
            end_date=TRADING.BACKTEST_END_DATE,
            frequency=TRADING.FREQUENCY
        )
        
        self.results = batch_results
        
        self.logger.info(f"批量回测完成，共 {len(batch_results['batch_results'])} 个策略")
        
        return batch_results
    
    def optimize_strategies(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """优化策略参数"""
        self.logger.info("开始策略优化...")
        
        # 准备优化配置
        optimization_configs = []
        
        for strategy in strategies:
            strategy_type = strategy['strategy_type']
            
            # 获取参数网格
            param_grids = STRATEGY_FACTORY.get_all_param_grids()
            param_grid = param_grids.get(strategy_type, {})
            
            if param_grid:
                config = {
                    'strategy_type': strategy_type,
                    'param_grid': param_grid,
                    'method': STRATEGY.OPTIMIZATION_METHOD,
                    'max_iterations': STRATEGY.MAX_OPTIMIZATION_ITERATIONS
                }
                optimization_configs.append(config)
                
                self.logger.info(f"准备优化: {strategy_type}")
                self.logger.info(f"  参数网格: {list(param_grid.keys())}")
        
        # 运行多策略优化
        optimization_results = self.optimizer.optimize_multiple_strategies(
            strategies_config=optimization_configs,
            symbol=TRADING.SYMBOL,
            start_date=TRADING.BACKTEST_START_DATE,
            end_date=TRADING.BACKTEST_END_DATE
        )
        
        self.optimization_results = optimization_results
        
        self.logger.info(f"策略优化完成，共 {len(optimization_results['optimization_results'])} 个策略")
        
        return optimization_results
    
    def analyze_results(self, backtest_results: Dict[str, Any],
                       optimization_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析结果"""
        self.logger.info("开始结果分析...")
        
        # 合并结果进行分析
        all_results = {}
        
        # 添加回测结果
        if 'batch_results' in backtest_results:
            all_results.update(backtest_results['batch_results'])
        
        # 添加优化后的最佳策略结果
        if 'optimization_results' in optimization_results:
            for strategy_type, result in optimization_results['optimization_results'].items():
                if result:
                    # 使用优化后的参数重新运行回测，获取完整结果
                    try:
                        optimized_result = self.backtest_engine.run_backtest(
                            strategy_type=strategy_type,
                            params=result['best_params'],
                            symbol=TRADING.SYMBOL,
                            start_date=TRADING.BACKTEST_START_DATE,
                            end_date=TRADING.BACKTEST_END_DATE,
                            frequency=TRADING.FREQUENCY
                        )
                        
                        key = f"{strategy_type}_optimized"
                        all_results[key] = optimized_result
                        
                    except Exception as e:
                        self.logger.warning(f"优化策略 {strategy_type} 回测失败: {e}")
        
        # 分析结果
        analysis_results = self.analyzer.analyze_multiple_backtests(all_results)
        
        # 保存最佳策略
        if analysis_results.get('best_strategy'):
            self.best_strategy = analysis_results['best_strategy']
            
            self.logger.info(f"找到最佳策略: {self.best_strategy['strategy_type']}")
            self.logger.info(f"综合得分: {self.best_strategy['ranking_info']['overall_score']:.4f}")
            self.logger.info(f"总收益率: {self.best_strategy['performance_summary'].get('total_return', 0):.2%}")
        
        # 生成报告
        report_dir = self.analyzer.generate_report(analysis_results)
        
        if report_dir:
            self.logger.info(f"分析报告已生成: {report_dir}")
        
        return analysis_results
    
    def run_full_pipeline(self):
        """运行完整流程"""
        self.logger.info("开始运行完整量化交易流程")
        self.logger.info("=" * 60)
        
        # 1. 准备数据
        data_info = self.prepare_data()
        
        # 2. 生成策略
        strategies = self.generate_strategies()
        
        # 3. 运行回测
        backtest_results = self.run_backtests(strategies)
        
        # 4. 优化策略
        optimization_results = self.optimize_strategies(strategies)
        
        # 5. 分析结果
        analysis_results = self.analyze_results(backtest_results, optimization_results)
        
        # 6. 输出最终结果
        self._output_final_results(analysis_results)
        
        self.logger.info("=" * 60)
        self.logger.info("量化交易流程完成!")
    
    def run_backtest_only(self):
        """只运行回测"""
        self.logger.info("开始运行回测流程")
        
        # 1. 准备数据
        data_info = self.prepare_data()
        
        # 2. 生成策略
        strategies = self.generate_strategies()
        
        # 3. 运行回测
        backtest_results = self.run_backtests(strategies)
        
        # 4. 分析回测结果
        analysis_results = self.analyzer.analyze_multiple_backtests(
            backtest_results['batch_results']
        )
        
        # 5. 输出结果
        self._output_backtest_results(analysis_results)
        
        self.logger.info("回测流程完成!")
    
    def run_optimization_only(self):
        """只运行优化"""
        self.logger.info("开始运行优化流程")
        
        # 1. 准备数据
        data_info = self.prepare_data()
        
        # 2. 生成策略
        strategies = self.generate_strategies()
        
        # 3. 优化策略
        optimization_results = self.optimize_strategies(strategies)
        
        # 4. 输出优化结果
        self._output_optimization_results(optimization_results)
        
        self.logger.info("优化流程完成!")
    
    def _output_final_results(self, analysis_results: Dict[str, Any]):
        """输出最终结果"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("最终结果汇总")
        self.logger.info("=" * 60)
        
        if self.best_strategy:
            best = self.best_strategy
            
            self.logger.info(f"🎯 最佳策略: {best['strategy_type']}")
            self.logger.info(f"📊 综合得分: {best['ranking_info']['overall_score']:.4f}")
            self.logger.info(f"💰 总收益率: {best['performance_summary'].get('total_return', 0):.2%}")
            self.logger.info(f"📈 年化收益率: {best['performance_summary'].get('annual_return', 0):.2%}")
            self.logger.info(f"⚖️  夏普比率: {best['performance_summary'].get('sharpe_ratio', 0):.2f}")
            self.logger.info(f"📉 最大回撤: {best['performance_summary'].get('max_drawdown', 0):.2%}")
            self.logger.info(f"✅ 胜率: {best['performance_summary'].get('win_rate', 0):.2%}")
            
            self.logger.info(f"\n🔧 最佳参数配置:")
            for param, value in best['params'].items():
                self.logger.info(f"   {param}: {value}")
            
            self.logger.info(f"\n💡 操作建议: {best['recommendation']['action']}")
            self.logger.info(f"🎯 置信度: {best['recommendation']['confidence']}")
            
            if best['recommendation']['suggestions']:
                self.logger.info(f"\n📝 具体建议:")
                for suggestion in best['recommendation']['suggestions']:
                    self.logger.info(f"   • {suggestion}")
            
            if best['recommendation']['warnings']:
                self.logger.info(f"\n⚠️  警告:")
                for warning in best['recommendation']['warnings']:
                    self.logger.info(f"   • {warning}")
        
        # 策略排名
        comparison = analysis_results.get('comparison', {})
        if comparison.get('ranking'):
            self.logger.info(f"\n🏆 策略排名 (前5名):")
            for i, ranking in enumerate(comparison['ranking'][:5], 1):
                self.logger.info(f"{i}. {ranking['strategy_key']}")
                self.logger.info(f"   得分: {ranking['overall_score']:.4f}, "
                               f"收益: {ranking.get('total_return', 0):.2%}, "
                               f"夏普: {ranking.get('sharpe_ratio', 0):.2f}")
        
        self.logger.info("\n" + "=" * 60)
        
        # 保存最终配置
        self._save_final_configuration()
    
    def _output_backtest_results(self, analysis_results: Dict[str, Any]):
        """输出回测结果"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("回测结果汇总")
        self.logger.info("=" * 60)
        
        if analysis_results.get('best_strategy'):
            best = analysis_results['best_strategy']
            
            self.logger.info(f"🎯 回测最佳策略: {best['strategy_type']}")
            self.logger.info(f"📊 综合得分: {best['ranking_info']['overall_score']:.4f}")
            self.logger.info(f"💰 总收益率: {best['performance_summary'].get('total_return', 0):.2%}")
            self.logger.info(f"⚖️  夏普比率: {best['performance_summary'].get('sharpe_ratio', 0):.2f}")
            
            self.logger.info(f"\n🔧 参数配置:")
            for param, value in best['params'].items():
                self.logger.info(f"   {param}: {value}")
        
        # 统计信息
        total_strategies = len(analysis_results.get('individual_analyses', {}))
        self.logger.info(f"\n📈 回测统计:")
        self.logger.info(f"   总策略数: {total_strategies}")
        
        if analysis_results.get('comparison', {}).get('summary'):
            summary = analysis_results['comparison']['summary']
            if 'total_return' in summary:
                ret_stats = summary['total_return']
                self.logger.info(f"   收益率范围: {ret_stats['min']:.2%} ~ {ret_stats['max']:.2%}")
                self.logger.info(f"   平均收益率: {ret_stats['mean']:.2%}")
        
        self.logger.info("\n" + "=" * 60)
    
    def _output_optimization_results(self, optimization_results: Dict[str, Any]):
        """输出优化结果"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("优化结果汇总")
        self.logger.info("=" * 60)
        
        if optimization_results.get('best_strategy_overall'):
            best = optimization_results['best_strategy_overall']
            
            self.logger.info(f"🎯 优化最佳策略: {best['strategy_type']}")
            self.logger.info(f"📊 最佳得分: {best['best_score']:.4f}")
            
            self.logger.info(f"\n🔧 最佳参数配置:")
            for param, value in best['best_params'].items():
                self.logger.info(f"   {param}: {value}")
            
            self.logger.info(f"\n📈 性能指标:")
            perf = best['best_performance']
            for metric, value in perf.items():
                if isinstance(value, (int, float)):
                    if metric == 'total_return':
                        self.logger.info(f"   {metric}: {value:.2%}")
                    elif metric == 'max_drawdown':
                        self.logger.info(f"   {metric}: {value:.2%}")
                    else:
                        self.logger.info(f"   {metric}: {value:.4f}")
        
        # 各策略优化结果
        opt_results = optimization_results.get('optimization_results', {})
        self.logger.info(f"\n📊 各策略优化结果:")
        
        for strategy_type, result in opt_results.items():
            if result:
                self.logger.info(f"   {strategy_type}: 最佳得分={result['best_score']:.4f}, "
                               f"参数组合数={result['total_results']}")
        
        self.logger.info("\n" + "=" * 60)
    
    def _save_final_configuration(self):
        """保存最终配置"""
        if not self.best_strategy:
            return
        
        try:
            # 创建最终配置目录
            final_dir = os.path.join(PROJECT_ROOT, "results", "final_configuration")
            os.makedirs(final_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 保存最佳策略配置
            config_file = os.path.join(final_dir, f"best_strategy_{timestamp}.py")
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write("# ClawQuant 最佳策略配置\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 策略类型: {self.best_strategy['strategy_type']}\n")
                f.write(f"# 综合得分: {self.best_strategy['ranking_info']['overall_score']:.4f}\n\n")
                
                f.write("BEST_STRATEGY_CONFIG = {\n")
                f.write(f"    'strategy_type': '{self.best_strategy['strategy_type']}',\n")
                f.write("    'params': {\n")
                for param, value in self.best_strategy['params'].items():
                    f.write(f"        '{param}': {repr(value)},\n")
                f.write("    },\n")
                f.write("    'performance': {\n")
                for metric, value in self.best_strategy['performance_summary'].items():
                    if isinstance(value, (int, float)):
                        f.write(f"        '{metric}': {repr(value)},\n")
                f.write("    },\n")
                f.write("    'recommendation': {\n")
                f.write(f"        'action': '{self.best_strategy['recommendation']['action']}',\n")
                f.write(f"        'confidence': '{self.best_strategy['recommendation']['confidence']}'\n")
                f.write("    }\n")
                f.write("}\n\n")
                
                f.write("# 使用示例:\n")
                f.write("# from strategies.base_strategy import StrategyFactory\n")
                f.write("# strategy = StrategyFactory.create_strategy(\n")
                f.write("#     BEST_STRATEGY_CONFIG['strategy_type'],\n")
                f.write("#     BEST_STRATEGY_CONFIG['params']\n")
                f.write("# )\n")
            
            # 保存JSON格式配置
            json_file = os.path.join(final_dir, f"best_strategy_{timestamp}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.best_strategy, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"最佳策略配置已保存: {config_file}")
            self.logger.info(f"JSON配置已保存: {json_file}")
        
        except Exception as e:
            self.logger.warning(f"保存最终配置失败: {e}")
    
    def run(self):
        """运行主程序"""
        try:
            # 打印配置摘要
            print_config_summary()
            
            # 根据模式运行
            if self.mode == "full":
                self.run_full_pipeline()
            elif self.mode == "backtest":
                self.run_backtest_only()
            elif self.mode == "optimize":
                self.run_optimization_only()
            elif self.mode == "analyze":
                # 分析现有结果
                self.logger.info("分析模式需要现有结果文件")
                self.logger.info("请先运行回测或优化模式")
            else:
                self.logger.error(f"未知的运行模式: {self.mode}")
                self.logger.info("可用模式: full, backtest, optimize, analyze")
        
        except KeyboardInterrupt:
            self.logger.info("用户中断程序")
        except Exception as e:
            self.logger.error(f"程序运行失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="ClawQuant 量化交易系统")
    
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "backtest", "optimize", "analyze"],
        help="运行模式: full(完整流程), backtest(只回测), optimize(只优化), analyze(只分析)"
    )
    
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="交易品种代码，如 '000001.SH'"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="开始日期，格式 'YYYY-MM-DD'"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="结束日期，格式 'YYYY-MM-DD'"
    )
    
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=None,
        help="初始资金"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="配置文件路径"
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    # 解析参数
    args = parse_arguments()
    
    # 更新配置（如果提供了参数）
    if args.symbol:
        TRADING.SYMBOL = args.symbol
    
    if args.start_date:
        TRADING.BACKTEST_START_DATE = args.start_date
    
    if args.end_date:
        TRADING.BACKTEST_END_DATE = args.end_date
    
    if args.initial_cash:
        TRADING.INITIAL_CASH = args.initial_cash
    
    # 创建并运行系统
    system = ClawQuant(mode=args.mode)
    system.run()
    
    # 输出完成信息
    logger.info("\n✨ ClawQuant 量化交易系统运行完成!")
    logger.info(f"📁 项目目录: {PROJECT_ROOT}")
    logger.info(f"📊 结果目录: {os.path.join(PROJECT_ROOT, 'results')}")
    
    if system.best_strategy:
        logger.info(f"🎯 最佳策略已保存到 results/final_configuration/")
        logger.info(f"💡 建议: {system.best_strategy['recommendation']['action']}")


if __name__ == "__main__":
    main()