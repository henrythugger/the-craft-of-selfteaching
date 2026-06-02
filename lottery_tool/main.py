#!/usr/bin/env python3
"""
天天樂 + 今彩539 版路分析工具
用法：
  python main.py            # 自動抓兩彩資料 + 分析
  python main.py --f5       # 只分析 Fantasy 5
  python main.py --539      # 只分析 539
  python main.py --no-fetch # 不抓網路，直接用已存的歷史檔案分析
  python main.py --count 50 # 指定抓取期數（預設 30）
"""

import argparse
import sys

import storage
import analyzer
import reporter
from fetcher import Fantasy5Fetcher, Lottery539Fetcher

GAMES = {
    "fantasy5": {
        "label":   "California Fantasy 5",
        "fetcher": Fantasy5Fetcher,
        "file":    "fantasy5",
    },
    "lottery539": {
        "label":   "台灣今彩 539",
        "fetcher": Lottery539Fetcher,
        "file":    "lottery539",
    },
}


def run(games: list[str], fetch: bool, count: int) -> None:
    all_results = {}

    for key in games:
        cfg = GAMES[key]
        print(f"\n{'='*60}")
        print(f"  處理：{cfg['label']}")
        print(f"{'='*60}")

        # 1. 載入歷史
        existing = storage.load(cfg["file"])
        print(f"  → 本地歷史：{len(existing)} 期")

        # 2. 抓新資料
        if fetch:
            print(f"  → 開始從網路抓取最新 {count} 期...")
            fetcher = cfg["fetcher"]()
            new_draws = fetcher.fetch_recent(count)

            if new_draws:
                merged, added = storage.merge(existing, new_draws)
                storage.save(cfg["file"], merged)
                print(f"  → 新增 {added} 期，目前共 {len(merged)} 期")
                draws = merged
            else:
                print("  → 抓取失敗或無新資料，使用本地歷史繼續分析")
                draws = existing
        else:
            draws = existing

        if not draws:
            print(f"  ⚠️  無任何資料可分析，跳過 {cfg['label']}")
            print(f"  → 請手動把資料填入 data/{cfg['file']}.json")
            continue

        # 3. 分析
        use_n = min(len(draws), count)
        print(f"  → 使用最新 {use_n} 期進行分析...")
        result = analyzer.analyze(draws[:use_n])
        all_results[cfg["label"]] = result

    # 4. 輸出報告
    if not all_results:
        print("\n沒有可輸出的分析結果。")
        return

    print()
    if len(all_results) >= 2:
        reporter.print_combined(all_results)
    else:
        for label, res in all_results.items():
            reporter.print_report(label, res)


def main() -> None:
    parser = argparse.ArgumentParser(description="天天樂 / 539 版路分析")
    parser.add_argument("--f5",       action="store_true", help="只分析 Fantasy 5")
    parser.add_argument("--539",      action="store_true", dest="lotto539", help="只分析 539")
    parser.add_argument("--no-fetch", action="store_true", help="不從網路抓資料")
    parser.add_argument("--count",    type=int, default=30, help="分析期數（預設 30）")
    args = parser.parse_args()

    if args.f5 and args.lotto539:
        print("⚠️  --f5 與 --539 不能同時使用，改為分析兩者")
        games = list(GAMES.keys())
    elif args.f5:
        games = ["fantasy5"]
    elif args.lotto539:
        games = ["lottery539"]
    else:
        games = list(GAMES.keys())

    run(games=games, fetch=not args.no_fetch, count=args.count)


if __name__ == "__main__":
    main()
