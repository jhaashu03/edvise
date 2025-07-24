#!/usr/bin/env python3
"""
Pure LLM-based PDF Question Extraction - Updated for current LLM service
Extracts all 19 questions from VisionIAS PDF using only LLM analysis
"""

import sys
import os
import logging
import asyncio
import fitz  # PyMuPDF for PDF page conversion only
import base64
import json
from io import BytesIO
from PIL import Image
from datetime import datetime
from typing import Dict, List, Optional
from typing import Dict, List, Optional

# Add the backend directory to Python path
sys.path.append('/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend')

from app.core.llm_service import get_llm_service

# Configuration
PDF_PATH = "/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/docs/VisionIAS Toppers Answer Booklet Shakti Dubey.pdf"
ENVIRONMENT = "local"
LLM_PROVIDER = "openai"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_only_extraction")

class PureLLMPDFExtractor:
    """Pure LLM-based PDF extractor using only text analysis capabilities"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.extracted_questions = []
        self.total_pages = 0
        
        # Load the PDF document
        if not os.path.exists(PDF_PATH):
            raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
        
        self.doc = fitz.open(PDF_PATH)
        self.total_pages = len(self.doc)
        print(f"📄 Loaded PDF: {self.total_pages} pages")
    
    def extract_text_from_page(self, page) -> str:
        """Extract any available text from PDF page (no OCR)"""
        try:
            # Get embedded text first
            text_content = page.get_text()
            
            # If no embedded text, we'll ask LLM to work with page metadata
            if not text_content.strip():
                # Get page info for LLM context
                page_info = {
                    "page_width": page.rect.width,
                    "page_height": page.rect.height,
                    "rotation": page.rotation,
                    "has_text": len(text_content.strip()) > 0,
                    "has_images": len(page.get_images()) > 0,
                    "has_drawings": len(page.get_drawings()) > 0
                }
                return f"Page metadata: {json.dumps(page_info)}\nText content: {text_content}"
            
            return text_content
            
        except Exception as e:
            logger.warning(f"Failed to extract text from page: {e}")
            return ""
    
    async def analyze_page_content_with_llm(self, page_text: str, page_num: int) -> Dict:
        """Use LLM to analyze page content and identify questions AND answers"""
        
        analysis_prompt = f"""You are an expert at analyzing UPSC answer booklet content. You are examining page {page_num} from a VisionIAS answer booklet.

Below is the text/metadata extracted from this page:

---
{page_text}
---

Your task is to analyze this content and:

1. **Find UPSC Questions** - Look for patterns like:
   - Numbers followed by periods: "1.", "2.", "3.", etc. (NOT Q1 or Question 1)
   - UPSC topics: governance, politics, economics, current affairs, international relations
   - Word limits like "(150 words)", "(250 words)" 
   - Marks like "10", "15", "25" at the end

2. **Find Student Answers** - Look for:
   - Handwritten content following questions
   - Answer text that responds to the questions
   - Any written explanations or analysis

3. **Extract BOTH questions and answers with complete details**

Please respond in this EXACT JSON format:
{{
    "page_number": {page_num},
    "has_questions": true/false,
    "has_answers": true/false,
    "page_type": "question_page/answer_page/mixed/instruction_page/other",
    "questions_found": [
        {{
            "question_number": 1,
            "question_text": "Complete question text extracted...",
            "word_limit": 150,
            "marks": 10,
            "confidence": "high/medium/low"
        }}
    ],
    "answers_found": [
        {{
            "linked_to_question": 1,
            "answer_text": "Complete student answer text...",
            "estimated_word_count": 120,
            "answer_quality": "complete/partial/incomplete"
        }}
    ],
    "content_analysis": {{
        "embedded_text_found": true/false,
        "likely_handwritten": true/false,
        "content_type": "questions/answers/mixed/instructions/other"
    }},
    "notes": "Analysis notes about this page"
}}

**CRITICAL PATTERN**: Questions start with JUST numbers and periods:
- "1. There are arguments that bills of national importance..." (150 words) 10
- "2. Discuss the role played by the Directorate..." (150 words) 10

NOT "Q1." or "Question 1" - just "1.", "2.", etc.

Focus on extracting actual substantive UPSC questions about:
- Governance and administration  
- Political science concepts
- Current affairs and policy
- Economic issues
- Social issues
- International relations  
- Constitutional matters

Where:
- Numbers (1., 2., 3.) indicate question start
- Question text follows immediately
- Word limit is in parentheses like "(150 words)"
- Marks are at the end like "10", "15", "25"

