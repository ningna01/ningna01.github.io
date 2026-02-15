#!/usr/bin/env python3
"""Build notes index JSON for homepage rendering."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

CATEGORY_NAME_OVERRIDES = {
    "TimeSeries": "时间序列",
    "Diffusion": "扩散模型",
    "RandomProcess": "随机过程",
    "StochasticProcess": "随机过程",
}

CATEGORY_ORDER_HINTS = [
    "timeseries",
    "diffusion",
    "randomprocess",
    "stochasticprocess",
]

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "assets",
    "data",
    "scripts",
}


def pretty_title(stem: str) -> str:
    chapter_match = re.fullmatch(r"chap(?:ter|er)(\d+)", stem, flags=re.IGNORECASE)
    if chapter_match:
        return f"第{int(chapter_match.group(1))}章"

    diffusion_match = re.fullmatch(r"diffusion[-_ ]?(\d+)", stem, flags=re.IGNORECASE)
    if diffusion_match:
        return f"Diffusion {int(diffusion_match.group(1))}"

    if stem.upper() == "VAE":
        return "VAE"

    return stem.replace("_", " ").replace("-", " ").strip()


def slugify_category_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if key:
        return key
    fallback = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"cat-{fallback}"


def prettify_category_name(name: str) -> str:
    if name in CATEGORY_NAME_OVERRIDES:
        return CATEGORY_NAME_OVERRIDES[name]

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    with_spaces = with_spaces.replace("_", " ").replace("-", " ").strip()
    return with_spaces or name


def discover_categories(root: Path) -> list[tuple[str, str, Path]]:
    discovered: list[tuple[str, str, Path]] = []
    used_keys: set[str] = set()

    for directory in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not directory.is_dir():
            continue
        if directory.name.startswith(".") or directory.name in IGNORED_DIRS:
            continue

        html_files = list(directory.glob("*.html"))
        if not html_files:
            continue

        base_key = slugify_category_key(directory.name)
        key = base_key
        suffix = 2
        while key in used_keys:
            key = f"{base_key}-{suffix}"
            suffix += 1
        used_keys.add(key)

        discovered.append((key, prettify_category_name(directory.name), directory))

    def sort_key(item: tuple[str, str, Path]) -> tuple[int, str]:
        key = item[0]
        if key in CATEGORY_ORDER_HINTS:
            return (CATEGORY_ORDER_HINTS.index(key), item[1].lower())
        return (len(CATEGORY_ORDER_HINTS), item[1].lower())

    discovered.sort(key=sort_key)
    return discovered


def build_note(root: Path, html_file: Path, category_key: str, category_name: str) -> dict[str, object]:
    mtime = datetime.fromtimestamp(html_file.stat().st_mtime).astimezone()
    relative_path = html_file.relative_to(root).as_posix()
    safe_id = re.sub(r"[^a-z0-9]+", "-", f"{category_key}-{html_file.stem.lower()}").strip("-")

    return {
        "id": safe_id,
        "title": pretty_title(html_file.stem),
        "fileName": html_file.name,
        "path": relative_path,
        "category": category_key,
        "categoryName": category_name,
        "updatedAt": mtime.strftime("%Y-%m-%d"),
        "updatedAtTs": int(mtime.timestamp()),
    }


def gather_notes(root: Path) -> dict[str, object]:
    notes: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    categories_meta: list[tuple[str, str]] = []

    for category_key, category_name, target_dir in discover_categories(root):
        html_files = sorted(target_dir.glob("*.html"))
        counts[category_key] = len(html_files)
        categories_meta.append((category_key, category_name))

        for html_file in html_files:
            notes.append(build_note(root, html_file, category_key, category_name))

    notes.sort(key=lambda item: (item["updatedAtTs"], str(item["title"])), reverse=True)

    categories = [{"key": "all", "name": "全部", "count": len(notes)}]
    for category_key, category_name in categories_meta:
        categories.append(
            {
                "key": category_key,
                "name": category_name,
                "count": counts.get(category_key, 0),
            }
        )

    return {
        "generatedAt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "total": len(notes),
        "categories": categories,
        "notes": notes,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_file = root / "data" / "notes.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    index_data = gather_notes(root)
    output_file.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {output_file} with {index_data['total']} notes.")


if __name__ == "__main__":
    main()
