# Vinyl Vault Data Dictionary

This file is generated from a raw Discogs collection export by:

```bash
python src/transforms/explore_collection.py
```

Run the command after creating `data/raw/collection_YYYY-MM-DD.json` with:

```bash
python src/ingestion/discogs_client.py --fetch-collection
```

## Initial key fields for analytics

| Field | Notes |
|---|---|
| `id` | Discogs collection instance identifier. |
| `date_added` | Timestamp when the record was added to the collection. |
| `basic_information.id` | Discogs release id; useful for joins to pricing/enrichment data. |
| `basic_information.title` | Release title. |
| `basic_information.artists[].name` | Artist names for artist breakdowns. |
| `basic_information.year` | Release year for decade distribution. |
| `basic_information.genres[]` | Broad genre tags. |
| `basic_information.styles[]` | More granular style tags. |
| `basic_information.formats[].name` | Physical format such as Vinyl, CD, etc. |
| `basic_information.labels[].name` | Label/publisher metadata. |

## Data quality questions to validate after the first full pull

- Are any release years missing or set to `0`?
- Are all records really vinyl, or are there mixed formats in the collection?
- Do multi-artist records need a bridge table later for artist analytics?
- Should genre/style fields be split into bridge tables for dashboard filtering?
- Are private collection notes present in the raw export, and should they be excluded from processed outputs?
