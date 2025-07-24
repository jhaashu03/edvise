#!/usr/bin/env python3
"""
Vision-Based LLM PDF Question Extractor (No OCR Libraries)
Uses GPT-4 Vision to directly analyze PDF pages as images
"""

import asyncio
import json
import logging
import fitz  # PyMuPDF for PDF to image conversion only
import base64
import io
from PIL import Image
import sys
import os
from typing import List, Dict, Optional

# Add the backend directory to Python path
sys.path.append('/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend')

from app.core.llm_service import LLMService

# Configuration
PDF_PATH = "/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/docs/VisionIAS Toppers Answer Booklet Shakti Dubey.pdf"
OUTPUT_FILE = "/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend/visionias_questions_vision_llm.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vision_extraction")

class VisionBasedPDFExtractor:
    """Extract questions using GPT-4 Vision to analyze PDF pages as images"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.total_questions_found = 0
        self.all_questions = []
        self.page_analysis = {}
        
    def pdf_page_to_base64_image(self, doc, page_num: int, zoom_factor: float = 2.0) -> str:
        """Convert PDF page to high-quality base64 image for vision analysis"""
        try:
            page = doc.load_page(page_num)
            
            # Create high-resolution image matrix
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True, quality=85)
            img_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return img_b64
            
        except Exception as e:
            logger.error(f"Failed to convert page {page_num} to image: {e}")
            return None

    async def analyze_page_with_vision(self, page_image_b64: str, page_num: int) -> Dict:
        """Use GPT-4 Vision to analyze a single PDF page for questions"""
        
        vision_prompt = f"""You are an expert UPSC question extractor. Analyze this image of page {page_num} from a handwritten UPSC answer booklet.

**Your Task:**
1. Look for UPSC exam questions that follow this pattern:
   [Number]. [Question text...] ([word count] words) [marks]
   
   Examples:
   - "1. There are arguments that bills of national importance should be placed before the Inter-State Council prior to their introduction in the Parliament. Discuss in light of the issues that have been observed in the passage of bills in the Parliament in recent times. (150 words) 10"
   - "2. Discuss the role played by the Directorate of Enforcement in the investigation of offence of money laundering and violations of foreign exchange laws. (150 words) 10"

2. **Key Patterns to Look For:**
   - Questions start with numbers: 1., 2., 3., etc.
   - UPSC topics: governance, politics, economics, current affairs, administration
   - Word limits in parentheses: (150 words), (250 words)
   - Marks at the end: 10, 15, 25

3. **What to Extract:**
   - Complete question text (clean and readable)
   - Question number
   - Word limit
   - Marks allocation

**Response Format (JSON):**
{{
    "page_number": {page_num},
    "has_questions": true/false,
    "page_type": "question_page/answer_page/instruction_page/mixed",
    "questions_found": [
        {{
            "question_number": 1,
            "question_text": "Complete question text here...",
            "word_limit": 150,
            "marks": 10,
            "confidence": "high/medium/low"
        }}
    ],
    "analysis_notes": "What you observed on this page"
}}

