# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper (resumable — safe to re-run)
python scraper.py

# Deploy to Cloudflare Pages after scraping
wrangler pages deploy . --project-name mitp --branch main
```

The scraper is resumable: if interrupted, re-running it picks up from the last saved page in `state.json`.

## Architecture

This is a two-part project: a Python scraper and a static HTML frontend.

### Scraper (`scraper.py`)

Hits the Moldova IT Park API (`https://mitp.md/p/api/web/list/getData`) with POST requests to paginate through all residents. Progress is saved to `state.json` after each page so runs can be interrupted and resumed.

Output pipeline:
- `data.jsonl` — append-only raw records (one JSON object per line)
- `data.json` — full array rebuilt from `data.jsonl` on each run (consumed by the frontend)
- `state.json` — resume cursor (`last_page`, `total_elements`)

### Frontend (`index.html`)

A single self-contained HTML file. Loads `data.json` via `fetch('./data.json')` at runtime and renders it using **AG Grid Community** (loaded from CDN). No build step. Features: search bar, status filter (Active/Inactive), sortable columns, stat summary cards.

Key data fields from the API: `residentNumber`, `companyName`, `administrator`, `legalHeadquarters`, `email`, `phone`, `isResident` (Active/Inactive), `activities` (array), `registrationDate`, `exitDate`.

### Deployment

Hosted on Cloudflare Pages at `https://mitp.pages.dev`. The entire repo root (including `index.html` and `data.json`) is deployed as a static site.
