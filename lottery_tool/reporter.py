"""報告列印（人類可讀格式）"""

from datetime import date


_ZONE_LABEL = {"low": "低(01-13)", "mid": "中(14-26)", "high": "高(27-39)"}
_STATUS_ICON = {"hot": "🔥熱", "cold": "❄️冷", "normal": "普通"}
_CONF_ICON   = {"high": "⭐高", "medium": "◎中", "low": "△低"}


def print_report(game_name: str, result: dict) -> None:
    summary = result.get("summary", {})
    dr = summary.get("date_range", {})

    _line("=", 64)
    print(f"  🎯 {game_name} 版路分析報告")
    print(f"     分析期數：{summary.get('total_periods', 0)} 期")
    print(f"     期間：{dr.get('from', '')} ～ {dr.get('to', '')}")
    print(f"     產生時間：{date.today()}")
    _line("=", 64)

    _print_tail(result.get("tail", {}))
    _print_missing(result.get("missing", {}))
    _print_drag(result.get("drag", {}))
    _print_zone(result.get("zone", {}))
    _print_odd_even(result.get("odd_even", {}))
    _print_recommend(result.get("recommend", []))

    _line("=", 64)
    print("  ✅ 分析完畢")
    _line("=", 64)
    print()


# ── 各區塊 ────────────────────────────────────

def _print_tail(tail: dict) -> None:
    _section("① 尾數統計")
    print(f"  {'尾數':<6} {'次數':<6} {'狀態':<8} {'最後出現':<10} {'補回訊號':<8} 包含號碼")
    _line("-", 64)
    for t in range(10):
        v = tail.get(t, {})
        signal = "⚡補回!" if v.get("comeback_signal") else ""
        print(
            f"  尾{t:<5} {v.get('count', 0):<6} "
            f"{_STATUS_ICON.get(v.get('status',''), ''):<10} "
            f"{v.get('last_seen_periods_ago', 0)}期前{'':<4} "
            f"{signal:<10} "
            f"{v.get('numbers', [])}"
        )


def _print_missing(missing: dict) -> None:
    _section("② 遺漏分析（遺漏最多的前 15 顆）")
    print(f"  {'號碼':<6} {'遺漏期':<8} {'尾數':<6} 標記")
    _line("-", 40)
    top15 = sorted(missing.items(), key=lambda x: -x[1]["missing_periods"])[:15]
    for n, v in top15:
        flag = "⚠️ 久未出" if v["missing_periods"] >= 8 else ""
        print(f"  {n:02d}     {v['missing_periods']:<8} 尾{v['tail']:<5} {flag}")


def _print_drag(drag: dict) -> None:
    _section("③ 拖牌偵測")
    print("  【目前在拖】")
    if drag.get("currently_dragging"):
        for d in drag["currently_dragging"]:
            print(f"    號碼 {d['number']:02d} → 已連拖 {d['consecutive_periods']} 期（最後：{d['last_seen']}）")
    else:
        print("    無")

    print("  【斷拖號碼（回馬槍警戒）】")
    if drag.get("recently_stopped"):
        risk_cn = {"high": "🔴高", "medium": "🟡中", "low": "🟢低"}
        for d in drag["recently_stopped"]:
            print(
                f"    號碼 {d['number']:02d} → 斷拖 {d['stopped_periods_ago']} 期前，"
                f"回馬槍風險：{risk_cn[d['comeback_risk']]}"
            )
    else:
        print("    無")


def _print_zone(zone: dict) -> None:
    _section("④ 區間分布（近10期）")
    print(f"  {'期數':<8} {'日期':<12} {'低(01-13)':<10} {'中(14-26)':<10} {'高(27-39)'}")
    _line("-", 55)
    for z in zone.get("recent_trend", []):
        print(f"  {z['period']:<8} {z['date']:<12} {z['low']:<10} {z['mid']:<10} {z['high']}")
    avg = zone.get("avg_last10", {})
    print(f"  {'均值':<8} {'':12} {avg.get('low',''):<10} {avg.get('mid',''):<10} {avg.get('high','')}")
    pred = zone.get("tomorrow_prediction", {})
    print(f"\n  明日預測：", end="")
    print(" | ".join(f"{_ZONE_LABEL[k]}→{v}" for k, v in pred.items()))


def _print_odd_even(oe: dict) -> None:
    _section("⑤ 單雙比（近10期）")
    print(f"  {'期數':<8} {'單':<5} {'雙':<5} 組合")
    _line("-", 35)
    for o in oe.get("recent_trend", []):
        print(f"  {o['period']:<8} {o['odd']:<5} {o['even']:<5} {o['combo']}")
    print(f"\n  最常見：{oe.get('most_common_combo', '')}")
    print(f"  明日預測：{oe.get('tomorrow_prediction', '')}")


def _print_recommend(recs: list) -> None:
    _section("⑥ 綜合推薦")
    for r in recs:
        nums_str = "  ".join(f"{n:02d}" for n in r["numbers"])
        zd = r["zone_distribution"]
        oe = r["odd_even"]
        print(f"\n  第{r['rank']}組【{r['strategy']}】  信心：{_CONF_ICON[r['confidence']]}")
        print(f"    ▶ 號碼：{nums_str}")
        print(f"    ▶ 區間：低{zd['low']} / 中{zd['mid']} / 高{zd['high']}")
        print(f"    ▶ 單雙：{oe['odd']}單{oe['even']}雙")
        print(f"    ▶ 依據：{r['reasoning']}")

    _line("-", 64)
    print("\n  ◆ 三組策略差異")
    strategies = {1: "主攻（熱尾補回）", 2: "偏鋒（冷尾爆發）", 3: "保守（均衡分布）"}
    for r in recs:
        print(f"    組{r['rank']}：{strategies.get(r['rank'], r['strategy'])}")


def print_combined(results: dict) -> None:
    """同時輸出兩彩報告 + 簡易對比"""
    for game, res in results.items():
        print_report(game, res)

    # 號碼交集提示
    all_sets = {}
    for game, res in results.items():
        for rec in res.get("recommend", []):
            key = f"{game}-組{rec['rank']}"
            all_sets[key] = set(rec["numbers"])

    _line("=", 64)
    print("  🔀 兩彩交叉比對（共同推薦號碼）")
    _line("-", 64)
    keys = list(all_sets.keys())
    printed = False
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            k1, k2 = keys[i], keys[j]
            if k1.split("-")[0] == k2.split("-")[0]:
                continue  # 同一彩種不比
            common = sorted(all_sets[k1] & all_sets[k2])
            if common:
                print(f"  {k1} ∩ {k2}：{common}")
                printed = True
    if not printed:
        print("  無兩彩共同號碼")
    _line("=", 64)


# ── 工具 ─────────────────────────────────────

def _line(char: str, width: int) -> None:
    print("  " + char * width)


def _section(title: str) -> None:
    print(f"\n  ── {title} {'─' * (54 - len(title))}")
