"""
Optimized Enhanced Comprehensive Analysis
Reduces LLM calls to prevent rate limiting while maintaining quality
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.llm_service import get_llm_service, LLMService
from app.services.topper_analysis_service import topper_analysis_service
from app.db.database import SessionLocal
from app.utils.rate_limit_handler import rate_limit_handler

logger = logging.getLogger(__name__)

class OptimizedEnhancedAnalysis:
    """Optimized version with reduced API calls"""
    
    def __init__(self):
        pass
    
    async def optimized_comprehensive_analysis(self,
                                             question: str,
                                             student_answer: str = "",
                                             exam_context: dict = None,
                                             llm_service: LLMService = None) -> dict:
        """
        Optimized 14-dimensional analysis with minimal LLM calls
        Combines standard analysis and topper comparison in single call
        """
        
        if not llm_service:
            llm_service = get_llm_service()
        
        if not exam_context:
            exam_context = {
                "marks": 15,
                "time_limit": 20,
                "word_limit": 250,
                "subject": "General Studies"  # Default to avoid extra LLM call
            }
        
        # Get database session
        db = SessionLocal()
        try:
            return await self._execute_optimized_analysis(
                question, student_answer, exam_context, llm_service, db
            )
        finally:
            db.close()
    
    async def _execute_optimized_analysis(self,
                                        question: str,
                                        student_answer: str,
                                        exam_context: dict,
                                        llm_service: LLMService,
                                        db: Session) -> dict:
        """Execute the optimized analysis with rate limiting"""
        
        try:
            logger.info("🚀 Starting optimized 14-dimensional analysis...")
            
            # Step 1: Get topper comparison data (vector search - no LLM call)
            logger.info("🔍 Performing vector search for topper comparison...")
            
            subject = exam_context.get('subject', 'General Studies')
            marks = exam_context.get('marks', 15)
            
            topper_comparison = await topper_analysis_service.compare_with_topper_answers(
                student_answer=student_answer,
                question=question,
                subject=subject,
                marks=marks,
                db=db
            )
            
            # Step 2: Combined analysis prompt (single LLM call)
            logger.info("🤖 Performing combined 14-dimensional analysis...")
            
            combined_result = await rate_limit_handler.execute_with_backoff(
                self._combined_analysis_call,
                question,
                student_answer,
                exam_context,
                topper_comparison,
                llm_service
            )
            
            return combined_result
            
        except Exception as e:
            logger.error(f"❌ Optimized analysis failed: {e}")
            return await self._fallback_analysis(question, student_answer, exam_context, llm_service)
    
    async def _combined_analysis_call(self,
                                    question: str,
                                    student_answer: str,
                                    exam_context: dict,
                                    topper_comparison,
                                    llm_service: LLMService) -> dict:
        """Single LLM call for complete 14-dimensional analysis"""
        
        # Prepare topper context
        topper_context = ""
        if topper_comparison:
            # Handle both dict and object formats
            if isinstance(topper_comparison, dict):
                topper_name = topper_comparison.get('topper_name', 'Unknown')
                similarity_score = topper_comparison.get('similarity_score', 0)
                missing_techniques = topper_comparison.get('missing_topper_techniques', [])
                topper_strengths = topper_comparison.get('topper_strengths_identified', [])
            else:
                topper_name = getattr(topper_comparison, 'topper_name', 'Unknown')
                similarity_score = getattr(topper_comparison, 'similarity_score', 0)
                missing_techniques = getattr(topper_comparison, 'missing_topper_techniques', [])
                topper_strengths = getattr(topper_comparison, 'topper_strengths_identified', [])
            
            if topper_name and topper_name != 'Unknown':
                topper_context = f"""
**Topper Comparison Context:**
- Best matching topper: {topper_name}
- Similarity score: {similarity_score:.2f}
- Missing techniques: {', '.join(missing_techniques[:3]) if missing_techniques else 'None identified'}
- Topper strengths: {', '.join(topper_strengths[:2]) if topper_strengths else 'None identified'}
"""
        
        # Combined analysis prompt
        analysis_prompt = f"""You are an expert UPSC evaluator providing complete 14-dimensional analysis including topper comparison.

**Question:** {question}

**Student Answer:**
{student_answer or "No answer provided"}

**Exam Context:**
- Marks: {exam_context.get('marks', 15)}
- Word Limit: {exam_context.get('word_limit', 250)}
- Subject: {exam_context.get('subject', 'General Studies')}

{topper_context}

