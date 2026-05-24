"""
六維度版路分析引擎（整合專家版路表）
適用於任何 1-39 選 5 的彩種（Fantasy 5 / 今彩539）

專家表權重最高：
  圖1 精準尾數表 — 依開獎日鎖定主尾/高機率尾
  圖2 1拖3固定拖牌法 — 上期號碼的固定拖牌候選池
"""

from collections import Counter, defaultdict
from datetime import date, timedelta
from expert_tables import get_tail_rule, get_drag_candidates, DRAG_TABLE


# ── 工具 ──────────────────────────────────────
def _tail(n: int) -> int:
    return n % 10

def _zone(n: int) -> str:
    if n <= 13:  return "low"
    if n <= 26:  return "mid"
    return "high"


# ── 主分析函式 ────────────────────────────────
def analyze(draws: list[dict], game_range: int = 39) -> dict:
    """
    draws: 依期號由新到舊排序的開獎資料清單
    回傳完整六維度 + 專家表分析結果 dict
    """
    if not draws:
        return {}

    n_draws = len(draws)

    # ─── 專家表分析（最高權重）───────────────────
    latest_date   = draws[0]["date"]
    last_numbers  = draws[0]["numbers"]

    # 推算「下一期」的開獎日（+1天，實際可依彩種調整）
    next_date = (date.fromisoformat(latest_date) + timedelta(days=1)).isoformat()

    # 圖1：依下期日期鎖定主尾/高機率尾
    tail_rule     = get_tail_rule(next_date)

    # 圖2：上期號碼的固定拖牌候選
    drag_expert   = get_drag_candidates(last_numbers)

    expert_result = {
        "next_draw_date":   next_date,
        "tail_rule": {
            "day_digit":  int(next_date.split("-")[2]) % 10,
            "main_tails": tail_rule.get("main", []),
            "high_tails": tail_rule.get("high", []),
        },
        "drag_1to3": {
            "last_numbers":  last_numbers,
            "candidates":    drag_expert["candidates"],
            "freq":          drag_expert["freq"],
            "sources":       drag_expert["sources"],
        },
    }

    # ─── 六維度分析 ──────────────────────────────
    tail_result    = _tail_analysis(draws)
    missing_result = _missing_analysis(draws, game_range)
    drag_result    = _drag_analysis(draws)
    zone_result    = _zone_analysis(draws)
    oe_result      = _odd_even_analysis(draws)

    # ⑥ 綜合推薦（傳入專家表結果）
    recs = _recommend(tail_result, missing_result, drag_result,
                      zone_result, oe_result, expert_result)

    return {
        "summary": {
            "total_periods": n_draws,
            "date_range": {"from": draws[-1]["date"], "to": draws[0]["date"]},
        },
        "expert":   expert_result,
        "tail":     tail_result,
        "missing":  missing_result,
        "drag":     drag_result,
        "zone":     zone_result,
        "odd_even": oe_result,
        "recommend": recs,
    }


# ── ① 尾數 ───────────────────────────────────
def _tail_analysis(draws: list[dict]) -> dict:
    counter   = Counter()
    tail_nums = defaultdict(set)
    # 計算每個尾數最後出現是哪一期（index）
    last_seen_idx = {}

    for idx, draw in enumerate(draws):
        for n in draw["numbers"]:
            t = _tail(n)
            counter[t] += 1
            tail_nums[t].add(n)
            if t not in last_seen_idx:
                last_seen_idx[t] = idx

    total = sum(counter.values())
    avg   = total / 10  # 10 個尾數

    result = {}
    for t in range(10):
        cnt  = counter.get(t, 0)
        last = last_seen_idx.get(t, len(draws))
        if cnt >= avg * 1.3:
            status = "hot"
        elif cnt <= avg * 0.5:
            status = "cold"
        else:
            status = "normal"

        # 冷尾補回訊號：遺漏 ≥ 8 期
        comeback = (status == "cold" and last >= 8)

        result[t] = {
            "count":       cnt,
            "status":      status,
            "last_seen_periods_ago": last,
            "comeback_signal": comeback,
            "numbers":     sorted(tail_nums.get(t, [])),
        }
    return result


# ── ② 遺漏 ───────────────────────────────────
def _missing_analysis(draws: list[dict], game_range: int) -> dict:
    last_seen: dict[int, int] = {}
    for idx, draw in enumerate(draws):
        for n in draw["numbers"]:
            if n not in last_seen:
                last_seen[n] = idx

    result = {}
    for n in range(1, game_range + 1):
        miss = last_seen.get(n, len(draws))
        t    = _tail(n)
        result[n] = {
            "missing_periods": miss,
            "tail": t,
        }
    return result