Example format:
"1. There are arguments that bills of national importance should be placed before the Inter-State Council prior to their introduction in the Parliament. Discuss in light of the issues that have been observed in the passage of bills in the Parliament in recent times. (150 words) 10"

Ignore:
- Instructions about filling answer sheets
- Contact information
- Page headers/footers
- Administrative text"""

        try:
            response = await self.llm_service.simple_chat(
                user_message=analysis_prompt,
                temperature=0.1
            )
            
            # Try to parse JSON response
            try:
                page_analysis = json.loads(response)
                return page_analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, create structured response from text
                logger.warning(f"Failed to parse JSON from LLM for page {page_num}")
                
                # Extract info from text response
                has_questions = any(keyword in response.lower() for keyword in [
                    "question", "marks", "words", "discuss", "analyze", "explain"
                ])
                
                return {
                    "page_number": page_num,
                    "has_questions": has_questions,
                    "page_type": "question_page" if has_questions else "other",
                    "questions_found": [],
                    "content_analysis": {
                        "embedded_text_found": len(page_text.strip()) > 0,
                        "likely_handwritten": "metadata" in page_text.lower(),
                        "content_type": "questions" if has_questions else "other"
                    },
                    "notes": f"LLM analysis (text format): {response[:200]}..."
                }
                
        except Exception as e:
            logger.error(f"Failed to analyze page {page_num} with LLM: {e}")
            return {
                "page_number": page_num,
                "has_questions": False,
                "questions_found": [],
                "page_type": "error",
                "content_analysis": {"embedded_text_found": False, "likely_handwritten": True, "content_type": "unknown"},
                "notes": f"Analysis failed: {str(e)}"
            }
    
    
    async def intelligent_question_extraction(self, potential_question_text: str, page_num: int) -> List[Dict]:
        """Use LLM to extract and clean up questions from mixed content"""
        
        extraction_prompt = f"""You are an expert at extracting UPSC questions from answer booklet content. 

Below is content from page {page_num} that may contain questions:

---
{potential_question_text}
---

Please extract ALL the actual UPSC questions from this content. For each question:

1. **Identify the complete question text**
2. **Extract the question number**
3. **Find the marks allocation**
4. **Identify word limits**
5. **Clean up any OCR errors or formatting issues**

Focus on questions that:
- Start with numbers followed by periods (1., 2., 3., etc.)
- Ask substantive questions about governance, politics, economics, current affairs, international relations
- Have clear marks allocation (10, 15, 25 marks typically) at the end
- Have word limits in parentheses like "(150 words)", "(250 words)"
- Are actual exam questions, not instructions

**Pattern to look for:**
[Number]. [Question text...] ([word count] words) [marks]

Example: "1. There are arguments that bills of national importance... (150 words) 10"

Return as JSON array:
{{
    "questions": [
        {{
            "question_number": 1,
            "question_text": "There are arguments that bills of national importance should be referred to the Inter-State Council prior to their introduction in Parliament. Discuss in light of the issues that have been observed in the passage of bills in Parliament in recent times.",
            "word_limit": 150,
            "marks": 10,
            "source_page": {page_num},
            "extraction_confidence": "high"
        }}
    ],
    "extraction_notes": "Notes about extraction process"
}}

