# Discogs API Guide for Vinyl Vault

## Overview

We'll use the `python3-discogs-client` library instead of raw HTTP requests. It handles pagination, rate limiting, and object mapping for us.

**Install:** `pip install python3-discogs-client`

**Rate Limit:** 60 requests per minute (authenticated). The library handles this automatically.

## Authentication

```python
import discogs_client

d = discogs_client.Client('VinylVault/1.0', user_token='YOUR_TOKEN')
me = d.identity()  # Returns your user profile
```

Get your token at: https://www.discogs.com/settings/developers

## Key Endpoints We'll Use

### 1. Collection (Phase 1)
```python
# Get all items in your collection (folder 0 = all)
me = d.identity()
for item in me.collection_folders[0].releases:
    release = item.release
    print(release.title)
    print(release.artists)
    print(release.year)
    print(release.genres)
    print(release.styles)
    print(release.formats)
    print(item.date_added)
```

**Available fields per release:**
- `title` — album/release title
- `artists` — list of Artist objects
- `year` — release year
- `genres` — list of genres (e.g., ['Rock', 'Pop'])
- `styles` — list of sub-genres (e.g., ['Indie Rock', 'Alternative'])
- `formats` — list of format dicts (Vinyl, CD, etc. + details like color)
- `labels` — record label(s)
- `country` — country of release
- `tracklist` — list of Track objects
- `images` — album art URLs (requires auth)
- `id` — unique Discogs release ID
- `data` — raw dict of all API fields

**Collection item fields:**
- `date_added` — when you added it to your collection
- `rating` — your rating (0-5)
- `notes` — custom field notes
- `folder_id` — which collection folder it's in

### 2. Marketplace/Pricing (Phase 2)
```python
# Get marketplace stats for a release
release = d.release(12345)
stats = release.marketplace_stats
# Contains: lowest_price, num_for_sale, blocked_from_sale
```

For more detailed pricing, use the marketplace search:
```python
# This requires additional API calls
# GET /marketplace/price_suggestions/{release_id}
# Returns suggested prices by condition (Mint, VG+, VG, etc.)
```

### 3. Collection Folders
```python
# List all folders
for folder in me.collection_folders:
    print(f"{folder.id}: {folder.name} ({folder.count} items)")

# Folder 0 = All items
# Folder 1 = Uncategorized
# Folder 2+ = Custom folders
```

### 4. Search
```python
results = d.search('Dark Side of the Moon', type='release')
for result in results.page(1):
    print(result.title, result.year)
```

## Pagination

The library handles pagination through iterators:
```python
# This automatically paginates through all items
for item in me.collection_folders[0].releases:
    # processes ALL items, fetching new pages as needed
    process(item)

# Or access specific pages
releases = me.collection_folders[0].releases
page_1 = releases.page(1)  # 50 items per page by default
```

## Data Shape (What We'll Store)

### Raw Collection Item
```json
{
    "id": 12345,
    "instance_id": 67890,
    "date_added": "2024-01-15T10:30:00-06:00",
    "rating": 4,
    "folder_id": 1,
    "release": {
        "id": 12345,
        "title": "OK Computer",
        "year": 1997,
        "artists": [{"name": "Radiohead", "id": 3840}],
        "genres": ["Electronic", "Rock"],
        "styles": ["Alternative Rock", "Art Rock"],
        "formats": [{"name": "Vinyl", "qty": "2", "descriptions": ["LP", "Album", "Reissue"]}],
        "labels": [{"name": "XL Recordings", "catno": "XLLP868"}],
        "country": "UK"
    }
}
```

## Rate Limiting Strategy

- Authenticated: 60 requests/minute
- The `python3-discogs-client` handles rate limiting with backoff
- For initial full collection pull, expect ~1 request per page (50 items/page)
- A 500-record collection = ~10 API calls = under a minute
- Pricing data requires 1 call per release, so throttle accordingly

## Gotchas

1. **Images require authentication** — make sure you're using a token
2. **Marketplace stats may be empty** for obscure releases
3. **Multiple pressings** — same album can have many release IDs (original vs reissue)
4. **Master releases** — group all pressings together; useful for deduplication
5. **Rate limit 429s** — the library sleeps automatically, but log when it happens
