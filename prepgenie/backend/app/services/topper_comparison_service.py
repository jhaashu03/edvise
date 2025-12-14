"""
Topper Comparison Service
Provides semantic comparison between student answers and topper answers
Identifies gaps, similarities, and improvement suggestions based on topper performance
"""
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from datetime import datetime
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
import numpy as np

from app.core.config import settings
from app.core.llm_service import get_llm_service

logger = logging.getLogger(__name__)

class TopperComparisonService:
    """Service for comparing student answers with topper answers using BGE embeddings"""
    
    def __init__(self):
        self.collection_name = "topper_embeddings"
        self.model = None
        self.milvus_client = None
        self.llm_service = get_llm_service()
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize BGE embedding model and Milvus connection (1024-dim)"""
        try:
            # Use BGE model for high-quality embeddings
            from sentence_transformers import SentenceTransformer
            import socket
            
            # Set socket timeout for model download
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)  # 30 second timeout
            
            try:
                self.model = SentenceTransformer('BAAI/bge-large-en-v1.5')
                logger.info("✅ BGE embedding model loaded (1024 dimensions)")
            finally:
                socket.setdefaulttimeout(original_timeout)
                
        except Exception as e:
            logger.error(f"❌ Failed to load BGE model: {e}")
            raise Exception(f"BGE model loading failed: {e}")
        
        # Use dedicated database file for topper comparisons to avoid locks
        self.topper_db_path = "topper_readonly.db"
        self.milvus_client = None
        logger.info("✅ Topper comparison service initialized (will use dedicated read-only DB)")
    
    async def find_similar_topper_answers(self, question_text: str, student_answer: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar topper answers using BGE embeddings"""
        if not self.model:
            logger.error("BGE model not initialized")
            return []
            
        # Use dedicated read-only database to avoid lock conflicts
        try:
            import shutil
            import os
            
            # Ensure we have a read-only copy for topper comparisons
            original_db = "milvus_lite_local.db"
            
            if not os.path.exists(self.topper_db_path) or os.path.getmtime(original_db) > os.path.getmtime(self.topper_db_path):
                # Update read-only copy if original is newer
                if os.path.exists(original_db):
                    shutil.copy2(original_db, self.topper_db_path)
                    logger.info("✅ Updated read-only topper database")
                else:
                    logger.error("❌ Original database not found")
                    return []
            
            # Connect to dedicated read-only database
            milvus_client = MilvusClient(uri=self.topper_db_path)
            logger.info("✅ Connected to dedicated topper database")
                
        except Exception as e:
            logger.error(f"❌ Failed to access topper database: {e}")
            return []
        
        try:
            # Create combined query from question and answer for better matching
            combined_query = f"Question: {question_text}\nAnswer: {student_answer}"
            
            # Generate embedding for the combined query
            query_embedding = self.model.encode([combined_query], normalize_embeddings=True)
            
            # Search in Milvus for similar topper answers
            results = milvus_client.search(
                collection_name=self.collection_name,
                data=[query_embedding[0].tolist()],
                anns_field='embedding',
                limit=limit,
                output_fields=['question_text', 'answer_text', 'combined_content', 'pdf_filename', 'question_number', 'marks']
            )
            
            similar_answers = []
            if results and len(results[0]) > 0:
                for hit in results[0]:
                    entity = hit['entity']
                    similarity_score = hit['distance']  # BGE uses distance, lower = more similar
                    
                    # Filter out Hindi content - check for Devanagari script
                    question_text = entity.get('question_text', '')
                    answer_text = entity.get('answer_text', '')
                    
                    # Check if text contains Hindi/Devanagari characters
                    def contains_hindi(text):
                        if not text:
                            return False
                        # Check for Devanagari Unicode range (U+0900-U+097F)
                        # Also check for common Hindi words to be more accurate
                        hindi_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
                        total_chars = len(text.replace(' ', '').replace('\n', ''))
                        
                        # If more than 10% of characters are Hindi, consider it Hindi content
                        return total_chars > 0 and (hindi_chars / total_chars) > 0.1
                    
                    # Skip if question or answer contains Hindi
                    if contains_hindi(question_text) or contains_hindi(answer_text):
                        logger.debug(f"Skipping Hindi content from {entity.get('pdf_filename', 'unknown')}")
                        continue
                    
                    similar_answers.append({
                        'question_text': question_text,
                        'answer_text': answer_text,
                        'combined_content': entity.get('combined_content', ''),
                        'pdf_filename': entity.get('pdf_filename', ''),
                        'question_number': entity.get('question_number', 0),
                        'marks': entity.get('marks', 10),
                        'similarity_score': float(1 - similarity_score),  # Convert to similarity (higher = more similar)
                        'topper_name': self._extract_topper_name(entity.get('pdf_filename', ''))
                    })
            
            logger.info(f"Found {len(similar_answers)} similar English topper answers (filtered out Hindi content)")
            
            # If no English answers found, include Hindi content as fallback
            if len(similar_answers) == 0:
                logger.warning("No English topper answers found, including Hindi content as fallback...")
                # Get results including Hindi content as fallback
                for hit in results[0]:
                    entity = hit['entity']
                    similarity_score = hit['distance']
                    
                    similar_answers.append({
                        'question_text': entity.get('question_text', ''),
                        'answer_text': entity.get('answer_text', ''),
                        'combined_content': entity.get('combined_content', ''),
                        'pdf_filename': entity.get('pdf_filename', ''),
                        'question_number': entity.get('question_number', 0),
                        'marks': entity.get('marks', 10),
                        'similarity_score': float(1 - similarity_score),
                        'topper_name': self._extract_topper_name(entity.get('pdf_filename', ''))
                    })
                    
                    # Limit to top 3 results as fallback
                    if len(similar_answers) >= 3:
                        break
                
                logger.info(f"Fallback: Using {len(similar_answers)} topper answers (including Hindi content)")
            
            return similar_answers
            
        except Exception as e:
            logger.error(f"Error finding similar topper answers: {e}")
            return []
    
    def _extract_topper_name(self, filename: str) -> str:
        """Extract topper name from PDF filename"""
        try:
            # Extract name from filename like "VisionIAS Toppers Answer Booklet Aayushi Bansal (1).pdf"
            if "Toppers Answer Booklet" in filename:
                parts = filename.split("Toppers Answer Booklet")
                if len(parts) > 1:
                    name_part = parts[1].strip()
                    # Remove file extension and parentheses
                    name_part = name_part.replace('.pdf', '').replace('_FIXED_V2_extracted', '')
                    # Extract name before parentheses
                    if '(' in name_part:
                        name_part = name_part.split('(')[0].strip()
                    return name_part
            return "Unknown Topper"
        except Exception:
            return "Unknown Topper"
    
    async def analyze_topper_comparison(self, question_text: str, student_answer: str, similar_toppers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze student answer against topper answers and provide detailed comparison"""
        try:
            if not similar_toppers:
                return {
                    'comparison_available': False,
                    'message': 'No similar topper answers found for comparison'
                }
            
            # Prepare detailed comparison data for LLM analysis
            topper_examples = []
            for i, topper in enumerate(similar_toppers[:3]):  # Use top 3 most similar
                topper_examples.append({
                    'topper_name': topper['topper_name'],
                    'similarity_score': topper['similarity_score'],  # Keep as float for LLM processing
                    'similarity_percentage': f"{topper['similarity_score']:.1%}",  # Formatted version
                    'question_text': topper['question_text'],  # Full question for exact matching
                    'complete_answer': topper['answer_text'],  # Full answer for detailed analysis
                    'marks': topper['marks'],
                    'word_count': len(topper['answer_text'].split()),
                    'pdf_source': topper.get('pdf_filename', 'Unknown')
                })
            
            # Create enhanced LLM prompt for specific, detailed comparison
            comparison_prompt = f"""
You are an expert UPSC evaluator conducting a DETAILED SIDE-BY-SIDE comparison between student and topper answers. Provide SPECIFIC, ACTIONABLE insights.

**QUESTION:**
{question_text}

**STUDENT'S ANSWER:**
{student_answer}

**TOPPER ANSWERS FOR DETAILED COMPARISON:**
{json.dumps(topper_examples, indent=2)}

**CRITICAL REQUIREMENTS - PROVIDE HIGHLY SPECIFIC ANALYSIS:**

1. **EXACT TOPPER QUESTION MATCHING**: 
   - Only compare with toppers who answered THE SAME or VERY SIMILAR questions
   - If no similar questions exist, clearly state "No matching questions found"
   - Show actual similarity percentage (use similarity_percentage field)

2. **DIRECT CONTENT COMPARISON**:
   - Quote 2-3 specific sentences from topper answers that student should have included
   - Show exact phrases toppers used vs what student wrote
   - Highlight specific facts/data toppers mentioned that student missed

3. **STRUCTURAL ANALYSIS**:
   - Show topper's exact paragraph flow with word counts
   - Compare student's actual structure vs topper's structure
   - Provide specific restructuring with exact sentences to add/remove

4. **MISSING ELEMENTS**:
   - List exact constitutional articles, acts, cases toppers cited
   - Show specific examples/case studies toppers used
   - Identify precise technical terms and their context

5. **ACTIONABLE REWRITES**:
   - Provide 2-3 specific sentences student should add verbatim
   - Show exact opening/closing lines toppers used
   - Give precise word targets for each paragraph

6. **SCORING JUSTIFICATION**:
   - Explain exactly why student got current score
   - Show specific point deductions (e.g., "-2 for missing Article 263")
   - Detail exactly what additions would increase score

**IMPORTANT**: If toppers answered different questions, focus on writing techniques and general UPSC answer patterns rather than content comparison.

Provide response in JSON format with SPECIFIC, DETAILED content:
{{
    "topper_matches": [
        {{
            "topper_name": "Name",
            "question_similarity": "X%",
            "exact_question": "Full question text",
            "marks": "X marks"
        }}
    ],
    "missing_keywords": ["keyword1", "keyword2", "keyword3", "..."],
    "technical_terms_missed": ["term1", "term2", "term3"],
    "structural_blueprint": {{
        "topper_structure": "Para 1: Intro with definition → Para 2: Key issues → Para 3: Solutions → Conclusion",
        "student_structure": "Current structure analysis",
        "recommended_structure": "Specific restructuring advice"
    }},
    "missing_content": {{
        "facts_statistics": ["fact1", "fact2", "fact3"],
        "examples_case_studies": ["example1", "example2"],
        "constitutional_references": ["Article X", "Committee Y"],
        "recent_developments": ["development1", "development2"]
    }},
    "writing_techniques": {{
        "sentence_starters": ["In this context", "Furthermore", "However"],
        "argument_frameworks": ["Problem-solution approach", "Multi-stakeholder analysis"],
        "transition_phrases": ["phrase1", "phrase2"]
    }},
    "unique_topper_insights": ["insight1", "insight2", "insight3"],
    "specific_improvements": [
        "Add paragraph on constitutional mandate with Article references",
        "Include 2-3 recent examples of contentious bills",
        "Restructure with clear problem-solution framework"
    ],
    "word_count_analysis": {{
        "student_words": "X words",
        "topper_average": "Y words", 
        "recommended_distribution": "Intro: 50 words, Body: 200 words, Conclusion: 50 words"
    }},
    "score_breakdown": {{
        "current_estimated": "X/10",
        "with_improvements": "Y/10",
        "reasoning": "Specific gaps and potential gains"
    }}
}}
}}
"""
            
            # Get LLM analysis
            response = await self.llm_service.simple_chat(comparison_prompt)
            
            # Parse JSON response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                analysis = {
                    'overall_comparison': response[:200] + "..." if len(response) > 200 else response,
                    'content_gaps': ['Analysis available in overall comparison'],
                    'structure_insights': 'Detailed analysis provided above',
                    'depth_analysis': 'See overall comparison for details',
                    'writing_style_tips': 'Review topper examples for style insights',
                    'specific_improvements': ['Study the topper examples provided'],
                    'student_strengths': ['Answer attempt shows effort'],
                    'estimated_topper_score': 'Analysis in progress',
                    'key_learning': 'Compare with topper approaches'
                }
            
            # Add metadata
            analysis['comparison_available'] = True
            analysis['toppers_analyzed'] = len(topper_examples)
            analysis['highest_similarity'] = max([t['similarity_score'] for t in topper_examples])
            analysis['topper_names'] = [t['topper_name'] for t in topper_examples]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in topper comparison analysis: {e}")
            return {
                'comparison_available': False,
                'error': str(e),
                'message': 'Failed to analyze topper comparison'
            }
    
    async def generate_topper_based_evaluation(self, question_text: str, student_answer: str, marks: int = 10) -> Dict[str, Any]:
        """Generate complete evaluation based on topper comparison"""
        try:
            # Find similar topper answers
            similar_toppers = await self.find_similar_topper_answers(question_text, student_answer, limit=5)
            
            if not similar_toppers:
                return {
                    'evaluation_type': 'topper_comparison',
                    'comparison_available': False,
                    'score': 0.0,
                    'max_score': marks,  # Keep as integer for proper display
                    'feedback': 'No similar topper answers found for comparison. This question may be unique or require different evaluation approach.',
                    'topper_insights': None
                }
            
            # Analyze comparison
            comparison_analysis = await self.analyze_topper_comparison(question_text, student_answer, similar_toppers)
            
            # Extract score from analysis - check multiple possible fields
            estimated_score = 0.0
            try:
                # Try score_breakdown first (new format)
                score_breakdown = comparison_analysis.get('score_breakdown', {})
                if score_breakdown and 'current_estimated' in score_breakdown:
                    score_text = score_breakdown['current_estimated']
                    if '/' in score_text:
                        score_part = score_text.split('/')[0].strip()
                        estimated_score = float(score_part)
                    else:
                        # Try to extract number from text
                        import re
                        numbers = re.findall(r'\d+\.?\d*', score_text)
                        if numbers:
                            estimated_score = float(numbers[0])
                
                # Fallback to old format
                if estimated_score == 0.0:
                    score_text = comparison_analysis.get('estimated_topper_score', '0/10')
                    if '/' in score_text:
                        score_part = score_text.split('/')[0].strip()
                        estimated_score = float(score_part)
                    else:
                        # Try to extract number from text
                        import re
                        numbers = re.findall(r'\d+\.?\d*', score_text)
                        if numbers:
                            estimated_score = float(numbers[0])
                
                # If still 0, provide a reasonable default based on similarity
                if estimated_score == 0.0 and similar_toppers:
                    avg_similarity = sum(t['similarity_score'] for t in similar_toppers[:3]) / len(similar_toppers[:3])
                    # Convert similarity to score (similarity ranges 0-1, multiply by marks)
                    # Ensure score doesn't exceed the marks allocation
                    estimated_score = min(marks, max(1.0, avg_similarity * marks * 0.8))  # At least 1 point for attempt, max = marks
                    
            except (ValueError, IndexError, TypeError):
                # Default scoring based on answer length and similarity
                if similar_toppers and student_answer.strip():
                    avg_similarity = sum(t['similarity_score'] for t in similar_toppers[:3]) / len(similar_toppers[:3])
                    word_count = len(student_answer.split())
                    # Base score on similarity and effort (word count)
                    base_score = avg_similarity * marks * 0.7
                    effort_bonus = min(2.0, word_count / 50)  # Up to 2 points for effort
                    estimated_score = min(marks, max(1.0, base_score + effort_bonus))  # Cap at marks allocation
                else:
                    estimated_score = 1.0  # Minimum score for attempt
            
            # Generate detailed, specific feedback
            topper_matches = comparison_analysis.get('topper_matches', [])
            missing_keywords = comparison_analysis.get('missing_keywords', [])
            structural_blueprint = comparison_analysis.get('structural_blueprint', {})
            missing_content = comparison_analysis.get('missing_content', {})
            writing_techniques = comparison_analysis.get('writing_techniques', {})
            
            feedback_parts = [
                f"🎯 **How Your Answer Compares to UPSC Toppers**",
                "",
                "📚 **Topper Answers We Analyzed:**"
            ]
            
            # Show actual topper questions being compared
            if topper_matches:
                for match in topper_matches:
                    similarity = match.get('question_similarity', '0%')
                    if similarity == '0%' or similarity == 'N/A':
                        similarity_note = "⚠️ Different question - analysis focuses on writing techniques"
                    else:
                        similarity_note = f"✅ {similarity} question similarity"
                    
                    feedback_parts.extend([
                        f"• **{match.get('topper_name', 'Unknown')}** ({match.get('marks', 'Unknown')} marks) - {similarity_note}",
                        f"  **Topper's Question**: {match.get('exact_question', 'Not specified')}",
                        ""
                    ])
            else:
                # If no matches from LLM analysis, show the actual toppers we found
                for i, topper in enumerate(similar_toppers[:3]):
                    similarity_pct = f"{topper['similarity_score']:.1%}"
                    feedback_parts.extend([
                        f"• **{topper['topper_name']}** ({topper['marks']} marks) - ✅ {similarity_pct} similarity",
                        f"  **Topper's Question**: {topper['question_text']}",
                        ""
                    ])
            
            feedback_parts.extend([
                "💡 **What You Can Add to Improve:**",
                f"Key terms to include: {', '.join(missing_keywords[:8])}",
                f"Technical concepts: {', '.join(comparison_analysis.get('technical_terms_missed', [])[:6])}",
                "",
                "📝 **How to Structure Better:**",
                f"✅ **What toppers do**: {structural_blueprint.get('topper_structure', 'Follow a clear introduction-body-conclusion format')}",
                f"📋 **Your current approach**: {structural_blueprint.get('student_structure', 'Could be more structured')}",
                f"🎯 **Try this instead**: {structural_blueprint.get('recommended_structure', 'Start with context, add examples, conclude with implications')}",
                "",
                "📚 **Content You're Missing:**"
            ])
            
            if missing_content.get('facts_statistics'):
                feedback_parts.append(f"📊 **Add these facts**: {', '.join(missing_content['facts_statistics'][:3])}")
            if missing_content.get('examples_case_studies'):
                feedback_parts.append(f"🔍 **Include examples like**: {', '.join(missing_content['examples_case_studies'][:3])}")
            if missing_content.get('constitutional_references'):
                feedback_parts.append(f"⚖️ **Reference these provisions**: {', '.join(missing_content['constitutional_references'][:3])}")
            
            feedback_parts.extend([
                "",
                "✨ **Writing Tips from Toppers:**",
                f"🚀 **Start sentences with**: {', '.join(writing_techniques.get('sentence_starters', [])[:4])}",
                f"🎯 **Structure arguments using**: {', '.join(writing_techniques.get('argument_frameworks', [])[:3])}",
                "",
                "🔥 **Quick Wins - Do This Next Time:**"
            ])
            
            for improvement in comparison_analysis.get('specific_improvements', [])[:5]:
                feedback_parts.append(f"• {improvement}")
            
            score_breakdown = comparison_analysis.get('score_breakdown', {})
            
            feedback_parts.extend([
                "",
                "📈 **Your Score Potential:**",
                f"🎯 **Current level**: {score_breakdown.get('current_estimated', 'Good effort!')}",
                f"⭐ **With these improvements**: {score_breakdown.get('with_improvements', 'Much higher!')}",
                f"💭 **Why**: {score_breakdown.get('reasoning', 'Focus on structure and key concepts')}",
                "",
                "🌟 **What Makes Toppers Special:**"
            ])
            
            for insight in comparison_analysis.get('unique_topper_insights', [])[:3]:
                feedback_parts.append(f"• {insight}")
            
            # Only add comparison section if we have actual topper matches
            if topper_matches and any(m.get('topper_name', 'Unknown') != 'Unknown' for m in topper_matches):
                feedback_parts.extend([
                    "",
                    f"📚 **Compared with**: {', '.join([m.get('topper_name', 'Unknown') for m in topper_matches if m.get('topper_name', 'Unknown') != 'Unknown'])}"
                ])
            
            # Generate varied dimensional scores based on analysis and marks allocation
            # For dimensional scores, use proportional scoring out of 10 regardless of question marks
            max_dimensional_score = 10.0
            score_ratio = estimated_score / marks if marks > 0 else 0
            
            structure_score = round(min(score_ratio * max_dimensional_score * 0.8, max_dimensional_score), 1)
            coverage_score = round(min(score_ratio * max_dimensional_score * 0.9, max_dimensional_score), 1)
            tone_score = round(min(score_ratio * max_dimensional_score * 0.85, max_dimensional_score), 1)
            
            return {
                'evaluation_type': 'topper_comparison',
                'comparison_available': True,
                'score': round(estimated_score, 1),
                'max_score': marks,  # Keep as integer for proper display
                'feedback': '\n'.join(feedback_parts),
                'topper_insights': comparison_analysis,
                'similar_toppers': similar_toppers[:3],  # Include top 3 for reference
                'structure': structure_score,
                'coverage': coverage_score,
                'tone': tone_score
            }
            
        except Exception as e:
            logger.error(f"Error generating topper-based evaluation: {e}")
            return {
                'evaluation_type': 'topper_comparison',
                'comparison_available': False,
                'score': 0.0,
                'max_score': marks,  # Keep as integer for proper display
                'feedback': f'Error in topper comparison: {str(e)}',
                'topper_insights': None,
                'error': str(e)
            }