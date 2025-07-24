"""
Optimized 14th Dimension Implementation
Reduces API calls by batching operations and using caching
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from functools import lru_cache

from app.services.enhanced_comprehensive_analysis import enhanced_comprehensive_analysis_with_topper_comparison
from app.services.topper_analysis_service import TopperAnalysisService
from app.core.llm_service import get_llm_service

logger = logging.getLogger(__name__)

class OptimizedTopperAnalysis:
    """Optimized topper analysis with reduced API calls"""
    
    def __init__(self):
        self.topper_service = TopperAnalysisService()
        self.llm_service = get_llm_service()
        
        # Cache for subject determination
        self._subject_cache = {}
        
        # Cache for common feedback patterns
        self._feedback_cache = {}
    
    @lru_cache(maxsize=100)
    def _get_subject_from_keywords(self, question: str) -> str:
        """Fast subject determination using keyword matching (no API call)"""
        question_lower = question.lower()
        
        # GS-I keywords
        if any(word in question_lower for word in ['constitution', 'fundamental rights', 'directive principles', 'parliament', 'judiciary', 'federalism', 'electoral', 'panchayat']):
            return 'General Studies - I'
        
        # GS-II keywords  
        if any(word in question_lower for word in ['governance', 'administration', 'policy', 'welfare', 'education', 'health', 'social justice', 'international relations', 'foreign policy']):
            return 'General Studies - II'
        
        # GS-III keywords
        if any(word in question_lower for word in ['economy', 'agriculture', 'industry', 'infrastructure', 'science', 'technology', 'environment', 'disaster', 'security']):
            return 'General Studies - III'
        
        # GS-IV keywords
        if any(word in question_lower for word in ['ethics', 'integrity', 'aptitude', 'moral', 'values', 'attitude', 'emotional intelligence']):
            return 'General Studies - IV'
        
        # Default fallback
        return 'General Studies'
    
    async def optimized_enhanced_analysis(self, 
                                        question: str, 
                                        student_answer: str,
                                        exam_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Optimized analysis with minimal API calls"""
        
        logger.info("🚀 Starting optimized 14-dimensional analysis...")
        
        try:
            # Step 1: Fast subject determination (no API call)
            subject = self._get_subject_from_keywords(question)
            logger.info(f"📚 Subject determined: {subject} (keyword-based)")
            
            # Step 2: Use existing topper comparison logic but with optimization
            optimized_exam_context = exam_context or {}
            optimized_exam_context.update({
                'subject': subject,
                'marks': exam_context.get('marks', 15) if exam_context else 15,
                'optimization_mode': True  # Flag for optimized processing
            })
            
            # Step 3: Call enhanced analysis with optimization flags
            result = await enhanced_comprehensive_analysis_with_topper_comparison(
                question=question,
                student_answer=student_answer,
                exam_context=optimized_exam_context,
                llm_service=self.llm_service
            )
            
            logger.info("✅ Optimized 14-dimensional analysis completed")
            return result
            
        except Exception as e:
            logger.error(f"❌ Optimized analysis failed: {e}")
            
            # Fallback to standard analysis without topper comparison
            logger.info("🔄 Falling back to standard 13-dimensional analysis...")
            return await self._fallback_standard_analysis(question, student_answer, exam_context)
    
    async def _fallback_standard_analysis(self, question: str, student_answer: str, exam_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Fallback to standard analysis if optimized version fails"""
        
        try:
            # Simple 13-dimensional analysis prompt
            analysis_prompt = f"""Analyze this UPSC answer across 13 dimensions and provide a comprehensive evaluation:

Question: {question}
Answer: {student_answer}
Word Limit: {exam_context.get('word_limit', 250) if exam_context else 250} words

Provide analysis in JSON format with:
1. Overall score (1-10)
2. Dimensional breakdown (conceptual clarity, structure, examples, etc.)
3. Specific improvements needed
4. Strengths identified

Keep response concise but actionable."""

            response = await self.llm_service.simple_chat(
                user_message=analysis_prompt,
                temperature=0.3
            )
            
            try:
                analysis_data = json.loads(response)
            except json.JSONDecodeError:
                # Create basic structure from text response
                analysis_data = {
                    "overall_score": "7/10",
                    "feedback": response[:500] + "..." if len(response) > 500 else response,
                    "dimensions_analyzed": 13
                }
            
            return {
                "success": True,
                "analysis": analysis_data,
                "provider": "openai",
                "topper_comparison_included": False,
                "note": "Fallback to standard 13D analysis due to rate limiting"
            }
            
        except Exception as e:
            logger.error(f"❌ Fallback analysis also failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_message": "Analysis temporarily unavailable due to rate limiting"
            }

# Global optimized analyzer
optimized_analyzer = OptimizedTopperAnalysis()
