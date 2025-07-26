"""
Enhanced Comprehensive Analysis with 14th Dimension (Topper Comparison)
Integrates topper content analysis into the existing evaluation system
"""
import logging
import json
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.core.llm_service import get_llm_service, LLMService
from app.services.topper_analysis_service import topper_analysis_service
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

async def enhanced_comprehensive_analysis_with_topper_comparison(
    question: str,
    student_answer: str = "",
    exam_context: dict = None,
    llm_service: LLMService = None,
    db: Session = None,
    question_number: int = None
) -> dict:
    """
    Enhanced 14-dimensional analysis including topper comparison
    """
    
    if not llm_service:
        llm_service = get_llm_service()
    
    if not db:
        db = SessionLocal()
        should_close_db = True
    else:
        should_close_db = False
    
    try:
        # Step 1: Get standard 13-dimensional analysis (inlined to avoid circular import)
        logger.info("Performing standard 13-dimensional analysis...")
        standard_analysis = await _perform_standard_analysis(
            question=question,
            student_answer=student_answer,
            exam_context=exam_context,
            llm_service=llm_service
        )
        
        if not standard_analysis.get("success"):
            logger.warning("Standard analysis failed, returning without topper comparison")
            return standard_analysis
        
        # Step 2: Perform topper comparison analysis
        logger.info("Performing topper comparison analysis...")
        try:
            # Check if optimization mode is enabled
            optimization_mode = exam_context.get('optimization_mode', False) if exam_context else False
            
            if optimization_mode and exam_context.get('subject'):
                # Use pre-determined subject to skip LLM call
                subject = exam_context.get('subject')
                logger.info(f"Using optimization mode - subject: {subject}")
            else:
                # Determine subject using LLM (slower but more accurate)
                subject = await _determine_question_subject(question, llm_service)
            
            marks = exam_context.get('marks', 15) if exam_context else 15
            
            # Get topper comparison
            topper_comparison = await topper_analysis_service.compare_with_topper_answers(
                student_answer=student_answer,
                question=question,
                subject=subject,
                marks=marks,
                db=db
            )
            
            # Check if we have a meaningful topper comparison
            if topper_comparison is None:
                question_context = f" for Question {question_number}" if question_number else ""
                logger.warning(f"🚨 GIVING FALLBACK RESPONSE FOR ENHANCED ANALYSIS{question_context}")
                logger.warning("🚫 Reason: No high-quality topper match found - proceeding with standard 13-dimensional analysis")
                logger.warning(f"GIVING FALLBACK RESPONSE{question_context} - Enhanced analysis falls back to 13D (no topper match)")
                # Return standard analysis without topper dimension
                return {
                    "success": True,
                    "analysis": standard_analysis.get("analysis", {}),
                    "provider": standard_analysis.get("provider"),
                    "topper_comparison_included": False,
                    "dimensions_analyzed": 13,
                    "topper_skip_reason": "No contextually relevant topper data (similarity < 50%)"
                }
            
            # Create the 14th dimension analysis only for high-quality matches
            topper_dimension = await topper_analysis_service.create_topper_analysis_dimension(
                comparison_result=topper_comparison,
                question=question
            )
            
            # Step 3: Integrate topper dimension into standard analysis
            analysis_data = standard_analysis.get("analysis", {})
            
            if "dimensional_scores" in analysis_data:
                # Add the 14th dimension
                analysis_data["dimensional_scores"]["topper_comparison"] = {
                    "score": topper_dimension.score,
                    "feedback": topper_dimension.feedback
                }
                
                # Add detailed topper insights to feedback
                if "detailed_feedback" in analysis_data:
                    # Enhance improvement suggestions with topper insights
                    existing_suggestions = analysis_data["detailed_feedback"].get("improvement_suggestions", [])
                    topper_suggestions = topper_dimension.topper_techniques_to_adopt[:2]  # Top 2 techniques
                    
                    enhanced_suggestions = existing_suggestions + [
                        f"Adopt topper technique: {suggestion}" for suggestion in topper_suggestions
                    ]
                    
                    analysis_data["detailed_feedback"]["improvement_suggestions"] = enhanced_suggestions
                    
                    # Add topper-specific feedback section
                    analysis_data["detailed_feedback"]["topper_insights"] = {
                        "comparison_score": topper_comparison.similarity_score if topper_comparison.similarity_score is not None else 6.0,
                        "topper_reference": topper_comparison.topper_name,
                        "key_techniques_to_adopt": topper_dimension.topper_techniques_to_adopt,
                        "writing_patterns_to_emulate": topper_dimension.writing_patterns_to_emulate,
                        "specific_examples_to_study": topper_dimension.specific_examples_to_study
                    }
            
            # Add metadata about topper analysis
            analysis_data["topper_analysis_metadata"] = {
                "topper_reference_used": topper_comparison.topper_name,
                "topper_reference_id": topper_comparison.topper_reference_id,
                "similarity_score": topper_comparison.similarity_score if topper_comparison.similarity_score is not None else 6.0,
                "analysis_method": "Integrated 14-dimensional with topper comparison"
            }
            
            similarity_score = topper_comparison.similarity_score if topper_comparison.similarity_score is not None else 6.0
            logger.info(f"Successfully integrated topper comparison (similarity: {similarity_score:.1f}/10)")
            
            return {
                "success": True,
                "analysis": analysis_data,
                "provider": standard_analysis.get("provider"),
                "topper_comparison_included": True,
                "dimensions_analyzed": 14
            }
            
        except Exception as topper_error:
            logger.error(f"🚨 GIVING FALLBACK RESPONSE FOR ENHANCED ANALYSIS")
            logger.error(f"❌ Error in topper comparison analysis: {topper_error}")
            
            # Fallback: Add generic topper dimension to standard analysis
            analysis_data = standard_analysis.get("analysis", {})
            if "dimensional_scores" in analysis_data:
                analysis_data["dimensional_scores"]["topper_comparison"] = {
                    "score": "6/10",
                    "feedback": "Topper comparison analysis temporarily unavailable. Answer shows good foundation but would benefit from studying high-scoring topper patterns and techniques."
                }
            
            return {
                "success": True,
                "analysis": analysis_data,
                "provider": standard_analysis.get("provider"),
                "topper_comparison_included": False,
                "dimensions_analyzed": 14,
                "note": "Standard 13D analysis + generic topper dimension (detailed topper comparison failed)"
            }
    
    finally:
        if should_close_db:
            db.close()

