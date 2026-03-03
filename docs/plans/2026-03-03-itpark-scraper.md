# IT Park Scraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a resumable Python scraper for Moldova IT Park residents registry and a static AG Grid web page, deployed to Cloudflare Pages at mitp.pages.dev via a private GitHub repo.

**Architecture:** The scraper fetches paginated JSON from the MITP API, appends records to `data.jsonl`, and exports `data.json` for the frontend. A `state.json` file tracks the last completed page so reruns resume where they left off. The frontend is a single `index.html` using AG Grid Community via CDN with virtual row rendering.

**Tech Stack:** Python 3 + requests, AG Grid Community v33 (CDN), Cloudflare Pages, GitHub (egor-n account)

---

### Task 1: Project scaffolding + .gitignore

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create requirements.txt**

```
requests
```

**Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
venv/
```

Note: `data.jsonl`, `data.json`, `state.json` are intentionally NOT ignored — we commit data to the repo so Cloudflare Pages can serve it.

**Step 3: Create README.md**

```markdown
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
```

**Step 4: Verify files exist**

```bash
ls -la requirements.txt .gitignore README.md
```

Expected: all three files listed.

---

### Task 2: Write the scraper

**Files:**
- Create: `scraper.py`

**Step 1: Write scraper.py**

```python
import json
import time
import requests
from pathlib import Path

API_URL = "https://mitp.md/p/api/web/list/getData"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ro",
    "Content-Type": "application/json",
}
PAGE_SIZE = 100
DELAY = 0.5  # seconds between requests

JSONL_PATH = Path("data.jsonl")
JSON_PATH = Path("data.json")
STATE_PATH = Path("state.json")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"last_page": -1, "total_elements": 0}


def save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def fetch_page(page_number: int) -> dict:
    body = {
        "id": "ipResidentsRegistry",
        "textFilter": "",
        "advancedFilter": [],
        "pageSize": PAGE_SIZE,
        "pageNumber": page_number,
        "sortFields": [{"field": "residentNumber", "direction": "ASC"}],
    }
    resp = requests.post(API_URL, headers=HEADERS, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def export_json():
    records = []
    if JSONL_PATH.exists():
        for line in JSONL_PATH.read_text().splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    JSON_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"Exported {len(records)} records to {JSON_PATH}")


def main():
    state = load_state()

    # Peek at page 0 to get current totals
    print("Checking current total...")
    first_page = fetch_page(0)
    total_elements = first_page["totalElements"]
    total_pages = first_page["totalPages"]
    print(f"API reports {total_elements} total elements across {total_pages} pages")

    if total_elements <= state["total_elements"] and state["last_page"] >= total_pages - 1:
        print("Nothing new to scrape. Exiting.")
        export_json()
        return

    start_page = state["last_page"] + 1
    print(f"Resuming from page {start_page} (0-indexed)")

    with JSONL_PATH.open("a", encoding="utf-8") as f:
        # Write page 0 if starting fresh
        if start_page == 0:
            for record in first_page["content"]:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            state["last_page"] = 0
            save_state(state)
            print(f"Page 0: {len(first_page['content'])} records")
            start_page = 1

        for page in range(start_page, total_pages):
            time.sleep(DELAY)
            data = fetch_page(page)
            records = data["content"]
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            state["last_page"] = page
            state["total_elements"] = total_elements
            save_state(state)
            print(f"Page {page}/{total_pages - 1}: {len(records)} records")

    print("Scraping complete.")
    export_json()


if __name__ == "__main__":
    main()
