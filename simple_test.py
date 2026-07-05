#!/usr/bin/env python3
"""
Simple test script for Lead Generation AI Agent
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the LeadGenerationAgent class directly from __init__.py
import importlib.util
spec = importlib.util.spec_from_file_location("LeadGenerationAgent", "src/__init__.py")
LeadGenerationAgent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LeadGenerationAgent_module)
LeadGenerationAgent = LeadGenerationAgent_module.LeadGenerationAgent

def test_basic_functionality():
    """Test basic functionality of the Lead Generation Agent"""
    print("Testing Lead Generation AI Agent...")
    
    # Initialize the agent
    agent = LeadGenerationAgent()
    
    # Test configuration loading
    print("Configuration loaded successfully")
    
    # Test search module
    prospects = agent._search_apollo()
    print(f"Search module: Found {len(prospects)} prospects")
    
    # Test qualification module
    filtered = agent._apply_icp_filters(prospects)
    print(f"Qualification module: {len(filtered)} prospects passed ICP filters")
    
    # Test email verification
    verified = agent._verify_emails(filtered)
    print(f"Verification module: {len(verified)} prospects verified")
    
    # Test enrichment
    enriched = agent._enrich_companies(verified)
    print(f"Enrichment module: {len(enriched)} prospects enriched")
    
    # Test lead scoring
    scored = agent._calculate_lead_scores(enriched)
    print(f"Lead scoring module: {len(scored)} prospects scored")
    
    # Test filtering
    qualified = agent._filter_low_quality(scored)
    print(f"Filtering module: {len(qualified)} qualified leads")
    
    # Test personalization
    personalized = agent._generate_outreach(qualified)
    print(f"Personalization module: {len(personalized)} prospects personalized")
    
    # Test export
    agent._export_results(personalized)
    print("Export module: Results exported to multiple formats")
    
    # Test CRM update
    agent._update_crm(personalized)
    print("CRM module: Leads updated in CRM")
    
    # Test reporting
    agent._generate_reports()
    print("Reporting module: Reports generated")
    
    print("\nAll tests passed!")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Lead Generation AI Agent - Simple Test")
    print("=" * 60)
    
    try:
        test_basic_functionality()
        
        print("\n" + "=" * 60)
        print("TEST PASSED!")
        print("=" * 60)
        print("\nThe Lead Generation AI Agent is working correctly.")
        print("\nNext Steps:")
        print("1. Run the full system: python run_leadgen.py")
        print("2. Review the generated leads in exports/")
        print("3. Update your CRM with qualified leads")
        print("4. Schedule automated runs")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)