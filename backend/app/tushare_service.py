"""
TuShare 数据服务层
提供股票行情数据接口
"""
import tushare as ts
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TuShareService:
    """TuShare 数据服务"""

    def __init__(self, token: str = None):
        """
        初始化 TuShare 服务

        Args:
            token: TuShare Token，为空则使用免费版
        """
        self.token = token
        self.pro = None
        if token:
            ts.set_token(token)
            self.pro = ts.pro_api()

    def set_token(self, token: str):
        """设置 Token"""
        self.token = token
        ts.set_token(token)
        self.pro = ts.pro_api()
        logger.info("TuShare Token 已设置")

    def get_stock_basic(self, ts_code: str = None) -> List[Dict]:
        """
        获取股票基本信息

        Args:
            ts_code: 股票代码，如 '000001.SZ'，为空则返回所有

        Returns:
            股票基本信息列表
        """
        try:
            if self.pro:
                df = self.pro.stock_basic(ts_code=ts_code, fields='ts_code,symbol,name,area,industry,list_date')
            else:
                df = ts.get_stock_basics()
                if df is not None and not df.empty:
                    df = df.reset_index()
                    df.columns = ['ts_code', 'name', 'industry', 'area', 'list_date']
                else:
                    return []

            if df is not None and not df.empty:
                return df.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            return []

    def get_daily_price(self, ts_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        获取日线行情数据

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            日线行情列表
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            if self.pro:
                df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                # 免费版使用旧接口
                symbol = ts_code.split('.')[0]
                df = ts.get_k_data(symbol, start=start_date[:4]+'-'+start_date[4:6]+'-'+start_date[6:],
                                   end=end_date[:4]+'-'+end_date[4:6]+'-'+end_date[6:])

            if df is not None and not df.empty:
                return df.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"获取日线行情失败: {e}")
            return []

    def get_realtime_quote(self, ts_code: str) -> Optional[Dict]:
        """
        获取实时行情

        Args:
            ts_code: 股票代码，如 '000001.SZ'

        Returns:
            实时行情数据
        """
        try:
            symbol = ts_code.split('.')[0]
            df = ts.get_realtime_quote(symbol=symbol)

            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'ts_code': ts_code,
                    'name': row.get('name', ''),
                    'price': float(row.get('price', 0)),
                    'change': float(row.get('price', 0)) - float(row.get('pre_close', 0)),
                    'change_pct': ((float(row.get('price', 0)) - float(row.get('pre_close', 0))) / float(row.get('pre_close', 1))) * 100,
                    'volume': int(row.get('volume', 0)),
                    'amount': float(row.get('amount', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'open': float(row.get('open', 0)),
                    'pre_close': float(row.get('pre_close', 0)),
                    'bid': float(row.get('bid', 0)),
                    'ask': float(row.get('ask', 0)),
                    'timestamp': datetime.now().isoformat()
                }
            return None
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return None

    def search_stocks(self, keyword: str) -> List[Dict]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词（代码或名称）

        Returns:
            匹配的股票列表
        """
        try:
            if self.pro:
                # 使用 pro 版搜索
                df = self.pro.stock_basic(list_status='L', fields='ts_code,symbol,name,industry')
                if df is not None and not df.empty:
                    # 模糊搜索
                    mask = df['symbol'].str.contains(keyword, case=False) | \
                           df['name'].str.contains(keyword, case=False)
                    results = df[mask].head(20).to_dict('records')
                    return results
            else:
                # 免费版使用股票列表
                df = ts.get_stock_basics()
                if df is not None and not df.empty:
                    df = df.reset_index()
                    mask = df['code'].str.contains(keyword, case=False) | \
                           df['name'].str.contains(keyword, case=False)
                    results = df[mask][['code', 'name', 'industry']].head(20).to_dict('records')
                    # 转换格式
                    for r in results:
                        r['ts_code'] = r.pop('code') + ('.SZ' if r['code'].startswith(('0', '3')) else '.SH')
                    return results
            return []
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []

    def get_index_component(self, index_code: str = '000300.SH') -> List[str]:
        """
        获取指数成分股

        Args:
            index_code: 指数代码，如 '000300.SH'（沪深300）

        Returns:
            成分股代码列表
        """
        try:
            if self.pro:
                df = self.pro.index_weight(index_code=index_code)
                if df is not None and not df.empty:
                    return df['con_code'].tolist()
            return []
        except Exception as e:
            logger.error(f"获取指数成分股失败: {e}")
            return []


# 全局实例
_tushare_service = None


def get_tushare_service() -> TuShareService:
    """获取 TuShare 服务实例"""
    global _tushare_service
    if _tushare_service is None:
        _tushare_service = TuShareService()
    return _tushare_service


def init_tushare(token: str = None):
    """初始化 TuShare 服务"""
    global _tushare_service
    _tushare_service = TuShareService(token)
    return _tushare_service
