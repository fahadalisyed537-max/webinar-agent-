"""
Lead Generation AI Agent - Apollo.io Prospect Search
Finds 80 qualified prospects across SaaS, Marketing Agency, Real Estate
in GCC + UK + USA. Scores, qualifies, and generates outreach.
"""

import requests
import json
import csv
import os
import time
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

APOLLO_API_KEY = "BBQ80MVVMEUrApNpFmFNpw"
APOLLO_BASE_URL = "https://api.apollo.io/v1"

# ICP Definition
TARGET_TITLES = [
    "Founder", "CEO", "Chief Executive Officer",
    "Co-Founder", "Managing Director",
    "VP Sales", "Vice President of Sales", "Head of Sales",
    "Director of Sales", "Director of Growth",
    "COO", "Chief Operating Officer",
    "Director of Operations", "CMO", "Chief Marketing Officer"
]

SEARCH_SEGMENTS = [
    # Segment: Industry keyword, Location tags
    {"industry": "SaaS", "keywords": ["SaaS", "Software as a Service", "B2B Software"],
     "locations": ["United States", "United Kingdom"], "label": "SaaS_Western"},
    {"industry": "SaaS", "keywords": ["SaaS", "Software as a Service", "B2B Software"],
     "locations": ["United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait"],
     "label": "SaaS_GCC"},
    {"industry": "Marketing Agency", "keywords": ["Marketing Agency", "Digital Marketing", "Advertising Agency"],
     "locations": ["United States", "United Kingdom"], "label": "MarketingAgency_Western"},
    {"industry": "Marketing Agency", "keywords": ["Marketing Agency", "Digital Marketing", "Advertising Agency"],
     "locations": ["United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait"],
     "label": "MarketingAgency_GCC"},
    {"industry": "Real Estate", "keywords": ["Real Estate", "Real Estate Development", "Property Development"],
     "locations": ["United States", "United Kingdom"], "label": "RealEstate_Western"},
    {"industry": "Real Estate", "keywords": ["Real Estate", "Real Estate Development", "Property Development"],
     "locations": ["United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait"],
     "label": "RealEstate_GCC"},
]

# Company Size Filter
MIN_EMPLOYEES = 11
MAX_EMPLOYEES = 200

# Lead Scoring Weights
TITLE_SCORES = {
    "founder": 30, "ceo": 30, "chief executive officer": 30,
    "co-founder": 30, "managing director": 28,
    "vp sales": 25, "vice president of sales": 25, "head of sales": 25,
    "director of sales": 22, "director of growth": 22,
    "coo": 22, "chief operating officer": 22,
    "director of operations": 20, "cmo": 20, "chief marketing officer": 20
}

TIER1_INDUSTRIES = ["real estate", "saas", "software", "b2b saas", "real estate development",
                     "mortgage", "property development"]
TIER2_INDUSTRIES = ["marketing", "advertising", "financial services", "wealth management",
                     "healthcare", "logistics", "digital marketing", "agency"]

# Generic emails to reject
REJECT_PREFIXES = ["info@", "support@", "contact@", "admin@", "sales@", "hello@",
                    "noreply@", "no-reply@", "team@", "office@"]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# APOLLO.IO API FUNCTIONS
# ============================================================

def search_apollo_people(keywords, locations, page=1, per_page=25):
    """Search Apollo.io for people matching criteria."""
    url = f"{APOLLO_BASE_URL}/mixed_people/search"

    payload = {
        "api_key": APOLLO_API_KEY,
        "q_organization_keyword_tags": keywords,
        "person_titles": TARGET_TITLES,
        "person_locations": locations,
        "organization_num_employees_ranges": ["11,50", "51,100", "101,200"],
        "page": page,
        "per_page": per_page,
        "contact_email_status": ["verified"],
    }

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"  [HTTP ERROR] {e.response.status_code}: {e.response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [REQUEST ERROR] {e}")
        return None


def enrich_person(person_id):
    """Enrich a person record from Apollo."""
    url = f"{APOLLO_BASE_URL}/people/match"
    payload = {
        "api_key": APOLLO_API_KEY,
        "id": person_id,
        "reveal_personal_emails": False,
        "reveal_phone_number": False,
    }
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# ============================================================
# LEAD PROCESSING
# ============================================================

