#!/usr/bin/env python3
"""
Lead Generation AI Agent - Main Entry Point
Autonomous AI lead generation system for AI Automation Agency
"""

import sys
import os
import importlib.util

# Import the LeadGenerationAgent class directly from __init__.py
spec = importlib.util.spec_from_file_location("LeadGenerationAgent", "src/__init__.py")
LeadGenerationAgent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LeadGenerationAgent_module)
LeadGenerationAgent = LeadGenerationAgent_module.LeadGenerationAgent

def main():
    """Main function to run the lead generation agent"""
    print("=" * 60)
    print("Lead Generation AI Agent - Autonomous System")
    print("=" * 60)
    print("\nSystem Purpose:")
    print("- Target: GCC and Western markets")
    print("- Focus: AI Automation solutions")
    print("- Goal: Generate qualified leads for AI Automation Agency")
    print("\n" + "=" * 60)
    
    # Initialize the agent
    agent = LeadGenerationAgent()
    
    # Run the autonomous workflow
    leads = agent.run_autonomous_workflow()
    
    # Display results
    print("\n" + "=" * 60)
    print("LEAD GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nTotal Leads Generated: {len(leads)}")
    print(f"Qualified Leads: {agent.get_metrics()['qualified_leads']}")
    print(f"Rejected Leads: {agent.get_metrics()['rejected_leads']}")
    print(f"Average Lead Score: {agent.get_metrics()['average_score']:.2f}")
    print(f"Email Verification Rate: {agent.get_metrics()['email_verification_rate']:.2%}")
    
    # Display top leads
    print("\n" + "=" * 60)
    print("TOP 10 LEADS (Sorted by Score)")
    print("=" * 60)
    
    sorted_leads = sorted(leads, key=lambda x: x['score'], reverse=True)[:10]
    for i, lead in enumerate(sorted_leads, 1):
        print(f"\n{i}. {lead['first_name']} {lead['last_name']} - {lead['title']}")
        print(f"   Company: {lead['company']}")
        print(f"   Industry: {lead['industry']}")
        print(f"   Country: {lead['country']}")
        print(f"   Score: {lead['score']}/100")
        print(f"   Email: {lead['email']}")
        print(f"   Pain Points: {lead.get('pain_points', 'N/A')}")
        print(f"   Business Opportunities: {lead.get('business_opportunities', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("SYSTEM SUCCESS")
    print("=" * 60)
    print("\nThe Lead Generation AI Agent has successfully completed its autonomous workflow.")
    print("All qualified leads have been exported, CRM updated, and reports generated.")
    print("\nNext Steps:")
    print("1. Review the generated leads in the exports folder")
    print("2. Update your CRM with the qualified leads")
    print("3. Review the daily/weekly/monthly reports")
    print("4. Schedule the next automated run")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())