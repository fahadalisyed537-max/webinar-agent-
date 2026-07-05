"""
Lead Generation AI Agent - Complete Autonomous System

This system generates qualified B2B leads for AI automation companies,
targeting specific markets and industries with high-quality prospects.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

from .modules.search_module import SearchModule
from .modules.qualification_module import QualificationModule
from .modules.enrichment_module import EnrichmentModule
from .modules.verification_module import VerificationModule
from .modules.scoring_module import ScoringModule
from .modules.personalization_module import PersonalizationModule
from .modules.export_module import ExportModule
from .modules.crm_sync_module import CRMSyncModule
from .modules.reporting_module import ReportingModule
from .config.settings import Settings
from .database.connection import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/lead_generation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class LeadGenerationAgent:
    """Main orchestrator for the autonomous lead generation system."""

    def __init__(self, settings_path: Optional[str] = None):
        self.settings = Settings(settings_path) if settings_path else Settings()
        self.db = Database(self.settings.database_url)
        self.modules = self._initialize_modules()
        self.workflow_state = {
            'current_step': 0,
            'total_steps': 10,
            'start_time': datetime.now(),
            'leads_found': 0,
            'leads_qualified': 0,
            'leads_enriched': 0,
            'leads_verified': 0,
            'leads_scored': 0,
            'leads_exported': 0,
            'crm_synced': 0,
            'reports_generated': 0
        }

    def _initialize_modules(self) -> Dict[str, Any]:
        """Initialize all modules with their dependencies."""
        modules = {}
        
        # Initialize modules in dependency order
        modules['search'] = SearchModule(self.settings)
        modules['qualification'] = QualificationModule(self.settings)
        modules['enrichment'] = EnrichmentModule(self.settings, self.db)
        modules['verification'] = VerificationModule(self.settings)
        modules['scoring'] = ScoringModule(self.settings)
        modules['personalization'] = PersonalizationModule(self.settings)
        modules['export'] = ExportModule(self.settings)
        modules['crm_sync'] = CRMSyncModule(self.settings)
        modules['reporting'] = ReportingModule(self.settings)
        
        return modules

    async def execute_workflow(self) -> Dict[str, Any]:
        """Execute the complete 10-step autonomous workflow."""
        logger.info("Starting autonomous lead generation workflow")
        
        workflow_steps = [
            ("Search Apollo for 100 prospects", self._step_1_search),
            ("Apply ICP filters", self._step_2_qualify),
            ("Verify emails", self._step_3_verify),
            ("Enrich companies", self._step_4_enrich),
            ("Calculate lead scores", self._step_5_score),
            ("Remove low-quality leads", self._step_6_filter),
            ("Generate outreach", self._step_7_personalize),
            ("Export results", self._step_8_export),
            ("Update CRM", self._step_9_crm_sync),
            ("Generate reports", self._step_10_report)
        ]
        
        all_leads = []
        
        for step_name, step_func in workflow_steps:
            self.workflow_state['current_step'] += 1
            logger.info(f"Step {self.workflow_state['current_step']}/10: {step_name}")
            
            try:
                result = await step_func()
                if result is not None:
                    if isinstance(result, list):
                        all_leads.extend(result)
                    else:
                        all_leads = result
                
                logger.info(f"✓ Completed: {step_name}")
            except Exception as e:
                logger.error(f"✗ Failed step {step_name}: {str(e)}")
                raise
        
        # Save final results to database
        await self.db.save_leads(all_leads)
        
        self.workflow_state['end_time'] = datetime.now()
        self.workflow_state['total_leads'] = len(all_leads)
        
        logger.info("Workflow completed successfully")
        return {
            'leads': all_leads,
            'workflow_state': self.workflow_state,
            'success': True
        }

    async def _step_1_search(self) -> List[Dict]:
        """Step 1: Search Apollo for 100 prospects."""
        logger.info("Searching Apollo.io for 100 prospects")
        leads = await self.modules['search'].search_apollo(100)
        self.workflow_state['leads_found'] = len(leads)
        return leads

    async def _step_2_qualify(self, leads: List[Dict]) -> List[Dict]:
        """Step 2: Apply ICP filters."""
        logger.info("Applying ICP filters to qualified leads")
        qualified = await self.modules['qualification'].apply_icp_filters(leads)
        self.workflow_state['leads_qualified'] = len(qualified)
        return qualified

    async def _step_3_verify(self, leads: List[Dict]) -> List[Dict]:
        """Step 3: Verify emails."""
        logger.info("Verifying email addresses")
        verified = await self.modules['verification'].verify_emails(leads)
        self.workflow_state['leads_verified'] = len(verified)
        return verified

    async def _step_4_enrich(self, leads: List[Dict]) -> List[Dict]:
        """Step 4: Enrich companies."""
        logger.info("Enriching company data")
        enriched = await self.modules['enrichment'].enrich_companies(leads)
        self.workflow_state['leads_enriched'] = len(enriched)
        return enriched

    async def _step_5_score(self, leads: List[Dict]) -> List[Dict]:
        """Step 5: Calculate lead scores."""
        logger.info("Calculating lead scores (100-point system)")
        scored = await self.modules['scoring'].calculate_scores(leads)
        self.workflow_state['leads_scored'] = len(scored)
        return scored

    async def _step_6_filter(self, leads: List[Dict]) -> List[Dict]:
        """Step 6: Remove low-quality leads."""
        logger.info("Filtering low-quality leads")
        filtered = await self.modules['qualification'].filter_low_quality(leads)
        return filtered

    async def _step_7_personalize(self, leads: List[Dict]) -> List[Dict]:
        """Step 7: Generate outreach."""
        logger.info("Generating personalized outreach")
        personalized = await self.modules['personalization'].generate_outreach(leads)
        return personalized

    async def _step_8_export(self, leads: List[Dict]) -> List[Dict]:
        """Step 8: Export results."""
        logger.info("Exporting leads to multiple formats")
        await self.modules['export'].export_all(leads)
        self.workflow_state['leads_exported'] = len(leads)
        return leads

    async def _step_9_crm_sync(self, leads: List[Dict]) -> List[Dict]:
        """Step 9: Update CRM."""
        logger.info("Syncing leads to CRM systems")
        synced = await self.modules['crm_sync'].sync_to_crm(leads)
        self.workflow_state['crm_synced'] = len(synced)
        return synced

    async def _step_10_report(self, leads: List[Dict]) -> List[Dict]:
        """Step 10: Generate reports."""
        logger.info("Generating comprehensive reports")
        await self.modules['reporting'].generate_all_reports(leads)
        self.workflow_state['reports_generated'] = 1
        return leads

    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        return self.workflow_state

    async def run(self) -> Dict[str, Any]:
        """Run the complete autonomous lead generation system."""
        logger.info("Starting Lead Generation AI Agent")
        
        try:
            result = await self.execute_workflow()
            logger.info("Lead generation completed successfully")
            return result
        except Exception as e:
            logger.error(f"Lead generation failed: {str(e)}")
            raise


if __name__ == "__main__":
    async def main():
        agent = LeadGenerationAgent()
        result = await agent.run()
        
        print("\n" + "="*70)
        print("LEAD GENERATION AI AGENT - EXECUTION SUMMARY")
        print("="*70)
        print(f"Total Leads Generated: {result['workflow_state']['total_leads']}")
        print(f"Execution Time: {datetime.now() - result['workflow_state']['start_time']}")
        print(f"Success: {result['success']}")
        print("="*70)
    
    asyncio.run(main())