def is_generic_email(email):
    """Check if email is generic/role-based."""
    if not email:
        return True
    email_lower = email.lower()
    return any(email_lower.startswith(prefix) for prefix in REJECT_PREFIXES)


def calculate_lead_score(person, org, industry_segment):
    """Score lead 0-100 per spec."""
    score = 0

    # Decision Maker Weight (max 30)
    title = (person.get("title") or "").lower()
    title_score = 0
    for key, val in TITLE_SCORES.items():
        if key in title:
            title_score = max(title_score, val)
    score += title_score

    # Industry Fit (max 25)
    org_industry = (org.get("industry") or "").lower()
    segment_industry = industry_segment.lower()
    combined = f"{org_industry} {segment_industry}"

    if any(t in combined for t in TIER1_INDUSTRIES):
        score += 25
    elif any(t in combined for t in TIER2_INDUSTRIES):
        score += 15

    # Company Size (max 20)
    emp_count = org.get("estimated_num_employees") or org.get("employee_count") or 0
    if isinstance(emp_count, str):
        try:
            emp_count = int(emp_count.replace(",", "").split("-")[0])
        except ValueError:
            emp_count = 0

    if 51 <= emp_count <= 100:
        score += 20
    elif 101 <= emp_count <= 200:
        score += 18
    elif 11 <= emp_count <= 50:
        score += 15

    # Contact Quality (max 15) - only verified emails pass our filter
    email = person.get("email")
    if email and not is_generic_email(email):
        email_status = person.get("email_status") or ""
        if email_status.lower() == "verified" or email:
            score += 15

    # LinkedIn Present (max 10)
    linkedin = person.get("linkedin_url") or ""
    if linkedin:
        score += 10

    return score


def qualify_lead(person, org):
    """Apply qualification rules. Return (qualified: bool, reason: str)."""
    emp = org.get("estimated_num_employees") or 0
    if isinstance(emp, str):
        try:
            emp = int(emp.replace(",", "").split("-")[0])
        except ValueError:
            emp = 0

    if emp < 11:
        return False, f"Too small ({emp} employees)"
    if emp > 200:
        return False, f"Too large ({emp} employees)"

    website = org.get("website_url") or org.get("primary_domain") or ""
    if not website:
        return False, "No website"

    email = person.get("email") or ""
    if not email:
        return False, "No email"
    if is_generic_email(email):
        return False, f"Generic email ({email})"

    return True, "Qualified"


def generate_outreach(person, org, industry, score):
    """Generate personalized cold email."""
    first = person.get("first_name") or "there"
    title = person.get("title") or "leader"
    company = org.get("name") or "your company"
    city = person.get("city") or org.get("city") or ""
    emp_count = org.get("estimated_num_employees") or "growing"

    # Industry-specific pain points
    pain_points = {
        "SaaS": "scaling outbound without burning through SDR budgets",
        "Marketing Agency": "handling lead gen for clients while managing your own pipeline",
        "Real Estate": "following up with every property inquiry before competitors do",
    }
    pain = pain_points.get(industry, "automating repetitive sales workflows")

    # Industry-specific value props
    value_props = {
        "SaaS": "AI agents that book 15-30 qualified demos/month on autopilot",
        "Marketing Agency": "white-label AI lead gen systems your clients will pay premium for",
        "Real Estate": "AI calling agents that qualify and book property viewings 24/7",
    }
    value = value_props.get(industry, "AI automation systems that cut costs 40% while scaling output")

    email_body = f"""Hi {first},

Noticed {company} is {f'a {emp_count}-person {industry.lower()} team' if isinstance(emp_count, int) else f'growing in {industry.lower()}'}{f' in {city}' if city else ''}. Impressive.

Most {title}s I talk to in {industry.lower()} struggle with {pain}.

We build {value} — no manual work, no extra hires.

Would a 15-min call this week make sense to see if this fits {company}?

Best,
[Your Name]
AI Automation Agency"""

    return email_body.strip()


def generate_linkedin_message(person, org, industry):
    """Generate short LinkedIn connection message."""
    first = person.get("first_name") or "there"
    company = org.get("name") or "your company"

    msg = f"""Hi {first} — saw your work at {company}. We help {industry.lower()} companies automate lead gen and appointment setting with AI agents. Would love to connect and share a quick case study if relevant."""

    return msg.strip()


