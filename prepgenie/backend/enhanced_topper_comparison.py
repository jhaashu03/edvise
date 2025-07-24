"""
Enhanced Topper Comparison with Similarity Search
Provides specific, relevant examples from similar topper answers
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.llm_service import get_llm_service
from app.services.topper_vector_service import TopperVectorService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedTopperComparison:
    """Enhanced topper comparison with similarity search"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.vector_service = TopperVectorService()
    
    async def initialize(self):
        """Initialize services"""
        logger.info("🔧 Initializing Enhanced Topper Comparison...")
        # Vector service will auto-connect when needed
        logger.info("✅ Services initialized")
    
    async def find_similar_topper_answers(
        self, 
        question_text: str, 
        student_answer: str,
        subject_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find similar topper answers using vector search"""
        
        try:
            # Build filters if subject provided
            filters = {}
            if subject_filter:
                filters['subject'] = subject_filter
            
            # Search for similar topper answers
            similar_answers = await self.vector_service.search_similar_topper_answers(
                query_question=question_text,
                student_answer=student_answer,
                limit=5,  # Get top 5 similar answers
                filters=filters if filters else None
            )
            
            logger.info(f"Found {len(similar_answers)} similar topper answers")
            return similar_answers
            
        except Exception as e:
            logger.error(f"Error finding similar topper answers: {e}")
            return []
    
    async def generate_enhanced_comparison(
        self,
        question_text: str,
        student_answer: str,
        student_score: float,
        similar_topper_answers: List[Dict[str, Any]]
    ) -> str:
        """Generate detailed comparison with specific topper examples"""
        
        if not similar_topper_answers:
            return "No similar topper answers found for comparison."
        
        # Prepare topper examples for LLM
        topper_examples = []
        for i, answer in enumerate(similar_topper_answers[:3], 1):  # Use top 3
            topper_examples.append({
                'topper_name': answer.get('topper_name', 'Unknown'),
                'rank': answer.get('rank', 'Unknown'),
                'institute': answer.get('institute', 'Unknown'),
                'question': answer.get('question_text', ''),
                'answer': answer.get('answer_text', ''),
                'marks': answer.get('marks', 'Unknown'),
                'similarity': answer.get('similarity', 0)
            })
        
        prompt = f"""
You are an expert UPSC evaluator. Analyze the student's answer by comparing it with similar topper answers from the database.

**Question:** {question_text}

**Student Answer:** {student_answer}
**Student Score:** {student_score}/10

**Similar Topper Answers for Reference:**

{self._format_topper_examples(topper_examples)}

**Instructions:**
1. **Structural Analysis:** Compare how toppers structured their answers vs the student
2. **Content Depth:** Identify specific concepts, examples, or dimensions toppers covered that student missed
3. **Writing Techniques:** Extract specific phrases, transitions, or approaches toppers used
4. **Key Learnings:** Provide actionable insights with exact topper phrases the student can emulate
5. **Scoring Insights:** Explain why toppers would score higher with specific evidence

**Format your response as:**
🎯 **Topper Comparison Analysis**

**Structural Differences:**
[Compare structure with specific examples from toppers]

**Content Gaps Identified:**
[List missing concepts with topper examples]

**Superior Writing Techniques:**
[Extract specific phrases and approaches from toppers]

**Key Topper Phrases to Emulate:**
[Provide exact quotes from topper answers]

**Actionable Improvements:**
[Specific recommendations based on topper analysis]

**Scoring Insights:**
[Why toppers score higher with evidence]

Be specific, use exact topper quotes, and provide actionable feedback.
"""
        
        try:
            response = await self.llm_service.generate_completion(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating enhanced comparison: {e}")
            return f"Error generating comparison: {e}"
    
    def _format_topper_examples(self, topper_examples: List[Dict]) -> str:
        """Format topper examples for LLM prompt"""
        formatted = ""
        
        for i, example in enumerate(topper_examples, 1):
            formatted += f"""
**Topper {i}: {example['topper_name']} (Rank {example['rank']}, {example['institute']})**
- **Question:** {example['question'][:150]}...
- **Answer:** {example['answer'][:800]}...
- **Marks:** {example['marks']}
- **Similarity Score:** {example['similarity']:.3f}

"""
        return formatted
    
    async def test_comparison_for_questions(self):
        """Test the enhanced comparison system with specific questions"""
        
        logger.info("🧪 Testing Enhanced Topper Comparison System")
        
        # Test Question 1: Inter-State Council
        question1 = "There are arguments that bills of national importance should be placed before the Inter-State Council"
        student_answer1 = """Article 263 provides for the establishment of Inter-State Council. It consists of PM as chairman, CMs of all states, and union ministers nominated by PM. Currently there are issues like reduced parliamentary sittings and misuse of money bills. The Inter-State Council can help address these concerns."""
        
        logger.info("\\n" + "="*60)
        logger.info("Testing Question 1: Inter-State Council")
        logger.info("="*60)
        
        similar_answers1 = await self.find_similar_topper_answers(
            question1, student_answer1, "General Studies"
        )
        
        if similar_answers1:
            comparison1 = await self.generate_enhanced_comparison(
                question1, student_answer1, 6.0, similar_answers1
            )
            print("\\nQ1 Enhanced Topper Comparison:")
            print(comparison1)
        else:
            print("No similar topper answers found for Q1")
        
        # Test Question 2: Enforcement Directorate
        question2 = "Discuss the role played by the Directorate of Enforcement in the investigation of offence of money laundering"
        student_answer2 = """The Enforcement Directorate (ED) is responsible for investigating money laundering cases under the Prevention of Money Laundering Act (PMLA), Foreign Exchange Management Act (FEMA), and Fugitive Economic Offenders Act (FEOA). It conducts investigations and enforces compliance with foreign exchange laws."""
        
        logger.info("\\n" + "="*60)
        logger.info("Testing Question 2: Enforcement Directorate")
        logger.info("="*60)
        
        similar_answers2 = await self.find_similar_topper_answers(
            question2, student_answer2, "General Studies"
        )
        
        if similar_answers2:
            comparison2 = await self.generate_enhanced_comparison(
                question2, student_answer2, 4.0, similar_answers2
            )
            print("\\nQ2 Enhanced Topper Comparison:")
            print(comparison2)
        else:
            print("No similar topper answers found for Q2")

async def main():
    """Main function to test enhanced topper comparison"""
    
    comparison_system = EnhancedTopperComparison()
    await comparison_system.initialize()
    await comparison_system.test_comparison_for_questions()

if __name__ == "__main__":
    asyncio.run(main())
