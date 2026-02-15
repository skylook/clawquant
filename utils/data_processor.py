"""
数据处理工具模块
用于处理、清洗和特征工程
"""

import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import talib
from loguru import logger

from config.settings import PROCESSED_DATA_DIR


class DataProcessor:
    """数据处理器"""
    
    def __init__(self):
        """初始化数据处理器"""
        self.processed_dir = PROCESSED_DATA_DIR
    
    def process_raw_data(self, raw_data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        处理原始数据
        
        Args:
            raw_data: 原始数据DataFrame
            symbol: 股票代码
            
        Returns:
            处理后的数据
        """
        logger.info(f"开始处理数据: {symbol}")
        
        # 复制数据以避免修改原始数据
        data = raw_data.copy()
        
        # 1. 基本数据清洗
        data = self._clean_data(data)
        
        # 2. 添加技术指标
        data = self._add_technical_indicators(data)
        
        # 3. 添加统计特征
        data = self._add_statistical_features(data)
        
        # 4. 添加价格模式
        data = self._add_price_patterns(data)
        
        # 5. 添加市场状态
        data = self._add_market_state(data)
        
        # 6. 添加目标变量（未来收益率）
        data = self._add_target_variables(data)
        
        # 7. 处理缺失值
        data = self._handle_missing_values(data)
        
        # 保存处理后的数据
        processed_file = os.path.join(self.processed_dir, f"{symbol}_processed.csv")
        data.to_csv(processed_file)
        logger.info(f"处理后的数据已保存: {processed_file}")
        
        return data
    
    def _clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        # 移除完全重复的行
        data = data.drop_duplicates()
        
        # 确保索引是DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'date' in data.columns:
                data['date'] = pd.to_datetime(data['date'])
                data = data.set_index('date')
            else:
                logger.warning("无法确定日期列，使用默认索引")
        
        # 按日期排序
        data = data.sort_index()
        
        # 检查是否有异常价格
        data = self._filter_abnormal_prices(data)
        
        return data
    
    def _filter_abnormal_prices(self, data: pd.DataFrame) -> pd.DataFrame:
        """过滤异常价格"""
        # 价格不能为0或负数
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in data.columns:
                data = data[data[col] > 0]
        
        # 检查价格合理性：high >= low, high >= open, high >= close, low <= open, low <= close
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            valid_mask = (
                (data['high'] >= data['low']) &
                (data['high'] >= data['open']) &
                (data['high'] >= data['close']) &
                (data['low'] <= data['open']) &
                (data['low'] <= data['close'])
            )
            data = data[valid_mask]
        
        return data
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加技术指标"""
        if 'close' not in data.columns:
            logger.warning("没有收盘价数据，跳过技术指标计算")
            return data
        
        close_prices = data['close'].values.astype(float)
        high_prices = data['high'].values.astype(float) if 'high' in data.columns else close_prices
        low_prices = data['low'].values.astype(float) if 'low' in data.columns else close_prices
        volume = data['volume'].values.astype(float) if 'volume' in data.columns else np.zeros(len(data)).astype(float)
        
        # 移动平均线
        data['SMA_5'] = talib.SMA(close_prices, timeperiod=5)
        data['SMA_10'] = talib.SMA(close_prices, timeperiod=10)
        data['SMA_20'] = talib.SMA(close_prices, timeperiod=20)
        data['SMA_30'] = talib.SMA(close_prices, timeperiod=30)
        data['SMA_60'] = talib.SMA(close_prices, timeperiod=60)
        
        # 指数移动平均线
        data['EMA_12'] = talib.EMA(close_prices, timeperiod=12)
        data['EMA_26'] = talib.EMA(close_prices, timeperiod=26)
        
        # MACD
        data['MACD'], data['MACD_signal'], data['MACD_hist'] = talib.MACD(
            close_prices, fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # RSI
        data['RSI_6'] = talib.RSI(close_prices, timeperiod=6)
        data['RSI_14'] = talib.RSI(close_prices, timeperiod=14)
        data['RSI_24'] = talib.RSI(close_prices, timeperiod=24)
        
        # 布林带
        data['BB_upper'], data['BB_middle'], data['BB_lower'] = talib.BBANDS(
            close_prices, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        
        # 随机指标
        data['STOCH_k'], data['STOCH_d'] = talib.STOCH(
            high_prices, low_prices, close_prices,
            fastk_period=14, slowk_period=3, slowk_matype=0,
            slowd_period=3, slowd_matype=0
        )
        
        # ATR（平均真实波幅）
        data['ATR_14'] = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)
        
        # OBV（能量潮）
        data['OBV'] = talib.OBV(close_prices, volume)
        
        # CCI（商品通道指数）
        data['CCI_14'] = talib.CCI(high_prices, low_prices, close_prices, timeperiod=14)
        
        # ADX（平均趋向指数）
        data['ADX_14'] = talib.ADX(high_prices, low_prices, close_prices, timeperiod=14)
        
        # 威廉指标
        data['WILLR_14'] = talib.WILLR(high_prices, low_prices, close_prices, timeperiod=14)
        
        return data
    
    def _add_statistical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加统计特征"""
        if 'close' not in data.columns:
            return data
        
        close_prices = data['close'].values
        
        # 收益率
        data['returns'] = data['close'].pct_change()
        
        # 对数收益率
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        
        # 滚动统计量
        windows = [5, 10, 20, 30, 60]
        
        for window in windows:
            # 滚动收益率
            data[f'returns_{window}d'] = data['close'].pct_change(window)
            
            # 滚动波动率
            data[f'volatility_{window}d'] = data['returns'].rolling(window).std() * np.sqrt(252)
            
            # 滚动偏度
            data[f'skewness_{window}d'] = data['returns'].rolling(window).skew()
            
            # 滚动峰度
            data[f'kurtosis_{window}d'] = data['returns'].rolling(window).kurt()
            
            # 滚动最大回撤
            data[f'max_drawdown_{window}d'] = self._calculate_rolling_drawdown(data['close'], window)
        
        # 价格位置特征
        data['price_position_20'] = (data['close'] - data['close'].rolling(20).min()) / \
                                   (data['close'].rolling(20).max() - data['close'].rolling(20).min())
        
        # 价格动量
        data['momentum_10'] = data['close'] / data['close'].shift(10) - 1
        data['momentum_20'] = data['close'] / data['close'].shift(20) - 1
        
        return data
    
    def _calculate_rolling_drawdown(self, prices: pd.Series, window: int) -> pd.Series:
        """计算滚动最大回撤"""
        rolling_max = prices.rolling(window, min_periods=1).max()
        drawdown = (prices - rolling_max) / rolling_max
        return drawdown.rolling(window, min_periods=1).min()
    
    def _add_price_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加价格模式识别"""
        if 'close' not in data.columns or 'high' not in data.columns or 'low' not in data.columns:
            return data
        
        close_prices = data['close'].values.astype(float)
        high_prices = data['high'].values.astype(float)
        low_prices = data['low'].values.astype(float)
        open_prices = data['open'].values.astype(float) if 'open' in data.columns else close_prices

        # 使用TA-Lib识别价格模式
        patterns = [
            ('CDL2CROWS', talib.CDL2CROWS),
            ('CDL3BLACKCROWS', talib.CDL3BLACKCROWS),
            ('CDL3INSIDE', talib.CDL3INSIDE),
            ('CDL3LINESTRIKE', talib.CDL3LINESTRIKE),
            ('CDL3OUTSIDE', talib.CDL3OUTSIDE),
            ('CDL3STARSINSOUTH', talib.CDL3STARSINSOUTH),
            ('CDL3WHITESOLDIERS', talib.CDL3WHITESOLDIERS),
            ('CDLABANDONEDBABY', talib.CDLABANDONEDBABY),
            ('CDLADVANCEBLOCK', talib.CDLADVANCEBLOCK),
            ('CDLBELTHOLD', talib.CDLBELTHOLD),
            ('CDLBREAKAWAY', talib.CDLBREAKAWAY),
            ('CDLCLOSINGMARUBOZU', talib.CDLCLOSINGMARUBOZU),
            ('CDLCONCEALBABYSWALL', talib.CDLCONCEALBABYSWALL),
            ('CDLCOUNTERATTACK', talib.CDLCOUNTERATTACK),
            ('CDLDARKCLOUDCOVER', talib.CDLDARKCLOUDCOVER),
            ('CDLDOJI', talib.CDLDOJI),
            ('CDLDOJISTAR', talib.CDLDOJISTAR),
            ('CDLDRAGONFLYDOJI', talib.CDLDRAGONFLYDOJI),
            ('CDLENGULFING', talib.CDLENGULFING),
            ('CDLEVENINGDOJISTAR', talib.CDLEVENINGDOJISTAR),
            ('CDLEVENINGSTAR', talib.CDLEVENINGSTAR),
            ('CDLGAPSIDESIDEWHITE', talib.CDLGAPSIDESIDEWHITE),
            ('CDLGRAVESTONEDOJI', talib.CDLGRAVESTONEDOJI),
            ('CDLHAMMER', talib.CDLHAMMER),
            ('CDLHANGINGMAN', talib.CDLHANGINGMAN),
            ('CDLHARAMI', talib.CDLHARAMI),
            ('CDLHARAMICROSS', talib.CDLHARAMICROSS),
            ('CDLHIGHWAVE', talib.CDLHIGHWAVE),
            ('CDLHIKKAKE', talib.CDLHIKKAKE),
            ('CDLHIKKAKEMOD', talib.CDLHIKKAKEMOD),
            ('CDLHOMINGPIGEON', talib.CDLHOMINGPIGEON),
            ('CDLIDENTICAL3CROWS', talib.CDLIDENTICAL3CROWS),
            ('CDLINNECK', talib.CDLINNECK),
            ('CDLINVERTEDHAMMER', talib.CDLINVERTEDHAMMER),
            ('CDLKICKING', talib.CDLKICKING),
            ('CDLKICKINGBYLENGTH', talib.CDLKICKINGBYLENGTH),
            ('CDLLADDERBOTTOM', talib.CDLLADDERBOTTOM),
            ('CDLLONGLEGGEDDOJI', talib.CDLLONGLEGGEDDOJI),
            ('CDLLONGLINE', talib.CDLLONGLINE),
            ('CDLMARUBOZU', talib.CDLMARUBOZU),
            ('CDLMATCHINGLOW', talib.CDLMATCHINGLOW),
            ('CDLMATHOLD', talib.CDLMATHOLD),
            ('CDLMORNINGDOJISTAR', talib.CDLMORNINGDOJISTAR),
            ('CDLMORNINGSTAR', talib.CDLMORNINGSTAR),
            ('CDLONNECK', talib.CDLONNECK),
            ('CDLPIERCING', talib.CDLPIERCING),
            ('CDLRICKSHAWMAN', talib.CDLRICKSHAWMAN),
            ('CDLRISEFALL3METHODS', talib.CDLRISEFALL3METHODS),
            ('CDLSEPARATINGLINES', talib.CDLSEPARATINGLINES),
            ('CDLSHOOTINGSTAR', talib.CDLSHOOTINGSTAR),
            ('CDLSHORTLINE', talib.CDLSHORTLINE),
            ('CDLSPINNINGTOP', talib.CDLSPINNINGTOP),
            ('CDLSTALLEDPATTERN', talib.CDLSTALLEDPATTERN),
            ('CDLSTICKSANDWICH', talib.CDLSTICKSANDWICH),
            ('CDLTAKURI', talib.CDLTAKURI),
            ('CDLTASUKIGAP', talib.CDLTASUKIGAP),
            ('CDLTHRUSTING', talib.CDLTHRUSTING),
            ('CDLTRISTAR', talib.CDLTRISTAR),
            ('CDLUNIQUE3RIVER', talib.CDLUNIQUE3RIVER),
            ('CDLUPSIDEGAP2CROWS', talib.CDLUPSIDEGAP2CROWS),
            ('CDLXSIDEGAP3METHODS', talib.CDLXSIDEGAP3METHODS),
        ]
        
        # 只添加部分常见的模式，避免特征过多
        common_patterns = ['CDLDOJI', 'CDLENGULFING', 'CDLMORNINGSTAR', 
                          'CDLEVENINGSTAR', 'CDLHAMMER', 'CDLSHOOTINGSTAR']
        
        for pattern_name, pattern_func in patterns:
            if pattern_name in common_patterns:
                try:
                    data[pattern_name] = pattern_func(open_prices, high_prices, low_prices, close_prices)
                except Exception as e:
                    logger.warning(f"价格模式识别失败 {pattern_name}: {e}")
                    data[pattern_name] = 0
        
        return data
    
    def _add_market_state(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加市场状态特征"""
        if 'close' not in data.columns:
            return data
        
        # 市场趋势
        data['trend_20'] = data['close'].rolling(20).mean() > data['close'].rolling(60).mean()
        data['trend_50'] = data['close'].rolling(50).mean() > data['close'].rolling(200).mean()
        
        # 市场波动状态
        volatility_20 = data['returns'].rolling(20).std()
        volatility_mean = volatility_20.mean()
        data['high_volatility'] = volatility_20 > volatility_mean * 1.5
        data['low_volatility'] = volatility_20 < volatility_mean * 0.5
        
        # 市场情绪（基于RSI）
        data['overbought'] = data['RSI_14'] > 70
        data['oversold'] = data['RSI_14'] < 30
        
        # 成交量异常
        if 'volume' in data.columns:
            volume_mean = data['volume'].rolling(20).mean()
            volume_std = data['volume'].rolling(20).std()
            data['high_volume'] = data['volume'] > (volume_mean + 2 * volume_std)
            data['low_volume'] = data['volume'] < (volume_mean - 2 * volume_std)
        
        return data
    
    def _add_target_variables(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加目标变量（未来收益率）"""
        if 'close' not in data.columns:
            return data
        
        # 未来1天收益率
        data['target_1d'] = data['close'].shift(-1) / data['close'] - 1
        
        # 未来3天收益率
        data['target_3d'] = data['close'].shift(-3) / data['close'] - 1
        
        # 未来5天收益率
        data['target_5d'] = data['close'].shift(-5) / data['close'] - 1
        
        # 未来10天收益率
        data['target_10d'] = data['close'].shift(-10) / data['close'] - 1
        
        # 分类目标：未来5天是否上涨（1表示上涨，0表示下跌）
        data['target_class_5d'] = (data['target_5d'] > 0).astype(int)
        
        return data
    
    def _handle_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 前向填充 - 使用现代 pandas 语法
        data = data.ffill()
        
        # 后向填充（处理开头缺失）- 使用现代 pandas 语法
        data = data.bfill()
        
        # 对于仍然缺失的值，用0填充（通常是技术指标）
        data = data.fillna(0)
        
        return data
    
    def prepare_features_for_training(self, data: pd.DataFrame, 
                                     feature_cols: List[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练特征
        
        Args:
            data: 处理后的数据
            feature_cols: 特征列列表，如果为None则使用所有数值列
            
        Returns:
            X: 特征DataFrame
            y: 目标DataFrame
        """
        # 如果没有指定特征列，使用所有数值列（排除目标列）
        if feature_cols is None:
            numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
            # 排除目标列
            target_cols = [col for col in numeric_cols if 'target' in col]
            feature_cols = [col for col in numeric_cols if col not in target_cols]
        
        # 分离特征和目标
        X = data[feature_cols].copy()
        
        # 可以有多个目标
        y_cols = [col for col in data.columns if 'target' in col]
        y = data[y_cols].copy() if y_cols else pd.DataFrame()
        
        # 移除包含缺失值的行
        valid_mask = X.notna().all(axis=1) & y.notna().all(axis=1)
        X = X[valid_mask]
        y = y[valid_mask]
        
        logger.info(f"准备训练数据: {X.shape[0]} 个样本, {X.shape[1]} 个特征")
        
        return X, y


# ========== 使用示例 ==========
if __name__ == "__main__":
    import os
    
    # 测试数据处理
    print("测试数据处理...")
    
    # 创建示例数据
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    sample_data = pd.DataFrame({
        'open': np.random.normal(100, 5, len(dates)),
        'high': np.random.normal(105, 5, len(dates)),
        'low': np.random.normal(95, 5, len(dates)),
        'close': np.random.normal(100, 5, len(dates)),
        'volume': np.random.lognormal(10, 1, len(dates))
    }, index=dates)
    
    processor = DataProcessor()
    processed_data = processor.process_raw_data(sample_data, "TEST")
    
    print(f"原始数据形状: {sample_data.shape}")
    print(f"处理后的数据形状: {processed_data.shape}")
    print(f"新增特征数量: {processed_data.shape[1] - sample_data.shape[1]}")
    
    # 查看特征
    print(f"\n前5个技术指标特征:")
    tech_cols = [col for col in processed_data.columns if any(x in col for x in ['SMA', 'EMA', 'MACD', 'RSI', 'BB'])]
    print(processed_data[tech_cols[:5]].head())
    
    # 准备训练数据
    X, y = processor.prepare_features_for_training(processed_data)
    print(f"\n训练特征形状: {X.shape}")
    print(f"目标变量形状: {y.shape}")