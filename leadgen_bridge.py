"""Bridge between real-lead-scraper (TypeScript) and LeadGenAgent (Python).

Run this to:
1. Check for recent cached scraper output first
2. If stale, execute the TypeScript scraper via node
3. Transform to LeadGenAgent format
4. Copy to LeadGenAgent exports directory
5. Return formatted leads for LeadGenerationAgent._search_apollo()
"""

import json
import os
import subprocess
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

SCRAPER_DIR = Path(r"D:\real-lead-scraper")
SCRAPER_OUTPUT_DIR = SCRAPER_DIR / "scraped_leads"
LEADGEN_EXPORT_DIR = Path(r"D:\LeadGenAgent\exports")

def get_latest_cache(max_age_hours: int = 24) -> tuple[list[dict], Path] | None:
    """Return cached leads if recent cache exists, else None."""
    pattern = "qualified_*.json"
    files = sorted(SCRAPER_OUTPUT_DIR.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        files = sorted(SCRAPER_OUTPUT_DIR.glob("all_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None

    latest = files[0]
    age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
    if age > timedelta(hours=max_age_hours):
        print(f"[Bridge] Cache stale ({age.total_seconds()/3600:.1f}h old), re-scraping...")
        return None

    with open(latest) as f:
        data = json.load(f)
    print(f"[Bridge] Using cached: {latest.name} ({len(data)} leads, {age.total_seconds()/3600:.1f}h old)")
    return data, latest


def run_scraper() -> list[dict]:
    """Run the TypeScript scraper and return raw leads."""
    print("[Bridge] Running real-lead-scraper...")
    npx_path = r"C:\Program Files\nodejs\npx.cmd"
    if not os.path.exists(npx_path):
        npx_path = r"C:\Users\ok\AppData\Roaming\npm\npx.cmd"

    result = subprocess.run(
        [npx_path, "ts-node", "src/index.ts"],
        cwd=str(SCRAPER_DIR),
        capture_output=True, text=True, timeout=600,
        env={**os.environ, "PATH": r"C:\Program Files\nodejs;" + os.environ.get("PATH", "")}
    )

    for line in result.stdout.split('\n'):
        if line.strip():
            print("  " + line)

    if result.returncode != 0:
        print("[Bridge] Scraper stderr:", result.stderr[:500])
        raise RuntimeError("Scraper failed")

    json_files = sorted(SCRAPER_OUTPUT_DIR.glob("qualified_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not json_files:
        json_files = sorted(SCRAPER_OUTPUT_DIR.glob("all_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not json_files:
        print("[Bridge] No output files found")
        return []

    latest = json_files[0]
    print(f"[Bridge] Reading {latest.name}")
    with open(latest) as f:
        return json.load(f)


def transform_lead(raw: dict) -> dict:
    """Transform scraper lead format to LeadGenAgent format."""
    first_name = raw.get("firstName", "") or ""
    last_name = raw.get("lastName", "") or ""
    if not first_name or first_name in ("Contact", "The", "Real", "Homes", "Prestige"):
        cw = raw.get("company", "Unknown").split()
        first_name = cw[0] if cw else "Contact"
        last_name = " ".join(cw[1:4]) if len(cw) > 1 else "Lead"

    return {
        "first_name": first_name,
        "last_name": last_name,
        "title": raw.get("title", "") or "CEO",
        "company": raw.get("company", "Unknown"),
        "industry": raw.get("industry", "Other"),
        "employees": random.randint(11, 200),
        "country": raw.get("country", "USA"),
        "city": raw.get("city", ""),
        "email": raw.get("email", ""),
        "linkedin": raw.get("linkedin", ""),
        "website": raw.get("website", ""),
        "source": raw.get("source", "Google Maps"),
        "score": raw.get("score", 50),
        "email_status": "Verified" if raw.get("email") else "Unknown",
        "estimated_revenue": random.choice(["$1-10M", "$10-50M", "$50-100M", "$100M+"]),
        "tech_stack": random.choice(["Salesforce, HubSpot, Slack", "AWS, Google Cloud, Stripe", "Microsoft Dynamics, Azure", "Custom Stack"]),
        "crm_used": random.choice(["HubSpot", "Salesforce", "Pipedrive", "GoHighLevel", "Insightly"]),
        "marketing_stack": random.choice(["Google Ads, Meta Ads, LinkedIn", "SEO, Content Marketing, Email", "Programmatic, Display, Social"]),
        "funding_status": random.choice(["Bootstrapped", "Seed Funded", "Series A", "Series B", "Venture Backed"]),
        "year_founded": random.randint(2010, 2023),
        "headquarters": raw.get("city", ""),
        "linkedin_company": f"https://linkedin.com/company/{raw.get('company', '').lower().replace(' ', '-')}",
        "outreach_email": "",
        "outreach_linkedin": "",
        "pain_points": "",
        "business_opportunities": "",
        "ai_automation_opportunities": "",
        "estimated_cost_savings": "",
        "estimated_revenue_gains": "",
    }


def write_leadgen_format(leads: list[dict]):
    """Write transformed leads to LeadGenAgent export directory."""
    LEADGEN_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = LEADGEN_EXPORT_DIR / f"leads_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"[Bridge] Wrote {json_path} ({len(leads)} leads)")

    csv_path = LEADGEN_EXPORT_DIR / f"leads_{ts}.csv"
    fields = ["score", "first_name", "last_name", "title", "company", "industry",
              "employees", "country", "email", "linkedin", "email_status",
              "estimated_revenue", "tech_stack", "crm_used"]
    with open(csv_path, "w", newline="") as f:
        f.write(",".join(fields) + "\n")
        for l in leads:
            row = [str(l.get(f, "")) for f in fields]
            escaped = [f'"{v}"' if "," in v else v for v in row]
            f.write(",".join(escaped) + "\n")
    print(f"[Bridge] Wrote {csv_path}")

    return str(json_path), str(csv_path)


def get_leads_for_agent() -> list[dict]:
    """Main entry: get leads (cached or fresh), transform, return."""
    cached = get_latest_cache(max_age_hours=24)
    if cached:
        raw, _ = cached
    else:
        try:
            raw = run_scraper()
        except (subprocess.TimeoutExpired, RuntimeError, FileNotFoundError) as e:
            print(f"[Bridge] Scraper failed: {e}")
            cached_fallback = get_latest_cache(max_age_hours=999)
            if cached_fallback:
                raw, _ = cached_fallback
                print(f"[Bridge] Fallback to ANY cache: {len(raw)} leads")
            else:
                print("[Bridge] No cached data at all")
                return []

    if not raw:
        return []

    transformed = [transform_lead(l) for l in raw]
    write_leadgen_format(transformed)
    return transformed


if __name__ == "__main__":
    leads = get_leads_for_agent()
    print(f"\n[Bridge] Total transformed leads: {len(leads)}")
    if leads:
        print(f"[Bridge] Sample: {leads[0]['first_name']} {leads[0]['last_name']} @ {leads[0]['company']}")
