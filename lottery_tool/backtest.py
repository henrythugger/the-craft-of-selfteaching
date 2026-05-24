#!/usr/bin/env python3
"""
回測腳本：驗證兩張專家表的命中率

測試方法：
  對每一期 draws[i]，用前面的資料預測，然後對照 draws[i] 的實際開獎
  計算圖1（精準尾數）和圖2（1拖3）各自的命中率

用法：
  python backtest.py               # 回測本地所有資料（Fantasy 5 + 539）
  python backtest.py --f5          # 只回測 Fantasy 5
  python backtest.py --539         # 只回測 539
  python backtest.py --count 100   # 指定回測期數
"""

import argparse
from collections import defaultdict
import storage
from expert_tables import get_tail_rule, get_drag_candidates, DRAG_TABLE


# ── 圖1回測：精準尾數法 ───────────────────────────────────────
def backtest_tail_rule(draws: list[dict]) -> dict:
    """
    對每一期，用「開獎日個位數」查主尾+高機率尾，
    統計開獎5顆中有幾顆符合（尾數在預測範圍內）。
    """
    results = []

    for draw in draws:
        rule = get_tail_rule(draw["date"])
        if not rule:
            continue

        main_tails = set(rule.get("main", []))
        all_tails  = set(rule.get("main", []) + rule.get("high", []))

        hit_main = sum(1 for n in draw["numbers"] if n % 10 in main_tails)
        hit_all  = sum(1 for n in draw["numbers"] if n % 10 in all_tails)

        results.append({
            "period":    draw["period"],
            "date":      draw["date"],
            "numbers":   draw["numbers"],
            "main_tails": sorted(main_tails),
            "all_tails":  sorted(all_tails),
            "hit_main":  hit_main,
            "hit_all":   hit_all,
        })

    if not results:
        return {}

    n = len(results)
    # 命中分布（5顆中幾顆符合尾數）
    dist_main = defaultdict(int)
    dist_all  = defaultdict(int)
    for r in results:
        dist_main[r["hit_main"]] += 1
        dist_all[r["hit_all"]]   += 1

    return {
        "periods_tested": n,
        "main_tails_only": {
            "avg_hit":    round(sum(r["hit_main"] for r in results) / n, 2),
            "hit_2plus":  round(sum(1 for r in results if r["hit_main"] >= 2) / n * 100, 1),
            "hit_3plus":  round(sum(1 for r in results if r["hit_main"] >= 3) / n * 100, 1),
            "distribution": dict(sorted(dist_main.items())),
        },
        "main_plus_high": {
            "avg_hit":    round(sum(r["hit_all"] for r in results) / n, 2),
            "hit_2plus":  round(sum(1 for r in results if r["hit_all"] >= 2) / n * 100, 1),
            "hit_3plus":  round(sum(1 for r in results if r["hit_all"] >= 3) / n * 100, 1),
            "hit_4plus":  round(sum(1 for r in results if r["hit_all"] >= 4) / n * 100, 1),
            "distribution": dict(sorted(dist_all.items())),
        },
        "details": results[:10],   # 只印最近10期細節
    }


