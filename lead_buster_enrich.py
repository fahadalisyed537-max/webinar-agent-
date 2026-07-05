"""
Lead Buster - Email Enrichment Add-on
=======================================
Takes a CSV produced by lead_buster.py (must have a 'website' column) and
visits each website to scrape any visible email addresses.

WHAT THIS DOES:
- Reads your leads CSV
- For each row with a website, fetches the homepage + common contact-page paths
  (/contact, /contact-us, /about, etc.)
- Extracts any email addresses found in the page text or mailto: links
- Writes a new CSV with an added 'email' column (and 'email_source_page')

REALISTIC EXPECTATIONS - READ THIS:
- This is NOT as reliable as a paid tool like Hunter.io. Hunter maintains a
  database; this script scrapes live, in real time, with no fallback database.
- Expect roughly 30-50% of leads to yield a usable email. The rest will have:
  - No email at all (contact form only, no visible address)
  - A generic inbox (info@, contact@, hello@) instead of a named person
  - A site that blocks scrapers / times out
- Generic inboxes (info@, contact@) ARE still usable for cold outreach, just
  lower-touch than a named contact.
- This script respects a per-request delay to avoid hammering sites. Don't
  remove the delays - that's not laziness, it's what keeps you from getting
  IP-blocked by individual sites at volume.

USAGE:
    python lead_buster_enrich.py test.csv --output test_enriched.csv
"""

import argparse
import csv
import random
import re
import time

import requests
from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Common junk patterns to filter out (image filenames, tracking pixels, etc.
# sometimes match the email regex by accident)
JUNK_PATTERNS = [
    re.compile(r"\.(png|jpg|jpeg|gif|svg|webp)$", re.IGNORECASE),
    re.compile(r"^(example|test|your|email)@", re.IGNORECASE),
    re.compile(r"sentry\.io|wixpress\.com|godaddy\.com|cloudflare", re.IGNORECASE),
]

CONTACT_PATHS = ["", "/contact", "/contact-us", "/about", "/about-us"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def is_junk_email(email: str) -> bool:
    return any(p.search(email) for p in JUNK_PATTERNS)


def extract_emails_from_html(html: str) -> set[str]:
    found = set()

    # mailto: links first - these are the most reliable signal
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            addr = href[7:].split("?")[0].strip()
            if addr and not is_junk_email(addr):
                found.add(addr)

    # Fallback: regex over visible text
    text = soup.get_text(" ")
    for match in EMAIL_REGEX.findall(text):
        if not is_junk_email(match):
            found.add(match)

    return found


def enrich_one_website(base_url: str, timeout: int = 10) -> tuple[str, str]:
    """Returns (best_email, source_page) or ('', '') if nothing found."""
    if not base_url:
        return "", ""

    base_url = base_url.rstrip("/")
    if not base_url.startswith("http"):
        base_url = "https://" + base_url

    for path in CONTACT_PATHS:
        url = base_url + path
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code != 200:
                continue
            emails = extract_emails_from_html(resp.text)
            if emails:
                # Prefer a non-generic email if one exists, else take generic
                generic_prefixes = ("info@", "contact@", "hello@", "admin@", "office@")
                named = [e for e in emails if not e.lower().startswith(generic_prefixes)]
                best = sorted(named)[0] if named else sorted(emails)[0]
                return best, url
        except requests.RequestException:
            continue
        finally:
            time.sleep(random.uniform(0.8, 1.8))

    return "", ""


def enrich_csv(input_path: str, output_path: str):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    if "website" not in fieldnames:
        print("[ERROR] Input CSV has no 'website' column. Can't enrich without it.")
        return

    if "email" not in fieldnames:
        fieldnames = fieldnames + ["email", "email_source_page"]

    total = len(rows)
    hits = 0

    for i, row in enumerate(rows, start=1):
        website = row.get("website", "").strip()
        name = row.get("name", "unknown")

        if not website:
            row["email"] = ""
            row["email_source_page"] = ""
            print(f"  [{i}/{total}] {name} -> no website, skipped")
            continue

        email, source = enrich_one_website(website)
        row["email"] = email
        row["email_source_page"] = source

        if email:
            hits += 1
            print(f"  [{i}/{total}] {name} -> {email}")
        else:
            print(f"  [{i}/{total}] {name} -> no email found")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    rate = (hits / total * 100) if total else 0
    print(f"\n[DONE] Enriched {total} leads. Found emails for {hits} ({rate:.0f}%).")
    print(f"[DONE] Saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich Lead Buster CSV with emails scraped from websites")
    parser.add_argument("input_csv", help="CSV file produced by lead_buster.py")
    parser.add_argument("--output", default=None, help="Output CSV filename (default: <input>_enriched.csv)")
    args = parser.parse_args()

    output = args.output or args.input_csv.replace(".csv", "_enriched.csv")
    print(f"[INFO] Enriching {args.input_csv} -> {output}")
    enrich_csv(args.input_csv, output)