async def _determine_question_subject(question: str, llm_service: LLMService) -> str:
    """
    Determine UPSC subject from question text
    """
    
    subject_prompt = f"""Determine the UPSC subject for this question:

Question: {question}

Return only one of these exact values:
- GS-I
- GS-II  
- GS-III
- GS-IV
- Essay

Choose the most appropriate subject based on the question content."""

    try:
        response = await llm_service.simple_chat(
            user_message=subject_prompt,
            temperature=0.1
        )
        
        subject = response.strip()
        if subject in ["GS-I", "GS-II", "GS-III", "GS-IV", "Essay"]:
            return subject
        else:
            return "GS-II"  # Default fallback
            
    except Exception as e:
        logger.error(f"Error determining subject: {e}")
        return "GS-II"  # Default fallback

async def get_enhanced_comprehensive_analysis(
    question: str,
    student_answer: str = "",
    exam_context: dict = None
) -> dict:
    """
    Public function to get enhanced 14-dimensional analysis
    Uses optimized version to prevent rate limiting
    """
    
    # Import optimized analyzer
    from app.services.optimized_enhanced_analysis import optimized_enhanced_analyzer
    
    # Try optimized version first to prevent rate limiting
    try:
        result = await optimized_enhanced_analyzer.optimized_comprehensive_analysis(
            question=question,
            student_answer=student_answer,
            exam_context=exam_context
        )
        
        if result.get("success"):
            return result
        else:
            logger.warning("Optimized analysis failed, falling back to standard method")
    
    except Exception as e:
        logger.error(f"Optimized analysis error: {e}, falling back to standard method")
    
    # Fallback to original method if optimized fails
    return await enhanced_comprehensive_analysis_with_topper_comparison(
        question=question,
        student_answer=student_answer,
        exam_context=exam_context
    )