# ── 圖2回測：1拖3固定拖牌法 ───────────────────────────────────
def backtest_drag_1to3(draws: list[dict]) -> dict:
    """
    對每相鄰兩期 (i, i+1)：
      用 draws[i+1]（較舊一期）的號碼查拖牌候選池，
      看候選池命中 draws[i]（較新一期）幾顆。
    """
    results = []

    # draws 已按「新→舊」排序，draws[0]=最新
    for i in range(len(draws) - 1):
        actual  = draws[i]       # 實際開獎（較新）
        source  = draws[i + 1]   # 上期（較舊）

        drag_info  = get_drag_candidates(source["numbers"])
        candidates = set(drag_info["candidates"])
        freq       = drag_info["freq"]

        hit = sum(1 for n in actual["numbers"] if n in candidates)
        # 高頻候選（被2顆以上上期號碼拖到）
        strong_cands = {n for n, f in freq.items() if f >= 2}
        hit_strong   = sum(1 for n in actual["numbers"] if n in strong_cands)

        results.append({
            "period":       actual["period"],
            "date":         actual["date"],
            "actual":       actual["numbers"],
            "source":       source["numbers"],
            "candidates":   sorted(candidates),
            "strong_cands": sorted(strong_cands),
            "pool_size":    len(candidates),
            "hit":          hit,
            "hit_strong":   hit_strong,
        })

    if not results:
        return {}

    n = len(results)
    dist = defaultdict(int)
    for r in results:
        dist[r["hit"]] += 1

    return {
        "periods_tested": n,
        "full_pool": {
            "avg_pool_size": round(sum(r["pool_size"] for r in results) / n, 1),
            "avg_hit":       round(sum(r["hit"] for r in results) / n, 2),
            "hit_1plus":     round(sum(1 for r in results if r["hit"] >= 1) / n * 100, 1),
            "hit_2plus":     round(sum(1 for r in results if r["hit"] >= 2) / n * 100, 1),
            "hit_3plus":     round(sum(1 for r in results if r["hit"] >= 3) / n * 100, 1),
            "distribution":  dict(sorted(dist.items())),
        },
        "strong_only": {
            "avg_hit":   round(sum(r["hit_strong"] for r in results) / n, 2),
            "hit_1plus": round(sum(1 for r in results if r["hit_strong"] >= 1) / n * 100, 1),
            "hit_2plus": round(sum(1 for r in results if r["hit_strong"] >= 2) / n * 100, 1),
        },
        "details": results[:10],
    }


# ── 雙表交叉回測 ─────────────────────────────────────────────
def backtest_combined(draws: list[dict]) -> dict:
    """
    圖1尾數 × 圖2拖牌交叉：
    候選池 = 拖牌候選中，尾數在圖1允許範圍內的號碼
    看這個精縮候選池命中率如何
    """
    results = []

    for i in range(len(draws) - 1):
        actual = draws[i]
        source = draws[i + 1]

        rule       = get_tail_rule(actual["date"])
        all_tails  = set(rule.get("main", []) + rule.get("high", []))

        drag_info  = get_drag_candidates(source["numbers"])
        # 交叉過濾
        combined   = [n for n in drag_info["candidates"] if n % 10 in all_tails]

        hit = sum(1 for n in actual["numbers"] if n in set(combined))
        results.append({
            "period":    actual["period"],
            "pool_size": len(combined),
            "hit":       hit,
        })

    if not results:
        return {}

    n = len(results)
    return {
        "periods_tested": n,
        "avg_pool_size":  round(sum(r["pool_size"] for r in results) / n, 1),
        "avg_hit":        round(sum(r["hit"] for r in results) / n, 2),
        "hit_1plus":      round(sum(1 for r in results if r["hit"] >= 1) / n * 100, 1),
        "hit_2plus":      round(sum(1 for r in results if r["hit"] >= 2) / n * 100, 1),
        "hit_3plus":      round(sum(1 for r in results if r["hit"] >= 3) / n * 100, 1),
    }


