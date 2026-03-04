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
   # Edit .env with your Discogs API token
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
