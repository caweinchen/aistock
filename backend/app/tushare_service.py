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
            # 直接使用token创建pro API，不保存到文件
            import tushare as ts
            self.pro = ts.pro_api(token)

    def set_token(self, token: str):
        """设置 Token"""
        import tushare as ts
        self.token = token
        self.pro = ts.pro_api(token)
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

    def get_daily_basic(self, ts_code: str, trade_date: str = None) -> Optional[Dict]:
        """
        获取每日基本面指标（PE、PB、PS、市值等）

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            trade_date: 交易日期，格式 YYYYMMDD，为空则取最新

        Returns:
            基本面指标数据
        """
        try:
            if not self.pro:
                return None

            if trade_date is None:
                trade_date = datetime.now().strftime('%Y%m%d')

            df = self.pro.daily_basic(ts_code=ts_code, trade_date=trade_date,
                                       fields='ts_code,trade_date,close,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,total_mv,circ_mv')
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'ts_code': row.get('ts_code'),
                    'trade_date': row.get('trade_date'),
                    'close': float(row.get('close', 0) or 0),
                    'pe': float(row.get('pe', 0) or 0),
                    'pe_ttm': float(row.get('pe_ttm', 0) or 0),
                    'pb': float(row.get('pb', 0) or 0),
                    'ps': float(row.get('ps', 0) or 0),
                    'ps_ttm': float(row.get('ps_ttm', 0) or 0),
                    'dv_ratio': float(row.get('dv_ratio', 0) or 0),  # 股息率
                    'total_mv': float(row.get('total_mv', 0) or 0),  # 总市值（万元）
                    'circ_mv': float(row.get('circ_mv', 0) or 0),    # 流通市值（万元）
                }
            return None
        except Exception as e:
            logger.error(f"获取每日基本面指标失败: {e}")
            return None

    def get_fina_indicator(self, ts_code: str, period: str = None) -> Optional[Dict]:
        """
        获取财务指标（ROE、净利润增长率、资产负债率等）

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            period: 报告期，如 '20231231'，为空则取最新

        Returns:
            财务指标数据
        """
        try:
            if not self.pro:
                return None

            df = self.pro.fina_indicator(ts_code=ts_code, period=period,
                                          fields='ts_code,ann_date,end_date,roe,roe_dt,netprofit_margin,grossprofit_margin,debt_to_assets,current_ratio,quick_ratio,ebit_of_gr,ocfps,bps,cfps,eps,dtprofit_margin,ebitps')
            if df is not None and not df.empty:
                # 取最新一条
                row = df.iloc[0]
                return {
                    'ts_code': row.get('ts_code'),
                    'period': row.get('end_date'),
                    'ann_date': row.get('ann_date'),
                    'roe': float(row.get('roe', 0) or 0),           # ROE
                    'roe_dt': float(row.get('roe_dt', 0) or 0),     # ROE(扣非)
                    'netprofit_margin': float(row.get('netprofit_margin', 0) or 0),  # 销售净利率
                    'grossprofit_margin': float(row.get('grossprofit_margin', 0) or 0),  # 销售毛利率
                    'debt_to_assets': float(row.get('debt_to_assets', 0) or 0),  # 资产负债率
                    'current_ratio': float(row.get('current_ratio', 0) or 0),    # 流动比率
                    'quick_ratio': float(row.get('quick_ratio', 0) or 0),        # 速动比率
                    'ebit_of_gr': float(row.get('ebit_of_gr', 0) or 0),          # EBIT/营业总收入
                    'ocfps': float(row.get('ocfps', 0) or 0),      # 每股经营现金流
                    'bps': float(row.get('bps', 0) or 0),          # 每股净资产
                    'cfps': float(row.get('cfps', 0) or 0),        # 每股现金流
                    'eps': float(row.get('eps', 0) or 0),          # 每股收益
                    'dtprofit_margin': float(row.get('dtprofit_margin', 0) or 0),  # 扣非净利率
                    'ebitps': float(row.get('ebitps', 0) or 0),    # 每股EBIT
                }
            return None
        except Exception as e:
            logger.error(f"获取财务指标失败: {e}")
            return None

    def get_moneyflow(self, ts_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        获取资金流向数据

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            资金流向数据列表
        """
        try:
            if not self.pro:
                return []

            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            df = self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date,
                                     fields='ts_code,trade_date,buy_sm_amount,sell_sm_amount,buy_md_amount,sell_md_amount,buy_lg_amount,sell_lg_amount,buy_elg_amount,sell_elg_amount,net_mf_amount,net_mf_vol')
            if df is not None and not df.empty:
                return df.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return []

    def get_dividend(self, ts_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        获取分红记录

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            分红记录列表
        """
        try:
            if not self.pro:
                return []

            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365 * 3)).strftime('%Y%m%d')

            df = self.pro.dividend(ts_code=ts_code, start_date=start_date, end_date=end_date,
                                    fields='ts_code,div_proc,ann_date,record_date,ex_date,pay_date,div_cash,bonus_share,transfer_share')
            if df is not None and not df.empty:
                results = []
                for _, row in df.iterrows():
                    results.append({
                        'ts_code': row.get('ts_code'),
                        'div_proc': row.get('div_proc', ''),       # 分红方案
                        'ann_date': row.get('ann_date', ''),       # 公告日期
                        'record_date': row.get('record_date', ''), # 股权登记日
                        'ex_date': row.get('ex_date', ''),         # 除权除息日
                        'pay_date': row.get('pay_date', ''),       # 派息日
                        'div_cash': float(row.get('div_cash', 0) or 0),   # 每股现金分红（元）
                        'bonus_share': float(row.get('bonus_share', 0) or 0), # 每股送股数
                        'transfer_share': float(row.get('transfer_share', 0) or 0), # 每股转增数
                    })
                return results
            return []
        except Exception as e:
            logger.error(f"获取分红记录失败: {e}")
            return []

    def get_stock_news(self, ts_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        获取股票重大事件/新闻

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            重大事件/新闻列表
        """
        try:
            if not self.pro:
                return []

            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')

            # Use documented pro API 'news' when available
            try:
                df = self.pro.news(ts_code=ts_code, start_date=start_date, end_date=end_date)
            except Exception:
                # Fallback to older/stk_news if present
                df = getattr(self.pro, 'stk_news')(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is not None and not df.empty:
                results = []
                for _, row in df.iterrows():
                    # Different pro endpoints may use different column names
                    pub_time = row.get('pub_time') or row.get('datetime') or row.get('time') or ''
                    results.append({
                        'ts_code': ts_code,
                        'title': row.get('title', ''),
                        'content': row.get('content', ''),
                        'pub_time': pub_time,
                        'src': row.get('src') or row.get('channels') or '',
                    })
                return results
            return []
        except Exception as e:
            logger.error(f"获取股票新闻失败: {e}")
            return []

    def get_adj_factor(self, ts_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        获取除权除息信息（重大事件相关）

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            除权除息信息列表
        """
        try:
            if not self.pro:
                return []

            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            df = self.pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                return df.to_dict('records')
            return []
        except Exception as e:
            logger.error(f"获取除权除息信息失败: {e}")
            return []

    def get_inst_hold(self, ts_code: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        获取机构持仓数据（按时间倒序）

        Args:
            ts_code: 股票代码，如 '000001.SZ'
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD

        Returns:
            机构持仓记录列表（按时间倒序）
        """
        try:
            if not self.pro:
                return []

            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

            # Use top10_holders API when available (documented)
            try:
                df = self.pro.top10_holders(ts_code=ts_code, start_date=start_date, end_date=end_date)
            except Exception:
                # Fallback to inst_hold if top10_holders not present
                df = getattr(self.pro, 'inst_hold')(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is not None and not df.empty:
                # top10_holders returns end_date as the holding period end
                results = []
                for _, row in df.iterrows():
                    trade_date = row.get('end_date') or row.get('trade_date') or ''
                    results.append({
                        'ts_code': ts_code,
                        'trade_date': trade_date,
                        'holder_name': row.get('holder_name') or row.get('holder_name') or '',
                        'hold_amount': float(row.get('hold_amount', 0) or 0),
                        'hold_ratio': float(row.get('hold_ratio', 0) or 0),
                        'hold_change': float(row.get('hold_change', 0) or 0),
                    })
                # sort descending by trade_date if available
                try:
                    results.sort(key=lambda r: r.get('trade_date', ''), reverse=True)
                except Exception:
                    pass
                return results
            return []
        except Exception as e:
            logger.error(f"获取机构持仓数据失败: {e}")
            return []

    # 交易日历缓存：{ "YYYYMM": set(交易日字符串) }
    _trade_cal_cache: Dict[str, set] = {}

    def get_trade_calendar(self, year: int, month: int) -> set:
        """
        获取指定年月的交易日历（带缓存）

        Args:
            year: 年份，如 2026
            month: 月份，1-12

        Returns:
            该月所有交易日的集合，格式 {"YYYYMMDD", ...}
        """
        cache_key = f"{year}{month:02d}"
        if cache_key in self._trade_cal_cache:
            return self._trade_cal_cache[cache_key]

        try:
            if not self.pro:
                logger.warning("TuShare Pro 未初始化，无法获取交易日历")
                return set()

            start_date = f"{year}{month:02d}01"
            if month == 12:
                end_date = f"{year}1231"
            else:
                end_date = f"{year}{(month + 1):02d}01"

            df = self.pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return set()

            trading_days = set()
            for _, row in df.iterrows():
                if row.get('is_open') == 1:
                    trade_date = str(row.get('cal_date', ''))
                    if trade_date:
                        trading_days.add(trade_date)

            self._trade_cal_cache[cache_key] = trading_days
            logger.info(f"已缓存 {year}年{month}月交易日历: {len(trading_days)} 个交易日")
            return trading_days
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            return set()

    def is_trading_day(self, date_obj: datetime = None) -> bool:
        """
        判断指定日期是否为交易日（考虑法定节假日）

        Args:
            date_obj: 日期对象，为空则取今天

        Returns:
            True 如果是交易日
        """
        if date_obj is None:
            date_obj = datetime.now()

        weekday = date_obj.weekday()
        if weekday >= 5:
            return False

        trading_days = self.get_trade_calendar(date_obj.year, date_obj.month)
        if not trading_days:
            return True

        date_str = date_obj.strftime('%Y%m%d')
        return date_str in trading_days

    def get_previous_trading_day(self, date_obj: datetime = None) -> datetime:
        """
        获取上一个交易日

        Args:
            date_obj: 起始日期，为空则取今天

        Returns:
            上一个交易日的 datetime 对象
        """
        if date_obj is None:
            date_obj = datetime.now()

        previous = date_obj - timedelta(days=1)
        while previous.weekday() >= 5 or not self.is_trading_day(previous):
            previous -= timedelta(days=1)
            if (date_obj - previous).days > 30:
                previous = date_obj - timedelta(days=1)
                while previous.weekday() >= 5:
                    previous -= timedelta(days=1)
                break

        return previous


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
