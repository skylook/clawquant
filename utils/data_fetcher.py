"""
数据获取工具模块
用于从不同数据源获取市场数据
"""

import os
import pandas as pd
import numpy as np
import akshare as ak
import tushare as ts
import yfinance as yf  # Added for international markets
from datetime import datetime, timedelta
import time
from typing import Optional, Dict, List, Tuple
import pickle
import hashlib
from loguru import logger

from config.settings import CACHE_DIR, RAW_DATA_DIR, SYSTEM


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, use_cache: bool = True):
        """
        初始化数据获取器
        
        Args:
            use_cache: 是否使用缓存
        """
        self.use_cache = use_cache
        self.cache_dir = CACHE_DIR
        self.raw_data_dir = RAW_DATA_DIR
        
        # 初始化tushare（如果需要）
        try:
            # 这里可以设置tushare token
            ts.set_token('your_tushare_token_here')
        except:
            pass
    
    def _get_cache_key(self, symbol: str, start_date: str, end_date: str, 
                      frequency: str) -> str:
        """生成缓存key"""
        key_str = f"{symbol}_{start_date}_{end_date}_{frequency}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """从缓存加载数据"""
        if not self.use_cache:
            return None
            
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        if os.path.exists(cache_file):
            try:
                # 检查缓存是否过期
                if SYSTEM.USE_CACHE:
                    file_mtime = os.path.getmtime(cache_file)
                    cache_age_hours = (time.time() - file_mtime) / 3600
                    if cache_age_hours < SYSTEM.CACHE_EXPIRE_HOURS:
                        with open(cache_file, 'rb') as f:
                            data = pickle.load(f)
                        logger.info(f"从缓存加载数据: {cache_key}")
                        return data
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, data: pd.DataFrame):
        """保存数据到缓存"""
        if not self.use_cache:
            return
            
        try:
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"数据已缓存: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存数据失败: {e}")
    
    def fetch_stock_data(self, symbol: str, start_date: str, end_date: str, 
                        frequency: str = "daily") -> pd.DataFrame:
        """
        获取股票数据
        
        Args:
            symbol: 股票代码，如 "000001.SZ", "0005.HK", "AAPL"
            start_date: 开始日期，格式 "YYYY-MM-DD"
            end_date: 结束日期，格式 "YYYY-MM-DD"
            frequency: 数据频率，支持 "daily", "weekly", "monthly"
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        # 生成缓存key
        cache_key = self._get_cache_key(symbol, start_date, end_date, frequency)
        
        # 尝试从缓存加载
        cached_data = self._load_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        logger.info(f"开始获取数据: {symbol} ({start_date} 到 {end_date})")
        
        # 识别市场类型
        market_type = self._identify_market_type(symbol)
        logger.info(f"识别市场类型: {market_type}")
        
        # 根据市场类型选择获取方法
        data = pd.DataFrame()
        
        try:
            if market_type == 'china_a':
                # A股市场
                try:
                    # 方法1: 使用akshare
                    data = self._fetch_with_akshare(symbol, start_date, end_date, frequency)
                except Exception as e1:
                    logger.warning(f"akshare获取失败: {e1}")
                    try:
                        # 方法2: 使用tushare
                        data = self._fetch_with_tushare(symbol, start_date, end_date, frequency)
                    except Exception as e2:
                        logger.warning(f"tushare获取失败: {e2}")
                        # 方法3: 使用模拟数据
                        data = self._generate_mock_data(symbol, start_date, end_date, frequency)
                        logger.info(f"使用模拟数据: {symbol}")
            
            elif market_type in ['hong_kong', 'us']:
                # 国际市场，优先使用yfinance
                try:
                    # 标准化符号格式
                    standardized_symbol = self._handle_international_symbol(symbol, market_type)
                    logger.info(f"标准化符号: {symbol} -> {standardized_symbol}")
                    
                    data = self._fetch_with_yfinance(standardized_symbol, start_date, end_date, frequency)
                    
                    if data.empty:
                        logger.warning(f"yfinance获取数据为空，使用模拟数据: {symbol}")
                        data = self._generate_mock_data(symbol, start_date, end_date, frequency)
                except Exception as e:
                    logger.warning(f"yfinance获取失败: {e}, 使用模拟数据: {symbol}")
                    data = self._generate_mock_data(symbol, start_date, end_date, frequency)
            
            else:
                # 默认使用原有方法
                try:
                    # 方法1: 使用akshare
                    data = self._fetch_with_akshare(symbol, start_date, end_date, frequency)
                except Exception as e1:
                    logger.warning(f"akshare获取失败: {e1}")
                    try:
                        # 方法2: 使用tushare
                        data = self._fetch_with_tushare(symbol, start_date, end_date, frequency)
                    except Exception as e2:
                        logger.warning(f"tushare获取失败: {e2}")
                        # 方法3: 使用yfinance
                        try:
                            standardized_symbol = self._handle_international_symbol(symbol, market_type)
                            data = self._fetch_with_yfinance(standardized_symbol, start_date, end_date, frequency)
                        except Exception as e3:
                            logger.warning(f"yfinance获取失败: {e3}")
                            # 方法4: 使用模拟数据
                            data = self._generate_mock_data(symbol, start_date, end_date, frequency)
                            logger.info(f"使用模拟数据: {symbol}")
        
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            # 最终回退到模拟数据
            data = self._generate_mock_data(symbol, start_date, end_date, frequency)
        
        # 确保数据格式正确
        data = self._standardize_data(data, symbol)
        
        # 保存到缓存
        self._save_to_cache(cache_key, data)
        
        # 保存原始数据
        raw_file = os.path.join(self.raw_data_dir, f"{symbol}_{frequency}_{start_date}_{end_date}.csv")
        data.to_csv(raw_file)
        logger.info(f"原始数据已保存: {raw_file}")
        
        return data
    
    def _fetch_with_akshare(self, symbol: str, start_date: str, end_date: str, 
                           frequency: str) -> pd.DataFrame:
        """使用akshare获取数据"""
        # 移除交易所后缀
        clean_symbol = symbol.replace('.SH', '').replace('.SZ', '')
        
        if frequency == "daily":
            # 获取日线数据
            df = ak.stock_zh_a_hist(
                symbol=clean_symbol,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权
            )
            
            # 重命名列
            if not df.empty:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'pct_change',
                    '涨跌额': 'change',
                    '换手率': 'turnover'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
        
        elif frequency == "weekly":
            df = ak.stock_zh_a_hist(
                symbol=clean_symbol,
                period="weekly",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
            if not df.empty:
                df = df.rename(columns={'日期': 'date'})
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
        
        else:  # monthly
            df = ak.stock_zh_a_hist(
                symbol=clean_symbol,
                period="monthly",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )
            if not df.empty:
                df = df.rename(columns={'日期': 'date'})
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
        
        return df
    
    def _fetch_with_tushare(self, symbol: str, start_date: str, end_date: str,
                           frequency: str) -> pd.DataFrame:
        """使用tushare获取数据"""
        pro = ts.pro_api()
        
        # 转换日期格式
        start_date_ts = start_date.replace('-', '')
        end_date_ts = end_date.replace('-', '')
        
        # 根据频率获取数据
        if frequency == "daily":
            df = pro.daily(
                ts_code=symbol,
                start_date=start_date_ts,
                end_date=end_date_ts
            )
        elif frequency == "weekly":
            df = pro.weekly(
                ts_code=symbol,
                start_date=start_date_ts,
                end_date=end_date_ts
            )
        else:  # monthly
            df = pro.monthly(
                ts_code=symbol,
                start_date=start_date_ts,
                end_date=end_date_ts
            )
        
        if not df.empty:
            df = df.rename(columns={
                'trade_date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'vol': 'volume',
                'amount': 'amount'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.sort_index()
        
        return df
    
    def _fetch_with_yfinance(self, symbol: str, start_date: str, end_date: str,
                           frequency: str) -> pd.DataFrame:
        """使用yfinance获取国际市场的数据"""
        # 映射频率
        freq_map = {
            "daily": "1d",
            "weekly": "1wk",
            "monthly": "1mo"
        }
        
        yf_freq = freq_map.get(frequency, "1d")
        
        # 使用yfinance获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=yf_freq,
            auto_adjust=True
        )
        
        if not df.empty:
            # 重命名列以匹配内部格式
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Dividends': 'dividends',
                'Stock Splits': 'stock_splits'
            })
            
            # 如果没有amount列，创建一个估算值
            if 'amount' not in df.columns:
                df['amount'] = df['close'] * df['volume']
        
        return df
    
    def _identify_market_type(self, symbol: str) -> str:
        """识别市场类型"""
        symbol_upper = symbol.upper()
        
        # A股市场
        if symbol_upper.endswith(('.SH', '.SZ')):
            return 'china_a'
        
        # 港股市场
        elif symbol_upper.endswith('.HK') or (len(symbol) == 4 and symbol.isdigit()):
            return 'hong_kong'
        
        # 美股市场
        elif '.' not in symbol_upper or symbol_upper.endswith(('.TO', '.MX', '.L', '.AX', '.T', '.K', '.O')):
            return 'us'
        
        # 默认为A股
        else:
            return 'china_a'
    
    def _handle_international_symbol(self, symbol: str, market_type: str) -> str:
        """处理国际市场的符号格式"""
        if market_type == 'hong_kong':
            # 处理港股代码
            if '.' not in symbol:
                # 如果没有后缀，添加.HK
                return f"{symbol}.HK"
            elif not symbol.upper().endswith('.HK'):
                # 如果不是.HK后缀，转换为.HK
                return f"{symbol.split('.')[0]}.HK"
        
        elif market_type == 'us':
            # 美股不需要特殊处理
            return symbol
        
        return symbol
    
    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str,
                           frequency: str) -> pd.DataFrame:
        """生成模拟数据（当真实数据不可用时）"""
        logger.warning(f"生成模拟数据: {symbol}")
        
        # 生成日期范围
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 基础价格（模拟上证指数）
        base_price = 3000
        
        # 生成随机价格序列（几何布朗运动）
        n_days = len(dates)
        returns = np.random.normal(0.0005, 0.015, n_days)  # 日均收益0.05%，波动1.5%
        prices = base_price * np.exp(np.cumsum(returns))
        
        # 生成OHLCV数据
        data = pd.DataFrame(index=dates)
        data['close'] = prices
        
        # 生成开盘价（基于前一日收盘价）
        data['open'] = data['close'].shift(1) * (1 + np.random.normal(0, 0.005, n_days))
        data.loc[data.index[0], 'open'] = data.loc[data.index[0], 'close'] * 0.99
        
        # 生成最高价和最低价
        data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
        data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
        
        # 确保 high >= max(open, close) >= min(open, close) >= low
        data['high'] = data[['high', 'open', 'close']].max(axis=1)
        data['low'] = data[['low', 'open', 'close']].min(axis=1)
        
        # 生成成交量
        data['volume'] = np.random.lognormal(14, 1, n_days)  # 对数正态分布
        
        # 生成成交额
        data['amount'] = data['volume'] * data['close']
        
        # 添加涨跌幅
        data['pct_change'] = data['close'].pct_change() * 100
        
        # 重采样到指定频率
        if frequency == "weekly":
            data = data.resample('W').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'amount': 'sum'
            })
        elif frequency == "monthly":
            data = data.resample('M').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'amount': 'sum'
            })
        
        return data
    
    def _standardize_data(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """标准化数据格式"""
        if data.empty:
            return data
        
        # 确保必要的列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in required_columns:
            if col not in data.columns:
                if col == 'volume':
                    data[col] = 0
                else:
                    data[col] = data['close']  # 用收盘价填充
        
        # 确保数据类型正确
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        for col in numeric_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # 处理缺失值 - 使用现代pandas语法
        data = data.ffill().bfill()
        
        # 添加股票代码
        data['symbol'] = symbol
        
        # 按日期排序
        data = data.sort_index()
        
        return data
    
    def get_multiple_symbols(self, symbols: List[str], start_date: str, 
                            end_date: str, frequency: str = "daily") -> Dict[str, pd.DataFrame]:
        """获取多个股票的数据"""
        all_data = {}
        
        for symbol in symbols:
            try:
                data = self.fetch_stock_data(symbol, start_date, end_date, frequency)
                all_data[symbol] = data
                logger.info(f"成功获取 {symbol} 数据，共 {len(data)} 条记录")
            except Exception as e:
                logger.error(f"获取 {symbol} 数据失败: {e}")
        
        return all_data
    
    def get_index_data(self, index_code: str, start_date: str, end_date: str,
                      frequency: str = "daily") -> pd.DataFrame:
        """获取指数数据"""
        # 这里可以添加专门的指数数据获取逻辑
        return self.fetch_stock_data(index_code, start_date, end_date, frequency)


# ========== 使用示例 ==========
if __name__ == "__main__":
    # 测试数据获取
    fetcher = DataFetcher(use_cache=True)
    
    # 测试获取上证指数数据
    print("测试获取上证指数数据...")
    data = fetcher.fetch_stock_data(
        symbol="000001.SH",
        start_date="2023-01-01",
        end_date="2023-12-31",
        frequency="daily"
    )
    
    print(f"数据形状: {data.shape}")
    print(f"数据列: {data.columns.tolist()}")
    print(f"数据时间范围: {data.index[0]} 到 {data.index[-1]}")
    print(f"前5行数据:")
    print(data.head())
    
    # 保存示例数据
    sample_file = os.path.join(RAW_DATA_DIR, "sample_data.csv")
    data.to_csv(sample_file)
    print(f"\n示例数据已保存到: {sample_file}")