Provide comprehensive analysis in JSON format covering all 14 dimensions:

{{
    "question_analysis": {{
        "difficulty_level": "Easy/Medium/Hard",
        "subject_area": "{exam_context.get('subject', 'General Studies')}",
        "question_type": "Analytical/Descriptive/Evaluative"
    }},
    "answer_evaluation": {{
        "current_score": "X/{exam_context.get('marks', 15)}",
        "potential_score": "X/{exam_context.get('marks', 15)}"
    }},
    "dimensional_scores": {{
        "content_knowledge": {{"score": "X/10", "feedback": "specific feedback"}},
        "analytical_thinking": {{"score": "X/10", "feedback": "specific feedback"}},
        "current_affairs": {{"score": "X/10", "feedback": "specific feedback"}},
        "factual_accuracy": {{"score": "X/10", "feedback": "specific feedback"}},
        "structure_organization": {{"score": "X/10", "feedback": "specific feedback"}},
        "language_expression": {{"score": "X/10", "feedback": "specific feedback"}},
        "critical_evaluation": {{"score": "X/10", "feedback": "specific feedback"}},
        "example_integration": {{"score": "X/10", "feedback": "specific feedback"}},
        "contemporary_relevance": {{"score": "X/10", "feedback": "specific feedback"}},
        "conclusion_effectiveness": {{"score": "X/10", "feedback": "specific feedback"}},
        "answer_completeness": {{"score": "X/10", "feedback": "specific feedback"}},
        "time_management": {{"score": "X/10", "feedback": "specific feedback"}},
        "presentation_quality": {{"score": "X/10", "feedback": "specific feedback"}},
        "topper_comparison": {{"score": "X/10", "feedback": "Compare with {topper_comparison.topper_name if topper_comparison and topper_comparison.topper_name else 'topper patterns'}: [specific comparison with techniques to adopt]"}}
    }},
    "detailed_feedback": {{
        "strengths": ["specific strength 1", "specific strength 2"],
        "improvement_suggestions": ["specific suggestion 1", "specific suggestion 2"],
        "topper_insights": {{
            "topper_reference": "{topper_comparison.topper_name if topper_comparison and topper_comparison.topper_name else 'General patterns'}",
            "comparison_score": {topper_comparison.similarity_score if topper_comparison and topper_comparison.similarity_score else 6.0},
            "key_techniques_to_adopt": {topper_comparison.missing_topper_techniques[:3] if topper_comparison and topper_comparison.missing_topper_techniques else ["structured approach", "detailed analysis"]},
            "specific_improvements": {topper_comparison.specific_improvements[:2] if topper_comparison and topper_comparison.specific_improvements else ["enhance depth", "add examples"]}
        }}
    }}
}}

Be specific, actionable, and reference actual content from the student's answer."""

        try:
            response = await llm_service.simple_chat(
                user_message=analysis_prompt,
                temperature=0.3
            )
            
            # Parse JSON response
            import json
            analysis_data = json.loads(response)
            
            return {
                "success": True,
                "analysis": analysis_data,
                "provider": llm_service.provider_name,
                "topper_comparison_included": True,
                "dimensions_analyzed": 14,
                "optimization": "single_call_analysis"
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed, using fallback: {e}")
            return await self._fallback_analysis(question, student_answer, exam_context, llm_service)
    
    async def _fallback_analysis(self,
                                question: str,
                                student_answer: str,
                                exam_context: dict,
                                llm_service: LLMService) -> dict:
        """Fallback to basic analysis if optimized version fails"""
        
        logger.warning("� GIVING FALLBACK RESPONSE - 13-dimensional analysis only")
        logger.warning("🔄 Reason: Optimized 14-dimensional analysis with topper comparison failed")
        
        fallback_prompt = f"""Provide basic 13-dimensional UPSC analysis for:

Question: {question}
Answer: {student_answer}
Marks: {exam_context.get('marks', 15)}

Return in simple JSON format with scores and feedback for each dimension."""
        
        try:
            response = await llm_service.simple_chat(
                user_message=fallback_prompt,
                temperature=0.3
            )
            
            return {
                "success": True,
                "analysis": {"raw_response": response},
                "provider": llm_service.provider_name,
                "topper_comparison_included": False,
                "dimensions_analyzed": 13,
                "note": "Fallback analysis used"
            }
            
        except Exception as e:
            logger.error(f"❌ Fallback analysis also failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }

# Global optimized analyzer instance
optimized_enhanced_analyzer = OptimizedEnhancedAnalysis()
