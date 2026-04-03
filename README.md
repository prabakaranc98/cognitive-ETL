# Cognitive ETL

Extract, transform, and load knowledge as a cognitive workflow.

This project is a low-friction system for turning books, papers, ideas, conversations, and notes into:

- structured `Sources`
- reusable `Atoms`
- public-facing `Artifacts`
- a static knowledge storefront that compounds over time

The core idea is simple:

- `Extract` what matters from reading and thinking
- `Transform` it into clearer, smaller units of thought
- `Load` it into views that are easy to browse, link, search, and publish

Human judgment does the meaning work.
AI helps with synthesis and structuring.
Automation handles sync, indexing, rendering, and deployment.

## Why This Exists

Most knowledge systems over-reward input:

- books read
- highlights saved
- notes collected

They do not create enough pressure to:

- clarify
- connect
- reuse
- ship

Cognitive ETL is meant to fix that.

It treats thinking like a pipeline:

```text
Source material
  -> capture and extraction
  -> atomic transformation
  -> linked graph + artifacts
  -> public presentation
```

The goal is not a perfect taxonomy.
The goal is a system you keep using.

## Current System

Today, the repo is built around four first-class system objects:

- `Sources` for books, papers, articles, conversations, and other inputs
- `Captures` for highlights, fragments, excerpts, reactions, and rough extraction
- `Atoms` for atomic claims, mechanisms, critiques, definitions, and linked ideas
- `Artifacts` for outputs like decks, notes, posts, and other consumable summaries

Those databases sync into local JSON, and the site is built from that local cache.

```text
Notion
  -> sync step
  -> data/*.json
  -> site build
  -> dist/ static storefront
```

## What The Site Does

The storefront is the public presentation layer for the knowledge graph.

It currently includes:

- a gallery for sources, captures, atoms, and artifacts
- a capture explorer and an atom explorer with search and domain filtering
- a graph view for sources, captures, atoms, artifacts, and their relations
- internal detail pages for sources, captures, atoms, and artifacts
- a generated `content/` folder with readable markdown exports
- public-link handling that prefers internal pages and only exposes explicitly public outbound URLs

Important behavior:

- the site no longer relies on private Notion page links as the main reading path
- internal detail pages are the default reading surface
- public outbound links are shown only if they appear viewable, such as:
  - `notion.site`
  - Google Slides share links
  - GitHub gists
  - custom public domains
- private `notion.so` workspace links are suppressed from the public UI

If a Notion page has body content, the sync pulls that content and renders it into the detail page.
If the Notion page body is empty, the site falls back to structured property-based rendering so the page is still useful.

## Knowledge Model

### Source

A source is any input you learned from.

Examples:

- book
- paper
- article
- lecture
- conversation

Typical fields:

- `Name`
- `Type`
- `Author`
- `Status`
- `Domain`
- `Source URL`
- `Related Sources`
- `Key Takeaway`

### Capture

A capture is the first extraction surface.
It sits between raw source material and cleaned atoms.

Examples:

- highlight
- excerpt
- thought fragment
- objection
- slide fragment
- rough synthesis

Typical fields:

- `Name` or `Title`
- `Capture ID`
- `Capture Type`
- `Status`
- `Source`
- `Spawned Atoms`
- `Artifacts`
- `Summary` or `Excerpt`
- `Capture URL`

### Atom

An atom is the main unit of thought in the system.
The graph is built from atoms, not from books.

Typical fields:

- `Claim`
- `Definition`
- `Because`
- `Boundaries`
- `Source Quote`
- `Source`
- `Related Atoms`
- `Confidence`
- `Reuse Count`

### Artifact

An artifact is a consumable output built from one or more atoms.

Examples:

- slide deck
- one-pager
- short note
- post
- synthesis page

Typical fields:

- `Name`
- `Format`
- `Status`
- `Built From`
- `Source`
- `Artifact URL`
- `Points`

## Repo Layout

