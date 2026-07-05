"""
Lead Buster - Full Run (Scrape + Enrich in One Command)
==========================================================
Runs the full pipeline: Google Maps scrape -> email enrichment -> final CSV.

Built specifically for your locked scope: AU + UK real estate brokers and
mortgage brokers/lenders. The --query argument is still required so you
control exactly what's searched - this does NOT auto-expand scope on its own.

USAGE (single command, does everything):
    python lead_buster_full.py "real estate agent in Manchester UK" --limit 50

This will:
    1. Scrape Google Maps for that query (up to --limit results)
    2. Save raw results to leads_raw_<timestamp>.csv
    3. Run email enrichment on every lead that has a website
    4. Save final result to leads_final_<timestamp>.csv
    5. Print a summary: how many leads, how many got emails, how many failed

If step 1 fails (CAPTCHA, no results, etc.) the script stops cleanly and
tells you why - it does NOT attempt enrichment on an empty/broken result,
and it does NOT silently produce a fake-looking success.
"""

import argparse
import csv
import sys
import time
from datetime import datetime

from lead_buster import scrape_google_maps, save_to_csv
from lead_buster_enrich import enrich_csv


def run_full_pipeline(query: str, limit: int, headless: bool):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = f"leads_raw_{timestamp}.csv"
    final_path = f"leads_final_{timestamp}.csv"

    print(f"{'='*60}")
    print(f"LEAD BUSTER - FULL RUN")
    print(f"Query: {query}")
    print(f"Limit: {limit}")
    print(f"{'='*60}\n")

    # ---- Step 1: Scrape ----
    print("[STEP 1/2] Scraping Google Maps...\n")
    results = scrape_google_maps(query, limit=limit, headless=headless)

    if not results:
        print("\n[FAILED] No leads scraped. This usually means:")
        print("  - Google served a CAPTCHA (try again later, or run with --show-browser to see)")
        print("  - The search query returned zero results (check spelling/location)")
        print("Stopping here. Enrichment skipped - nothing to enrich.")
        sys.exit(1)

    save_to_csv(results, raw_path)
    print(f"\n[OK] {len(results)} leads scraped -> {raw_path}\n")

    # Brief pause before hammering websites right after hammering Google Maps
    time.sleep(2)

    # ---- Step 2: Enrich ----
    print(f"[STEP 2/2] Enriching with emails (visiting each website)...\n")
    enrich_csv(raw_path, final_path)

    # ---- Final summary ----
    with open(final_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    with_email = sum(1 for r in rows if r.get("email"))
    with_phone = sum(1 for r in rows if r.get("phone"))
    with_website = sum(1 for r in rows if r.get("website"))

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total leads:        {total}")
    print(f"With phone number:  {with_phone} ({with_phone/total*100:.0f}%)" if total else "With phone number: 0")
    print(f"With website:       {with_website} ({with_website/total*100:.0f}%)" if total else "With website: 0")
    print(f"With email found:   {with_email} ({with_email/total*100:.0f}%)" if total else "With email found: 0")
    print(f"\nFinal file: {final_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape Google Maps + enrich with emails, in one command"
    )
    parser.add_argument("query", help='e.g. "real estate agent in Manchester UK"')
    parser.add_argument("--limit", type=int, default=50, help="Max leads to scrape (default 50)")
    parser.add_argument("--show-browser", action="store_true",
                         help="Show the browser window during scraping (for debugging)")
    args = parser.parse_args()

    run_full_pipeline(args.query, limit=args.limit, headless=not args.show_browser)