# ── ③ 拖牌 ───────────────────────────────────
def _drag_analysis(draws: list[dict]) -> dict:
    """
    「拖牌」＝連續 2 期（含）以上出現同一號碼。
    掃描各號碼的出現 index 序列，找連拖段。
    """
    num_periods: dict[int, list[int]] = defaultdict(list)
    for idx, draw in enumerate(draws):
        for n in draw["numbers"]:
            num_periods[n].append(idx)

    currently_dragging = []
    recently_stopped   = []

    for n, idxs in sorted(num_periods.items()):
        # 找所有連拖段
        runs: list[list[int]] = []
        run = [idxs[0]]
        for j in range(1, len(idxs)):
            if idxs[j] == idxs[j - 1] + 1:
                run.append(idxs[j])
            else:
                if len(run) >= 2:
                    runs.append(run)
                run = [idxs[j]]
        if len(run) >= 2:
            runs.append(run)

        if not runs:
            continue

        # runs 是按 index 由小到大排列（index 小 = 最新期）
        # 取「最近一段」連拖：runs[0] 是最新的連拖段
        recent_run      = runs[0]
        recent_run_start = recent_run[0]   # 連拖中最新期的 index
        recent_run_end   = recent_run[-1]  # 連拖中最舊期的 index

        if recent_run_start == 0:
            # 連拖段包含最新期 → 目前在拖
            currently_dragging.append({
                "number":              n,
                "consecutive_periods": len(recent_run),
                "last_seen":           draws[0]["date"],
            })
        elif recent_run_start <= 5:
            # 連拖段在最近 5 期內斷拖 → 可能回馬槍
            stopped_ago = recent_run_start  # 距今幾期前斷拖
            if stopped_ago <= 3:
                risk = "high"
            elif stopped_ago <= 5:
                risk = "medium"
            else:
                risk = "low"
            recently_stopped.append({
                "number":           n,
                "stopped_periods_ago": stopped_ago,
                "comeback_risk":    risk,
            })

    return {
        "currently_dragging": sorted(currently_dragging, key=lambda x: -x["consecutive_periods"]),
        "recently_stopped":   sorted(recently_stopped,   key=lambda x: -{"high": 3, "medium": 2, "low": 1}[x["comeback_risk"]]),
    }


# ── ④ 區間分布 ────────────────────────────────
def _zone_analysis(draws: list[dict]) -> dict:
    recent10 = draws[:10]
    trend = []
    low_sum = mid_sum = high_sum = 0

    for draw in recent10:
        lo = sum(1 for n in draw["numbers"] if _zone(n) == "low")
        mi = sum(1 for n in draw["numbers"] if _zone(n) == "mid")
        hi = sum(1 for n in draw["numbers"] if _zone(n) == "high")
        low_sum  += lo
        mid_sum  += mi
        high_sum += hi
        trend.append({
            "period": draw["period"],
            "date":   draw["date"],
            "low": lo, "mid": mi, "high": hi,
        })

    # 最新期各區數量
    latest = trend[0] if trend else {"low": 0, "mid": 0, "high": 0}

    # 預測：若某區最新期掛零且均值 > 0，視為「補回優先」
    avg_lo = low_sum  / 10
    avg_mi = mid_sum  / 10
    avg_hi = high_sum / 10

    pred = {}
    for zone, latest_val, avg in [("low", latest["low"], avg_lo),
                                   ("mid", latest["mid"], avg_mi),
                                   ("high", latest["high"], avg_hi)]:
        if latest_val == 0 and avg >= 1:
            pred[zone] = "補回優先"
        elif latest_val >= avg * 1.5:
            pred[zone] = "可能回落"
        else:
            pred[zone] = "延續"

    return {
        "recent_trend":        trend,
        "avg_last10":          {"low": round(avg_lo, 1), "mid": round(avg_mi, 1), "high": round(avg_hi, 1)},
        "tomorrow_prediction": pred,
    }


