"""Quick test of the bridge subprocess."""
import sys
sys.path.insert(0, r'D:\real-lead-scraper')
from leadgen_bridge import run_scraper
try:
    leads = run_scraper()
    print("Scraper returned " + str(len(leads)) + " leads")
    if leads:
        print("First: " + leads[0].get('company', 'N/A'))
except Exception as e:
    print("Error: " + str(e))
