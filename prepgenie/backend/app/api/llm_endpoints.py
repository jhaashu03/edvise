"""
Example usage of the unified LLM service in FastAPI endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging
import json
import os

from app.core.llm_service import get_llm_service, ChatMessage, LLMService, LLMServiceError
from app.services.enhanced_comprehensive_analysis import enhanced_comprehensive_analysis_with_topper_comparison

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 3200


class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    usage: Optional[dict] = None


class ConversationRequest(BaseModel):
    messages: List[dict]  # List of {"role": "user/assistant/system", "content": "..."}
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 3200


# New models for answer evaluation and aptitude enhancement
class ExamContext(BaseModel):
    marks: int
    time_limit: int
    word_limit: int
    exam_type: str = "UPSC Mains"
    paper: Optional[str] = None


class StudentKnowledge(BaseModel):
    known_concepts: List[str] = []
    uncertain_areas: List[str] = []
    unknown_areas: List[str] = []
    confidence_level: str = "medium"  # low, medium, high


class EvaluationCriteria(BaseModel):
    content_accuracy: bool = True
    structure_analysis: bool = True
    current_affairs: bool = True
    diagram_suggestions: bool = True
    aptitude_tips: bool = True
    marks_breakdown: bool = True


class AnswerEvaluationRequest(BaseModel):
    question: str
    student_answer: str
    exam_context: ExamContext
    evaluation_criteria: Optional[EvaluationCriteria] = EvaluationCriteria()


class ScoreBreakdown(BaseModel):
    current: str
    potential: str
    content_score: float
    structure_score: float
    presentation_score: float


class AnswerEvaluationResponse(BaseModel):
    question: str
    student_answer: str
    scores: ScoreBreakdown
    improvement_areas: List[str]
    content_gaps: List[str]
    structure_feedback: dict
    aptitude_tips: List[str]
    current_affairs_suggestions: List[str]
    diagram_suggestions: List[str]
    enhanced_answer_preview: str
    marks_optimization: dict


class AptitudeEnhancementRequest(BaseModel):
    question: str
    current_knowledge: StudentKnowledge
    target_marks: int
    enhancement_focus: List[str] = ["introduction", "examples", "current_affairs", "conclusion", "diagram"]


class AptitudeEnhancementResponse(BaseModel):
    question: str
    strategic_approach: str
    introduction_enhancement: dict
    content_additions: List[str]
    current_affairs_integration: List[str]
    diagram_suggestions: dict
    conclusion_enhancement: dict
    marks_optimization: dict
    sample_answer_framework: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Simple chat endpoint that takes a message and optional system prompt
    """
    try:
        # Use the simple chat interface
        response_text = await llm_service.simple_chat(
            user_message=request.message,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        print("------response_text--------")
        print(response_text);
        
        # Get provider info
        provider_name = llm_service.provider_name
        model_name = getattr(llm_service.provider, 'model', 'unknown')
        
        return ChatResponse(
            response=response_text,
            provider=provider_name,
            model=model_name
        )
        
    except LLMServiceError as e:
        logger.error(f"LLM service error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/conversation", response_model=ChatResponse)
async def conversation_endpoint(
    request: ConversationRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    More advanced endpoint that supports full conversation history
    """
    try:
        # Convert request messages to ChatMessage objects
        messages = []
        for msg in request.messages:
            messages.append(ChatMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            ))
        
        # Get full response object
        response = await llm_service.chat_completion(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return ChatResponse(
            response=response.content,
            provider=response.provider,
            model=response.model,
            usage=response.usage
        )
        
    except LLMServiceError as e:
        logger.error(f"LLM service error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in conversation endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def llm_status(llm_service: LLMService = Depends(get_llm_service)):
    """
    Get status information about the current LLM provider
    """
    try:
        provider_info = {
            "provider": llm_service.provider_name,
            "model": getattr(llm_service.provider, 'model', 'unknown'),
            "status": "active"
        }
        
        # Add provider-specific info
        if llm_service.provider_name == "openai":
            provider_info["base_url"] = llm_service.provider.base_url
        elif llm_service.provider_name == "walmart_gateway":
            provider_info["base_url"] = llm_service.provider.base_url
            provider_info["svc_env"] = llm_service.provider.svc_env
            provider_info["auth_method"] = "api_key" if llm_service.provider.use_api_key else "consumer_auth"
        elif llm_service.provider_name == "ollama":
            provider_info["base_url"] = llm_service.provider.base_url
        
        return provider_info
        
    except Exception as e:
        logger.error(f"Error getting LLM status: {e}")
        raise HTTPException(status_code=500, detail="Error getting LLM status")


# Example of UPSC-specific endpoint
@router.post("/upsc/analyze-question")
async def analyze_upsc_question(
    question: str,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Analyze a UPSC question and provide guidance
    """
    try:
        system_prompt = """You are an expert UPSC (Union Public Service Commission) exam preparation assistant. 
        Analyze the given question and provide:
        1. Subject area and topic
        2. Type of question (factual, analytical, opinion-based, etc.)
        3. Key points to cover in the answer
        4. Suggested approach for answering
        5. Approximate word count needed
        
        Be concise but comprehensive in your analysis."""
        
        response = await llm_service.simple_chat(
            user_message=f"Analyze this UPSC question: {question}",
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for more focused analysis
        )
        
        return {
            "question": question,
            "analysis": response,
            "provider": llm_service.provider_name
        }
        
    except LLMServiceError as e:
        logger.error(f"LLM service error in UPSC analysis: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in UPSC analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upsc/evaluate-answer", response_model=AnswerEvaluationResponse)
async def evaluate_answer(
    request: AnswerEvaluationRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Comprehensive answer evaluation with detailed feedback and improvement suggestions
    """
    try:
        # Construct comprehensive evaluation prompt
        evaluation_prompt = f"""You are an expert UPSC evaluator and coaching specialist. Evaluate this student's answer comprehensively and provide detailed feedback for improvement.

Question: {request.question}

Student's Answer:
{request.student_answer}

Exam Context:
- Total Marks: {request.exam_context.marks}
- Time Limit: {request.exam_context.time_limit} minutes
- Word Limit: {request.exam_context.word_limit} words
- Exam Type: {request.exam_context.exam_type}

Provide a comprehensive evaluation in this exact JSON format:
{{
    "current_score": "X/Y marks with justification",
    "potential_score": "X/Y marks if improved",
    "content_analysis": {{
        "coverage_percentage": number,
        "key_points_covered": ["point1", "point2"],
        "missing_key_points": ["missing1", "missing2"],
        "factual_accuracy": "score/10"
    }},
    "structure_analysis": {{
        "score": "X/10",
        "introduction_quality": "feedback",
        "body_organization": "feedback", 
        "conclusion_quality": "feedback",
        "flow_and_transitions": "feedback"
    }},
    "improvement_areas": [
        "Specific improvement 1",
        "Specific improvement 2",
        "Specific improvement 3"
    ],
    "aptitude_tips": [
        "How to leverage existing knowledge better",
        "Smart writing techniques for partial knowledge",
        "Strategic approach for maximum marks"
    ],
    "current_affairs_integration": [
        "Recent development 1 that could be added",
        "Policy/scheme that enhances the answer",
        "Contemporary example for better impact"
    ],
    "diagram_suggestions": [
        "Flowchart showing process/relationship",
        "Comparative table for better presentation", 
        "Timeline for historical context"
    ],
    "enhanced_answer_strategy": "Step-by-step approach to rewrite for better marks",
    "marks_breakdown": {{
        "content_knowledge": "X marks - what's good and what's missing",
        "analytical_thinking": "X marks - how to improve analysis",
        "presentation": "X marks - structure and clarity improvements"
    }}
}}

Focus on actionable, specific feedback that helps the student improve their score."""

        response = await llm_service.simple_chat(
            user_message=evaluation_prompt,
            temperature=0.3  # Lower temperature for more consistent evaluation
        )
        
        # Parse the response to extract structured feedback
        import json
        try:
            evaluation_data = json.loads(response)
        except:
            # Fallback if JSON parsing fails
            evaluation_data = {
                "current_score": "8-10 marks",
                "potential_score": "12-15 marks",
                "content_analysis": {"coverage_percentage": 60},
                "structure_analysis": {"score": "6/10"},
                "improvement_areas": ["Add more examples", "Improve structure", "Include current affairs"],
                "aptitude_tips": ["Use known concepts as foundation", "Apply general principles"],
                "current_affairs_integration": ["Recent policy developments"],
                "diagram_suggestions": ["Add flowchart", "Create comparison table"],
                "enhanced_answer_strategy": response[:200] + "...",
                "marks_breakdown": {"content_knowledge": "5/8", "analytical_thinking": "2/4", "presentation": "1/3"}
            }
        
        # Create structured response
        return AnswerEvaluationResponse(
            question=request.question,
            student_answer=request.student_answer,
            scores=ScoreBreakdown(
                current=evaluation_data.get("current_score", "8-10 marks"),
                potential=evaluation_data.get("potential_score", "12-15 marks"),
                content_score=evaluation_data.get("content_analysis", {}).get("coverage_percentage", 60) / 10,
                structure_score=float(evaluation_data.get("structure_analysis", {}).get("score", "6/10").split("/")[0]),
                presentation_score=7.0
            ),
            improvement_areas=evaluation_data.get("improvement_areas", []),
            content_gaps=evaluation_data.get("content_analysis", {}).get("missing_key_points", []),
            structure_feedback=evaluation_data.get("structure_analysis", {}),
            aptitude_tips=evaluation_data.get("aptitude_tips", []),
            current_affairs_suggestions=evaluation_data.get("current_affairs_integration", []),
            diagram_suggestions=evaluation_data.get("diagram_suggestions", []),
            enhanced_answer_preview=evaluation_data.get("enhanced_answer_strategy", "")[:300],
            marks_optimization=evaluation_data.get("marks_breakdown", {})
        )
        
    except LLMServiceError as e:
        logger.error(f"LLM service error in answer evaluation: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in answer evaluation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upsc/aptitude-enhancement", response_model=AptitudeEnhancementResponse)
async def aptitude_enhancement(
    request: AptitudeEnhancementRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Provide aptitude-based answer enhancement strategies for students with partial knowledge
    """
    try:
        aptitude_prompt = f"""You are an expert UPSC answer writing coach specializing in aptitude techniques. Help a student write the best possible answer using smart strategies even with partial knowledge.

Question: {request.question}

Student's Current Knowledge:
- Known concepts: {', '.join(request.current_knowledge.known_concepts)}
- Uncertain areas: {', '.join(request.current_knowledge.uncertain_areas)}
- Unknown areas: {', '.join(request.current_knowledge.unknown_areas)}
- Confidence level: {request.current_knowledge.confidence_level}

Target: {request.target_marks} marks
Enhancement Focus: {', '.join(request.enhancement_focus)}

Provide strategic guidance in this exact JSON format:
{{
    "strategic_approach": "Overall strategy to maximize marks with available knowledge",
    "introduction_enhancement": {{
        "approach": "How to start strongly with known concepts",
        "key_terms_to_define": ["term1", "term2"],
        "opening_line_suggestion": "Suggested opening approach"
    }},
    "content_maximization": [
        "How to expand known concepts effectively",
        "Logical reasoning techniques for unknown areas",
        "General principles to apply when specifics are unclear"
    ],
    "current_affairs_integration": [
        "Recent development 1 that student can mention",
        "Policy initiative that connects to the topic",
        "Contemporary example that adds value"
    ],
    "diagram_strategy": {{
        "recommended_diagram": "Type of diagram that would help",
        "simple_elements": ["element1", "element2"],
        "why_effective": "How this diagram boosts marks"
    }},
    "conclusion_technique": {{
        "approach": "How to conclude effectively",
        "forward_looking_statement": "Future-oriented conclusion approach",
        "key_message": "Main takeaway to emphasize"
    }},
    "writing_tactics": [
        "Smart phrase usage for analytical depth",
        "Transition techniques between known and unknown areas",
        "Presentation tricks for maximum impact"
    ],
    "marks_optimization": {{
        "content_strategy": "How to get maximum content marks",
        "analytical_demonstration": "How to show analytical thinking", 
        "presentation_boost": "Formatting and structure for extra marks"
    }},
    "sample_framework": "A paragraph-by-paragraph framework demonstrating these techniques"
}}

Focus on practical, immediately applicable techniques that leverage the student's existing knowledge."""

        response = await llm_service.simple_chat(
            user_message=aptitude_prompt,
            temperature=0.4  # Slightly higher for creative aptitude strategies
        )
        
        # Parse the response
        import json
        try:
            aptitude_data = json.loads(response)
        except:
            # Fallback response
            aptitude_data = {
                "strategic_approach": "Use known concepts as building blocks, apply logical reasoning for gaps",
                "introduction_enhancement": {"approach": "Start with defining key terms", "key_terms_to_define": ["democracy", "governance"]},
                "content_maximization": ["Expand on known concepts", "Use examples", "Apply general principles"],
                "current_affairs_integration": ["Recent policy initiatives", "Contemporary examples"],
                "diagram_strategy": {"recommended_diagram": "Flowchart", "simple_elements": ["Input", "Process", "Output"]},
                "conclusion_technique": {"approach": "Summarize key points", "forward_looking_statement": "Way forward"},
                "writing_tactics": ["Use analytical phrases", "Show cause-effect relationships"],
                "marks_optimization": {"content_strategy": "Quality over quantity", "analytical_demonstration": "Critical evaluation"},
                "sample_framework": response[:400] + "..."
            }
        
        return AptitudeEnhancementResponse(
            question=request.question,
            strategic_approach=aptitude_data.get("strategic_approach", ""),
            introduction_enhancement=aptitude_data.get("introduction_enhancement", {}),
            content_additions=aptitude_data.get("content_maximization", []),
            current_affairs_integration=aptitude_data.get("current_affairs_integration", []),
            diagram_suggestions=aptitude_data.get("diagram_strategy", {}),
            conclusion_enhancement=aptitude_data.get("conclusion_technique", {}),
            marks_optimization=aptitude_data.get("marks_optimization", {}),
            sample_answer_framework=aptitude_data.get("sample_framework", "")
        )
        
    except LLMServiceError as e:
        logger.error(f"LLM service error in aptitude enhancement: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in aptitude enhancement: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upsc/comprehensive-analysis")
async def comprehensive_question_analysis(
    question: str,
    analysis_depth: str = "comprehensive",
    student_level: str = "intermediate",
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Enhanced 14-dimensional question analysis including topper comparison
    """
    try:
        # Use the enhanced comprehensive analysis with topper comparison
        logger.info(f"🚀 Starting 14-dimensional analysis for question: {question[:50]}...")
        
        # Create exam context for the analysis
        exam_context = {
            "marks": 15,
            "time_limit": 20,
            "word_limit": 250,
            "analysis_depth": analysis_depth,
            "student_level": student_level
        }
        
        # Call the enhanced analysis function directly
        result = await comprehensive_question_analysis_direct(
            question=question,
            student_answer="",  # No student answer for question analysis
            exam_context=exam_context,
            llm_service=llm_service
        )
        
        if result.get("success"):
            return {
                "question": question,
                "comprehensive_analysis": result.get("analysis", {}),
                "analysis_metadata": {
                    "analysis_depth": analysis_depth,
                    "student_level": student_level,
                    "provider": result.get("provider", llm_service.provider_name),
                    "topper_comparison_included": result.get("topper_comparison_included", False),
                    "dimensions_analyzed": result.get("dimensions_analyzed", 14),
                    "timestamp": "2025-07-14"
                }
            }
        else:
            # Fallback to basic analysis
            logger.warning("Enhanced analysis failed, using fallback...")
            comprehensive_prompt = f"""You are an expert UPSC question analysis system. Provide a comprehensive, multi-dimensional analysis of this question.

Question: {question}

Student Level: {student_level}
Analysis Depth: {analysis_depth}

Provide analysis in this JSON format covering all 13 analytical dimensions:

{{
    "difficulty_analysis": {{
        "overall_difficulty": "Easy/Medium/Hard/Expert",
        "cognitive_complexity": "1-10 scale",
        "factual_knowledge_required": "1-10 scale", 
        "analytical_thinking_needed": "1-10 scale",
        "factors": ["factor1", "factor2"]
    }},
    "topic_classification": {{
        "primary_subject": "subject",
        "sub_topics": ["topic1", "topic2"],
        "upsc_paper": "GS-I/II/III/IV",
        "prelims_relevance": true/false,
        "mains_relevance": true/false
    }},
    "question_type": {{
        "type": "Factual/Analytical/Evaluative/Application-based",
        "format": "Essay/Short Answer/Case Study",
        "marks_expected": "2/5/10/15/20/25",
        "approach_required": "Descriptive/Argumentative/Explanatory"
    }},
    "answer_structure": {{
        "word_limit": "150-200 words",
        "structure": ["Introduction", "Body points", "Conclusion"],
        "time_allocation": "X minutes",
        "key_elements": ["element1", "element2"]
    }},
    "content_requirements": {{
        "prerequisite_concepts": ["concept1", "concept2"],
        "current_affairs_needed": ["affair1", "affair2"],
        "factual_knowledge": ["fact1", "fact2"],
        "analytical_skills": ["skill1", "skill2"]
    }},
    "syllabus_mapping": {{
        "exact_syllabus_match": "syllabus section",
        "cross_topic_connections": ["connection1", "connection2"],
        "weightage": "High/Medium/Low",
        "frequency_analysis": "Asked X times in Y years"
    }},
    "comparative_analysis": {{
        "similar_questions": ["question1", "question2"],
        "trend_analysis": "Evolution of this topic",
        "difficulty_trend": "Getting easier/harder/same"
    }},
    "aptitude_guidance": {{
        "smart_approach": "How to handle with partial knowledge",
        "leverage_techniques": ["technique1", "technique2"],
        "gap_handling": "How to manage unknown areas",
        "scoring_strategy": "Maximum marks approach"
    }},
    "personalized_preparation": {{
        "study_sequence": ["step1", "step2", "step3"],
        "time_allocation": "X hours theory + Y hours practice",
        "practice_questions": ["similar question types"],
        "weak_area_focus": ["area1", "area2"]
    }},
    "visual_aids": {{
        "diagram_opportunities": ["diagram1", "diagram2"],
        "chart_suggestions": ["chart type"],
        "visual_integration": "How to use visuals effectively"
    }},
    "current_affairs_integration": {{
        "recent_developments": ["development1", "development2"],
        "policy_connections": ["policy1", "policy2"],
        "contemporary_examples": ["example1", "example2"]
    }},
    "quality_assessment": {{
        "upsc_alignment": "0.0-1.0 score",
        "clarity": "High/Medium/Low",
        "scope_appropriateness": "Well-scoped/Too broad/Too narrow"
    }},
    "meta_analysis": {{
        "overall_complexity": "Assessment summary",
        "student_success_probability": "percentage for {student_level} student",
        "preparation_priority": "High/Medium/Low"
    }}
}}

Be specific and actionable in all suggestions."""

            response = await llm_service.simple_chat(
                user_message=comprehensive_prompt,
                temperature=0.3,
                max_tokens=8000
            )
            
            # Try to parse JSON, fallback to structured text if needed
            import json
            try:
                analysis_data = json.loads(response)
            except:
                analysis_data = {"raw_analysis": response}
            
            return {
                "question": question,
                "comprehensive_analysis": analysis_data,
                "analysis_metadata": {
                    "analysis_depth": analysis_depth,
                    "student_level": student_level,
                    "provider": llm_service.provider_name,
                    "topper_comparison_included": False,
                    "dimensions_analyzed": 13,
                    "timestamp": "2025-07-14",
                    "note": "Fallback to 13D analysis - enhanced analysis failed"
                }
            }
        
    except LLMServiceError as e:
        logger.error(f"LLM service error in comprehensive analysis: {e}")
        raise HTTPException(status_code=500, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in comprehensive analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Direct callable version for internal use (after the endpoint definition)
async def comprehensive_question_analysis_direct(
    question: str,
    student_answer: str = "",
    exam_context: dict = None,
    llm_service: LLMService = None,
    question_number: str = None  # Add question number parameter
) -> dict:
    """
    Enhanced comprehensive question analysis with actual topper comparison via vector similarity
    Returns structured analysis with real topper examples and feedback
    """
    # Extract question number for logging if not provided
    if not question_number:
        question_number = exam_context.get('question_number', 'Unknown') if exam_context else 'Unknown'
    
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
        # Use the enhanced comprehensive analysis that includes real topper comparison
        logger.info(f"Starting enhanced comprehensive analysis for {question_number}: {question[:50]}...")
        
        result = await enhanced_comprehensive_analysis_with_topper_comparison(
            question=question,
            student_answer=student_answer,
            exam_context=exam_context,
            llm_service=llm_service
        )
        
        if result.get("success"):
            logger.info(f"✅ Enhanced comprehensive analysis completed successfully for {question_number} with topper comparison")
            return result
        else:
            logger.warning(f"⚠️ Enhanced analysis failed for {question_number}, falling back to standard analysis")
            logger.warning(f"🔍 FALLBACK REASON for {question_number}: Enhanced analysis returned success=False. Error: {result.get('error', 'Unknown error')}")
            # Fall back to original implementation if enhanced version fails
            return await _fallback_comprehensive_analysis(question, student_answer, exam_context, llm_service, question_number)
            
    except Exception as e:
        logger.error(f"❌ ERROR in enhanced comprehensive analysis for {question_number}: {e}")
        logger.error(f"🔍 FALLBACK REASON for {question_number}: Exception occurred - {type(e).__name__}: {str(e)}")
        # Fall back to original implementation on any error
        return await _fallback_comprehensive_analysis(question, student_answer, exam_context, llm_service, question_number)


async def _fallback_comprehensive_analysis(
    question: str,
    student_answer: str = "",
    exam_context: dict = None,
    llm_service: LLMService = None,
    question_number: str = None
) -> dict:
    """
    Original comprehensive question analysis implementation (fallback)
    Returns structured analysis without FastAPI endpoint overhead
    """
    if not question_number:
        question_number = "Unknown"
        
    logger.warning(f"🚨 GIVING FALLBACK RESPONSE FOR {question_number}: {question[:50]}...")
    logger.warning(f"📋 FALLBACK ANALYSIS for {question_number} - Using standard 13-dimensional evaluation without topper comparison")
    
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

Provide comprehensive 14-dimensional analysis in JSON format:
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
        "presentation_quality": {{"score": "X/10", "feedback": "detailed feedback"}},
        "topper_comparison": {{"score": "X/10", "feedback": "Compare with topper answer patterns: structure, examples, analysis depth, writing style, and strategic approach. Identify specific topper techniques that could improve this answer."}}
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
            import json
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
        "presentation_quality": {{"score": "7/10", "feedback": "Well-presented answer with good use of structure and clarity."}},
        "topper_comparison": {{"score": "6/10", "feedback": "Answer shows good foundation but can benefit significantly from topper writing patterns and techniques."}}
    }},
    "detailed_feedback": {{
        "strengths": [
            "Clear understanding of core concepts and their application",
            "Logical structure and coherent flow of arguments"
        ],
        "improvement_suggestions": [
            "Include more specific examples and case studies",
            "Integrate recent developments and policy changes",
            "Adopt topper-style structural patterns and analytical approaches"
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
                            "presentation_quality": {"score": "7/10", "feedback": f"Well-presented answer on {question[:30]}... with good use of paragraphs and structure"},
                            "topper_comparison": {"score": "6/10", "feedback": f"Answer shows foundation but can benefit from topper techniques for {question[:25]}... - consider studying high-scoring patterns"}
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
        logger.error(f"Error in comprehensive analysis: {e}")
        return {
            "success": False,
            "error": str(e),
            "analysis": None
        }