# ── ⑤ 單雙比 ─────────────────────────────────
def _odd_even_analysis(draws: list[dict]) -> dict:
    recent10 = draws[:10]
    trend = []
    combo_counter: Counter = Counter()

    for draw in recent10:
        odd  = sum(1 for n in draw["numbers"] if n % 2 != 0)
        even = 5 - odd
        combo = f"{odd}單{even}雙"
        combo_counter[combo] += 1
        trend.append({"period": draw["period"], "odd": odd, "even": even, "combo": combo})

    # 最常見組合
    most_common = combo_counter.most_common(1)[0][0] if combo_counter else ""
    latest_combo = trend[0]["combo"] if trend else ""

    # 若最新期連續 2 期相同 → 預測換向
    if len(trend) >= 2 and trend[0]["combo"] == trend[1]["combo"]:
        prediction = "可能換組合（連續相同後易反轉）"
    else:
        prediction = f"延續趨勢，主推 {most_common}"

    return {
        "recent_trend":        trend,
        "most_common_combo":   most_common,
        "tomorrow_prediction": prediction,
    }


# ── ⑥ 綜合推薦 ───────────────────────────────
def _recommend(tail, missing, drag, zone, odd_even, expert=None) -> list[dict]:
    """
    產生 3 組推薦號碼，專家表（圖1+圖2）為最高權重。
      組1 — 圖2拖牌候選 × 圖1尾數過濾（雙表交叉）
      組2 — 圖2拖牌候選 × 遺漏補回
      組3 — 圖1尾數 × 遺漏長期未出
    """
    by_missing = sorted(missing.items(), key=lambda x: -x[1]["missing_periods"])
    fallback   = [n for n, _ in by_missing]

    # ── 專家表資料 ──
    expert_tails   = set()   # 圖1：允許的尾數
    drag_cands     = []      # 圖2：拖牌候選（依頻率排序）
    drag_freq: dict[int, int] = {}

    if expert:
        rule = expert.get("tail_rule", {})
        expert_tails = set(rule.get("main_tails", []) + rule.get("high_tails", []))
        d1to3 = expert.get("drag_1to3", {})
        drag_cands = d1to3.get("candidates", [])
        drag_freq  = d1to3.get("freq", {})

    # ── 組1：圖2拖牌 × 圖1尾數（雙重過濾，最精準）──
    set1_pool = [n for n in drag_cands if (_tail(n) in expert_tails)] if expert_tails else drag_cands
    set1 = _pick_set(set1_pool, 5, fallback=drag_cands or fallback)

    # ── 組2：圖2拖牌 × 遺漏補回（拖牌中找久未出的）──
    drag_by_miss = sorted(drag_cands, key=lambda x: -missing.get(x, {}).get("missing_periods", 0))
    set2 = _pick_set(drag_by_miss, 5, fallback=fallback, exclude=set(set1))

    # ── 組3：圖1尾數 × 最長遺漏（純尾數策略）──
    tail_filtered = [n for n, v in by_missing if v["tail"] in expert_tails] if expert_tails else fallback
    set3 = _pick_set(tail_filtered, 5, fallback=fallback, exclude=set(set1) | set(set2))

    return [
        _build_rec(1, sorted(set1), "圖2拖牌×圖1尾數（雙表交叉）", missing),
        _build_rec(2, sorted(set2), "圖2拖牌×遺漏補回",             missing),
        _build_rec(3, sorted(set3), "圖1尾數×最長遺漏",             missing),
    ]


def _pick_set(candidates, n, fallback, exclude=None) -> list[int]:
    exclude = exclude or set()
    pool = list(dict.fromkeys(c for c in candidates if c not in exclude))
    if len(pool) < n:
        pool += [x for x in fallback if x not in exclude and x not in pool]
    return pool[:n]


def _build_rec(rank: int, numbers: list[int], strategy: str, missing: dict) -> dict:
    lo = sum(1 for n in numbers if _zone(n) == "low")
    mi = sum(1 for n in numbers if _zone(n) == "mid")
    hi = sum(1 for n in numbers if _zone(n) == "high")
    odd  = sum(1 for n in numbers if n % 2 != 0)
    even = 5 - odd

    avg_miss = sum(missing[n]["missing_periods"] for n in numbers) / len(numbers) if numbers else 0
    if avg_miss >= 8:
        conf = "high"
    elif avg_miss >= 5:
        conf = "medium"
    else:
        conf = "low"

    reasoning = (
        f"平均遺漏 {avg_miss:.1f} 期，"
        f"區間 低{lo}/中{mi}/高{hi}，"
        f"單雙 {odd}單{even}雙"
    )
    return {
        "rank":     rank,
        "numbers":  numbers,
        "strategy": strategy,
        "zone_distribution": {"low": lo, "mid": mi, "high": hi},
        "odd_even": {"odd": odd, "even": even},
        "confidence": conf,
        "reasoning":  reasoning,
    }
