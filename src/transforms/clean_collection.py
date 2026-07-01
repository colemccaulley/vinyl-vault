"""Clean and normalize raw Discogs collection JSON into analytics-friendly CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"


def latest_raw_collection() -> Path:
    candidates = sorted(RAW_DATA_DIR.glob("collection_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("No data/raw/collection_*.json files found. Run ingestion first.")
    return candidates[0]


def load_collection(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("releases"), list):
        return payload["releases"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Unsupported collection shape in {path}")


def parse_year(value: Any) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    if year <= 0:
        return None
    return year


def parse_date(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text[:10] if len(text) >= 10 else text


def join_names(items: list[dict[str, Any]] | None, key: str = "name") -> str:
    if not items:
        return ""
    return "; ".join(str(item.get(key, "")).strip() for item in items if isinstance(item, dict) and item.get(key))


def first_format(formats: list[dict[str, Any]] | None) -> str:
    if not formats:
        return ""
    first = formats[0]
    if not isinstance(first, dict):
        return ""
    descriptions = first.get("descriptions") or []
    desc = f" ({', '.join(descriptions)})" if descriptions else ""
    return f"{first.get('name', '')}{desc}".strip()


def normalize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_instance_ids: set[str] = set()

    for record in records:
        basic = record.get("basic_information", {}) if isinstance(record, dict) else {}
        instance_id = str(record.get("id") or record.get("instance_id") or "")
        if instance_id in seen_instance_ids:
            continue
        seen_instance_ids.add(instance_id)

        year = parse_year(basic.get("year")) if isinstance(basic, dict) else None
        genres = basic.get("genres") or [] if isinstance(basic, dict) else []
        styles = basic.get("styles") or [] if isinstance(basic, dict) else []
        formats = basic.get("formats") or [] if isinstance(basic, dict) else []

        normalized.append(
            {
                "instance_id": instance_id,
                "date_added": parse_date(record.get("date_added")),
                "folder_id": record.get("folder_id"),
                "rating": record.get("rating"),
                "release_id": basic.get("id") if isinstance(basic, dict) else None,
                "title": str(basic.get("title", "")).strip() if isinstance(basic, dict) else "",
                "artists": join_names(basic.get("artists") if isinstance(basic, dict) else []),
                "release_year": year,
                "release_decade": f"{year // 10 * 10}s" if year else "Unknown",
                "genres": "; ".join(map(str, genres)),
                "styles": "; ".join(map(str, styles)),
                "format": first_format(formats),
                "labels": join_names(basic.get("labels") if isinstance(basic, dict) else []),
                "resource_url": basic.get("resource_url") if isinstance(basic, dict) else None,
                "thumb": basic.get("thumb") if isinstance(basic, dict) else None,
            }
        )

    return normalized


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "instance_id",
        "date_added",
        "folder_id",
        "rating",
        "release_id",
        "title",
        "artists",
        "release_year",
        "release_decade",
        "genres",
        "styles",
        "format",
        "labels",
        "resource_url",
        "thumb",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def write_quality_notes(rows: list[dict[str, Any]], output_path: Path) -> Path:
    total = len(rows)
    missing_year = sum(1 for row in rows if not row.get("release_year"))
    missing_genre = sum(1 for row in rows if not row.get("genres"))
    missing_artist = sum(1 for row in rows if not row.get("artists"))
    duplicate_release_ids = total - len({row.get("release_id") for row in rows if row.get("release_id")})

    lines = [
        "# Collection Cleaning Notes",
        "",
        f"Rows written: {total}",
        "",
        "## Decisions",
        "",
        "- Output is one row per Discogs collection instance, not one row per artist/genre/style.",
        "- Array fields such as artists, genres, styles, and labels are semicolon-delimited for the first clean CSV milestone.",
        "- Release year values of `0`, blank, or non-numeric are normalized to blank and decade `Unknown`.",
        "- Duplicate collection instance ids are dropped, preserving the first observed row.",
        "",
        "## Basic quality checks",
        "",
        f"- Missing release year: {missing_year}",
        f"- Missing genre: {missing_genre}",
        f"- Missing artist: {missing_artist}",
        f"- Duplicate release ids retained as separate collection instances: {duplicate_release_ids}",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean raw Discogs collection JSON")
    parser.add_argument("--input", type=Path, help="Raw collection JSON; defaults to newest data/raw/collection_*.json")
    parser.add_argument("--output", type=Path, default=PROCESSED_DATA_DIR / "collection_clean.csv")
    parser.add_argument("--notes", type=Path, default=DOCS_DIR / "cleaning_decisions.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input or latest_raw_collection()
    records = load_collection(input_path)
    rows = normalize_records(records)
    output_path = write_csv(rows, args.output)
    notes_path = write_quality_notes(rows, args.notes)
    print(f"Cleaned {len(rows)} records from {input_path}")
    print(f"Wrote processed CSV to {output_path}")
    print(f"Wrote cleaning notes to {notes_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
