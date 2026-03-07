"""
实时监控仪表板
提供策略性能监控和实时警报功能
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger

from config.settings import RESULTS_DIR
from utils.visualizer import PerformanceVisualizer, RealTimeMonitor
from backtests.enhanced_backtest_engine import EnhancedBacktestEngine


class RealTimeDashboard:
    """实时监控仪表板"""
    
    def __init__(self, refresh_interval: int = 300):  # 5分钟刷新一次
        """
        初始化实时监控仪表板
        
        Args:
            refresh_interval: 刷新间隔（秒）
        """
        self.refresh_interval = refresh_interval
        self.visualizer = PerformanceVisualizer()
        self.monitor = RealTimeMonitor(refresh_interval=refresh_interval)
        self.engine = EnhancedBacktestEngine()
        
        # 监控状态
        self.is_running = False
        self.monitor_thread = None
        
        # 存储策略结果
        self.strategy_results = {}
        self.alerts_log = []
        
        # 仪表板配置
        self.dashboard_config = {
            'title': 'ClawQuant 实时监控仪表板',
            'refresh_interval': refresh_interval,
            'strategies_monitored': [],
            'alerts_enabled': True
        }
    
    def add_strategy_for_monitoring(self, strategy_config: Dict[str, Any]):
        """
        添加策略到监控列表
        
        Args:
            strategy_config: 策略配置
        """
        self.dashboard_config['strategies_monitored'].append(strategy_config)
        logger.info(f"已添加策略到监控: {strategy_config.get('strategy_type', 'Unknown')}")
    
    def start_monitoring(self):
        """启动实时监控"""
        if self.is_running:
            logger.warning("监控已在运行中")
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("实时监控已启动")
    
    def stop_monitoring(self):
        """停止实时监控"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)  # 等待最多5秒
        
        logger.info("实时监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 更新策略性能
                self._update_strategy_performance()
                
                # 检查警报条件
                self._check_alerts()
                
                # 生成更新的仪表板
                self._update_dashboard()
                
                # 等待下一个刷新周期
                time.sleep(self.refresh_interval)
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(60)  # 出错时等待1分钟再继续
    
    def _update_strategy_performance(self):
        """更新策略性能数据"""
        for config in self.dashboard_config['strategies_monitored']:
            try:
                strategy_type = config.get('strategy_type')
                params = config.get('params', {})
                symbol = config.get('symbol', '000001.SH')
                
                # 运行简短的回测以获取最新性能
                # 注意：在实际应用中，这应该是连接到实盘数据的实时性能更新
                result = self._get_recent_performance(strategy_type, params, symbol)
                
                if result:
                    self.strategy_results[f"{strategy_type}_{symbol}"] = result
                    logger.info(f"已更新策略性能: {strategy_type}")
                
            except Exception as e:
                logger.error(f"更新策略性能失败: {e}")
    
    def _get_recent_performance(self, strategy_type: str, params: Dict[str, Any], 
                              symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取近期性能数据
        
        Args:
            strategy_type: 策略类型
            params: 策略参数
            symbol: 交易品种
            
        Returns:
            性能数据
        """
        try:
            # 为了演示目的，我们使用最近几天的数据进行快速回测
            # 在实际应用中，这里应该连接到实盘数据
            from datetime import datetime, timedelta
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # 运行快速回测
            result = self.engine.run_backtest(
                strategy_type=strategy_type,
                params=params,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                frequency="daily"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"获取近期性能失败: {e}")
            return None
    
    def _check_alerts(self):
        """检查警报条件"""
        # 示例警报条件
        alerts_to_check = [
            {
                'name': '最大回撤警报',
                'condition': lambda data: data.get('max_drawdown', 0) < -0.15,  # 超过15%回撤
                'message': '策略出现超过15%的最大回撤',
                'severity': 'HIGH'
            },
            {
                'name': '夏普比率下降',
                'condition': lambda data: data.get('sharpe_ratio', 0) < 0.5,  # 夏普比率低于0.5
                'message': '策略夏普比率低于0.5',
                'severity': 'MEDIUM'
            },
            {
                'name': '收益率下降',
                'condition': lambda data: data.get('total_return', 0) < -0.05,  # 收益率低于-5%
                'message': '策略总收益率低于-5%',
                'severity': 'MEDIUM'
            }
        ]
        
        # 检查每个策略的警报条件
        for strategy_key, result in self.strategy_results.items():
            perf = result.get('performance', {})
            
            for alert in alerts_to_check:
                if alert['condition'](perf):
                    alert_entry = {
                        'strategy': strategy_key,
                        'alert_name': alert['name'],
                        'message': alert['message'],
                        'severity': alert['severity'],
                        'timestamp': datetime.now(),
                        'performance_data': perf
                    }
                    
                    self.alerts_log.append(alert_entry)
                    logger.warning(f"警报触发: {alert_entry}")
    
    def _update_dashboard(self):
        """更新仪表板"""
        try:
            # 生成监控仪表板
            if self.strategy_results:
                results_list = list(self.strategy_results.values())
                dashboard_path = self.monitor.generate_monitoring_dashboard(
                    results_list,
                    f"live_monitoring_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                )
                
                logger.info(f"仪表板已更新: {dashboard_path}")
            
            # 保存警报日志
            self._save_alerts_log()
            
        except Exception as e:
            logger.error(f"更新仪表板失败: {e}")
    
    def _save_alerts_log(self):
        """保存警报日志"""
        try:
            alerts_dir = os.path.join(RESULTS_DIR, "alerts")
            os.makedirs(alerts_dir, exist_ok=True)
            
            alerts_file = os.path.join(alerts_dir, f"alerts_log_{datetime.now().strftime('%Y%m%d')}.json")
            
            # 准备保存的警报数据
            alerts_to_save = []
            for alert in self.alerts_log:
                alert_copy = alert.copy()
                alert_copy['timestamp'] = alert['timestamp'].isoformat()
                alerts_to_save.append(alert_copy)
            
            with open(alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts_to_save, f, ensure_ascii=False, indent=2)
            
            logger.info(f"警报日志已保存: {alerts_file}")
        
        except Exception as e:
            logger.error(f"保存警报日志失败: {e}")
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """获取仪表板状态"""
        return {
            'is_running': self.is_running,
            'strategies_monitored': len(self.dashboard_config['strategies_monitored']),
            'total_alerts': len(self.alerts_log),
            'last_update': datetime.now().isoformat(),
            'strategy_results': {k: {
                'strategy_type': v.get('strategy_type'),
                'total_return': v.get('total_return', 0),
                'sharpe_ratio': v.get('performance', {}).get('sharpe_ratio', 0),
                'max_drawdown': v.get('performance', {}).get('max_drawdown', 0)
            } for k, v in self.strategy_results.items()}
        }
    
    def export_dashboard_data(self, filename: str = None) -> str:
        """
        导出仪表板数据
        
        Args:
            filename: 输出文件名
            
        Returns:
            文件路径
        """
        if not filename:
            filename = f"dashboard_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_dir = os.path.join(RESULTS_DIR, "dashboard_exports")
        os.makedirs(export_dir, exist_ok=True)
        
        export_path = os.path.join(export_dir, filename)
        
        export_data = {
            'dashboard_config': self.dashboard_config,
            'strategy_results': self.strategy_results,
            'alerts_log': [],
            'export_timestamp': datetime.now().isoformat()
        }
        
        # 处理警报日志中的时间戳
        for alert in self.alerts_log:
            alert_copy = alert.copy()
            alert_copy['timestamp'] = alert['timestamp'].isoformat()
            export_data['alerts_log'].append(alert_copy)
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"仪表板数据已导出: {export_path}")
        return export_path


class AlertManager:
    """警报管理器"""
    
    def __init__(self):
        self.alerts = []
        self.subscribers = []  # 警报订阅者
    
    def add_alert(self, condition_func, message: str, severity: str = "INFO", 
                  strategy_name: str = "Unknown"):
        """
        添加警报条件
        
        Args:
            condition_func: 条件函数
            message: 警报消息
            severity: 严重程度
            strategy_name: 策略名称
        """
        alert = {
            'condition': condition_func,
            'message': message,
            'severity': severity,
            'strategy_name': strategy_name,
            'last_triggered': None,
            'trigger_count': 0
        }
        
        self.alerts.append(alert)
    
    def check_and_trigger_alerts(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查并触发警报
        
        Args:
            data: 监控数据
            
        Returns:
            触发的警报列表
        """
        triggered_alerts = []
        
        for alert in self.alerts:
            try:
                if alert['condition'](data):
                    # 更新警报统计
                    alert['trigger_count'] += 1
                    alert['last_triggered'] = datetime.now()
                    
                    triggered_alert = {
                        'message': alert['message'],
                        'severity': alert['severity'],
                        'strategy': alert['strategy_name'],
                        'timestamp': datetime.now().isoformat(),
                        'data': data
                    }
                    
                    triggered_alerts.append(triggered_alert)
                    
                    # 通知订阅者
                    self._notify_subscribers(triggered_alert)
                    
            except Exception as e:
                logger.error(f"检查警报时出错: {e}")
        
        return triggered_alerts
    
    def _notify_subscribers(self, alert: Dict[str, Any]):
        """通知订阅者"""
        for subscriber in self.subscribers:
            try:
                subscriber(alert)
            except Exception as e:
                logger.error(f"通知订阅者失败: {e}")
    
    def add_subscriber(self, callback_func):
        """添加订阅者"""
        self.subscribers.append(callback_func)


def create_sample_dashboard():
    """创建示例仪表板"""
    logger.info("创建示例实时监控仪表板...")
    
    # 创建仪表板实例
    dashboard = RealTimeDashboard(refresh_interval=600)  # 10分钟刷新一次
    
    # 添加一些策略到监控列表
    sample_strategies = [
        {
            'strategy_type': 'MA',
            'params': {'sma_period': 20, 'lma_period': 60},
            'symbol': '000001.SH'
        },
        {
            'strategy_type': 'MACD',
            'params': {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
            'symbol': '000001.SH'
        },
        {
            'strategy_type': 'MOMENTUM',
            'params': {'momentum_period': 20, 'sma_period': 50},
            'symbol': 'AAPL'
        }
    ]
    
    for strategy in sample_strategies:
        dashboard.add_strategy_for_monitoring(strategy)
    
    # 启动监控（在实际应用中，这会在后台运行）
    logger.info("示例仪表板创建完成")
    return dashboard


# ========== 使用示例 ==========
if __name__ == "__main__":
    print("测试实时监控仪表板...")
    
    # 创建示例仪表板
    dashboard = create_sample_dashboard()
    
    # 显示仪表板状态
    status = dashboard.get_dashboard_status()
    print(f"仪表板状态: {status}")
    
    # 导出仪表板数据
    export_path = dashboard.export_dashboard_data()
    print(f"仪表板数据已导出到: {export_path}")
    
    print("实时监控仪表板测试完成!")