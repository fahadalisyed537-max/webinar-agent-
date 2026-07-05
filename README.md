# Lead Generation AI Agent

Autonomous AI lead generation system for AI Automation Agency

## Overview

The Lead Generation AI Agent is a fully autonomous system designed to find, qualify, and generate leads for AI Automation Agency. The system targets GCC and Western markets, focusing on companies with 11-200 employees in specific industries and job titles.

## System Architecture

### 9 Modular Components

1. **Search Module** - Finds prospects across Apollo.io, LinkedIn, Crunchbase, Google Maps, and company websites
2. **Qualification Module** - Applies ICP filters to reject unqualified leads
3. **Enrichment Module** - Collects detailed company information (tech stack, CRM used, revenue, etc.)
4. **Verification Module** - Ensures email quality and removes invalid contacts
5. **Lead Scoring Module** - Calculates lead scores (0-100) based on decision maker, industry, company size, and contact quality
6. **Personalization Module** - Generates personalized outreach based on prospect analysis
7. **Export Module** - Exports leads to CSV, JSON, Google Sheets, Excel, and Markdown formats
8. **CRM Sync Module** - Updates HubSpot, GoHighLevel, Salesforce, and Pipedrive with qualified leads
9. **Reporting Module** - Generates daily, weekly, and monthly reports

## Target Markets

### GCC Countries
- Dubai
- Abu Dhabi
- Riyadh
- Jeddah
- Doha
- Kuwait City

### Western Markets
- USA
- UK
- Canada
- Australia

## Ideal Customer Profile

### Company Size
- Minimum: 11 employees
- Maximum: 200 employees

### Target Industries

**Priority Tier 1**
- Real Estate
- Real Estate Developers
- Mortgage Brokers
- B2B SaaS

**Priority Tier 2**
- Marketing Agencies
- Advertising Agencies
- Financial Services
- Wealth Management
- Healthcare Clinics
- Logistics

### Target Job Titles

**Priority 1**
- Founder
- CEO
- Managing Director
- Co-Founder

**Priority 2**
- VP Sales
- Head of Sales
- Director of Sales
- Director of Growth
- COO
- Director of Operations
- CMO

## Workflow

### Step 1: Search Apollo
- Retrieve 100 prospects from Apollo.io

### Step 2: Apply ICP Filters
- Filter by industry, location, company size, title

### Step 3: Verify Emails
- Verify email addresses
- Remove invalid emails

### Step 4: Enrich Companies
- Collect detailed company information

### Step 5: Calculate Lead Scores
- Apply scoring algorithm (0-100)

### Step 6: Remove Low-Quality Leads
- Filter based on score thresholds (>= 40)

### Step 7: Generate Outreach
- Create personalized emails/messages

### Step 8: Export Results
- Export to multiple formats

### Step 9: Update CRM
- Sync qualified leads to CRM

### Step 10: Generate Reports
- Create daily/weekly/monthly reports

## Success Criteria

- 90%+ email verification rate
- 85%+ lead score accuracy
- 80%+ personalization rate
- 30+ qualified leads per run
- CRM records automatically updated
- Reports generated without manual intervention

## System Features

### Autonomous Operation
- Runs without human intervention
- Completes full 10-step workflow
- Automatically handles all modules

### Multi-Source Prospecting
- Primary: Apollo.io, LinkedIn, Crunchbase
- Secondary: Google Maps, Company Websites
- Backup: Clearbit, Hunter, Clay, RocketReach

### Lead Scoring
- Decision Maker (30 points): Founder/CEO = 30, Managing Director = 28, VP Sales = 25
- Industry Fit (25 points): Tier 1 = 25, Tier 2 = 15
- Company Size (20 points): 11-50 = 15, 51-100 = 20, 101-200 = 18
- Contact Quality (15 points): Verified Email = 15, LinkedIn Present = 10

### Personalization
- Analyzes website, LinkedIn profile, company description, and news
- Generates pain points, business opportunities, and AI automation opportunities
- Creates personalized emails and LinkedIn messages

### Export Options
- CSV format for data analysis
- JSON format for API integration
- Google Sheets for collaboration
- Excel for reporting
- Markdown for documentation

### CRM Integration
- Supports HubSpot, GoHighLevel, Salesforce, Pipedrive
- Automatically updates lead records
- Maintains outreach history

### Reporting
- Daily reports with metrics and top leads
- Weekly and monthly summaries
- Tracks performance and ROI

## Installation

### Prerequisites
- Python 3.7+
- pip

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the System
```bash
python run_leadgen.py
```

## Requirements

requirements.txt
```
python-dateutil>=2.8.2
pyyaml>=6.0
requests>=2.31.0
pandas>=2.0.3
openpyxl>=3.1.2
```

## Usage

### Basic Usage
```bash
# Run the lead generation system
python run_leadgen.py
```

### Configuration
Edit `config/system.json` to customize:
- Target markets
- Company size range
- Target industries
- Target job titles

### Automation
To run the system automatically:
```bash
# Add to crontab for daily runs
0 9 * * * cd /path/to/LeadGenAgent && python run_leadgen.py
```

## Output

### Exports
All leads are exported to the `exports/` directory:
- `leads_YYYYMMDD_HHMMSS.csv` - CSV format
- `leads_YYYYMMDD_HHMMSS.json` - JSON format
- `leads_google_sheets_YYYYMMDD_HHMMSS.csv` - Google Sheets format
- `leads_excel_YYYYMMDD_HHMMSS.csv` - Excel format
- `leads_markdown_YYYYMMDD_HHMMSS.md` - Markdown format

### Reports
Reports are saved to the `reports/` directory:
- `daily_report_YYYYMMDD.md` - Daily report
- `weekly_report_YYYYMMDD.md` - Weekly report
- `monthly_report_YYYYMMDD.md` - Monthly report

## Support

For support or questions:
1. Check the documentation in the `docs/` directory
2. Review the system logs in the `exports/` directory
3. Contact the development team

## License

This system is provided as open-source software for AI Automation Agency.

## Version

Version: 1.0.0
Created: 2026-06-20
Last Updated: 2026-06-20