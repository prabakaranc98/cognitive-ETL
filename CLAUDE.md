# CLAUDE.md — Claude Code Instructions for Cognitive ETL

## Project Overview
This is a Cognitive ETL system: Notion (backend) → Python (sync/build) → GitHub Pages (storefront).
Three Notion databases: Sources, Atoms, Artifacts — connected via relations.

## Key Commands

### Sync & Build
```bash
./scripts/cognitive_etl.sh test      # Smoke test local build path
./scripts/cognitive_etl.sh sync      # Pull latest from Notion → data/*.json
./scripts/cognitive_etl.sh build     # Build static site → dist/
./scripts/cognitive_etl.sh refresh   # test + sync + build
./scripts/cognitive_etl.sh serve     # Serve dist/ locally on 127.0.0.1:4323
```

### Deploy
```bash
# GitHub Actions handles deploys on push to main / workflow_dispatch / schedule
# Required GitHub secrets:
# NOTION_API_KEY, SOURCES_DB_ID, ATOMS_DB_ID, ARTIFACTS_DB_ID
```

### Common Workflows

**Add a Source:**
Use the Notion API to create a page in the Sources database.
Required fields: Name (title), Type, Author, Domain, Status="Reading"

**Extract Atoms from highlights:**
Parse the user's highlights/notes into atomic claims.
Each atom needs: Claim (title), Definition, Because, Boundaries, Source Quote
Push to Atoms DB via Notion API, link to the Source.

**Ship an Artifact:**
Create the artifact content (slides, post, etc.)
Create Artifacts DB entry linking to the atoms it uses.
Increment Reuse Count on each referenced atom.
Calculate Points: +3 for artifact, +5 if ≥3 atoms linked, +10 per reused atom.

**Rebuild & Deploy:**
```bash
./scripts/cognitive_etl.sh refresh
# Then commit and push to trigger GitHub Actions deploy
```

## File Structure
- `scripts/sync_notion.py` — stable CLI entrypoint for Notion API → JSON sync
- `scripts/build_site.py` — stable CLI entrypoint for JSON → static HTML build
- `scripts/cognitive_etl.sh` — consolidated local entrypoint for test/sync/build/serve
- `src/cognitive_etl/config.py` — shared paths and environment-backed settings
- `src/cognitive_etl/notion_sync.py` — Notion sync implementation
- `src/cognitive_etl/site_builder.py` — static site build implementation
- `tests/` — smoke tests with sample data fixtures
- `.github/workflows/ci.yml` — GitHub smoke-test workflow
- `.github/workflows/deploy.yml` — GitHub Pages deploy workflow
- `data/` — JSON cache of Notion data (gitignored except schema)
- `src/templates/` — Jinja2 HTML templates
- `src/static/` — CSS, JS, assets
- `dist/` — Built site output (GitHub Pages serves this)

## Notion Database IDs
- Sources: 5fa5511f-5aba-40d7-a12b-84eb9794c238
- Atoms: e5ea2f2f-0dd2-4078-bf1f-6b0b7ce7ab28
- Artifacts: 964e4625-0b58-4c2e-a310-95e41203893c

## Code Style
- Python: type hints, f-strings, pathlib
- HTML: semantic, accessible
- JS: vanilla ES6+, no frameworks on the frontend
- CSS: custom properties, responsive, dark mode support
