"""
Topper Analysis Service
Service for analyzing topper answer patterns and comparing with student answers
"""
import logging
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from app.core.llm_service import get_llm_service, LLMService
from app.models.topper_reference import TopperReference, TopperPattern
from app.schemas.topper_reference import TopperComparisonResult, TopperAnalysisDimension
from app.services.topper_vector_service import TopperVectorService

logger = logging.getLogger(__name__)

class TopperAnalysisService:
    """Service for topper content analysis and comparison"""
    
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or get_llm_service()
        self.vector_service = TopperVectorService()  # Create local instance
    
    async def analyze_topper_answer_patterns(self, 
                                           topper_answer: str, 
                                           question: str, 
                                           subject: str,
                                           marks: int) -> Dict[str, Any]:
        """
        Analyze a topper's answer to extract patterns and techniques
        """
        
        analysis_prompt = f"""You are an expert UPSC evaluator analyzing a topper's answer to identify high-scoring patterns and techniques.

Question: {question}
Subject: {subject}
Marks: {marks}

Topper's Answer:
{topper_answer}

Analyze this topper's answer and extract key patterns in JSON format:

{{
    "structural_patterns": {{
        "introduction_approach": "How does the topper start the answer?",
        "body_organization": "How is the main content structured?",
        "conclusion_technique": "How does the topper conclude?",
        "paragraph_flow": "How are ideas connected?"
    }},
    "content_techniques": {{
        "example_usage": ["List of examples used and their placement"],
        "current_affairs_integration": ["How recent developments are woven in"],
        "factual_presentation": "How facts and data are presented",
        "analytical_approach": "How analysis is demonstrated"
    }},
    "writing_style": {{
        "language_sophistication": "Assessment of language use",
        "sentence_structure": "Pattern of sentence construction",
        "terminology_usage": "Use of technical terms",
        "clarity_techniques": "How clarity is maintained"
    }},
    "visual_elements": {{
        "diagrams_used": ["Any diagrams or visual elements"],
        "formatting_techniques": ["Bullet points, numbering, etc."],
        "emphasis_methods": ["How key points are highlighted"]
    }},
    "scoring_strategies": {{
        "mark_optimization": "Techniques that likely earned maximum marks",
        "word_efficiency": "How maximum content is packed efficiently",
        "examiner_appeal": "Elements that would appeal to examiners"
    }},
    "unique_strengths": [
        "Specific strengths that make this answer stand out"
    ],
    "replicable_patterns": [
        "Patterns that other students can learn and apply"
    ]
}}"""

        try:
            response = await self.llm_service.simple_chat(
                user_message=analysis_prompt,
                temperature=0.3
            )
            
            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Return structured fallback
                return {
                    "structural_patterns": {"introduction_approach": "Strong conceptual opening"},
                    "content_techniques": {"example_usage": ["Multiple relevant examples"]},
                    "writing_style": {"language_sophistication": "Clear and precise"},
                    "visual_elements": {"diagrams_used": ["Flowchart or table"]},
                    "scoring_strategies": {"mark_optimization": "Comprehensive coverage"},
                    "unique_strengths": ["Excellent structure and examples"],
                    "replicable_patterns": ["Clear paragraph organization", "Strategic example placement"]
                }
                
        except Exception as e:
            logger.error(f"Error analyzing topper patterns: {e}")
            return {}
    
    async def compare_with_topper_answers(self,
                                        student_answer: str,
                                        question: str,
                                        subject: str,
                                        marks: int,
                                        db: Session) -> Optional[TopperComparisonResult]:
        """
        Compare student answer with relevant topper answers using vector similarity search
        Returns None if no meaningful comparison can be made (better than generic feedback)
        """
        
        # Define minimum similarity threshold for meaningful comparison
        MIN_SIMILARITY_THRESHOLD = 0.30  # Temporarily lowered from 0.50 to allow more topper comparisons (was rejecting all matches)
        
        try:
            # Ensure vector service is connected
            if not self.vector_service._connected:
                await self.vector_service.connect()
            
            # Search for similar topper answers using vector similarity
            similar_toppers = await self.vector_service.search_similar_topper_answers(
                query_question=question,
                student_answer=student_answer,
                limit=10,  # Get more results to filter by quality
                filters=None  # No filters for broader search
            )
            
            # Debug log
            logger.info(f"Vector search found {len(similar_toppers) if similar_toppers else 0} similar topper answers")
            
            if similar_toppers and len(similar_toppers) > 0:
                # Filter by similarity threshold - only keep meaningful matches
                high_quality_matches = [
                    topper for topper in similar_toppers 
                    if topper.get('similarity_score', 0) >= MIN_SIMILARITY_THRESHOLD
                ]
                
                if high_quality_matches:
                    # Use only top 1-2 highest similarity matches
                    best_matches = high_quality_matches[:2]
                    best_match = best_matches[0]
                    
                    similarity_score = best_match.get('similarity_score', 0)
                    logger.info(f"High-quality match found: {best_match.get('topper_name', 'Unknown')} with similarity {similarity_score:.3f}")
                    
                    # Generate contextual comparison using only high-quality matches
                    return await self._generate_contextual_comparison(
                        question, student_answer, best_matches, subject, marks
                    )
                else:
                    # No high-quality matches found
                    best_similarity = similar_toppers[0].get('similarity_score', 0)
                    logger.warning(f"🚨 No high-quality topper matches found")
                    logger.warning(f"🔍 Best similarity: {best_similarity:.3f} (below threshold {MIN_SIMILARITY_THRESHOLD})")
                    logger.warning("🚫 Skipping 14th dimension - no contextually relevant topper data")
                    logger.warning(f"GIVING FALLBACK RESPONSE FOR QUES - Best match similarity {best_similarity:.3f} < {MIN_SIMILARITY_THRESHOLD}")
                    return None
            else:
                logger.warning("� Vector search found no results")
                logger.warning("🚫 Skipping 14th dimension - no vector search results")
                logger.warning("GIVING FALLBACK RESPONSE FOR QUES - Vector search returned 0 results")
                return None
                
        except Exception as e:
            logger.error(f"🚨 Vector search failed: {e}")
            logger.warning("🚫 Skipping 14th dimension - vector search error")
            return None

    async def _generate_contextual_comparison(self,
                                            question: str,
                                            student_answer: str,
                                            best_matches: List[Dict],
                                            subject: str,
                                            marks: int) -> TopperComparisonResult:
        """Generate contextual comparison using only high-quality matches"""
        
        best_match = best_matches[0]
        similarity_score = best_match.get('similarity_score', 0)
        
        # Create contextual comparison prompt with actual topper data
        comparison_prompt = f"""You are an expert UPSC evaluator comparing a student's answer with a high-quality topper answer.

Question: {question}
Subject: {subject}
Marks: {marks}

Student's Answer:
{student_answer}

High-Quality Topper Match (Similarity: {similarity_score:.2f}):
Topper: {best_match.get('topper_name', 'Top Performer')}
Rank: {best_match.get('rank', 'High rank')}

Topper's Answer:
{best_match.get('answer_text', '')[:1500]}...

Analyze the differences and provide specific, contextual feedback in JSON format:

{{
    "similarity_score": {similarity_score * 10:.1f},
    "topper_strengths_identified": ["specific strength 1", "specific strength 2", "specific strength 3"],
    "missing_topper_techniques": ["specific technique 1", "specific technique 2", "specific technique 3"],
    "specific_improvements": ["actionable improvement 1", "actionable improvement 2"],
    "contextual_feedback": "Detailed comparison highlighting what the topper did differently and why it's effective for this specific question"
}}

Focus on SPECIFIC techniques this topper used for THIS question, not generic advice."""

        try:
            # Import rate limit handler
            from app.utils.rate_limit_handler import rate_limit_handler
            
            response = await rate_limit_handler.execute_with_backoff(
                self.llm_service.simple_chat,
                user_message=comparison_prompt,
                temperature=0.3
            )
            
            # Parse response
            try:
                comparison_data = json.loads(response)
                
                return TopperComparisonResult(
                    similarity_score=comparison_data.get("similarity_score", similarity_score * 10),
                    topper_reference_id=best_match.get("topper_id"),
                    topper_name=best_match.get("topper_name", "Top Performer"),
                    structure_comparison={"quality": "high", "contextual": True},
                    content_approach_comparison={"relevance": "high"},
                    writing_style_comparison={"similarity": similarity_score},
                    example_usage_comparison={"contextual": True},
                    topper_strengths_identified=comparison_data.get("topper_strengths_identified", []),
                    missing_topper_techniques=comparison_data.get("missing_topper_techniques", []),
                    specific_improvements=comparison_data.get("specific_improvements", []),
                    topper_inspired_suggestions=comparison_data.get("specific_improvements", [])
                )
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse contextual comparison JSON, using structured fallback")
                return TopperComparisonResult(
                    similarity_score=similarity_score * 10,
                    topper_name=best_match.get("topper_name", "Top Performer"),
                    structure_comparison={},
                    content_approach_comparison={},
                    writing_style_comparison={},
                    example_usage_comparison={},
                    topper_strengths_identified=[
                        f"Clear structure similar to {best_match.get('topper_name', 'top performer')}",
                        "Contextual examples and evidence",
                        "Balanced analytical approach"
                    ],
                    missing_topper_techniques=[
                        "More specific examples like the topper used",
                        "Stronger analytical framework",
                        "Better conclusion technique"
                    ],
                    specific_improvements=[
                        f"Study {best_match.get('topper_name', 'this topper')}'s approach to similar questions",
                        "Develop more structured argument flow"
                    ],
                    topper_inspired_suggestions=[
                        "Focus on evidence-based reasoning",
                        "Improve transition between points"
                    ]
                )
                
        except Exception as e:
            logger.error(f"Error generating contextual comparison: {e}")
            # Return meaningful result even if LLM fails
            return TopperComparisonResult(
                similarity_score=similarity_score * 10,
                topper_name=best_match.get("topper_name", "Top Performer"),
                structure_comparison={},
                content_approach_comparison={},
                writing_style_comparison={},
                example_usage_comparison={},
                topper_strengths_identified=[
                    f"Learned from {best_match.get('topper_name', 'high-performing')} answer pattern",
                    "Contextually relevant comparison available"
                ],
                missing_topper_techniques=[
                    "Study the matched topper's specific approach",
                    "Improve structural organization"
                ],
                specific_improvements=[
                    f"Compare your approach with {best_match.get('topper_name', 'this performer')}'s method",
                    "Focus on the techniques that made this answer successful"
                ],
                topper_inspired_suggestions=[
                    "Adopt successful answer patterns",
                    "Focus on contextual relevance"
                ]
            )
        

    
    async def _generic_topper_comparison(self, 
                                       student_answer: str, 
                                       question: str, 
                                       subject: str, 
                                       marks: int) -> TopperComparisonResult:
        """
        Generic topper comparison when no specific topper content is available
        """
        
        generic_prompt = f"""Based on general UPSC topper answer patterns, analyze this student answer:

Question: {question}
Student Answer: {student_answer}

Provide topper-inspired feedback based on common high-scoring patterns:

{{
    "similarity_score": 6.0,
    "topper_strengths_identified": [
        "Common strengths found in topper answers for this type of question"
    ],
    "missing_topper_techniques": [
        "Common techniques toppers use that student hasn't employed"
    ],
    "specific_improvements": [
        "Improvements based on general topper patterns"
    ],
    "topper_inspired_suggestions": [
        "Suggestions based on how toppers typically approach such questions"
    ]
}}"""

        try:
            response = await self.llm_service.simple_chat(
                user_message=generic_prompt,
                temperature=0.3
            )
            
            data = json.loads(response)
            
            return TopperComparisonResult(
                similarity_score=data.get("similarity_score", 6.0),
                topper_reference_id=None,
                topper_name="General Topper Patterns",
                structure_comparison={"analysis": "Based on general topper patterns"},
                content_approach_comparison={"analysis": "Compared with typical topper approaches"},
                writing_style_comparison={"analysis": "Assessed against topper writing standards"},
                example_usage_comparison={"analysis": "Evaluated using topper example patterns"},
                topper_strengths_identified=data.get("topper_strengths_identified", []),
                missing_topper_techniques=data.get("missing_topper_techniques", []),
                specific_improvements=data.get("specific_improvements", []),
                topper_inspired_suggestions=data.get("topper_inspired_suggestions", [])
            )
            
        except:
            return self._create_fallback_generic_comparison()
    
    async def _fallback_comparison(self, 
                                 best_match: Dict, 
                                 student_answer: str) -> TopperComparisonResult:
        """Fallback comparison when parsing fails"""
        
        return TopperComparisonResult(
            similarity_score=6.5,
            topper_reference_id=best_match.get('topper_id'),
            topper_name=best_match.get('topper_name', 'Top Performer'),
            structure_comparison={"analysis": f"Compared with {best_match.get('topper_name', 'topper')}'s structured approach"},
            content_approach_comparison={"analysis": "Content depth comparison with topper answer"},
            writing_style_comparison={"analysis": "Writing style assessed against topper standards"},
            example_usage_comparison={"analysis": "Example usage compared with topper patterns"},
            topper_strengths_identified=[
                f"{best_match.get('topper_name', 'This topper')}'s clear structure and comprehensive coverage",
                "Strategic use of examples and current affairs",
                "Analytical depth and evaluative approach"
            ],
            missing_topper_techniques=[
                "Could adopt topper's introduction technique",
                "Consider topper's use of multiple perspectives",
                "Implement topper's conclusion strategy"
            ],
            specific_improvements=[
                f"Study {best_match.get('topper_name', 'this topper')}'s approach to similar questions",
                "Enhance structural organization following topper patterns",
                "Integrate more analytical elements as done by toppers"
            ],
            topper_inspired_suggestions=[
                f"Emulate {best_match.get('topper_name', 'this topper')}'s balanced approach",
                "Adopt similar example-to-analysis ratio",
                "Use topper-style forward-looking conclusions"
            ]
        )
    
    def _create_fallback_generic_comparison(self) -> TopperComparisonResult:
        """Create fallback comparison when all else fails"""
        
        return TopperComparisonResult(
            similarity_score=6.0,
            topper_reference_id=None,
            topper_name="UPSC Toppers",
            structure_comparison={"analysis": "Structure assessed against general topper standards"},
            content_approach_comparison={"analysis": "Content approach compared with topper patterns"},
            writing_style_comparison={"analysis": "Writing evaluated against topper benchmarks"},
            example_usage_comparison={"analysis": "Examples compared with topper usage patterns"},
            topper_strengths_identified=[
                "Clear conceptual understanding and structured presentation",
                "Strategic use of examples and contemporary relevance",
                "Analytical depth with evaluative conclusions"
            ],
            missing_topper_techniques=[
                "Could enhance introduction with topper-style hook",
                "Consider multiple perspective analysis like toppers",
                "Strengthen conclusion with forward-looking statements"
            ],
            specific_improvements=[
                "Adopt topper-style paragraph organization",
                "Enhance analytical depth following topper patterns",
                "Integrate more strategic example placement"
            ],
            topper_inspired_suggestions=[
                "Emulate topper balance of facts and analysis",
                "Adopt topper approach to current affairs integration",
                "Use topper-style connecting phrases and transitions"
            ]
        )
    
    async def create_topper_analysis_dimension(self,
                                             comparison_result: TopperComparisonResult,
                                             question: str) -> TopperAnalysisDimension:
        """
        Create the 14th dimension analysis based on topper comparison
        """
        
        # Calculate score based on similarity and improvement potential
        # Handle None similarity_score to prevent NoneType arithmetic errors
        similarity_score = comparison_result.similarity_score if comparison_result.similarity_score is not None else 6.0
        base_score = min(similarity_score, 10.0) if similarity_score is not None else 6.0
        
        # Ensure base_score is never None
        if base_score is None:
            base_score = 6.0
        
        # Adjust score based on number of missing techniques (room for improvement)
        missing_count = len(comparison_result.missing_topper_techniques) if comparison_result.missing_topper_techniques else 0
        improvement_potential = max(0, 10 - base_score)
        
        # Final score considers both current performance and learning from toppers
        final_score = base_score + (improvement_potential * 0.3 if missing_count <= 3 else improvement_potential * 0.1)
        final_score = min(final_score, 10.0)
        
        # Create enhanced specific feedback using LLM for detailed analysis
        feedback = await self._generate_enhanced_topper_feedback(
            comparison_result, question, final_score
        )
        
        return TopperAnalysisDimension(
            score=f"{final_score:.1f}/10",
            feedback=feedback,
            comparison_result=comparison_result,
            topper_techniques_to_adopt=comparison_result.missing_topper_techniques,
            specific_examples_to_study=[
                f"Study how {comparison_result.topper_name or 'toppers'} handle similar questions",
                "Analyze topper's introduction and conclusion techniques",
                "Observe topper's integration of examples with analysis"
            ],
            writing_patterns_to_emulate=[
                "Adopt topper's structured paragraph organization",
                "Emulate topper's analytical language patterns",
                "Follow topper's balanced fact-to-analysis ratio"
            ],
            structural_improvements=comparison_result.specific_improvements
        )
    
    async def _generate_enhanced_topper_feedback(self, 
                                               comparison_result: TopperComparisonResult,
                                               question: str,
                                               final_score: float) -> str:
        """Generate specific, detailed feedback using LLM analysis with rate limiting"""
        
        if not comparison_result.topper_name or comparison_result.topper_name == "General Topper Patterns":
            # Fallback to generic feedback if no specific topper
            return f"""Topper Comparison: {final_score:.1f}/10 - Your answer shows good foundation but can significantly benefit from topper patterns. Key areas for improvement: {', '.join(comparison_result.missing_topper_techniques[:2]) if comparison_result.missing_topper_techniques else 'strengthen structure and depth'}."""
        
        # Create specific feedback based on actual topper comparison
        prompt = f"""Create a concise, specific topper comparison feedback based on this analysis:

Topper: {comparison_result.topper_name}
Score: {final_score:.1f}/10
Question Type: {question[:100]}...

Key Missing Techniques:
{chr(10).join(['• ' + technique for technique in (comparison_result.missing_topper_techniques[:3] or ['No specific techniques identified'])])}

Topper's Strengths to Adopt:
{chr(10).join(['• ' + strength for strength in (comparison_result.topper_strengths_identified[:2] or ['No specific strengths identified'])])}

Specific Improvements:
{chr(10).join(['• ' + improvement for improvement in (comparison_result.specific_improvements[:2] or ['No specific improvements identified'])])}

Create a 2-3 sentence feedback in this exact format:
"Topper Comparison: [Score]/10 - Your answer scores [score] when compared with [Topper Name]'s approach. [Specific analysis of what topper does better]. [Specific actionable improvements student should adopt]."

Be specific about what the topper does differently and provide actionable advice. Limit to 150 words maximum."""

        try:
            # Import rate limit handler
            from app.utils.rate_limit_handler import rate_limit_handler
            
            response = await rate_limit_handler.execute_with_backoff(
                self.llm_service.simple_chat,
                user_message=prompt,
                temperature=0.3
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating enhanced feedback: {e}")
            # Fallback to more detailed generic feedback
            return f"""Topper Comparison: {final_score:.1f}/10 - Compared with {comparison_result.topper_name}'s approach, your answer demonstrates good foundational understanding but can be enhanced. Key techniques to adopt: {', '.join(comparison_result.missing_topper_techniques[:2]) if comparison_result.missing_topper_techniques else 'structured analysis and comprehensive coverage'}. Focus on {', '.join(comparison_result.specific_improvements[:2]) if comparison_result.specific_improvements else 'strengthening depth and examples'}."""

# Global instance
topper_analysis_service = TopperAnalysisService()
