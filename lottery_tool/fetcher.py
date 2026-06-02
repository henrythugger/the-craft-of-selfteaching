"""
網路爬蟲：California Fantasy 5 + 台灣今彩539

若爬蟲失敗，請手動把資料填入 data/fantasy5.json 或 data/lottery539.json：
[
  {"date": "2026-05-15", "period": 11877, "numbers": [1, 8, 31, 32, 38]},
  ...
]
"""

import re
import json
from datetime import date, timedelta
from bs4 import BeautifulSoup

# 優先使用 curl-cffi（模擬真實瀏覽器 TLS 指紋，繞過部分反爬蟲）
# 若未安裝則退回標準 requests
try:
    from curl_cffi import requests
    _IMPERSONATE = "chrome"   # 模擬 Chrome 的 TLS/HTTP2 指紋
    _USE_CFFI = True
except ImportError:
    import requests
    _IMPERSONATE = None
    _USE_CFFI = False

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/html, */*",
    "Referer": "https://www.google.com/",
}


def _get(url, **kwargs):
    """統一 GET，自動使用 curl-cffi 或 requests"""
    if _USE_CFFI:
        return requests.get(url, headers=_HEADERS, impersonate=_IMPERSONATE,
                            timeout=15, **kwargs)
    return requests.get(url, headers=_HEADERS, timeout=15, **kwargs)


def _session():
    """建立 Session（curl-cffi 或 requests 均相容）"""
    if _USE_CFFI:
        return requests.Session()
    import requests as _req
    s = _req.Session()
    s.headers.update(_HEADERS)
    return s


# ─────────────────────────────────────────────
# California Fantasy 5
# ─────────────────────────────────────────────

class Fantasy5Fetcher:
    """
    從 calottery.com 抓 Fantasy 5 開獎資料。
    先嘗試 JSON API，失敗再嘗試 HTML 解析。

    API gameId=19 是 Fantasy 5（若官方更改請同步修改）。
    """

    # CA Lottery 內部 API（可能隨時改版）
    API = (
        "https://www.calottery.com/api/DrawGameApi/DrawHistory"
        "?gameId=19&languageId=0&pageNumber={page}&pageSize=20"
    )
    HTML_URL = "https://www.calottery.com/draw-games/fantasy-5"

    def fetch_recent(self, count: int = 30) -> list[dict]:
        draws, page = [], 1
        while len(draws) < count:
            try:
                url = self.API.format(page=page)
                r = _get(url)
                r.raise_for_status()
                items = r.json().get("DrawHistory") or r.json().get("drawHistory") or []
                if not items:
                    break
                for item in items:
                    d = self._parse_api(item)
                    if d:
                        draws.append(d)
                page += 1
            except Exception as exc:
                print(f"  [Fantasy5] API 失敗（{exc}），改用 HTML 爬蟲...")
                return self._html_fallback(count)
        return draws[:count]

    def _parse_api(self, item: dict) -> dict | None:
        try:
            raw = item.get("WinningNumbers") or item.get("winningNumbers", "")
            nums = sorted(int(x) for x in re.findall(r"\d+", str(raw)) if 1 <= int(x) <= 39)
            if len(nums) != 5:
                return None
            draw_date = str(item.get("DrawDate") or item.get("drawDate", ""))[:10]
            period = int(item.get("DrawOrder") or item.get("drawOrder") or 0)
            return {"date": draw_date, "period": period, "numbers": nums}
        except (ValueError, TypeError):
            return None

    def _html_fallback(self, count: int) -> list[dict]:
        try:
            r = _get(self.HTML_URL)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            draws = []
            for block in soup.select(
                ".draw-result, .winning-numbers-result, "
                "[class*='DrawResult'], [class*='drawResult']"
            ):
                d = self._parse_html_block(block)
                if d:
                    draws.append(d)
            if not draws:
                print(
                    "  [Fantasy5] HTML 也沒有解析到資料。\n"
                    "  → 請手動把資料填入 data/fantasy5.json"
                )
            return draws[:count]
        except Exception as exc:
            print(f"  [Fantasy5] HTML 爬蟲失敗：{exc}")
            return []

    def _parse_html_block(self, block) -> dict | None:
        try:
            nums = sorted(
                int(n.get_text(strip=True))
                for n in block.select(".number, .ball, [class*='Ball'], [class*='ball']")
                if n.get_text(strip=True).isdigit()
            )
            nums = [n for n in nums if 1 <= n <= 39]
            if len(nums) != 5:
                return None
            date_tag = block.select_one(".draw-date, .date, [class*='Date'], [class*='date']")
            draw_date = date_tag.get_text(strip=True) if date_tag else ""
            return {"date": draw_date, "period": 0, "numbers": nums}
        except (ValueError, AttributeError):
            return None


# ─────────────────────────────────────────────
# 台灣今彩 539
# ─────────────────────────────────────────────

class Lottery539Fetcher:
    """
    從台灣彩券官方 JSON API 抓今彩539開獎歷史。
    來源：https://github.com/stu01509/TaiwanLotteryCrawler

    API：https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result
         ?period&month=YYYY-MM&pageSize=31
    """

    API = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"

    def fetch_recent(self, count: int = 30) -> list[dict]:
        today = date.today()
        draws: list[dict] = []

        # 從本月往前推，每次查一個月，直到累積足夠期數
        year, month = today.year, today.month
        months_tried = 0

        while len(draws) < count and months_tried < 6:
            url = f"{self.API}?period&month={year}-{month:02d}&pageSize=31"
            try:
                r = _get(url)
                r.raise_for_status()
                data = r.json()
                items = data.get("content", {}).get("daily539Res", [])
                for item in items:
                    d = self._parse(item)
                    if d:
                        draws.append(d)
            except Exception as exc:
                print(f"  [539] API 失敗 ({year}-{month:02d})：{exc}")

            # 往前推一個月
            month -= 1
            if month == 0:
                month = 12
                year -= 1
            months_tried += 1

        # 依期號由新到舊排序
        draws.sort(key=lambda x: x["period"], reverse=True)
        return draws[:count]

    def _parse(self, item: dict) -> dict | None:
        try:
            period  = int(item["period"])
            raw_date = item["lotteryDate"][:10]   # "2026-05-15T..."
            numbers = sorted(int(n) for n in item["drawNumberSize"] if 1 <= int(n) <= 39)
            if len(numbers) != 5:
                return None
            return {"date": raw_date, "period": period, "numbers": numbers}
        except (KeyError, ValueError, TypeError):
            return None

