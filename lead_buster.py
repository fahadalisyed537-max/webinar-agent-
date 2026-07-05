"""
Lead Buster - Google Maps Lead Scraper
=========================
Scrapes business listings from Google Maps search results.

WHAT THIS DOES:
- Opens Google Maps, runs a search query (e.g. "real estate agency in Dubai")
- Scrolls the results panel to load more listings
- Clicks into each listing to extract: name, address, phone, website, rating, review count
- Saves everything to a CSV

WHAT THIS DOES NOT DO:
- Does not get emails (Maps doesn't show them — that's a separate enrichment step)
- Does not bypass CAPTCHAs. If Google shows a CAPTCHA, the run will fail/stall.
  This happens if you scrape too fast or too much from one IP. Mitigations are
  built in (delays, headless=False option, limited scroll) but there's no
  guaranteed workaround — that's the real tradeoff of free scraping vs paid APIs.
- Does not run in parallel / multi-threaded. Running multiple instances at once
  from the same IP will get you blocked faster, not get more data faster.

USAGE:
    python lead_buster.py "real estate agency in Dubai" --limit 50 --output dubai_real_estate.csv
"""

import argparse
import csv
import random
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def human_delay(min_s=1.0, max_s=2.5):
    """Random delay to look less like a bot hammering requests."""
    time.sleep(random.uniform(min_s, max_s))


def scrape_google_maps(query: str, limit: int = 50, headless: bool = True) -> list[dict]:
    results = []
    seen_names = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()

        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        print(f"[INFO] Opening: {search_url}")
        page.goto(search_url, timeout=60000)

        # Wait for the results feed to load
        try:
            page.wait_for_selector('div[role="feed"]', timeout=15000)
        except PlaywrightTimeoutError:
            print("[ERROR] Results feed never loaded. Google may have served a "
                  "CAPTCHA or changed their layout. Try headless=False to see what happened.")
            browser.close()
            return results

        feed = page.locator('div[role="feed"]')

        # Scroll the feed to load more results until we hit the limit or stop getting new ones
        stagnant_rounds = 0
        max_stagnant_rounds = 4

        while len(results) < limit and stagnant_rounds < max_stagnant_rounds:
            cards = feed.locator('div[role="article"]')
            count = cards.count()

            for i in range(count):
                if len(results) >= limit:
                    break
                card = cards.nth(i)
                try:
                    name = card.get_attribute("aria-label")
                except Exception:
                    name = None

                if not name or name in seen_names:
                    continue
                seen_names.add(name)

                try:
                    card.click()
                    human_delay(1.5, 3.0)
                    detail = extract_detail_panel(page)
                    detail["name"] = name
                    detail["search_query"] = query
                    results.append(detail)
                    print(f"  [{len(results)}/{limit}] {name} -> {detail.get('phone', 'N/A')}")
                except Exception as e:
                    print(f"  [WARN] Skipped a listing due to error: {e}")
                    continue

            prev_len = len(results)
            feed.evaluate("el => el.scrollBy(0, 1000)")
            human_delay(1.5, 2.5)

            if len(results) == prev_len:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0

        browser.close()

    return results


def extract_detail_panel(page) -> dict:
    """Pulls fields from the right-hand detail panel after clicking a listing."""
    detail = {"address": "", "phone": "", "website": "", "rating": "", "review_count": ""}

    # Rating + review count
    try:
        rating_el = page.locator('div[role="main"] span[aria-hidden="true"]').first
        detail["rating"] = rating_el.inner_text(timeout=3000)
    except Exception:
        pass

    try:
        review_el = page.locator('button[aria-label*="reviews"]').first
        review_text = review_el.get_attribute("aria-label", timeout=3000) or ""
        digits = "".join(c for c in review_text if c.isdigit())
        detail["review_count"] = digits
    except Exception:
        pass

    # Address, phone, website live in buttons with data-item-id attributes
    try:
        addr_el = page.locator('button[data-item-id="address"]').first
        detail["address"] = addr_el.get_attribute("aria-label", timeout=3000) or ""
        detail["address"] = detail["address"].replace("Address: ", "").strip()
    except Exception:
        pass

    try:
        phone_el = page.locator('button[data-item-id^="phone:tel:"]').first
        label = phone_el.get_attribute("aria-label", timeout=3000) or ""
        detail["phone"] = label.replace("Phone: ", "").strip()
    except Exception:
        pass

    try:
        website_el = page.locator('a[data-item-id="authority"]').first
        detail["website"] = website_el.get_attribute("href", timeout=3000) or ""
    except Exception:
        pass

    return detail


def save_to_csv(results: list[dict], output_path: str):
    if not results:
        print("[WARN] No results to save.")
        return

    fieldnames = ["name", "address", "phone", "website", "rating", "review_count", "search_query"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"[DONE] Saved {len(results)} leads to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape business leads from Google Maps")
    parser.add_argument("query", help='Search query, e.g. "real estate agency in Dubai"')
    parser.add_argument("--limit", type=int, default=50, help="Max number of listings to scrape")
    parser.add_argument("--output", default="leads.csv", help="Output CSV filename")
    parser.add_argument("--show-browser", action="store_true",
                         help="Run with visible browser window (useful for debugging CAPTCHAs)")
    args = parser.parse_args()

    print(f"[INFO] Starting scrape for: '{args.query}' (limit={args.limit})")
    results = scrape_google_maps(args.query, limit=args.limit, headless=not args.show_browser)
    save_to_csv(results, args.output)