```

**Step 2: Run the scraper (first run)**

```bash
pip install -r requirements.txt
python scraper.py
```

Expected output:
```
Checking current total...
API reports 3578 total elements across 36 pages
Resuming from page 0 (0-indexed)
Page 0: 100 records
Page 1/35: 100 records
...
Scraping complete.
Exported 3578 records to data.json
```

**Step 3: Verify output files**

```bash
wc -l data.jsonl
python -c "import json; d=json.load(open('data.json')); print(len(d), 'records')"
cat state.json
```

Expected: `data.jsonl` has 3578 lines, `data.json` has 3578 records, `state.json` shows `"last_page": 35`.

**Step 4: Test resume behavior**

```bash
# Edit state.json to simulate partial run
python -c "import json; s=json.load(open('state.json')); s['last_page']=10; open('state.json','w').write(json.dumps(s))"
python scraper.py
```

Expected: scraper resumes from page 11, doesn't re-fetch pages 0-10.

**Step 5: Restore full state and commit**

```bash
python scraper.py  # re-run to restore full state
git add scraper.py requirements.txt
git commit -m "feat: add resumable scraper"
```

---

### Task 3: Write the web page

**Files:**
- Create: `index.html`

**Step 1: Write index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Moldova IT Park Residents</title>
  <script src="https://cdn.jsdelivr.net/npm/ag-grid-community@33/dist/ag-grid-community.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f5f5f5;
      color: #1a1a1a;
    }

    header {
      background: #1a56db;
      color: #fff;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      gap: 24px;
      flex-wrap: wrap;
    }

    header h1 {
      font-size: 1.2rem;
      font-weight: 600;
      flex: 1;
    }

    .stats {
      display: flex;
      gap: 16px;
      font-size: 0.85rem;
      opacity: 0.9;
    }

    .stat strong { font-size: 1.1rem; display: block; }

    .controls {
      background: #fff;
      padding: 12px 24px;
      display: flex;
      gap: 12px;
      align-items: center;
      border-bottom: 1px solid #e5e7eb;
      flex-wrap: wrap;
    }

    .controls input {
      padding: 8px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 0.9rem;
      width: 280px;
    }

    .controls select {
      padding: 8px 12px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      font-size: 0.9rem;
      background: #fff;
    }

    .controls label {
      font-size: 0.85rem;
      color: #6b7280;
    }

    #grid-container {
      height: calc(100vh - 120px);
      width: 100%;
    }

    .badge {
      display: inline-block;
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.75rem;
      background: #e0e7ff;
      color: #3730a3;
      margin: 1px;
    }

    .status-active {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 500;
      background: #d1fae5;
      color: #065f46;
    }

    .status-inactive {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.8rem;
      font-weight: 500;
      background: #f3f4f6;
      color: #6b7280;
    }
  </style>
</head>
<body>

<header>
  <h1>Moldova IT Park — Residents Registry</h1>
  <div class="stats">
    <div class="stat"><strong id="stat-total">—</strong> total</div>
    <div class="stat"><strong id="stat-active">—</strong> active</div>
    <div class="stat"><strong id="stat-inactive">—</strong> inactive</div>
  </div>
</header>

<div class="controls">
  <label>Search:</label>
  <input type="text" id="search" placeholder="Company, administrator, email…" />
  <label>Status:</label>
  <select id="status-filter">
    <option value="all">All</option>
    <option value="Active">Active</option>
    <option value="Inactive">Inactive</option>
  </select>
</div>

<div id="grid-container" class="ag-theme-quartz"></div>

<script>
  const columnDefs = [
    { field: "residentNumber", headerName: "#", width: 70, pinned: "left", sort: "asc" },
    {
      field: "companyName", headerName: "Company", width: 260, pinned: "left",
      cellStyle: params => params.data.isResident === "Inactive" ? { color: "#9ca3af" } : {}
    },
    { field: "administrator", headerName: "Administrator", width: 180 },
    { field: "legalHeadquarters", headerName: "Headquarters", width: 300 },
    {
      field: "isResident", headerName: "Status", width: 110,
      cellRenderer: params => {
        const cls = params.value === "Active" ? "status-active" : "status-inactive";
        return `<span class="${cls}">${params.value}</span>`;
      }
    },
    { field: "joinDate", headerName: "Joined", width: 110 },
    { field: "requestedRegistrationPeriod", headerName: "Reg. Until", width: 110 },
    { field: "recallDate", headerName: "Recall Date", width: 115 },
    {
      field: "eligibleActivities", headerName: "Activities", width: 220,
      cellRenderer: params => {
        if (!params.value) return "";
        return params.value.map(a => `<span class="badge">${a}</span>`).join("");
      }
    },
    {
      field: "phone", headerName: "Phone", width: 150,
      cellRenderer: params => params.value ? `<a href="tel:${params.value}">${params.value}</a>` : ""
    },
    {
      field: "email", headerName: "Email", width: 220,
      cellRenderer: params => params.value ? `<a href="mailto:${params.value}">${params.value}</a>` : ""
    },
  ];

  let allData = [];

  function filterData() {
    const text = document.getElementById("search").value.toLowerCase();
    const status = document.getElementById("status-filter").value;
    return allData.filter(row => {
      const matchStatus = status === "all" || row.isResident === status;
      const matchText = !text || [row.companyName, row.administrator, row.email, row.phone]
        .some(v => v && v.toLowerCase().includes(text));
      return matchStatus && matchText;
    });
  }

  const gridOptions = {
    columnDefs,
    rowData: [],
    defaultColDef: {
      resizable: true,
      sortable: true,
      filter: false,
    },
    rowHeight: 40,
    suppressRowVirtualisation: false,
    animateRows: false,
    getRowId: params => params.data.id,
  };

  document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("grid-container");
    agGrid.createGrid(container, gridOptions);

    const resp = await fetch("./data.json");
    allData = await resp.json();

    const active = allData.filter(r => r.isResident === "Active").length;
    document.getElementById("stat-total").textContent = allData.length.toLocaleString();
    document.getElementById("stat-active").textContent = active.toLocaleString();
    document.getElementById("stat-inactive").textContent = (allData.length - active).toLocaleString();

    gridOptions.api.setGridOption("rowData", filterData());

    function onFilter() {
      gridOptions.api.setGridOption("rowData", filterData());
    }

    document.getElementById("search").addEventListener("input", onFilter);
    document.getElementById("status-filter").addEventListener("change", onFilter);
  });
</script>
</body>
</html>
```