If no clear questions are found, return empty questions array."""

        try:
            response = await self.llm_service.simple_chat(
                user_message=extraction_prompt,
                temperature=0.1
            )
            
            # Parse response
            try:
                extracted = json.loads(response)
                return extracted.get("questions", [])
            except json.JSONDecodeError:
                # Try to extract questions from text response
                logger.warning(f"Failed to parse extraction JSON for page {page_num}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to extract questions from page {page_num}: {e}")
            return []
    
    async def extract_from_page_range(self, start_page: int, end_page: int) -> List[Dict]:
        """Extract questions from a specific page range"""
        doc = fitz.open(PDF_PATH)
        page_analyses = []
        
        logger.info(f"� Analyzing pages {start_page} to {end_page} for questions...")
        
        for page_num in range(start_page - 1, min(end_page, len(doc))):
            page = doc.load_page(page_num)
            
            logger.info(f"📄 Processing page {page_num + 1}...")
            
            # Extract text content
            page_text = self.extract_text_from_page(page)
            
            if page_text.strip():
                logger.info(f"   Found {len(page_text)} characters of content")
                
                # Analyze with LLM
                analysis = await self.analyze_page_content_with_llm(page_text, page_num + 1)
                
                # If questions are indicated but not extracted, try deeper extraction
                if analysis.get("has_questions") and not analysis.get("questions_found"):
                    logger.info(f"   Attempting deeper question extraction...")
                    extracted_questions = await self.intelligent_question_extraction(page_text, page_num + 1)
                    analysis["questions_found"] = extracted_questions
                
                page_analyses.append(analysis)
                
                # Show immediate results
                if analysis.get("questions_found"):
                    questions = analysis["questions_found"]
                    logger.info(f"✅ Found {len(questions)} question(s) on page {page_num + 1}")
                    for q in questions:
                        q_text = q.get('question_text', 'N/A')[:100]
                        logger.info(f"   Q{q.get('question_number', '?')}: {q_text}...")
                else:
                    logger.info(f"   No questions found on page {page_num + 1}")
            else:
                logger.info(f"   No text content found (likely handwritten page)")
                # Create analysis for handwritten page
                analysis = {
                    "page_number": page_num + 1,
                    "has_questions": False,
                    "page_type": "answer_page",
                    "questions_found": [],
                    "content_analysis": {
                        "embedded_text_found": False,
                        "likely_handwritten": True,
                        "content_type": "answers"
                    },
                    "notes": "No embedded text - likely handwritten answer page"
                }
                page_analyses.append(analysis)
            
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.2)
        
        doc.close()
        return page_analyses
    
    def _match_questions_to_answers(self, questions: List[Dict], answers: List[Dict]) -> List[Dict]:
        """Match questions to their corresponding answers"""
        matched_pairs = []
        
        for question in questions:
            q_num = question.get('question_number')
            # Find matching answer
            matching_answer = None
            for answer in answers:
                if answer.get('linked_to_question') == q_num:
                    matching_answer = answer
                    break
            
            pair = {
                'question': question,
                'answer': matching_answer,
                'has_answer': matching_answer is not None
            }
            matched_pairs.append(pair)
        
        return matched_pairs

    async def extract_all_questions_and_answers(self) -> Dict:
        """Extract all questions AND answers from the PDF using LLM"""
        
        print(f"🎯 Starting comprehensive LLM-only extraction of questions and answers...")
        print(f"📄 Total pages to analyze: {len(self.doc)}")
        
        results = {
            'total_pages': len(self.doc),
            'all_questions': [],
            'all_answers': [],
            'page_analyses': [],
            'extraction_summary': {},
            'processing_metadata': {
                'extraction_method': 'LLM-only (no OCR)',
                'llm_model': 'gpt-4.1-mini via Walmart Gateway',
                'timestamp': datetime.now().isoformat(),
                'question_pattern': 'Number + period format (1., 2., 3.)',
                'answer_extraction': 'Handwritten student responses'
            }
        }
        
        questions_found = 0
        answers_found = 0
        pages_with_content = 0
        
        # Process all pages
        for page_num in range(len(self.doc)):
            try:
                page = self.doc[page_num]
                page_text = page.get_text()
                
                print(f"📖 Analyzing page {page_num + 1}...")
                
                # Get LLM analysis
                analysis = await self.analyze_page_content_with_llm(page_text, page_num + 1)
                results['page_analyses'].append(analysis)
                
                # Count findings
                if analysis.get('has_questions'):
                    questions_count = len(analysis.get('questions_found', []))
                    questions_found += questions_count
                    results['all_questions'].extend(analysis.get('questions_found', []))
                    print(f"   ✅ Found {questions_count} questions on page {page_num + 1}")
                
                if analysis.get('has_answers'):
                    answers_count = len(analysis.get('answers_found', []))
                    answers_found += answers_count
                    results['all_answers'].extend(analysis.get('answers_found', []))
                    print(f"   ✅ Found {answers_count} answers on page {page_num + 1}")
                    
                if analysis.get('has_questions') or analysis.get('has_answers'):
                    pages_with_content += 1
                
                # Add page metadata
                analysis['page_metadata'] = {
                    'page_number': page_num + 1,
                    'text_length': len(page_text),
                    'processing_timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                print(f"❌ Error processing page {page_num + 1}: {str(e)}")
                error_analysis = {
                    'page_number': page_num + 1,
                    'error': str(e),
                    'has_questions': False,
                    'has_answers': False,
                    'page_type': 'error'
                }
                results['page_analyses'].append(error_analysis)
                continue
        
        # Create summary
        results['extraction_summary'] = {
            'total_questions_found': questions_found,
            'total_answers_found': answers_found,
            'pages_with_content': pages_with_content,
            'pages_processed': len(self.doc),
            'extraction_success_rate': f"{(pages_with_content / len(self.doc)) * 100:.1f}%",
            'question_answer_pairs': self._match_questions_to_answers(results['all_questions'], results['all_answers'])
        }
        
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"📊 Questions found: {questions_found}")
        print(f"📝 Answers found: {answers_found}")
        print(f"📄 Pages with content: {pages_with_content}/{len(self.doc)}")
        
        return results
        """Extract all questions from the entire PDF using intelligent sampling"""
        logger.info(f"🚀 Starting pure LLM extraction from: {PDF_PATH}")
        
        # Check PDF exists
        if not os.path.exists(PDF_PATH):
            raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
        
        doc = fitz.open(PDF_PATH)
        self.total_pages = len(doc)
        doc.close()
        
        logger.info(f"📊 PDF has {self.total_pages} total pages")
        
        # Strategy: Extract from likely question pages first, then fill in gaps
        
        # Phase 1: Sample key pages that likely contain questions (based on previous analysis)
        logger.info("🎯 Phase 1: Analyzing high-probability question pages...")
        key_pages = [3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        key_page_analyses = []
        
        for page_num in key_pages:
            if page_num <= self.total_pages:
                analyses = await self.extract_from_page_range(page_num, page_num)
                key_page_analyses.extend(analyses)
        
        # Compile questions found so far
        initial_questions = []
        for analysis in key_page_analyses:
            if analysis.get("questions_found"):
                initial_questions.extend(analysis["questions_found"])
        
        logger.info(f"📊 Phase 1 complete: Found {len(initial_questions)} questions")
        
        # Phase 2: If we need more questions, scan remaining pages
        all_page_analyses = key_page_analyses
        
        if len(initial_questions) < 15:  # If we haven't found most questions yet
            logger.info("🔍 Phase 2: Scanning remaining pages for missing questions...")
            
            # Scan remaining pages
            remaining_pages = [p for p in range(1, self.total_pages + 1) if p not in key_pages]
            
            # Analyze in chunks to avoid overwhelming
            for i in range(0, len(remaining_pages), 10):
                chunk = remaining_pages[i:i+10]
                if chunk:
                    start_page = chunk[0]
                    end_page = chunk[-1]
                    chunk_analyses = await self.extract_from_page_range(start_page, end_page)
                    all_page_analyses.extend(chunk_analyses)
        
        # Compile all questions found
        all_questions = []
        question_pages = []
        
        for analysis in all_page_analyses:
            if analysis.get("questions_found"):
                for question in analysis["questions_found"]:
                    question["source_page"] = analysis["page_number"]
                    all_questions.append(question)
                question_pages.append(analysis["page_number"])
        
        # Remove duplicates and sort
        seen_questions = set()
        unique_questions = []
        
        for q in all_questions:
            q_text = q.get("question_text", "")[:100]  # First 100 chars as identifier
            if q_text not in seen_questions:
                seen_questions.add(q_text)
                unique_questions.append(q)
        
        # Sort by question number
        unique_questions.sort(key=lambda x: x.get("question_number", 999))
        
        return {
            "pdf_path": PDF_PATH,
            "total_pages_analyzed": len(all_page_analyses),
            "pages_with_questions": list(set(question_pages)),
            "total_questions_found": len(unique_questions),
            "questions": unique_questions,
            "extraction_method": "Pure LLM Text Analysis (No OCR)",
            "total_marks": sum(q.get("marks", 0) for q in unique_questions),
            "extraction_strategy": "Intelligent sampling + comprehensive scan",
            "page_analyses": all_page_analyses  # Full detail for debugging
        }

    
    async def create_comprehensive_summary(self, results: Dict) -> str:
        """Create a formatted summary of extracted questions AND answers"""
        
        summary = f"""
