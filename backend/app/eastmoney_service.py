import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class EastMoneyService:
    """Realtime quote and stock-search service for China A-shares."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": "https://quote.eastmoney.com/",
        })

    def get_realtime_quote(self, codes: List[str]) -> List[Dict]:
        if not codes:
            return []

        try:
            symbols = [_to_sina_symbol(code) for code in codes]
            response = self.session.get(
                f"https://hq.sinajs.cn/list={','.join(symbols)}",
                headers={
                    "Referer": "https://finance.sina.com.cn/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
                timeout=15,
            )
            response.raise_for_status()
            response.encoding = "gbk"

            stocks = []
            for line in response.text.strip().split("\n"):
                if not line or "=" not in line:
                    continue

                symbol = line.split("=", 1)[0].split("_")[-1].replace('"', "")
                data_str = line.split("=", 1)[1].strip('";\n\r')
                fields = data_str.split(",") if data_str else []
                if len(fields) < 10:
                    continue

                prev_close = _to_float(fields[2])
                current_price = _to_float(fields[3])
                change = current_price - prev_close
                code = symbol[2:] if symbol.startswith(("sh", "sz")) else symbol

                stocks.append({
                    "code": code,
                    "name": fields[0],
                    "price": current_price,
                    "change_percent": (change / prev_close * 100) if prev_close > 0 else 0,
                    "volume": int(_to_float(fields[8])),
                    "high": _to_float(fields[4]),
                    "low": _to_float(fields[5]),
                    "open": _to_float(fields[1]),
                    "pre_close": prev_close,
                    "timestamp": datetime.now().isoformat(),
                })

            return stocks
        except Exception as exc:
            logger.error("Failed to fetch realtime quotes: %s", exc)
            return []

    def search_stocks(self, keyword: str) -> List[Dict]:
        if not keyword:
            return []

        try:
            response = self.session.get(
                "https://searchapi.eastmoney.com/api/suggest/get",
                params={
                    "input": keyword,
                    "type": "14",
                    "token": "D43BF722C8E33BDC906FB84D85E326E8",
                    "count": 10,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("QuotationCodeTable", {}).get("Data", []):
                code = item.get("Code", "")
                name = item.get("Name", "")
                if not code or not name or not _is_a_share(code):
                    continue

                market = "SH" if code.startswith(("600", "601", "603", "605", "688")) else "SZ"
                results.append({
                    "code": code,
                    "name": name,
                    "ts_code": f"{code}.{market}",
                    "market": market,
                })
                if len(results) >= 10:
                    break

            return results
        except Exception as exc:
            logger.error("Failed to search stocks: %s", exc)
            return []

    def get_stock_info(self, code: str) -> Optional[Dict]:
        quotes = self.get_realtime_quote([code])
        return quotes[0] if quotes else None


_eastmoney_service: EastMoneyService | None = None


def get_eastmoney_service() -> EastMoneyService:
    global _eastmoney_service
    if _eastmoney_service is None:
        _eastmoney_service = EastMoneyService()
    return _eastmoney_service


def init_eastmoney() -> EastMoneyService:
    global _eastmoney_service
    _eastmoney_service = EastMoneyService()
    return _eastmoney_service


def get_stock_info_by_code(code: str) -> Optional[Dict]:
    session = requests.Session()
    session.headers.update({
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })

    try:
        response = session.get(f"https://hq.sinajs.cn/list={_to_sina_symbol(code)}", timeout=10)
        response.raise_for_status()
        response.encoding = "gbk"
        if "=" not in response.text:
            return None

        data_str = response.text.split("=", 1)[1].strip('";\n\r')
        fields = data_str.split(",") if data_str else []
        if len(fields) < 10:
            return None

        market = "SH" if code.startswith(("6", "5", "9")) else "SZ"
        return {
            "code": code,
            "name": fields[0],
            "ts_code": f"{code}.{market}",
            "market": market,
        }
    except Exception as exc:
        logger.error("Failed to fetch stock info for %s: %s", code, exc)
        return None


def _is_a_share(code: str) -> bool:
    return code.startswith(("600", "601", "603", "605", "000", "001", "002", "300", "688"))


def _to_sina_symbol(code: str) -> str:
    return f"sh{code}" if code.startswith(("6", "5", "9")) else f"sz{code}"


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
