"""
Fix Generic Topper Feedback - Make it Specific
The issue is that topper comparison is working, but feedback generation is generic.
Need to use the actual LLM-generated detailed comparison instead of generic templates.
"""

import os
import sys
import json
import asyncio
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.topper_analysis_service import TopperAnalysisService
from app.core.llm_service import get_llm_service
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TopperFeedbackFixer:
    """Fix the generic feedback issue in topper comparison"""
    
    def __init__(self):
        self.topper_service = TopperAnalysisService()
        self.llm_service = get_llm_service()
        
    async def demonstrate_current_issue(self):
        """Show what's currently happening vs what should happen"""
        
        logger.info("🔍 DEMONSTRATING CURRENT ISSUE WITH TOPPER FEEDBACK")
        logger.info("=" * 60)
        
        # Test question about Directorate of Enforcement
        question = "Discuss the role played by the Directorate of Enforcement in the investigation of offence of money laundering and foreign exchange violations."
        student_answer = """The Directorate of Enforcement (ED) plays a crucial role in investigating money laundering and foreign exchange violations under various statutes.

**Statutory Framework:**
- Prevention of Money Laundering Act (PMLA) 2002
- Foreign Exchange Management Act (FEMA) 1999

**Role in Money Laundering:**
- Investigates offences under PMLA
- Traces proceeds of crime
- Arrests accused persons

**Way Forward:**
- Strengthening capacity building
- Enhanced coordination with banks"""
        
        # Get database session
        from app.database.session import get_db_session
        db = get_db_session()
        
        try:
            # Step 1: Get topper comparison result (this works correctly)
            logger.info("\n🔍 STEP 1: Getting topper comparison result...")
            comparison_result = await self.topper_service.compare_with_topper_answers(
                student_answer=student_answer,
                question=question,
                subject="General Studies",
                marks=15,
                db=db
            )
            
            logger.info(f"✅ Topper found: {comparison_result.topper_name}")
            logger.info(f"✅ Similarity score: {comparison_result.similarity_score}")
            logger.info(f"✅ Missing techniques: {comparison_result.missing_topper_techniques[:3]}")
            
            # Step 2: Show current generic feedback generation
            logger.info("\n❌ STEP 2: Current generic feedback generation...")
            current_dimension = await self.topper_service.create_topper_analysis_dimension(
                comparison_result, question
            )
            
            logger.info("Current feedback (GENERIC):")
            logger.info(f"📝 {current_dimension.feedback}")
            
            # Step 3: Show what it should be (specific feedback)
            logger.info("\n✅ STEP 3: What it should be (specific feedback)...")
            enhanced_feedback = await self.create_enhanced_specific_feedback(
                comparison_result, question, student_answer
            )
            
            logger.info("Enhanced feedback (SPECIFIC):")
            logger.info(f"📝 {enhanced_feedback}")
            
            # Show the difference
            logger.info("\n🎯 THE DIFFERENCE:")
            logger.info("Current: Generic template with just topper name")
            logger.info("Enhanced: Specific comparison with actual topper techniques and quotes")
            
        finally:
            db.close()
    
    async def create_enhanced_specific_feedback(self, comparison_result, question, student_answer):
        """Create enhanced feedback using the detailed comparison data"""
        
        # Use the detailed comparison data from the LLM
        prompt = f"""Create a specific, actionable topper comparison feedback based on this detailed analysis:

Question: {question}

Topper Matched: {comparison_result.topper_name}
Similarity Score: {comparison_result.similarity_score}

Student's Missing Techniques:
{chr(10).join(['• ' + technique for technique in comparison_result.missing_topper_techniques[:3]])}

Topper's Strengths to Adopt:
{chr(10).join(['• ' + strength for strength in comparison_result.topper_strengths_identified[:3]])}

Specific Improvements Needed:
{chr(10).join(['• ' + improvement for improvement in comparison_result.specific_improvements[:3]])}

Create feedback in this format:
"Topper Comparison: [Score]/10 - Compared with [Topper Name]'s approach, your answer [specific analysis]. Key techniques to adopt from [Topper]: [specific techniques]. [Specific actionable improvements]."

Make it specific, mention the topper by name, and include actual techniques they used. Limit to 2-3 sentences, be actionable."""

        try:
            response = await self.llm_service.simple_chat(
                user_message=prompt,
                temperature=0.3
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating enhanced feedback: {e}")
            return f"Topper Comparison: {comparison_result.similarity_score:.1f}/10 - Compared with {comparison_result.topper_name}'s approach"

async def main():
    """Demonstrate the issue and solution"""
    fixer = TopperFeedbackFixer()
    
    # Show the current issue
    await fixer.demonstrate_current_issue()
    
    logger.info("\n" + "="*60)
    logger.info("🎯 SOLUTION: Modify create_topper_analysis_dimension method")
    logger.info("Instead of generic templates, use LLM to create specific feedback")
    logger.info("Include actual topper techniques, quotes, and specific comparisons")

if __name__ == "__main__":
    print("🔧 Fixing Generic Topper Feedback Issue")
    print("Making feedback specific with actual topper techniques")
    print("-" * 60)
    
    # Enable vector service
    os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
    
    asyncio.run(main())
