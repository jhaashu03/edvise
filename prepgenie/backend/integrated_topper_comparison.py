"""
Integrated Enhanced Topper Comparison Service
Ready to be integrated into the main evaluation pipeline
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

logger = logging.getLogger(__name__)

class IntegratedTopperComparisonService:
    """
    Enhanced topper comparison service with similarity search
    Ready for integration into main evaluation pipeline
    """
    
    def __init__(self):
        self.llm_service = None
        self.vector_service = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize services - call once before using"""
        if self._initialized:
            return
            
        try:
            self.llm_service = get_llm_service()
            self.vector_service = TopperVectorService()
            self._initialized = True
            logger.info("✅ Integrated Topper Comparison Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize topper comparison service: {e}")
            self._initialized = False
    
    async def generate_enhanced_topper_comparison(
        self,
        question_text: str,
        student_answer: str,
        student_score: float,
        subject: Optional[str] = None
    ) -> str:
        """
        Generate enhanced topper comparison with similarity search
        
        Args:
            question_text: The question being answered
            student_answer: Student's answer text
            student_score: Student's score (e.g., 6.0)
            subject: Optional subject filter for search
            
        Returns:
            Enhanced comparison text with specific topper examples
        """
        
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            return "Topper comparison service not available."
        
        try:
            # Find similar topper answers
            similar_answers = await self._find_similar_topper_answers(
                question_text, student_answer, subject
            )
            
            if not similar_answers:
                return await self._generate_fallback_comparison(
                    question_text, student_answer, student_score
                )
            
            # Generate enhanced comparison with specific examples
            return await self._generate_detailed_comparison(
                question_text, student_answer, student_score, similar_answers
            )
            
        except Exception as e:
            logger.error(f"Error generating enhanced topper comparison: {e}")
            return f"Error generating topper comparison: {str(e)[:100]}..."
    
    async def _find_similar_topper_answers(
        self, 
        question_text: str, 
        student_answer: str,
        subject_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find similar topper answers using vector search"""
        
        try:
            # Build filters if subject provided
            filters = {}
            if subject_filter and subject_filter.strip():
                # Map common subject names
                subject_map = {
                    'GS-I': 'General Studies',
                    'GS-II': 'General Studies',
                    'GS-III': 'General Studies',
                    'GS-IV': 'General Studies',
                    'Polity': 'General Studies',
                    'Economy': 'General Studies',
                    'Geography': 'General Studies',
                    'History': 'General Studies'
                }
                mapped_subject = subject_map.get(subject_filter, subject_filter)
                filters['subject'] = mapped_subject
            
            # Search for similar topper answers
            similar_answers = await self.vector_service.search_similar_topper_answers(
                query_question=question_text,
                student_answer=student_answer,
                limit=5,  # Get top 5 similar answers
                filters=filters if filters else None
            )
            
            logger.info(f"Found {len(similar_answers)} similar topper answers for comparison")
            return similar_answers
            
        except Exception as e:
            logger.error(f"Error finding similar topper answers: {e}")
            return []
    
    async def _generate_detailed_comparison(
        self,
        question_text: str,
        student_answer: str,
        student_score: float,
        similar_topper_answers: List[Dict[str, Any]]
    ) -> str:
        """Generate detailed comparison with specific topper examples"""
        
        # Prepare topper examples for LLM (use top 3 most similar)
        topper_examples = []
        for answer in similar_topper_answers[:3]:
            topper_examples.append({
                'topper_name': answer.get('topper_name', 'Unknown'),
                'rank': answer.get('rank', 'Unknown'),
                'institute': answer.get('institute', 'Unknown'),
                'question': answer.get('question_text', ''),
                'answer': answer.get('answer_text', ''),
                'marks': answer.get('marks', 'Unknown'),
                'similarity': answer.get('similarity', 0)
            })
        
        prompt = f"""You are an expert UPSC evaluator. Provide a concise but detailed topper comparison analysis.

**Question:** {question_text}

**Student Answer:** {student_answer}
**Student Score:** {student_score}/10

**Similar Topper Answers for Reference:**
{self._format_topper_examples_concise(topper_examples)}

**Instructions:**
Provide a focused analysis comparing the student's answer with topper approaches. Include:

1. **Key Structural Differences** (2-3 points with specific topper examples)
2. **Content Gaps** (3-4 missing elements with topper evidence)  
3. **Superior Techniques** (2-3 specific topper phrases/approaches to emulate)
4. **Actionable Improvements** (3-4 concrete recommendations)

**Format as:**
🏆 **Topper Comparison:** [Brief intro comparing overall approach]

**Structural Differences:**
• [Point with specific topper example]
• [Point with specific topper example]

**Content Gaps:**
• [Missing element with topper evidence]
• [Missing element with topper evidence]
• [Missing element with topper evidence]

**Key Techniques to Emulate:**
• "[Exact topper phrase]" - [Why effective]
• "[Exact topper phrase]" - [Why effective]

**Actionable Improvements:**
• [Specific recommendation based on topper analysis]
• [Specific recommendation based on topper analysis]
• [Specific recommendation based on topper analysis]

Keep it concise but specific with actual topper examples and quotes.
"""
        
        try:
            response = await self.llm_service.generate_completion(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating detailed comparison: {e}")
            return f"Error generating comparison: {e}"
    
    async def _generate_fallback_comparison(
        self,
        question_text: str,
        student_answer: str,
        student_score: float
    ) -> str:
        """Generate fallback comparison when no similar topper answers found"""
        
        prompt = f"""You are an expert UPSC evaluator. The student scored {student_score}/10 on this question.

**Question:** {question_text}
**Student Answer:** {student_answer}

Since no similar topper answers are available in the database, provide general guidance based on UPSC toppers' common approaches:

🏆 **Topper Comparison:** Based on general topper strategies, here's how this answer can be improved:

**Common Topper Techniques:**
• Clear introduction with definition/context
• Structured presentation using numbered points or headings
• Specific examples and case studies
• Current affairs integration where relevant
• Balanced analysis with multiple perspectives
• Strong conclusion linking back to the question

**Key Improvements Needed:**
• [Specific recommendation for this answer]
• [Specific recommendation for this answer]
• [Specific recommendation for this answer]

**Typical Topper Approach for Similar Questions:**
[Brief description of how toppers typically handle this type of question]

Keep it concise and actionable.
"""
        
        try:
            response = await self.llm_service.generate_completion(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating fallback comparison: {e}")
            return "Enhanced topper comparison not available at this time."
    
    def _format_topper_examples_concise(self, topper_examples: List[Dict]) -> str:
        """Format topper examples concisely for LLM prompt"""
        formatted = ""
        
        for i, example in enumerate(topper_examples, 1):
            formatted += f"""
**Topper {i}: {example['topper_name']} (Rank {example['rank']})**
- Question: {example['question'][:120]}...
- Key Excerpt: {example['answer'][:400]}...
- Similarity: {example['similarity']:.2f}
"""
        return formatted

# Example integration function
async def integrate_enhanced_topper_comparison(
    question_text: str,
    student_answer: str,
    current_score: float,
    subject: str = None
) -> str:
    """
    Integration function to be called from main evaluation pipeline
    
    Usage:
        enhanced_comparison = await integrate_enhanced_topper_comparison(
            question_text="Your question here",
            student_answer="Student's answer here", 
            current_score=6.0,
            subject="General Studies"
        )
    """
    
    service = IntegratedTopperComparisonService()
    return await service.generate_enhanced_topper_comparison(
        question_text, student_answer, current_score, subject
    )

# Test function
async def test_integration():
    """Test the integrated service"""
    
    # Test with your actual questions
    question1 = "There are arguments that bills of national importance should be placed before the Inter-State Council"
    student_answer1 = """Article 263 provides for the establishment of Inter-State Council. It consists of PM as chairman, CMs of all states, and union ministers nominated by PM. Currently there are issues like reduced parliamentary sittings and misuse of money bills. The Inter-State Council can help address these concerns."""
    
    print("Testing Integrated Enhanced Topper Comparison...")
    print("="*60)
    
    enhanced_comparison = await integrate_enhanced_topper_comparison(
        question_text=question1,
        student_answer=student_answer1,
        current_score=6.0,
        subject="General Studies"
    )
    
    print("Enhanced Topper Comparison Result:")
    print(enhanced_comparison)

if __name__ == "__main__":
    asyncio.run(test_integration())
