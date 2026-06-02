"""歷史資料存取（JSON）"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def _path(game: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    return DATA_DIR / f"{game}.json"


def load(game: str) -> list[dict]:
    p = _path(game)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def save(game: str, draws: list[dict]) -> None:
    with open(_path(game), "w", encoding="utf-8") as f:
        json.dump(draws, f, ensure_ascii=False, indent=2)


def merge(existing: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """把新資料合併進現有資料，回傳 (合併後列表, 新增筆數)"""
    seen = {d["period"] for d in existing}
    added = [d for d in new if d["period"] not in seen]
    merged = sorted(existing + added, key=lambda x: x["period"], reverse=True)
    return merged, len(added)