**Important:** 
- Only extract actual UPSC questions, not instructions or student answers
- If no questions are visible, return empty questions_found array
- Be precise with question text - avoid OCR-like errors
- Look carefully at handwritten content"""

        try:
            # Prepare vision message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": vision_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{page_image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            # Call OpenAI Vision API through Walmart Gateway
            response = await self.llm_service.vision_chat(
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse JSON response
            try:
                page_analysis = json.loads(response)
                return page_analysis
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for page {page_num}: {e}")
                logger.error(f"Raw response: {response[:500]}...")
                return {
                    "page_number": page_num,
                    "has_questions": False,
                    "questions_found": [],
                    "analysis_notes": f"JSON parsing failed: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Vision analysis failed for page {page_num}: {e}")
            return {
                "page_number": page_num,
                "has_questions": False,
                "questions_found": [],
                "analysis_notes": f"Vision analysis error: {str(e)}"
            }

    async def extract_all_questions(self) -> Dict:
        """Extract all questions using vision-based analysis"""
        
        print("🔍 Vision-Based LLM PDF Question Extractor")
        print("=" * 60)
        print("🎯 Goal: Extract all 19 questions from VisionIAS PDF")
        print("👁️ Method: GPT-4 Vision analysis of PDF pages as images")
        print("🚫 No OCR libraries - Pure vision AI analysis")
        print("=" * 60)
        
        try:
            # Open PDF
            doc = fitz.open(PDF_PATH)
            logger.info(f"🚀 Starting vision-based extraction from: {PDF_PATH}")
            logger.info(f"📊 PDF has {len(doc)} total pages")
            
            # Analyze key pages first (where questions are likely to be)
            question_pages = [3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50]
            
            logger.info("🎯 Phase 1: Analyzing high-probability question pages...")
            
            for page_num in question_pages:
                if page_num > len(doc):
                    continue
                    
                logger.info(f"📄 Analyzing page {page_num} with Vision AI...")
                
                # Convert page to image
                page_image = self.pdf_page_to_base64_image(doc, page_num - 1, zoom_factor=2.5)
                if not page_image:
                    logger.warning(f"⚠️ Failed to convert page {page_num} to image")
                    continue
                
                # Analyze with vision
                page_analysis = await self.analyze_page_with_vision(page_image, page_num)
                self.page_analysis[page_num] = page_analysis
                
                # Process found questions
                questions = page_analysis.get('questions_found', [])
                if questions:
                    logger.info(f"✅ Found {len(questions)} questions on page {page_num}")
                    for q in questions:
                        q['source_page'] = page_num
                        self.all_questions.append(q)
                        self.total_questions_found += 1
                        
                        # Log the question
                        print(f"\n🔢 Question {q.get('question_number', 'N/A')}:")
                        print(f"   Text: {q.get('question_text', '')[:100]}...")
                        print(f"   Words: {q.get('word_limit', 'N/A')}")
                        print(f"   Marks: {q.get('marks', 'N/A')}")
                else:
                    logger.info(f"   No questions found on page {page_num}")
            
            # If we haven't found all 19 questions, scan remaining pages
            if self.total_questions_found < 19:
                logger.info(f"🔍 Phase 2: Found {self.total_questions_found}/19 questions, scanning remaining pages...")
                
                remaining_pages = [i for i in range(1, len(doc) + 1) if i not in question_pages]
                
                for page_num in remaining_pages:
                    logger.info(f"📄 Analyzing page {page_num} with Vision AI...")
                    
                    page_image = self.pdf_page_to_base64_image(doc, page_num - 1, zoom_factor=2.5)
                    if not page_image:
                        continue
                    
                    page_analysis = await self.analyze_page_with_vision(page_image, page_num)
                    self.page_analysis[page_num] = page_analysis
                    
                    questions = page_analysis.get('questions_found', [])
                    if questions:
                        logger.info(f"✅ Found {len(questions)} questions on page {page_num}")
                        for q in questions:
                            q['source_page'] = page_num
                            self.all_questions.append(q)
                            self.total_questions_found += 1
                    
                    # Stop if we found all 19 questions
                    if self.total_questions_found >= 19:
                        logger.info("🎯 Found all expected questions!")
                        break
            
            doc.close()
            
            logger.info(f"📊 Vision extraction complete: Found {self.total_questions_found} questions")
            
            return self.compile_results()
            
        except Exception as e:
            logger.error(f"❌ Vision extraction failed: {e}")
            return {"error": str(e), "questions": [], "total_questions": 0}

    def compile_results(self) -> Dict:
        """Compile final extraction results"""
        
        # Sort questions by question number
        sorted_questions = sorted(self.all_questions, key=lambda x: x.get('question_number', 0))
        
        # Calculate total marks
        total_marks = sum(q.get('marks', 0) for q in sorted_questions)
        
        # Find question pages
        question_pages = list(set(q.get('source_page') for q in sorted_questions))
        question_pages.sort()
        
        results = {
            "source_file": PDF_PATH,
            "extraction_method": "GPT-4 Vision Analysis",
            "extraction_timestamp": str(asyncio.get_event_loop().time()),
            "total_questions_found": self.total_questions_found,
            "expected_questions": 19,
            "total_marks": total_marks,
            "question_pages": question_pages,
            "questions": sorted_questions,
            "page_analysis": self.page_analysis,
            "extraction_metadata": {
                "pdf_pages_total": len(fitz.open(PDF_PATH)),
                "pages_analyzed": len(self.page_analysis),
                "vision_model": "gpt-4-vision-preview",
                "image_resolution": "2.5x zoom",
                "success_rate": f"{self.total_questions_found}/19"
            }
        }
        
        return results

    def save_results(self, results: Dict):
        """Save extraction results to JSON file"""
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Results saved to: {OUTPUT_FILE}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

    def print_summary(self, results: Dict):
        """Print extraction summary"""
        
        print("\n" + "=" * 60)
        print("📋 VisionIAS PDF Question Extraction Results (Vision AI)")
        print("=" * 60)
        
        print(f"📄 Source: {os.path.basename(PDF_PATH)}")
        print(f"📊 Total Questions Found: {results['total_questions_found']}/19 (expected)")
        print(f"📈 Total Marks: {results['total_marks']}")
        print(f"🔧 Method: {results['extraction_method']}")
        print(f"📋 Question Pages: {', '.join(map(str, results['question_pages']))}")
        
        if results['questions']:
            print(f"\n📝 Questions Found:")
            for i, q in enumerate(results['questions'], 1):
                print(f"  {i}. Q{q.get('question_number', '?')}: {q.get('question_text', '')[:80]}...")
                print(f"      Words: {q.get('word_limit', 'N/A')}, Marks: {q.get('marks', 'N/A')}, Page: {q.get('source_page', 'N/A')}")
        
        print(f"\n💾 Detailed results saved to: {OUTPUT_FILE}")
        print("=" * 60)
        print("📊 EXTRACTION STATISTICS")
        print("=" * 60)
        print(f"✅ Questions Found: {results['total_questions_found']}/19 (expected)")
        print(f"📈 Total Marks: {results['total_marks']}")
        print(f"📄 Question Pages: {len(results['question_pages'])}")
        print(f"🔧 Method: Vision-based GPT-4 Analysis")
        
        if results['total_questions_found'] >= 15:
            print("🎉 EXCELLENT: Most questions extracted successfully!")
        elif results['total_questions_found'] >= 10:
            print("✅ GOOD: Majority of questions extracted!")
        elif results['total_questions_found'] >= 5:
            print("⚠️ PARTIAL: Some questions extracted, may need refinement")
        else:
            print("❌ LIMITED: Few questions extracted, check vision analysis")
        
        print("\n🏁 Vision-based extraction completed!")
        print(f"📋 Found {results['total_questions_found']} questions using GPT-4 Vision")
        print(f"📄 Check {os.path.basename(OUTPUT_FILE)} for full details")

async def main():
    """Main extraction workflow"""
    extractor = VisionBasedPDFExtractor()
    
    try:
        # Extract questions using vision analysis
        results = await extractor.extract_all_questions()
        
        # Save and display results
        extractor.save_results(results)
        extractor.print_summary(results)
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