📋 VisionIAS PDF Question & Answer Extraction Results (LLM-Only)
════════════════════════════════════════════════════════════

📄 Source: VisionIAS Toppers Answer Booklet
📊 Total Pages Analyzed: {results['total_pages']}
🔍 Pages with Content: {results['extraction_summary']['pages_with_content']}
📝 Total Questions Found: {results['extraction_summary']['total_questions_found']}/19 (expected)
� Total Answers Found: {results['extraction_summary']['total_answers_found']}
� Question-Answer Pairs: {len(results['extraction_summary']['question_answer_pairs'])}
� Method: {results['processing_metadata']['extraction_method']}
⏰ Timestamp: {results['processing_metadata']['timestamp']}

🎯 EXTRACTION DETAILS:
─────────────────────────────────────────────────────────────

"""
        
        # Show question-answer pairs
        if results['extraction_summary']['question_answer_pairs']:
            for pair in results['extraction_summary']['question_answer_pairs']:
                question = pair['question']
                answer = pair.get('answer')
                
                q_num = question.get('question_number', '?')
                q_text = question.get('question_text', 'No text extracted')
                marks = question.get('marks', 'Unknown')
                word_limit = question.get('word_limit', 'Not specified')
                
                summary += f"Question {q_num} - {marks} marks"
                if word_limit != 'Not specified':
                    summary += f" - {word_limit} words"
                summary += "\n"
                summary += f"Text: {q_text}\n"
                
                if pair['has_answer'] and answer:
                    answer_text = answer.get('answer_text', 'No answer text')
                    word_count = answer.get('estimated_word_count', 'Unknown')
                    quality = answer.get('answer_quality', 'Unknown')
                    
                    summary += f"Answer ({quality}, ~{word_count} words): {answer_text}\n"
                else:
                    summary += "Answer: Not found or not extracted\n"
                
                summary += "─" * 80 + "\n\n"
        
        else:
            summary += "❌ No questions or answers were successfully extracted.\n"
            summary += "🔍 Possible reasons:\n"
            summary += "  • PDF contains only handwritten content (no embedded text)\n"
            summary += "  • Questions are in image format requiring vision models\n"
            summary += "  • Content is heavily formatted or in non-standard layout\n\n"
            
            summary += "📄 Page Analysis Summary:\n"
            for analysis in results['page_analyses'][:10]:  # Show first 10 pages
                page_num = analysis['page_number']
                page_type = analysis.get('page_type', 'unknown')
                has_text = analysis.get('content_analysis', {}).get('embedded_text_found', False)
                
                summary += f"Page {page_num}: {page_type} (Text: {'Yes' if has_text else 'No'})\n"
        
        return summary

async def main():
    """Main extraction function for questions AND answers"""
    print("🤖 Pure LLM PDF Question & Answer Extractor (Text-Based)")
    print("=" * 60)
    print("🎯 Goal: Extract all 19 questions AND student answers from VisionIAS PDF")
    print("🚫 No OCR libraries - Pure LLM text analysis only") 
    print("💡 Works best with PDFs that have embedded text")
    print("=" * 60)
    
    # Set environment
    os.environ["ENVIRONMENT"] = ENVIRONMENT
    os.environ["LLM_PROVIDER"] = LLM_PROVIDER
    
    try:
        extractor = PureLLMPDFExtractor()
        
        # Extract all questions and answers
        results = await extractor.extract_all_questions_and_answers()
        
        # Create and display summary
        summary = await extractor.create_comprehensive_summary(results)
        print(summary)
        
        # Save results to file
        output_file = "/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend/visionias_extraction_comprehensive.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Detailed results saved to: {output_file}")
        
        # Final statistics
        print("\n" + "=" * 60)
        print("📊 EXTRACTION STATISTICS")
        print("=" * 60)
        print(f"✅ Questions Found: {results['extraction_summary']['total_questions_found']}/19 (expected)")
        print(f"� Answers Found: {results['extraction_summary']['total_answers_found']}")
        print(f"� Q&A Pairs: {len(results['extraction_summary']['question_answer_pairs'])}")
        print(f"📄 Pages with Content: {results['extraction_summary']['pages_with_content']}")
        print(f"🔧 Method: Pure LLM Text Analysis (No OCR libraries)")
        
        success_rate = (results['extraction_summary']['total_questions_found'] / 19) * 100 if results['extraction_summary']['total_questions_found'] else 0
        
        if success_rate >= 80:
            print("🎉 EXCELLENT: Most questions extracted successfully!")
        elif success_rate >= 60:
            print("✅ GOOD: Majority of questions extracted!")
        elif success_rate >= 30:
            print("⚠️  PARTIAL: Some questions extracted")
        else:
            print("❌ LIMITED: Few questions extracted")
            print("💡 This PDF likely requires vision-capable models for handwritten content")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        print(f"\n💥 Error: {e}")
        return None

if __name__ == "__main__":
    # Run the extraction
    results = asyncio.run(main())
    
    if results:
        print(f"\n🏁 Extraction completed!")
        print(f"📋 Found {results['extraction_summary']['total_questions_found']} questions")
        print(f"💬 Found {results['extraction_summary']['total_answers_found']} answers")
        print(f"📄 Check visionias_extraction_comprehensive.json for full details")
        
        if results['extraction_summary']['total_questions_found'] > 0:
            print(f"\n🔍 First question preview:")
            first_q = results['all_questions'][0]
            print(f"Q{first_q.get('question_number', '?')}: {first_q.get('question_text', 'N/A')[:150]}...")
    else:
        print("\n💥 Extraction failed!")
        print("🔍 Check the logs above for error details")
