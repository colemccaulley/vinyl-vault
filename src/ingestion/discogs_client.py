"""
Discogs API client for Vinyl Vault.

Supports two safe CLI actions:
- --test-auth: verify DISCOGS_USER_TOKEN and print non-secret profile metadata.
- --fetch-collection: pull the full collection with pagination and land raw JSON.

Default action is --test-auth so running the script never accidentally starts a
full collection pull.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DISCOGS_API_BASE = "https://api.discogs.com"
USER_AGENT = "VinylVault/1.0 +https://github.com/colemccaulley/vinyl-vault"
PLACEHOLDER_VALUES = {"", "your_token_here", "your_username_here", "changeme", "todo"}


class DiscogsConfigError(RuntimeError):
    """Raised when local Discogs configuration is missing or unsafe."""


class DiscogsApiError(RuntimeError):
    """Raised when Discogs returns an unsuccessful API response."""


def load_env_file(path: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from .env without requiring python-dotenv."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _clean_env_value(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    if value.lower() in PLACEHOLDER_VALUES:
        return None
    return value


def get_token() -> str:
    """Return the Discogs personal access token or raise a clear config error."""
    load_env_file()
    token = _clean_env_value("DISCOGS_USER_TOKEN")
    if not token:
        raise DiscogsConfigError(
            "DISCOGS_USER_TOKEN is missing or still set to the placeholder value. "
            "Copy .env.example to .env and add a Discogs personal access token."
        )
    return token


def get_configured_username() -> str | None:
    """Return optional configured Discogs username, ignoring placeholder values."""
    load_env_file()
    return _clean_env_value("DISCOGS_USERNAME")


def discogs_get(path: str, *, params: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    """Perform an authenticated GET request against the Discogs API."""
    token = get_token()
    query = f"?{urlencode(params)}" if params else ""
    url = f"{DISCOGS_API_BASE}{path}{query}"
    request = Request(
        url,
        headers={
            "Authorization": f"Discogs token={token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise DiscogsApiError(f"Discogs API returned HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise DiscogsApiError(f"Discogs API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise DiscogsApiError("Discogs API returned invalid JSON") from exc


def test_auth() -> dict[str, Any]:
    """Authenticate and return non-secret Discogs identity metadata."""
    identity = discogs_get("/oauth/identity")
    return {
        "username": identity.get("username"),
        "id": identity.get("id"),
        "resource_url": identity.get("resource_url"),
        "consumer_name": identity.get("consumer_name"),
    }


def fetch_collection(username: str | None = None, *, per_page: int = 50, sleep_seconds: float = 1.1) -> dict[str, Any]:
    """Fetch all collection releases for a Discogs user with explicit pagination."""
    if username is None:
        identity = test_auth()
        username = identity["username"]
    if not username:
        raise DiscogsConfigError("Could not determine Discogs username from identity or DISCOGS_USERNAME.")

    releases: list[dict[str, Any]] = []
    page = 1
    total_pages = 1
    total_items = None

    while page <= total_pages:
        payload = discogs_get(
            f"/users/{username}/collection/folders/0/releases",
            params={"page": page, "per_page": per_page, "sort": "added", "sort_order": "desc"},
        )
        pagination = payload.get("pagination", {})
        total_pages = int(pagination.get("pages") or 1)
        total_items = pagination.get("items", total_items)
        page_releases = payload.get("releases", [])
        releases.extend(page_releases)
        print(f"Fetched page {page}/{total_pages}: {len(page_releases)} releases")
        page += 1
        if page <= total_pages:
            time.sleep(sleep_seconds)

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "username": username,
        "source": "discogs_collection_folder_0",
        "expected_count": total_items,
        "record_count": len(releases),
        "releases": releases,
    }


def save_raw_collection(data: dict[str, Any], filename: str | None = None) -> Path:
    """Save raw collection data to data/raw/collection_YYYY-MM-DD.json."""
    if filename is None:
        filename = f"collection_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DATA_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Saved {data.get('record_count', 0)} collection records to {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discogs ingestion utility for Vinyl Vault")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--test-auth", action="store_true", help="Verify Discogs token and print user metadata")
    action.add_argument("--fetch-collection", action="store_true", help="Fetch full collection and save raw JSON")
    parser.add_argument("--username", help="Discogs username; defaults to API identity or DISCOGS_USERNAME")
    parser.add_argument("--output", help="Optional output filename under data/raw/")
    parser.add_argument("--per-page", type=int, default=50, choices=range(1, 101), metavar="1-100")
    parser.add_argument("--sleep-seconds", type=float, default=1.1, help="Delay between paginated requests")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.fetch_collection:
            username = args.username or get_configured_username()
            data = fetch_collection(username=username, per_page=args.per_page, sleep_seconds=args.sleep_seconds)
            save_raw_collection(data, args.output)
            return 0

        # Safe default: auth-only smoke test.
        user_info = test_auth()
        print(f"Authenticated as: {user_info.get('username')}")
        print(f"Discogs user id: {user_info.get('id')}")
        print(f"Consumer app: {user_info.get('consumer_name')}")
        return 0
    except (DiscogsConfigError, DiscogsApiError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
