"""
Fixed Enhanced 14th Dimension Test
Tests the bug fixes for NoneType arithmetic errors and verifies enhanced topper comparison
"""

import os
import sys
import json
import asyncio
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.topper_vector_service import TopperVectorService
from app.services.enhanced_comprehensive_analysis import enhanced_comprehensive_analysis_with_topper_comparison
from app.core.llm_service import get_llm_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FixedEnhanced14thDimensionTest:
    """Test the fixed enhanced 14th dimension"""
    
    def __init__(self):
        self.vector_service = None
        self.llm_service = None
        
    async def initialize(self):
        """Initialize services"""
        logger.info("🔧 Initializing fixed test services...")
        
        self.vector_service = TopperVectorService()
        await self.vector_service.connect()
        
        self.llm_service = get_llm_service()
        
        logger.info("✅ Services initialized")
        
    async def test_bug_fixes(self):
        """Test the specific bug fixes"""
        logger.info("🐛 Testing Bug Fixes")
        logger.info("=" * 50)
        
        # Test 1: Verify vector search returns actual similarity scores
        logger.info("1. Testing vector similarity search...")
        
        test_question = "Discuss the role played by the Directorate of Enforcement"
        search_results = await self.vector_service.search_similar_topper_answers(test_question)
        
        if search_results:
            best_match = search_results[0]
            similarity_score = best_match.get('similarity_score', 0.0)
            logger.info(f"✅ Vector search working: similarity_score = {similarity_score}")
            
            if similarity_score > 0:
                logger.info("✅ Similarity scores are non-zero!")
            else:
                logger.warning("⚠️ Similarity scores are still 0.000")
        else:
            logger.error("❌ No search results returned")
            
        # Test 2: Test enhanced comprehensive analysis with topper comparison
        logger.info("\n2. Testing enhanced comprehensive analysis...")
        
        test_student_answer = """The Directorate of Enforcement (ED) plays a crucial role in investigating money laundering and foreign exchange violations under various statutes.

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
        
        try:
            result = await enhanced_comprehensive_analysis_with_topper_comparison(
                question=test_question,
                student_answer=test_student_answer,
                exam_context={
                    "marks": 15,
                    "time_limit": 20,
                    "word_limit": 250,
                    "exam_type": "UPSC Mains"
                },
                llm_service=self.llm_service
            )
            
            if result.get("success"):
                logger.info("✅ Enhanced analysis completed successfully!")
                
                # Check if topper comparison is included
                topper_included = result.get("topper_comparison_included", False)
                logger.info(f"🎯 Topper comparison included: {topper_included}")
                
                # Check the analysis data
                analysis = result.get("analysis", {})
                if "dimensional_scores" in analysis:
                    topper_dimension = analysis["dimensional_scores"].get("topper_comparison")
                    if topper_dimension:
                        score = topper_dimension.get("score", "N/A")
                        feedback = topper_dimension.get("feedback", "No feedback")
                        
                        logger.info(f"📊 Topper Comparison Score: {score}")
                        logger.info(f"💬 Topper Feedback: {feedback[:100]}...")
                        
                        # Check if it's generic or specific
                        if "temporarily unavailable" in feedback:
                            logger.warning("⚠️ Still getting generic topper feedback")
                        elif "similarity" in feedback.lower() or "technique" in feedback.lower():
                            logger.info("✅ Getting specific topper feedback!")
                        
                # Check metadata
                if "topper_analysis_metadata" in analysis:
                    metadata = analysis["topper_analysis_metadata"]
                    logger.info(f"🏆 Topper Reference: {metadata.get('topper_reference_used', 'N/A')}")
                    logger.info(f"📈 Similarity Score: {metadata.get('similarity_score', 'N/A')}")
                    
            else:
                logger.error(f"❌ Enhanced analysis failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Error during enhanced analysis: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_specific_scenarios(self):
        """Test specific scenarios to verify fixes"""
        logger.info("\n🧪 Testing Specific Scenarios")
        logger.info("=" * 50)
        
        # Scenario 1: Constitutional question (should match Aayushi Bansal)
        constitutional_q = "The Indian Constitution has been successful in providing a framework for liberal democracy to flourish. Analyze."
        constitutional_a = """The Indian Constitution has indeed provided a robust framework for liberal democracy, though with some challenges.

