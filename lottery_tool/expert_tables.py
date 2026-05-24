"""
專家版路表（最高權重）

圖1：精準尾數表（彩卷精準尾數 三/四星專用）
  依「開獎日期的日數個位數」決定主尾與高機率尾
  使用方式：先鎖定尾數，再從遺漏/拖牌中找符合的號碼

圖2：今彩1拖3固定拖牌法（2022版）
  上期開出號碼X → 下期必有 DRAG_TABLE[X] 其中之一出現
  使用方式：把上期5顆號碼的拖牌候選池撈出，取交集或高頻
"""

# ── 圖1：精準尾數表 ─────────────────────────────────────────
# key = 開獎日期的「日數個位數」（0代表10/20/30號）
# value = {"main": [主尾...], "high": [高機率尾...]}

TAIL_BY_DAY = {
    1: {"main": [1, 6],    "high": [2, 7, 8, 0]},
    2: {"main": [2, 7],    "high": [1, 5, 9, 0]},
    3: {"main": [3, 8],    "high": [3, 5, 8]},
    4: {"main": [4, 9],    "high": [3, 7]},
    5: {"main": [5, 0],    "high": [2, 8]},
    6: {"main": [6, 1],    "high": [3, 9]},
    7: {"main": [7, 2],    "high": [3, 5, 6, 7]},
    8: {"main": [8, 3],    "high": [0]},
    9: {"main": [9, 4],    "high": [1, 7]},
    0: {"main": [0, 5],    "high": [1, 3, 8]},   # 10/20/30號
}


def get_tail_rule(draw_date: str) -> dict:
    """
    輸入開獎日期（YYYY-MM-DD），回傳當天適用的尾數規則。
    例：2026-05-16 → day=16 → 個位=6 → main=[6,1], high=[3,9]
    """
    try:
        day = int(draw_date.split("-")[2])
        key = day % 10  # 個位數；10/20/30 → key=0
        return TAIL_BY_DAY.get(key, {})
    except (IndexError, ValueError):
        return {}


def get_all_tails(draw_date: str) -> list[int]:
    """回傳主尾+高機率尾的合集（去重）"""
    rule = get_tail_rule(draw_date)
    combined = rule.get("main", []) + rule.get("high", [])
    return list(dict.fromkeys(combined))  # 保持順序去重


# ── 圖2：1拖3固定拖牌法 ─────────────────────────────────────
# DRAG_TABLE[n] = 上期開出n號後，下期最可能出現的3顆

DRAG_TABLE: dict[int, list[int]] = {
     1: [ 6, 12, 18],
     2: [ 7, 14, 21],
     3: [22, 30, 38],
     4: [17, 26, 35],
     5: [32, 33, 34],
     6: [ 9, 11, 13],
     7: [25, 28, 31],
     8: [ 5, 10, 15],
     9: [16, 20, 24],
    10: [19, 29, 39],
    11: [ 2, 23, 27],
    12: [ 3,  8, 36],
    13: [ 1,  4, 27],
    14: [15, 26, 37],
    15: [ 9, 24, 38],
    16: [ 2, 23, 33],
    17: [18, 27, 36],
    18: [ 5, 22, 32],
    19: [11, 16, 34],
    20: [ 4, 13, 31],
    21: [19, 28, 35],
    22: [ 6, 14, 29],
    23: [ 3, 20, 21],
    24: [ 1,  7, 30],
    25: [ 8, 12, 39],
    26: [10, 17, 25],
    27: [10, 18, 26],
    28: [16, 24, 33],
    29: [ 4, 21, 36],
    30: [ 7, 28, 39],
    31: [ 2,  8, 13],
    32: [14, 19, 37],
    33: [ 6, 25, 34],
    34: [12, 23, 35],
    35: [ 1, 22, 31],
    36: [ 3, 15, 32],
    37: [ 5, 17, 27],
    38: [ 9, 11, 30],
    39: [20, 29, 38],
}


def get_drag_candidates(last_draw_numbers: list[int]) -> dict:
    """
    輸入上期5顆號碼，回傳：
    - candidates: 所有拖牌候選號碼（去重）
    - freq: 每顆候選號被幾顆上期號碼拖到（頻率越高越強）
    - sources: 每顆候選號是被哪些上期號碼拖到的
    """
    freq: dict[int, int] = {}
    sources: dict[int, list[int]] = {}

    for n in last_draw_numbers:
        for drag_num in DRAG_TABLE.get(n, []):
            freq[drag_num] = freq.get(drag_num, 0) + 1
            sources.setdefault(drag_num, []).append(n)

    # 依頻率排序
    candidates = sorted(freq.keys(), key=lambda x: -freq[x])
    return {
        "candidates": candidates,
        "freq":       freq,
        "sources":    sources,
    }
