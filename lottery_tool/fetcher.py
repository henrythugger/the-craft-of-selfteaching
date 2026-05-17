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
    從台灣彩券官網抓今彩539開獎歷史。
    使用民國年（ROC +1911 = 西元年）。

    若官網改版導致爬蟲失敗，請手動把資料填入 data/lottery539.json
    或至下方網址手動複製：
    https://www.taiwanlottery.com.tw/Lotto/539/history.aspx
    """

    URL = "https://www.taiwanlottery.com.tw/Lotto/539/history.aspx"

    def fetch_recent(self, count: int = 30) -> list[dict]:
        end   = date.today()
        start = end - timedelta(days=count + 15)  # 多抓幾天，扣掉非開獎日

        session = _session()
        try:
            # Step 1: GET 取得 ASP.NET 隱藏欄位
            get_kw = {"impersonate": _IMPERSONATE} if _USE_CFFI else {}
            r = session.get(self.URL, headers=_HEADERS, timeout=15, **get_kw)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            roc_y1 = start.year - 1911
            roc_y2 = end.year   - 1911

            # Step 2: 建立 POST 資料（欄位名稱依官網 form 控制項）
            post_data = {
                "__VIEWSTATE":          self._field(soup, "__VIEWSTATE"),
                "__VIEWSTATEGENERATOR": self._field(soup, "__VIEWSTATEGENERATOR"),
                "__EVENTVALIDATION":    self._field(soup, "__EVENTVALIDATION"),
                # 開始日期
                "D539Control_history1$dropYear":   str(roc_y1),
                "D539Control_history1$dropMonth":  str(start.month),
                "D539Control_history1$startDay":   str(start.day),
                # 結束日期
                "D539Control_history1$dropYear2":  str(roc_y2),
                "D539Control_history1$dropMonth2": str(end.month),
                "D539Control_history1$endDay":     str(end.day),
                # 查詢按鈕
                "D539Control_history1$btnSubmit":  "查詢",
            }

            post_kw = {"impersonate": _IMPERSONATE} if _USE_CFFI else {}
            r2 = session.post(self.URL, data=post_data, headers=_HEADERS, timeout=20, **post_kw)
            r2.raise_for_status()
            soup2 = BeautifulSoup(r2.text, "lxml")
            results = self._parse_table(soup2, count)

            if not results:
                print(
                    "  [539] 查詢成功但解析不到資料，官網可能已改版。\n"
                    "  → 請手動把資料填入 data/lottery539.json"
                )
            return results

        except Exception as exc:
            print(
                f"  [539] 爬蟲失敗：{exc}\n"
                "  → 請手動把資料填入 data/lottery539.json"
            )
            return []

    @staticmethod
    def _field(soup, name: str) -> str:
        tag = soup.find("input", {"name": name})
        return tag["value"] if tag else ""

    def _parse_table(self, soup, count: int) -> list[dict]:
        # 嘗試多種 table 選擇器
        table = (
            soup.find("table", id=re.compile(r"history", re.I)) or
            soup.find("table", class_=re.compile(r"table_history|tblHistory", re.I))
        )
        if not table:
            for t in soup.find_all("table"):
                if "期別" in t.get_text() or "開獎號碼" in t.get_text():
                    table = t
                    break
        if not table:
            return []

        draws = []
        for row in table.find_all("tr")[1:]:
            d = self._parse_row(row)
            if d:
                draws.append(d)
            if len(draws) >= count:
                break
        return draws

    def _parse_row(self, row) -> dict | None:
        cells = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cells) < 3:
            return None
        try:
            period = int(re.sub(r"\D", "", cells[0]))
            roc_parts = re.findall(r"\d+", cells[1])
            if len(roc_parts) < 3:
                return None
            year  = int(roc_parts[0]) + 1911
            month = int(roc_parts[1])
            day   = int(roc_parts[2])
            draw_date = f"{year:04d}-{month:02d}-{day:02d}"

            # 嘗試從各 td 直接讀號碼
            nums: list[int] = []
            if len(cells) >= 7:
                for i in range(2, 7):
                    if cells[i].isdigit() and 1 <= int(cells[i]) <= 39:
                        nums.append(int(cells[i]))
            # 若讀不到，從 cells[2] 用 regex 撈
            if len(nums) != 5:
                raw = " ".join(cells[2:7])
                nums = [
                    int(x) for x in re.findall(r"\b([1-9]|[1-3]\d)\b", raw)
                    if 1 <= int(x) <= 39
                ]
            numbers = sorted(set(nums))[:5]
            if len(numbers) != 5:
                return None
            return {"date": draw_date, "period": period, "numbers": numbers}
        except (ValueError, IndexError):
            return None