**Success Factors:**
The Constitution enshrines fundamental rights, separation of powers, and federal structure. The Emergency period (1975-77) tested democratic institutions.

**Liberal Democratic Features:**
- Universal adult franchise
- Multi-party system
- Independent judiciary
- Free press and expression

**Challenges:**
Some concerns exist regarding increasing authoritarianism, but overall the constitutional framework has ensured democratic continuity for over 75 years."""
        
        logger.info("Testing constitutional democracy question...")
        await self._test_single_scenario(constitutional_q, constitutional_a, "Constitutional Democracy")
        
        # Scenario 2: Enforcement question (should find relevant matches)
        enforcement_q = "Discuss the role played by the Directorate of Enforcement in the investigation of offence of money laundering and foreign exchange violations."
        enforcement_a = """The Directorate of Enforcement (ED) is responsible for investigating financial crimes under multiple acts.

**Legal Framework:**
- Prevention of Money Laundering Act (PMLA) 2002
- Foreign Exchange Management Act (FEMA) 1999
- Fugitive Economic Offenders Act (FEOA) 2018

**Key Functions:**
- Investigation of money laundering cases
- Attachment and confiscation of proceeds of crime
- Enforcement of foreign exchange regulations
- Coordination with international agencies

**Challenges:**
- Complex financial investigations
- Need for specialized skills
- International cooperation requirements"""
        
        logger.info("\nTesting enforcement investigation question...")
        await self._test_single_scenario(enforcement_q, enforcement_a, "Enforcement Investigation")
    
    async def _test_single_scenario(self, question: str, student_answer: str, scenario_name: str):
        """Test a single scenario"""
        try:
            # First check vector search
            search_results = await self.vector_service.search_similar_topper_answers(question)
            
            if search_results:
                best_match = search_results[0]
                topper_name = best_match.get('topper_name', 'Unknown')
                similarity = best_match.get('similarity_score', 0.0)
                logger.info(f"🔍 {scenario_name} - Best match: {topper_name} (similarity: {similarity:.3f})")
                
                # Now test comprehensive analysis
                result = await enhanced_comprehensive_analysis_with_topper_comparison(
                    question=question,
                    student_answer=student_answer,
                    exam_context={"marks": 15, "time_limit": 20, "word_limit": 250}
                )
                
                if result.get("success"):
                    analysis = result.get("analysis", {})
                    if "dimensional_scores" in analysis:
                        topper_score = analysis["dimensional_scores"].get("topper_comparison", {}).get("score", "N/A")
                        logger.info(f"📊 {scenario_name} - Final topper score: {topper_score}")
                        
                        # Check if metadata includes actual similarity
                        if "topper_analysis_metadata" in analysis:
                            meta_similarity = analysis["topper_analysis_metadata"].get("similarity_score", "N/A")
                            logger.info(f"📈 {scenario_name} - Metadata similarity: {meta_similarity}")
                
            else:
                logger.warning(f"❌ {scenario_name} - No search results")
                
        except Exception as e:
            logger.error(f"❌ {scenario_name} test failed: {e}")

async def main():
    """Main test function"""
    print("🔧 Fixed Enhanced 14th Dimension Test")
    print("Testing bug fixes and enhanced topper comparison")
    print("-" * 60)
    
    # Enable vector service
    os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
    
    test = FixedEnhanced14thDimensionTest()
    await test.initialize()
    
    await test.test_bug_fixes()
    await test.test_specific_scenarios()
    
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    asyncio.run(main())