**Step 2: Test locally**

```bash
python -m http.server 8080
```

Open http://localhost:8080 in a browser. Verify:
- Table loads with 3578 rows
- Scrolling is smooth (AG Grid virtualizes rows)
- Search filters work
- Status filter works
- Stats header shows correct counts

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add AG Grid web page with search and filters"
```

---

### Task 4: Create GitHub private repo

**Step 1: Authenticate and create repo**

```bash
gh auth status  # verify logged in as egor-n
gh repo create egor-n/itpark-scraper --private --description "Moldova IT Park residents registry scraper and viewer"
```

Expected: repo URL printed, e.g. `https://github.com/egor-n/itpark-scraper`

**Step 2: Initialize git and push**

```bash
git init
git add .
git commit -m "feat: initial commit — scraper, web page, data"
git remote add origin https://github.com/egor-n/itpark-scraper.git
git branch -M main
git push -u origin main
```

Expected: all files pushed to GitHub.

**Step 3: Verify**

```bash
gh repo view egor-n/itpark-scraper
```

Expected: repo details shown with correct description and private visibility.

---

### Task 5: Set up Cloudflare Pages

The Cloudflare Pages project will be named `mitp` so the default URL is `mitp.pages.dev`. We deploy directly with wrangler (no CI needed — we'll push manually after each scraper run).

**Step 1: Check wrangler auth**

```bash
wrangler whoami
```

Expected: shows authenticated account.

**Step 2: Create Pages project**

```bash
wrangler pages project create mitp --production-branch main
```

Expected: project created, URL `https://mitp.pages.dev` assigned.

**Step 3: Deploy**

```bash
wrangler pages deploy . --project-name mitp --branch main
```

Note: the `.` deploys all files in the current directory. Expected output includes deployment URL.

**Step 4: Verify**

Open https://mitp.pages.dev in a browser. Verify the page loads and data is shown.

**Step 5: Add deploy script to README**

Update `README.md` to include:

```markdown
## Deploying

After scraping new data:

```bash
python scraper.py
git add data.jsonl data.json state.json
git commit -m "data: update scraped data"
git push
wrangler pages deploy . --project-name mitp --branch main
```
```

**Step 6: Final commit**

```bash
git add README.md
git commit -m "docs: add deploy instructions"
git push
```

---

## Summary

| File | Purpose |
|------|---------|
| `scraper.py` | Resumable scraper |
| `requirements.txt` | Python deps |
| `data.jsonl` | Raw records (append-only) |
| `data.json` | Array for web page |
| `state.json` | Scraper resume state |
| `index.html` | AG Grid web page |
| `.gitignore` | Excludes virtualenv/pycache |
| `README.md` | Usage + deploy docs |
