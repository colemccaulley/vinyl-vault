# Collection Cleaning Notes

This file documents the first-pass cleaning decisions implemented in:

```bash
python src/transforms/clean_collection.py
```

The script updates this file with concrete row counts and quality metrics when run against a real raw collection export.

## Current decisions

- The first processed dataset is one row per Discogs collection instance.
- `instance_id` is treated as the collection item key.
- `release_id` is retained separately because the same release can appear more than once in a collection.
- Artist, genre, style, format, and label arrays are preserved as semicolon-delimited fields in the first CSV milestone.
- Release years of `0`, blank, or invalid values become blank with decade `Unknown`.
- Duplicate collection instance ids are dropped, keeping the first observed record.

## Future modeling notes

For the database/dbt phase, split multi-value fields into relational tables or bridge tables:

- `collection_items`
- `releases`
- `artists`
- `release_artists`
- `genres`
- `release_genres`
- `styles`
- `release_styles`
- `labels`
- `release_labels`