# ============================================================
# MAIN PIPELINE
# ============================================================

def run_lead_generation():
    """Execute full lead gen pipeline."""
    print("=" * 70)
    print("  LEAD GENERATION AI AGENT — APOLLO.IO PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    all_leads = []
    rejected = []
    seen_emails = set()
    target_count = 80
    leads_per_segment = 15  # ~15 per segment, 6 segments = 90 raw, filter to 80

    for seg in SEARCH_SEGMENTS:
        print(f"\n{'─' * 60}")
        print(f"  Segment: {seg['label']}")
        print(f"  Industry: {seg['industry']}")
        print(f"  Locations: {', '.join(seg['locations'])}")
        print(f"{'─' * 60}")

        page = 1
        segment_leads = 0
        max_pages = 3

        while segment_leads < leads_per_segment and page <= max_pages:
            print(f"  Searching page {page}...")
            data = search_apollo_people(
                keywords=seg["keywords"],
                locations=seg["locations"],
                page=page,
                per_page=25
            )

            if not data:
                print("  No data returned. Skipping.")
                break

            people = data.get("people") or []
            if not people:
                print("  No more results.")
                break

            print(f"  Found {len(people)} prospects. Processing...")

            for person in people:
                if len(all_leads) >= target_count:
                    break

                email = person.get("email") or ""
                if not email or email in seen_emails:
                    continue
                seen_emails.add(email)

                # Get org data
                org = person.get("organization") or {}

                # Qualify
                qualified, reason = qualify_lead(person, org)
                if not qualified:
                    rejected.append({
                        "name": f"{person.get('first_name', '')} {person.get('last_name', '')}",
                        "email": email,
                        "reason": reason
                    })
                    continue

                # Score
                score = calculate_lead_score(person, org, seg["industry"])

                # Skip low scores
                if score < 40:
                    rejected.append({
                        "name": f"{person.get('first_name', '')} {person.get('last_name', '')}",
                        "email": email,
                        "reason": f"Low score ({score})"
                    })
                    continue

                # Generate outreach
                cold_email = generate_outreach(person, org, seg["industry"], score)
                linkedin_msg = generate_linkedin_message(person, org, seg["industry"])

                lead = {
                    "score": score,
                    "first_name": person.get("first_name", ""),
                    "last_name": person.get("last_name", ""),
                    "title": person.get("title", ""),
                    "email": email,
                    "email_status": person.get("email_status", ""),
                    "phone": person.get("phone_number") or (
                        person.get("phone_numbers", [{}])[0].get("sanitized_number", "")
                        if person.get("phone_numbers") else ""
                    ),
                    "linkedin_url": person.get("linkedin_url", ""),
                    "company": org.get("name", ""),
                    "company_website": org.get("website_url") or org.get("primary_domain", ""),
                    "company_linkedin": org.get("linkedin_url", ""),
                    "industry": org.get("industry") or seg["industry"],
                    "employee_count": org.get("estimated_num_employees", ""),
                    "city": person.get("city") or org.get("city", ""),
                    "state": person.get("state") or org.get("state", ""),
                    "country": person.get("country") or org.get("country", ""),
                    "segment": seg["label"],
                    "cold_email": cold_email,
                    "linkedin_message": linkedin_msg,
                }

                all_leads.append(lead)
                segment_leads += 1
                print(f"    ✓ [{score}pts] {lead['first_name']} {lead['last_name']} — "
                      f"{lead['title']} @ {lead['company']} ({lead['country']})")

            if len(all_leads) >= target_count:
                break

            page += 1
            time.sleep(1)  # Rate limit respect

        print(f"  Segment total: {segment_leads} qualified leads")

    # Sort by score descending
    all_leads.sort(key=lambda x: x["score"], reverse=True)

    # ── Export to CSV ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUTPUT_DIR, f"qualified_leads_{timestamp}.csv")

    csv_fields = [
        "score", "first_name", "last_name", "title", "email", "email_status",
        "phone", "linkedin_url", "company", "company_website", "company_linkedin",
        "industry", "employee_count", "city", "state", "country", "segment",
        "cold_email", "linkedin_message"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(all_leads)

    # ── Export rejected leads ──
    rejected_path = os.path.join(OUTPUT_DIR, f"rejected_leads_{timestamp}.csv")
    with open(rejected_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "reason"])
        writer.writeheader()
        writer.writerows(rejected)

    # ── Generate Report ──
    report_path = os.path.join(OUTPUT_DIR, f"lead_report_{timestamp}.md")
    generate_report(all_leads, rejected, report_path, timestamp)

    # ── Print Summary ──
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Total qualified leads:  {len(all_leads)}")
    print(f"  Total rejected:         {len(rejected)}")
    print(f"  Average score:          {sum(l['score'] for l in all_leads) / max(len(all_leads), 1):.1f}")
    print(f"  CSV exported:           {csv_path}")
    print(f"  Rejected CSV:           {rejected_path}")
    print(f"  Report:                 {report_path}")

    if all_leads:
        print(f"\n  TOP 10 LEADS:")
        print(f"  {'Score':<6} {'Name':<25} {'Title':<30} {'Company':<25} {'Country':<15}")
        print(f"  {'─' * 101}")
        for lead in all_leads[:10]:
            name = f"{lead['first_name']} {lead['last_name']}"
            print(f"  {lead['score']:<6} {name:<25} {lead['title'][:29]:<30} "
                  f"{lead['company'][:24]:<25} {lead['country']:<15}")

    print(f"\n{'=' * 70}")
    return all_leads, rejected


def generate_report(leads, rejected, report_path, timestamp):
    """Generate markdown report."""
    total = len(leads)
    avg_score = sum(l["score"] for l in leads) / max(total, 1)

    # Industry breakdown
    industries = {}
    for l in leads:
        ind = l["industry"]
        industries[ind] = industries.get(ind, 0) + 1

    # Country breakdown
    countries = {}
    for l in leads:
        c = l["country"]
        countries[c] = countries.get(c, 0) + 1

    # Title breakdown
    titles = {}
    for l in leads:
        t = l["title"]
        titles[t] = titles.get(t, 0) + 1

    # Segment breakdown
    segments = {}
    for l in leads:
        s = l["segment"]
        segments[s] = segments.get(s, 0) + 1

    report = f"""# Lead Generation Report
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
| Metric | Value |
|--------|-------|
| Total Qualified Leads | {total} |
| Total Rejected | {len(rejected)} |
| Average Lead Score | {avg_score:.1f} / 100 |
| Highest Score | {leads[0]['score'] if leads else 'N/A'} |
| Lowest Score | {leads[-1]['score'] if leads else 'N/A'} |

## By Segment
| Segment | Count |
|---------|-------|
"""
    for seg, count in sorted(segments.items(), key=lambda x: -x[1]):
        report += f"| {seg} | {count} |\n"

    report += """
## By Industry
| Industry | Count |
|----------|-------|
"""
    for ind, count in sorted(industries.items(), key=lambda x: -x[1]):
        report += f"| {ind} | {count} |\n"

    report += """
## By Country
| Country | Count |
|---------|-------|
"""
    for c, count in sorted(countries.items(), key=lambda x: -x[1]):
        report += f"| {c} | {count} |\n"

    report += """
## Top Titles
| Title | Count |
|-------|-------|
"""
    for t, count in sorted(titles.items(), key=lambda x: -x[1])[:10]:
        report += f"| {t} | {count} |\n"

    report += f"""
## Top 20 Leads
| Score | Name | Title | Company | Industry | Country | Email |
|-------|------|-------|---------|----------|---------|-------|
"""
    for l in leads[:20]:
        name = f"{l['first_name']} {l['last_name']}"
        report += (f"| {l['score']} | {name} | {l['title']} | {l['company']} | "
                   f"{l['industry']} | {l['country']} | {l['email']} |\n")

    report += f"""
## Rejection Reasons
| Reason | Count |
|--------|-------|
"""
    reasons = {}
    for r in rejected:
        reason = r["reason"].split("(")[0].strip()
        reasons[reason] = reasons.get(reason, 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        report += f"| {reason} | {count} |\n"

    report += f"""
---
*Files generated:*
- `qualified_leads_{timestamp}.csv`
- `rejected_leads_{timestamp}.csv`
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    run_lead_generation()