# ── 報告輸出 ─────────────────────────────────────────────────
def print_backtest(game_name: str, draws: list[dict], count: int) -> None:
    draws = draws[:count]
    print(f"\n{'='*62}")
    print(f"  📊 {game_name} 回測報告")
    print(f"  回測期數：{len(draws)} 期  ({draws[-1]['date']} ～ {draws[0]['date']})")
    print(f"{'='*62}")

    # ── 圖1 ──
    t = backtest_tail_rule(draws)
    if t:
        print(f"\n  【圖1：精準尾數法】")
        print(f"  ┌─────────────────────────────────────────────┐")
        m = t["main_plus_high"]
        print(f"  │ 主尾+高機率尾  平均命中 {m['avg_hit']} 顆/期              │")
        print(f"  │  2顆以上命中：{m['hit_2plus']:>5}%                          │")
        print(f"  │  3顆以上命中：{m['hit_3plus']:>5}%                          │")
        print(f"  │  4顆以上命中：{m['hit_4plus']:>5}%                          │")
        print(f"  │ 分布 {dict(sorted(t['main_plus_high']['distribution'].items()))}  │")
        print(f"  └─────────────────────────────────────────────┘")
        print(f"\n  最近10期細節：")
        print(f"  {'期數':<8} {'日期':<12} {'開獎號碼':<20} {'命中顆數'}")
        print(f"  {'-'*55}")
        for r in t["details"]:
            nums = " ".join(f"{n:02d}" for n in r["numbers"])
            print(f"  {r['period']:<8} {r['date']:<12} {nums:<20} {r['hit_all']}顆 (尾:{r['all_tails']})")

    # ── 圖2 ──
    d = backtest_drag_1to3(draws)
    if d:
        fp = d["full_pool"]
        print(f"\n  【圖2：1拖3固定拖牌法】")
        print(f"  ┌─────────────────────────────────────────────┐")
        print(f"  │ 平均候選池大小：{fp['avg_pool_size']:>4} 顆                     │")
        print(f"  │ 平均命中：{fp['avg_hit']:>4} 顆/期                        │")
        print(f"  │  1顆以上命中：{fp['hit_1plus']:>5}%                          │")
        print(f"  │  2顆以上命中：{fp['hit_2plus']:>5}%                          │")
        print(f"  │  3顆以上命中：{fp['hit_3plus']:>5}%                          │")
        print(f"  │ 分布 {dict(sorted(fp['distribution'].items()))}  │")
        print(f"  └─────────────────────────────────────────────┘")
        print(f"\n  最近10期細節：")
        print(f"  {'期數':<8} {'日期':<12} {'上期號碼':<18} {'命中'}")
        print(f"  {'-'*55}")
        for r in d["details"]:
            src  = " ".join(f"{n:02d}" for n in r["source"])
            act  = " ".join(f"{n:02d}" for n in r["actual"])
            print(f"  {r['period']:<8} {r['date']:<12} 上期:{src}")
            print(f"  {'':8} {'':12} 實際:{act}  命中{r['hit']}顆 (強:{r['hit_strong']})")

    # ── 雙表交叉 ──
    c = backtest_combined(draws)
    if c:
        print(f"\n  【圖1×圖2 雙表交叉】精縮候選池")
        print(f"  ┌─────────────────────────────────────────────┐")
        print(f"  │ 平均候選池：{c['avg_pool_size']:>4} 顆（已過濾非目標尾數）    │")
        print(f"  │ 平均命中：{c['avg_hit']:>4} 顆/期                        │")
        print(f"  │  1顆以上：{c['hit_1plus']:>5}%   2顆以上：{c['hit_2plus']:>5}%           │")
        print(f"  │  3顆以上：{c['hit_3plus']:>5}%                              │")
        print(f"  └─────────────────────────────────────────────┘")

    # ── 結論 ──
    print(f"\n  ── 結論 {'─'*50}")
    if t and d:
        tail_score = t["main_plus_high"]["hit_2plus"]
        drag_score = d["full_pool"]["hit_2plus"]
        winner = "圖1尾數法" if tail_score > drag_score else "圖2拖牌法"
        print(f"  圖1尾數法（2顆以上）：{tail_score}%")
        print(f"  圖2拖牌法（2顆以上）：{drag_score}%")
        if c:
            print(f"  雙表交叉（2顆以上）：{c['hit_2plus']}%")
        print(f"\n  ✨ 本資料集較優方法：{winner}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--f5",    action="store_true")
    parser.add_argument("--539",   action="store_true", dest="lotto539")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()

    run_f5  = args.f5 or (not args.f5 and not args.lotto539)
    run_539 = args.lotto539 or (not args.f5 and not args.lotto539)

    if run_f5:
        draws = storage.load("fantasy5")
        if not draws:
            print("Fantasy 5 無本地資料，請先執行 python main.py --f5 抓取資料")
        else:
            print_backtest("California Fantasy 5", draws, args.count)

    if run_539:
        draws = storage.load("lottery539")
        if not draws:
            print("今彩539 無本地資料，請先執行 python main.py --539 抓取資料")
        else:
            print_backtest("台灣今彩 539", draws, args.count)


if __name__ == "__main__":
    main()