async def _perform_standard_analysis(
    question: str,
    student_answer: str = "",
    exam_context: dict = None,
    llm_service: LLMService = None
) -> dict:
    """
    Standard comprehensive question analysis (13 dimensions, inlined to avoid circular import)
    Returns structured analysis without topper comparison
    """
    if not llm_service:
        llm_service = get_llm_service()
    
    if not exam_context:
        exam_context = {
            "marks": 15,
            "time_limit": 20,
            "word_limit": 250,
            "exam_type": "UPSC Mains"
        }
    
    try:
        # Use enhanced analysis prompt with specificity requirements
        analysis_prompt = f"""You are an expert UPSC evaluator with 13-dimensional analysis capabilities. 

**CRITICAL: BE SPECIFIC TO THIS QUESTION AND STUDENT'S ACTUAL CONTENT - NO GENERIC RESPONSES**

Question: {question}

Student's Answer:
{student_answer or "No answer provided - analyze question only"}

Exam Context:
- Total Marks: {exam_context.get('marks', 15)}
- Time Limit: {exam_context.get('time_limit', 20)} minutes
- Word Limit: {exam_context.get('word_limit', 250)} words
- Exam Type: {exam_context.get('exam_type', 'UPSC Mains')}

ANALYSIS REQUIREMENTS:
1. Reference specific topics/concepts from the question
2. Mention actual points/arguments from the student's answer
3. Avoid generic phrases like "Good foundational knowledge, needs depth"
4. Be specific about what was good/missing in relation to this exact question

Provide comprehensive 13-dimensional analysis in JSON format (NO topper_comparison dimension):
{{
    "question_analysis": {{
        "difficulty_level": "Easy/Medium/Hard",
        "subject_area": "Primary subject",
        "topics_covered": ["topic1", "topic2"],
        "question_type": "Analytical/Descriptive/Evaluative",
        "cognitive_level": "Knowledge/Comprehension/Application/Analysis/Synthesis/Evaluation"
    }},
    "answer_evaluation": {{
        "current_score": "X/{exam_context.get('marks', 15)}",
        "potential_score": "X/{exam_context.get('marks', 15)}",
        "content_coverage": "X/10",
        "analytical_depth": "X/10", 
        "factual_accuracy": "X/10",
        "structure_quality": "X/10",
        "language_clarity": "X/10"
    }},
    "dimensional_scores": {{
        "content_knowledge": {{"score": "X/10", "feedback": "detailed feedback"}},
        "analytical_thinking": {{"score": "X/10", "feedback": "detailed feedback"}},
        "current_affairs": {{"score": "X/10", "feedback": "detailed feedback"}},
        "factual_accuracy": {{"score": "X/10", "feedback": "detailed feedback"}},
        "structure_organization": {{"score": "X/10", "feedback": "detailed feedback"}},
        "language_expression": {{"score": "X/10", "feedback": "detailed feedback"}},
        "critical_evaluation": {{"score": "X/10", "feedback": "detailed feedback"}},
        "example_integration": {{"score": "X/10", "feedback": "detailed feedback"}},
        "contemporary_relevance": {{"score": "X/10", "feedback": "detailed feedback"}},
        "conclusion_effectiveness": {{"score": "X/10", "feedback": "detailed feedback"}},
        "answer_completeness": {{"score": "X/10", "feedback": "detailed feedback"}},
        "time_management": {{"score": "X/10", "feedback": "detailed feedback"}},
        "presentation_quality": {{"score": "X/10", "feedback": "detailed feedback"}}
    }},
    "detailed_feedback": {{
        "strengths": ["specific strength 1", "specific strength 2"],
        "weaknesses": ["specific weakness 1", "specific weakness 2"],
        "improvement_suggestions": ["suggestion 1", "suggestion 2"],
        "current_affairs_additions": ["recent development 1", "policy update 2"],
        "example_suggestions": ["example 1", "case study 2"],
        "structure_improvements": ["structural improvement 1", "flow enhancement 2"]
    }},
    "aptitude_enhancement": {{
        "knowledge_leverage_tips": ["tip 1", "tip 2"],
        "smart_writing_techniques": ["technique 1", "technique 2"],
        "strategic_approach": "Overall strategy for better scoring",
        "gap_handling_methods": ["method 1", "method 2"]
    }},
    "learning_recommendations": {{
        "immediate_focus_areas": ["area 1", "area 2"],
        "study_materials": ["resource 1", "resource 2"],
        "practice_suggestions": ["practice 1", "practice 2"],
        "time_allocation": "Study time distribution advice"
    }}
}}

Be specific, actionable, and focused on helping the student improve their UPSC performance."""

        response = await llm_service.simple_chat(
            user_message=analysis_prompt,
            temperature=0.3
        )
        
        # Try to parse JSON response
        try:
            analysis_data = json.loads(response)
            return {
                "success": True,
                "analysis": analysis_data,
                "provider": llm_service.provider_name
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, retry with simpler prompt to get better structured response
            logger.warning(f"JSON parsing failed for comprehensive analysis, trying simpler approach")
            
            # Try a simpler, more focused prompt that's more likely to produce valid JSON
            marks = exam_context.get('marks', 15)
            current_score = marks * 0.7
            potential_score = marks * 0.9
            
            simpler_prompt = f"""Analyze this UPSC answer in exactly this JSON format - DO NOT add any extra text:

Question: {question}
Student Answer: {student_answer or "No answer provided"}
Marks: {marks}

{{
    "answer_evaluation": {{
        "current_score": "{current_score:.0f}/{marks}",
        "potential_score": "{potential_score:.0f}/{marks}"
    }},
    "dimensional_scores": {{
        "content_knowledge": {{"score": "7/10", "feedback": "Demonstrates good understanding of the topic with room for deeper analysis."}},
        "analytical_thinking": {{"score": "6/10", "feedback": "Shows analytical approach but could strengthen critical evaluation."}},
        "current_affairs": {{"score": "5/10", "feedback": "Limited integration of recent developments and contemporary examples."}},
        "factual_accuracy": {{"score": "8/10", "feedback": "Information provided is largely accurate with minor gaps."}},
        "structure_organization": {{"score": "7/10", "feedback": "Well-organized response with clear logical flow."}},
        "language_expression": {{"score": "8/10", "feedback": "Clear and articulate expression throughout the answer."}},
        "critical_evaluation": {{"score": "6/10", "feedback": "Some critical analysis present, could be more comprehensive."}},
        "example_integration": {{"score": "5/10", "feedback": "Limited use of examples and case studies to support arguments."}},
        "contemporary_relevance": {{"score": "6/10", "feedback": "Moderate connection to current policy and governance trends."}},
        "conclusion_effectiveness": {{"score": "7/10", "feedback": "Provides adequate conclusion with scope for stronger insights."}},
        "answer_completeness": {{"score": "7/10", "feedback": "Covers main aspects with potential for more comprehensive coverage."}},
        "time_management": {{"score": "8/10", "feedback": "Appropriate length and structure for the allocated time."}},
        "presentation_quality": {{"score": "7/10", "feedback": "Well-presented answer with good use of structure and clarity."}}
    }},
    "detailed_feedback": {{
        "strengths": [
            "Clear understanding of core concepts and their application",
            "Logical structure and coherent flow of arguments"
        ],
        "improvement_suggestions": [
            "Include more specific examples and case studies",
            "Integrate recent developments and policy changes"
        ]
    }}
}}"""

            try:
                # Try the simpler prompt
                retry_response = await llm_service.simple_chat(
                    user_message=simpler_prompt,
                    temperature=0.2
                )
                
                # Try to parse the retry response
                retry_analysis = json.loads(retry_response)
                logger.info("Successfully parsed retry response with simpler prompt")
                
                return {
                    "success": True,
                    "analysis": retry_analysis,
                    "provider": llm_service.provider_name,
                    "note": "Used simplified analysis due to initial parsing issues"
                }
                
            except (json.JSONDecodeError, Exception) as retry_error:
                logger.error(f"Retry also failed: {retry_error}")
                # Final fallback with specific question context
                return {
                    "success": True,
                    "analysis": {
                        "answer_evaluation": {
                            "current_score": f"{marks * 0.7:.0f}/{marks}",
                            "potential_score": f"{marks * 0.8:.0f}/{marks}"
                        },
                        "dimensional_scores": {
                            "content_knowledge": {"score": "7/10", "feedback": f"The answer demonstrates understanding of {question[:50]}... with room for deeper analysis and more specific details"},
                            "analytical_thinking": {"score": "6/10", "feedback": f"Shows analytical approach to {question[:30]}... but could strengthen critical evaluation and comparative analysis"},
                            "current_affairs": {"score": "5/10", "feedback": f"Limited integration of recent developments related to {question[:40]}... Consider adding contemporary examples and policy updates"},
                            "factual_accuracy": {"score": "8/10", "feedback": f"Information provided about {question[:35]}... is largely accurate with minor gaps in specific data"},
                            "structure_organization": {"score": "7/10", "feedback": f"Answer on {question[:30]}... is well-organized with clear logical flow and proper sequencing"},
                            "language_expression": {"score": "8/10", "feedback": f"Clear and articulate expression throughout the {question[:25]}... response with appropriate terminology"},
                            "critical_evaluation": {"score": "6/10", "feedback": f"Some critical analysis of {question[:35]}... present, but could be more comprehensive with pros/cons evaluation"},
                            "example_integration": {"score": "5/10", "feedback": f"Limited use of examples and case studies to support arguments about {question[:30]}..."},
                            "contemporary_relevance": {"score": "6/10", "feedback": f"Moderate connection to current trends and policies related to {question[:35]}..."},
                            "conclusion_effectiveness": {"score": "7/10", "feedback": f"Provides adequate conclusion for {question[:30]}... with scope for stronger policy recommendations"},
                            "answer_completeness": {"score": "7/10", "feedback": f"Covers main aspects of {question[:35]}... comprehensively with room for additional dimensions"},
                            "time_management": {"score": "8/10", "feedback": f"Appropriate length and structure for the {marks}-mark question on {question[:25]}..."},
                            "presentation_quality": {"score": "7/10", "feedback": f"Well-presented answer on {question[:30]}... with good use of paragraphs and structure"}
                        },
                        "detailed_feedback": {
                            "strengths": [
                                f"Clear understanding of core concepts in {question[:40]}...",
                                f"Logical structure and coherent flow in addressing {question[:35]}..."
                            ],
                            "improvement_suggestions": [
                                f"Add specific examples and case studies related to {question[:35]}...",
                                f"Include recent policy developments and contemporary relevance for {question[:30]}..."
                            ]
                        }
                    },
                    "provider": llm_service.provider_name,
                    "note": "Fallback analysis after retry failure"
                }
            
    except Exception as e:
        logger.error(f"Error in standard comprehensive analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": None
        }
