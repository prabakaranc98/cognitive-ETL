# Cognitive ETL

Extract, transform, and publish a personal knowledge base.
The project pulls structured notes from Notion, writes a local JSON cache, and builds a static storefront for browsing sources, atoms, artifacts, and graph data.

## Flow

```text
Notion databases
  -> sync step
  -> data/*.json cache
  -> site build step
  -> dist/ static site
```

## Project Layout

```text
cognitive-ETL/
├── .github/workflows/       GitHub CI and Pages deploy workflows
├── data/                    Local JSON cache from Notion
├── scripts/                 Stable command entrypoints
│   ├── cognitive_etl.sh
│   ├── build_site.py
│   └── sync_notion.py
├── src/
│   ├── cognitive_etl/       Python package with project logic
│   │   ├── config.py
│   │   ├── notion_sync.py
│   │   └── site_builder.py
│   ├── static/              Frontend assets
│   └── templates/           Jinja templates
├── tests/                   Local smoke tests and sample fixtures
├── .env.example             Environment variable template
├── CLAUDE.md                Local assistant workflow notes
└── requirements.txt         Python dependencies
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env

./scripts/cognitive_etl.sh refresh
./scripts/cognitive_etl.sh serve 4323
```

## Commands

```bash
./scripts/cognitive_etl.sh test
./scripts/cognitive_etl.sh sync
./scripts/cognitive_etl.sh build
./scripts/cognitive_etl.sh refresh
./scripts/cognitive_etl.sh serve 4323
```

## GitHub Pages Deploy

The repo includes a Pages workflow in `.github/workflows/deploy.yml`.

Set these repository secrets before enabling it:
- `NOTION_API_KEY`
- `SOURCES_DB_ID`
- `ATOMS_DB_ID`
- `ARTIFACTS_DB_ID`

Optional repository variable:
- `SITE_URL`

Then set Pages in GitHub repository settings to use `GitHub Actions` as the source.

## Environment Variables

Required for Notion sync:
- `NOTION_API_KEY`
- `SOURCES_DB_ID`
- `ATOMS_DB_ID`
- `ARTIFACTS_DB_ID`

Optional site metadata:
- `SITE_TITLE`
- `SITE_AUTHOR`
- `SITE_URL`
- `SITE_DESCRIPTION`

## Storefront Features

- Artifact gallery for shipped outputs and drafts
- Knowledge graph powered by generated `graph.json`
- Atom explorer with search and domain filters
- Search index spanning atoms, artifacts, and sources
- Summary stats generated during sync/build

## Notes

- `scripts/` stays stable so existing commands do not change.
- `src/cognitive_etl/` holds the real Python implementation.
- `data/*.json` is ignored by git except for `data/.gitkeep`.
- `dist/` is generated output and can be rebuilt at any time.
- `.github/workflows/ci.yml` runs a lightweight smoke test on GitHub.
- `.github/workflows/deploy.yml` syncs Notion, builds the site, and deploys `dist/` to GitHub Pages.
- `scripts/cognitive_etl.sh` is the consolidated local entrypoint for test/sync/build/serve.
