"""Explore raw Discogs collection JSON and generate a lightweight data dictionary."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DOCS_DIR = PROJECT_ROOT / "docs"


def latest_raw_collection() -> Path:
    candidates = sorted(RAW_DATA_DIR.glob("collection_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No data/raw/collection_*.json files found. Run --fetch-collection first.")
    return candidates[0]


def load_collection(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("releases"), list):
        return payload["releases"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Unsupported raw collection shape in {path}")


def flatten_keys(value: Any, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            keys.add(name)
            keys.update(flatten_keys(nested, name))
    elif isinstance(value, list):
        keys.add(f"{prefix}[]")
        for item in value[:10]:
            keys.update(flatten_keys(item, f"{prefix}[]"))
    return keys


def summarize_collection(records: list[dict[str, Any]]) -> dict[str, Any]:
    key_counts: Counter[str] = Counter()
    type_counts: dict[str, Counter[str]] = defaultdict(Counter)
    genre_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    format_counts: Counter[str] = Counter()

    for record in records:
        for key in flatten_keys(record):
            key_counts[key] += 1

        basic = record.get("basic_information", {}) if isinstance(record, dict) else {}
        if isinstance(basic, dict):
            for field, value in basic.items():
                type_counts[f"basic_information.{field}"][type(value).__name__] += 1
            for genre in basic.get("genres") or []:
                genre_counts[str(genre)] += 1
            for style in basic.get("styles") or []:
                style_counts[str(style)] += 1
            year = basic.get("year")
            if year:
                year_counts[str(year)] += 1
            for fmt in basic.get("formats") or []:
                if isinstance(fmt, dict):
                    format_counts[str(fmt.get("name", "Unknown"))] += 1

    return {
        "record_count": len(records),
        "key_counts": key_counts,
        "type_counts": type_counts,
        "genre_counts": genre_counts,
        "style_counts": style_counts,
        "year_counts": year_counts,
        "format_counts": format_counts,
    }


def display_path(path: Path) -> str:
    """Return a repo-relative path when possible, otherwise an absolute path."""
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_data_dictionary(summary: dict[str, Any], source_path: Path, output_path: Path) -> Path:
    record_count = summary["record_count"]
    key_counts: Counter[str] = summary["key_counts"]

    lines = [
        "# Vinyl Vault Data Dictionary",
        "",
        f"Source file: `{display_path(source_path)}`",
        f"Records profiled: {record_count}",
        "",
        "## Key fields for analytics",
        "",
        "| Field | Notes |",
        "|---|---|",
        "| `id` | Collection instance identifier from Discogs. |",
        "| `date_added` | Timestamp when the record was added to the collection. |",
        "| `basic_information.id` | Discogs release id; useful natural key for release-level joins. |",
        "| `basic_information.title` | Release title. |",
        "| `basic_information.artists[].name` | Artist names for artist breakdowns. |",
        "| `basic_information.year` | Release year for decade distribution. |",
        "| `basic_information.genres[]` | Genres for collection composition. |",
        "| `basic_information.styles[]` | More granular style tags. |",
        "| `basic_information.formats[].name` | Physical format such as Vinyl, CD, etc. |",
        "| `basic_information.labels[].name` | Label/publisher metadata. |",
        "",
        "## Observed raw fields",
        "",
        "| Field | Presence |",
        "|---|---:|",
    ]

    for key, count in sorted(key_counts.items()):
        lines.append(f"| `{key}` | {count}/{record_count} |")

    for title, counter_name in [
        ("Top genres", "genre_counts"),
        ("Top styles", "style_counts"),
        ("Top formats", "format_counts"),
        ("Top release years", "year_counts"),
    ]:
        lines.extend(["", f"## {title}", "", "| Value | Count |", "|---|---:|"])
        for value, count in summary[counter_name].most_common(15):
            lines.append(f"| {value} | {count} |")

    lines.extend([
        "",
        "## Data quality notes to review",
        "",
        "- Confirm whether `id` or `instance_id` should be the collection item key; Discogs collection exports commonly use `id` as the instance id.",
        "- Treat release year `0`, blank, or missing values as unknown during cleaning.",
        "- Multi-artist, multi-genre, multi-style, and multi-format fields are arrays and should be modeled carefully for analytics.",
    ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profile raw Discogs collection JSON")
    parser.add_argument("--input", type=Path, help="Raw collection JSON; defaults to newest data/raw/collection_*.json")
    parser.add_argument("--output", type=Path, default=DOCS_DIR / "data_dictionary.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_path = args.input or latest_raw_collection()
    records = load_collection(source_path)
    summary = summarize_collection(records)
    output_path = write_data_dictionary(summary, source_path, args.output)
    print(f"Profiled {summary['record_count']} records from {source_path}")
    print(f"Wrote data dictionary to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
