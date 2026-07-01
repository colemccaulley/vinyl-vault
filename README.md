# 🎵 Vinyl Vault

A data engineering pipeline that ingests vinyl record collection data from Discogs, tracks market values over time, enriches with external sources, and serves analytics through a dashboard.

## Architecture

```
Discogs API → Ingestion (Python) → Storage (Postgres) → Transform (dbt) → Dashboard (Streamlit)
```

## Project Structure

```
vinyl-vault/
├── src/
│   ├── ingestion/      # API clients and data extraction
│   ├── transforms/     # Data cleaning and transformation
│   └── utils/          # Shared utilities and config
├── data/
│   ├── raw/            # Raw API responses (git-ignored)
│   └── processed/      # Cleaned data (git-ignored)
├── tests/              # Unit and integration tests
├── docs/               # Documentation and architecture diagrams
├── .env.example        # Environment variable template
└── requirements.txt    # Python dependencies
```

## Setup

1. Clone the repo
   ```bash
   git clone git@github.com:colemccaulley/vinyl-vault.git
   cd vinyl-vault
   ```

2. Create a virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env with your Discogs personal access token and username
   ```

## Local Pipeline Quick Start

The ingestion CLI defaults to the safe auth-only smoke test. It will not pull your full collection unless you explicitly pass `--fetch-collection`.

```bash
# Issue #1: verify Discogs authentication
python src/ingestion/discogs_client.py --test-auth

# Issue #2: pull the full collection to data/raw/collection_YYYY-MM-DD.json
PYTHONUNBUFFERED=1 python src/ingestion/discogs_client.py --fetch-collection

# Issue #3: profile the newest raw collection and write docs/data_dictionary.md
python src/transforms/explore_collection.py

# Issue #4: clean/normalize the newest raw collection to data/processed/collection_clean.csv
python src/transforms/clean_collection.py
```

## Tech Stack

- **Language:** Python
- **Ingestion:** Discogs API (REST)
- **Storage:** PostgreSQL (local) → Azure SQL (cloud)
- **Transformation:** dbt
- **Orchestration:** Dagster
- **Dashboard:** Streamlit / Power BI

## Roadmap

- [x] Project scaffolding
- [ ] Discogs API ingestion
- [ ] Local database storage
- [ ] Incremental loading
- [ ] Orchestration with Dagster
- [ ] Data enrichment (Spotify, MusicBrainz)
- [ ] Cloud migration (Azure)
- [ ] dbt transformations
- [ ] Dashboard

## License

MIT
