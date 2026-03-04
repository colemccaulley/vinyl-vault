"""
Discogs API client for Vinyl Vault.

Handles authentication, collection fetching, and raw data export.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import discogs_client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def get_client() -> discogs_client.Client:
    """Create and return an authenticated Discogs client."""
    token = os.getenv("DISCOGS_USER_TOKEN")
    if not token:
        raise ValueError(
            "DISCOGS_USER_TOKEN not found in environment. "
            "Copy .env.example to .env and add your token."
        )

    return discogs_client.Client(
        "VinylVault/1.0",
        user_token=token,
    )


def test_auth() -> dict:
    """Test authentication and return user info."""
    client = get_client()
    me = client.identity()
    return {
        "username": me.username,
        "id": me.id,
        "num_collection": me.num_collection,
    }


def fetch_collection() -> list[dict]:
    """
    Fetch the full collection from Discogs.

    Returns a list of dicts, one per collection item, with release details.
    The library handles pagination automatically.
    """
    client = get_client()
    me = client.identity()

    print(f"Fetching collection for {me.username}...")
    print(f"Expected items: {me.num_collection}")

    collection = []
    folder = me.collection_folders[0]  # Folder 0 = all items

    for i, item in enumerate(folder.releases, 1):
        release = item.release

        record = {
            "instance_id": item.id,
            "date_added": str(item.date_added),
            "rating": item.rating,
            "folder_id": item.folder_id,
            "release": {
                "id": release.id,
                "title": release.title,
                "year": release.year,
                "artists": [
                    {"name": a.name, "id": a.id} for a in release.artists
                ],
                "genres": release.genres,
                "styles": getattr(release, "styles", []),
                "formats": release.formats,
                "labels": [
                    {"name": l.name, "catno": l.data.get("catno", "")}
                    for l in release.labels
                ],
                "country": getattr(release, "country", ""),
                "tracklist": [
                    {"position": t.position, "title": t.title}
                    for t in release.tracklist
                ],
            },
        }

        collection.append(record)

        if i % 25 == 0:
            print(f"  Fetched {i} items...")

    print(f"Done! Fetched {len(collection)} items total.")
    return collection


def save_raw(data: list[dict], filename: str | None = None) -> Path:
    """Save raw collection data to a JSON file in data/raw/."""
    if filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"collection_{today}.json"

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = RAW_DATA_DIR / filename

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Saved to {filepath} ({len(data)} items)")
    return filepath


# ---- Main entry point ----

if __name__ == "__main__":
    # Step 1: Test authentication
    print("Testing Discogs authentication...")
    try:
        user_info = test_auth()
        print(f"✓ Authenticated as: {user_info['username']}")
        print(f"  Collection size: {user_info['num_collection']} items")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print("  Make sure your .env file has a valid DISCOGS_USER_TOKEN")
        exit(1)

    print()

    # Step 2: Fetch collection
    collection = fetch_collection()

    # Step 3: Save raw data
    filepath = save_raw(collection)

    print()
    print(f"Next step: explore the data in {filepath}")
    print("Try: python -c \"import json; data = json.load(open('{}')); print(len(data))\"".format(filepath))