```text
cognitive-ETL/
├── .github/workflows/       CI and GitHub Pages deploy workflows
├── content/                 Generated markdown exports for sources, captures, atoms, artifacts
├── data/                    Local JSON cache from Notion
├── dist/                    Generated static site
├── scripts/                 Stable command entrypoints
│   ├── cognitive_etl.sh
│   ├── build_site.py
│   └── sync_notion.py
├── src/
│   ├── cognitive_etl/       Python package with sync/build logic
│   ├── static/              CSS and JS
│   └── templates/           Jinja templates
├── tests/                   Smoke tests and fixtures
├── .env.example
├── CLAUDE.md
└── requirements.txt
```

## Local Usage

### 1. Install

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in:

- `NOTION_API_KEY`
- `SOURCES_DB_ID`
- `CAPTURES_DB_ID` (optional, enables the capture layer)
- `ATOMS_DB_ID`
- `ARTIFACTS_DB_ID`

### 2. Run Everything

```bash
./scripts/cognitive_etl.sh refresh
./scripts/cognitive_etl.sh serve 4323
```

This rebuilds two outputs:

- `dist/` for the static site
- `content/` for local markdown exports

### 3. Useful Commands

```bash
./scripts/cognitive_etl.sh test
./scripts/cognitive_etl.sh sync
./scripts/cognitive_etl.sh build
./scripts/cognitive_etl.sh refresh
./scripts/cognitive_etl.sh serve 4323
./scripts/cognitive_etl.sh all 4323
```

## Deployment

GitHub Pages deployment is already wired in `.github/workflows/deploy.yml`.
The workflow uses GitHub Actions secrets directly on the runner. It does not rely on a checked-in `.env` file.
The current project-pages target is `https://prabakaranc98.github.io/cogETL`.

Required GitHub repository secrets:

- `NOTION_API_KEY`
- `SOURCES_DB_ID`
- `ATOMS_DB_ID`
- `ARTIFACTS_DB_ID`

Optional GitHub repository secret:

- `CAPTURES_DB_ID`

Then set GitHub Pages to use `GitHub Actions` as the source.

The deploy workflow:

- runs smoke tests
- syncs Notion
- rebuilds the storefront
- verifies the Pages bundle exists
- deploys `dist/` to GitHub Pages

## Environment Variables

Required:

- `NOTION_API_KEY`
- `SOURCES_DB_ID`
- `ATOMS_DB_ID`
- `ARTIFACTS_DB_ID`

Optional:

- `CAPTURES_DB_ID`
- `SITE_TITLE`
- `SITE_AUTHOR`
- `SITE_DESCRIPTION`
- `COGNITIVE_ETL_DATA_DIR`
- `COGNITIVE_ETL_DIST_DIR`

## How To Work With It

The intended loop is:

1. Add or update a `Source` in Notion.
2. Create `Captures` while reading or thinking, before trying to compress everything.
3. Distill captures into `Atoms`.
4. Link atoms to each other and to related sources.
5. Ship an `Artifact`.
6. Run sync/build or let GitHub Actions deploy the refreshed public view.

This repo is at its best when:

- the private thinking stays lightweight
- captures preserve rough extraction instead of forcing premature compression
- the atoms stay sharp
- source-to-source relationships become explicit
- artifacts get shipped instead of sitting as notes

## Current Direction

The system is moving toward:

- richer source-to-source relationships
- stronger capture-to-atom and capture-to-artifact flows
- more complete page-body rendering from Notion
- multiple public links per item
- stronger detail pages and recommendations
- a cleaner public “reading surface” so the site itself becomes the primary place to consume the work

## Notes

- `scripts/` is the stable operational surface
- `src/cognitive_etl/` holds the real implementation
- `data/` is a cache, not the source of truth
- `dist/` is fully rebuildable
- `content/` is a generated markdown layer meant for local reading, browsing, and reuse
- the README describes the system as it exists now, not just the original concept
