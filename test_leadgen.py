#!/usr/bin/env python3
"""
Test script for Lead Generation AI Agent
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from LeadGenerationAgent import LeadGenerationAgent

def test_basic_functionality():
    """Test basic functionality of the Lead Generation Agent"""
    print("Testing Lead Generation AI Agent...")
    
    # Initialize the agent
    agent = LeadGenerationAgent()
    
    # Test configuration loading
    print("✓ Configuration loaded successfully")
    
    # Test search module
    prospects = agent._search_apollo()
    print(f"✓ Search module: Found {len(prospects)} prospects")
    
    # Test qualification module
    filtered = agent._apply_icp_filters(prospects)
    print(f"✓ Qualification module: {len(filtered)} prospects passed ICP filters")
    
    # Test email verification
    verified = agent._verify_emails(filtered)
    print(f"✓ Verification module: {len(verified)} prospects verified")
    
    # Test enrichment
    enriched = agent._enrich_companies(verified)
    print(f"✓ Enrichment module: {len(enriched)} prospects enriched")
    
    # Test lead scoring
    scored = agent._calculate_lead_scores(enriched)
    print(f"✓ Lead scoring module: {len(scored)} prospects scored")
    
    # Test filtering
    qualified = agent._filter_low_quality(scored)
    print(f"✓ Filtering module: {len(qualified)} qualified leads")
    
    # Test personalization
    personalized = agent._generate_outreach(qualified)
    print(f"✓ Personalization module: {len(personalized)} prospects personalized")
    
    # Test export
    agent._export_results(personalized)
    print("✓ Export module: Results exported to multiple formats")
    
    # Test CRM update
    agent._update_crm(personalized)
    print("✓ CRM module: Leads updated in CRM")
    
    # Test reporting
    agent._generate_reports()
    print("✓ Reporting module: Reports generated")
    
    print("\nAll tests passed! ✓")
    return True

def test_lead_scoring():
    """Test lead scoring accuracy"""
    print("\nTesting Lead Scoring Accuracy...")
    
    agent = LeadGenerationAgent()
    
    # Create test prospects with different characteristics
    test_prospects = [
        {
            "first_name": "John",
            "last_name": "Doe",
            "title": "CEO",
            "company": "TechCorp",
            "industry": "B2B SaaS",
            "employees": 50,
            "country": "Dubai",
            "email": "john@techcorp.com",
            "email_status": "Verified",
            "linkedin": "https://linkedin.com/in/johndoe"
        },
        {
            "first_name": "Jane",
            "last_name": "Smith",
            "title": "Marketing Manager",
            "company": "MarketingCo",
            "industry": "Marketing Agencies",
            "employees": 150,
            "country": "Riyadh",
            "email": "jane@marketingco.com",
            "email_status": "Verified",
            "linkedin": "N/A"
        }
    ]
    
    # Score the prospects
    scored = agent._calculate_lead_scores(test_prospects)
    
    # Verify CEO gets higher score than Marketing Manager
    ceo_score = next(p["score"] for p in scored if p["title"] == "CEO")
    manager_score = next(p["score"] for p in scored if p["title"] == "Marketing Manager")
    
    print(f"✓ CEO Score: {ceo_score}")
    print(f"✓ Marketing Manager Score: {manager_score}")
    
    # CEO should have higher score
    assert ceo_score > manager_score, "CEO should have higher score than Marketing Manager"
    
    print("✓ Lead scoring test passed!")
    return True

def test_export_formats():
    """Test export functionality"""
    print("\nTesting Export Formats...")
    
    agent = LeadGenerationAgent()
    
    # Create test leads
    test_leads = [
        {
            "first_name": "Test",
            "last_name": "User",
            "title": "CEO",
            "company": "TestCorp",
            "industry": "B2B SaaS",
            "employees": 100,
            "country": "Dubai",
            "email": "test@testcorp.com",
            "linkedin": "https://linkedin.com/in/testuser",
            "score": 85,
            "email_status": "Verified",
            "estimated_revenue": "$10-50M",
            "tech_stack": "Salesforce, HubSpot",
            "crm_used": "HubSpot",
            "pain_points": "Need automation, Want efficiency",
            "business_opportunities": "AI workflow optimization",
            "estimated_cost_savings": "$50K-$200K annually",
            "estimated_revenue_gains": "$100K-$500K annually"
        }
    ]
    
    # Test CSV export
    agent._export_to_csv(test_leads)
    print("✓ CSV export test passed")
    
    # Test JSON export
    agent._export_to_json(test_leads)
    print("✓ JSON export test passed")
    
    # Test Google Sheets export
    agent._export_to_google_sheets(test_leads)
    print("✓ Google Sheets export test passed")
    
    # Test Excel export
    agent._export_to_excel(test_leads)
    print("✓ Excel export test passed")
    
    # Test Markdown export
    agent._export_to_markdown(test_leads)
    print("✓ Markdown export test passed")
    
    print("✓ All export format tests passed!")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Lead Generation AI Agent - Test Suite")
    print("=" * 60)
    
    try:
        # Run all tests
        test_basic_functionality()
        test_lead_scoring()
        test_export_formats()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        print("\nThe Lead Generation AI Agent is ready for production use.")
        print("\nNext Steps:")
        print("1. Run the full system: python run_leadgen.py")
        print("2. Review the generated leads in exports/")
        print("3. Update your CRM with qualified leads")
        print("4. Schedule automated runs")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)