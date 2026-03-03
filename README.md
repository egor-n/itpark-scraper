# IT Park Moldova Residents Scraper

Scrapes the [Moldova IT Park](https://mitp.md) residents registry.

## Usage

```bash
pip install -r requirements.txt
python scraper.py
```

Open `index.html` in a browser or visit https://mitp.pages.dev

## Files

- `scraper.py` — resumable scraper
- `data.jsonl` — raw scraped records (one JSON per line)
- `data.json` — array for the web page
- `state.json` — scraper resume state (auto-created)
- `index.html` — static web page

## Deploying

After scraping new data:

```bash
python scraper.py
git add data.jsonl data.json state.json
git commit -m "data: update scraped data"
git push
wrangler pages deploy . --project-name mitp --branch main
```
