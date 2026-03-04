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
    default = {"last_page": -1, "total_elements": 0}
    if STATE_PATH.exists():
        try:
            loaded = json.loads(STATE_PATH.read_text())
            return {**default, **loaded}
        except (json.JSONDecodeError, TypeError):
            print("Warning: state.json is corrupt. Starting fresh.")
    return default


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
        with JSONL_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    JSON_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"Exported {len(records)} records to {JSON_PATH}")


def main():
    state = load_state()

    # Peek at page 0 to get current totals
    print("Checking current total...")
    try:
        first_page = fetch_page(0)
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch page 0: {e}")
        return
    total_elements = first_page["totalElements"]
    total_pages = first_page["totalPages"]
    print(f"API reports {total_elements} total elements across {total_pages} pages")
    new_count = total_elements - state["total_elements"]
    if new_count > 0:
        print(f"{new_count} new companies since last run")

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
            state["total_elements"] = total_elements
            save_state(state)
            print(f"Page 0: {len(first_page['content'])} records")
            start_page = 1

        for page in range(start_page, total_pages):
            time.sleep(DELAY)
            try:
                data = fetch_page(page)
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch page {page}: {e}. Progress saved. Rerun to resume.")
                break
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
