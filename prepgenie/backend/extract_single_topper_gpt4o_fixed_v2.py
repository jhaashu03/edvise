#!/usr/bin/env python3
"""
Fixed Single Topper PDF Extraction with GPT-4o (One Page at a Time)
==================================================================

This script correctly extracts questions and answers from a single topper PDF using GPT-4o
and saves the results in a clean JSON format ready for Mil                                # Collect ALL cont                        if extra_page in page_content_map and extra_page not in processed_pages:
                            extra_questions = page_content_map[extra_page]
                            for extra_q in extra_questions:
                                # Fix: Check if extra_q is not None and is a dict before calling methods
                                if extra_q is None or not isinstance(extra_q, dict):
                                    continue
                                
                                extra_answer = extra_q.get("answer_text", "")
                                extra_question_text = extra_q.get("question_text", "")
                                
                                # Ensure we have strings before calling strip()
                                if not isinstance(extra_answer, str):
                                    extra_answer = str(extra_answer) if extra_answer else ""
                                if not isinstance(extra_question_text, str):
                                    extra_question_text = str(extra_question_text) if extra_question_text else ""
                                
                                extra_answer = extra_answer.strip()
                                extra_question_text = extra_question_text.strip()
                                
                                # If it looks like continuation (no clear new question)
                                if extra_answer and not extra_question_text and len(extra_answer) > 30:
                                    complete_answer += f"\n{extra_answer}"
                                    pages_spanned.append(extra_page)
                                    processed_pages.add(extra_page)
                                    print(f"   🔗 Added extra page {extra_page} continuation to Q{q_num}")
                                    break page that could be continuation
                                page_content = []
                                for next_q in next_page_questions:
                                    # Fix: Check if next_q is not None and is a dict before calling methods
                                    if next_q is None or not isinstance(next_q, dict):
                                        continue
                                    
                                    next_answer = next_q.get("answer_text", "")
                                    next_question_text = next_q.get("question_text", "")
                                    
                                    # Ensure we have strings before calling strip()
                                    if not isinstance(next_answer, str):
                                        next_answer = str(next_answer) if next_answer else ""
                                    if not isinstance(next_question_text, str):
                                        next_question_text = str(next_question_text) if next_question_text else ""
                                    
                                    next_answer = next_answer.strip()
                                    next_question_text = next_question_text.strip()
                                    
                                    # Include content if:
                                    # 1. It has answer text, OR
                                    # 2. It's detected as continuation content, OR  
                                    # 3. It has no clear question text (likely continuation)
                                    if next_answer and (not next_question_text or len(next_answer) > 50):
                                        page_content.append(next_answer)g.

FEATURES:
- One page at a time processing to avoid token limits
- Proper page-by-page question handling
- Correct multi-page answer continuation detection using marks-based logic
- Batch processing with configurable batch size
- No incorrect merging of different questions

Output Format:
{
    "pdf_metadata": {...},
    "questions": {
        "page_3_question_1": {
            "question_text": "...",
            "metadata": {...},
            "answer_text": "..."
        },
        "page_5_question_2": {...}
    }
}

Usage:
    python extract_single_topper_gpt4o_fixed_v2.py --pdf_path "path/to/pdf" --year 2024 --batch_size 3
"""

import json
import asyncio
import argparse
import fitz  # PyMuPDF
import base64
from pathlib import Path
from datetime import datetime
import sys
import os

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.core.llm_service import LLMService

class FixedTopperExtractor:
    def __init__(self, output_base_dir="/Users/a0j0agc/Desktop/Personal/Dump/ExtractedToppersCopy"):
        self.output_base_dir = Path(output_base_dir)
        self.llm_service = LLMService()
        
    def create_output_structure(self, year):
        """Create year-based output directory structure"""
        year_dir = self.output_base_dir / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)
        return year_dir
    
    def pdf_page_to_base64(self, pdf_path: str, page_num: int) -> str:
        """Convert PDF page to base64 image"""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
        img_data = pix.tobytes("png")
        doc.close()
        return base64.b64encode(img_data).decode('utf-8')
    
    def get_enhanced_vision_prompt(self) -> str:
        """Get the enhanced vision prompt for GPT-4o"""
        return """You are an expert OCR system specializing in handwritten text extraction from UPSC exam answer sheets.

TASK: Extract questions and answers from this handwritten answer sheet page.

REQUIREMENTS:
1. QUESTIONS: Look for numbered questions (1, 2, 3, etc.) with text content and word limits
2. ANSWERS: Extract all handwritten answer text for each question ON THIS PAGE ONLY
3. CONTINUATION: If this page only has answer text without a question, it's likely a continuation
4. FORMATTING: Preserve line breaks and paragraph structure
5. ACCURACY: Focus on complete text extraction, not perfect spelling

OUTPUT FORMAT (JSON):
{
  "page_analysis": {
    "page_has_questions": boolean,
    "page_has_answers": boolean,
    "estimated_questions_count": number
  },
  "questions_found": [
    {
      "question_number": "1",
      "question_text": "exact question text with word limit if present OR empty string if no question",
      "marks_allocated": "10",
      "word_limit": "150 words",
      "answer_text": "ONLY the handwritten answer text visible on THIS PAGE",
      "answer_continues": boolean,
      "handwriting_quality": "good/moderate/poor",
      "page_number": current_page_number,
      "content_type": "question_with_answer" OR "answer_continuation" OR "mixed"
    }
  ]
}

CRITICAL INSTRUCTIONS:
- If you see a numbered question (like "1.", "2.", etc.) with marks/words, set content_type: "question_with_answer"
- If you only see answer text without a clear question, set content_type: "answer_continuation" and leave question_text empty
- Extract ALL visible text from THIS PAGE ONLY
- Do NOT combine text from multiple questions
- Be precise about what constitutes a "question" vs "answer continuation\""""
    
    def extract_pdf_metadata(self, pdf_path):
        """Extract metadata from PDF path and file"""
        pdf_path = Path(pdf_path)
        
        # Get page count
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        metadata = {
            "filename": pdf_path.name,
            "file_size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "total_pages": total_pages,
            "extraction_timestamp": datetime.now().isoformat(),
            "extraction_method": "gpt-4o_vision_fixed_v2",
            "model_used": "gpt-4o",
            "processing_mode": "one_page_at_a_time"
        }
        
        # Try to extract year from filename or path
        filename = pdf_path.name.lower()
        for year in [2024, 2023, 2022, 2021, 2020]:
            if str(year) in filename or str(year) in str(pdf_path):
                metadata["year"] = year
                break
        
        return metadata

    async def extract_single_page(self, pdf_path, page_num, total_pages):
        """Extract content from a single page to avoid token limits"""
        try:
            print(f"📖 Processing page {page_num + 1}/{total_pages}...")
            
            # Convert page to base64
            page_image = self.pdf_page_to_base64(pdf_path, page_num)
            
            # Create vision message
            vision_message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{self.get_enhanced_vision_prompt()}\n\nPage Number: {page_num + 1}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{page_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Call GPT-4o vision for this single page
            response = await self.llm_service.vision_chat(
                messages=vision_message,
                model="gpt-4o",
                max_tokens=4000,
                temperature=0.1
            )
            
            if response and response.strip():
                try:
                    # Clean response (remove markdown if present)
                    clean_response = response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response.replace("```json", "").replace("```", "").strip()
                    
                    page_result = json.loads(clean_response)
                    page_result["page_number"] = page_num + 1
                    
                    questions_found = page_result.get('questions_found', [])
                    questions_count = len(questions_found)
                    
                    if questions_count > 0:
                        # Analyze what type of content we found
                        actual_questions = 0
                        answer_continuations = 0
                        
                        for q in questions_found:
                            question_text = (q.get("question_text") or "").strip()
                            answer_text = (q.get("answer_text") or "").strip()
                            marks_allocated = q.get("marks_allocated", "")
                            
                            if question_text and marks_allocated:
                                actual_questions += 1
                            elif answer_text and not question_text:
                                answer_continuations += 1
                        
                        # Provide accurate logging
                        if actual_questions > 0 and answer_continuations > 0:
                            print(f"✅ Page {page_num + 1}: Found {actual_questions} questions + {answer_continuations} answer continuations")
                        elif actual_questions > 0:
                            print(f"✅ Page {page_num + 1}: Found {actual_questions} questions")
                        elif answer_continuations > 0:
                            print(f"📝 Page {page_num + 1}: Found {answer_continuations} answer continuations (no new questions)")
                        else:
                            print(f"📄 Page {page_num + 1}: Found content but unclear type")
                    else:
                        print(f"📄 Page {page_num + 1}: No questions found")
                    
                    return page_result
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error on page {page_num + 1}: {e}")
                    print(f"Raw response: {response[:200]}...")
                    return {"page_number": page_num + 1, "questions_found": []}
            else:
                print(f"⚠️ Page {page_num + 1}: Empty response")
                return {"page_number": page_num + 1, "questions_found": []}
                
        except Exception as e:
            print(f"❌ Error processing page {page_num + 1}: {str(e)}")
            return {"page_number": page_num + 1, "questions_found": []}

    async def extract_questions_and_answers(self, pdf_path, batch_size=5):
        """Extract questions and answers using one-page-at-a-time processing with batching"""
        print(f"🔍 Extracting from: {pdf_path}")
        print(f"⚡ Processing pages one at a time (batch size: {batch_size}) to avoid token limits")
        
        # Get PDF metadata for page count
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        print(f"📄 Total pages: {total_pages}")
        
        all_page_results = []
        
        # Process pages in batches to avoid overwhelming the system
        for batch_start in range(0, total_pages, batch_size):
            batch_end = min(batch_start + batch_size, total_pages)
            print(f"\n🔄 Processing batch: pages {batch_start + 1}-{batch_end}")
            
            # Process pages in current batch
            batch_tasks = []
            for page_num in range(batch_start, batch_end):
                task = self.extract_single_page(pdf_path, page_num, total_pages)
                batch_tasks.append(task)
            
            # Wait for all pages in batch to complete
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process batch results
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"❌ Batch error: {result}")
                    continue
                    
                if result and result.get("page_number"):
                    all_page_results.append(result)
            
            print(f"✅ Batch complete: {len(batch_results)} pages processed")
            
            # Small delay between batches to be respectful to the API
            if batch_end < total_pages:
                print("⏸️ Brief pause between batches...")
                await asyncio.sleep(2)
        
        print(f"\n🎯 Total pages processed: {len(all_page_results)}")
        return all_page_results
    
    def get_expected_pages_for_marks(self, marks_str):
        """Determine expected number of pages based on marks allocation"""
        try:
            # Extract numeric marks from string like "10", "15", "10 marks", etc.
            marks_num = int(''.join(filter(str.isdigit, str(marks_str))))
            
            if marks_num == 10:
                return 2  # 10 marks = 2 pages
            elif marks_num == 15:
                return 3  # 15 marks = 3 pages
            elif marks_num == 20:
                return 4  # 20 marks = 4 pages
            elif marks_num >= 25:
                return 5  # 25+ marks = 5 pages
            else:
                return 1  # Default for other marks (5, 7.5, etc.)
        except (ValueError, TypeError):
            return 1  # Default if marks parsing fails

    def marks_based_consolidation(self, all_page_results):
        """Consolidate answers based on marks allocation patterns (10 marks = 2 pages, 15 marks = 3 pages)"""
        print("🔗 Smart consolidation using marks-based page prediction...")
        
        consolidated_questions = {}
        page_content_map = {}
        
        # First pass: collect all content by page
        for page_result in all_page_results:
            page_num = page_result.get("page_number", 0)
            questions = page_result.get("questions_found", [])
            page_content_map[page_num] = questions
        
        # Second pass: process questions with marks-based consolidation
        processed_pages = set()
        
        # First, process all clear questions with marks
        main_questions = []
        for page_num in sorted(page_content_map.keys()):
            questions = page_content_map[page_num]
            for question in questions:
                question_text = (question.get("question_text") or "").strip()
                marks_allocated = question.get("marks_allocated", "")
                if question_text and marks_allocated:
                    main_questions.append((page_num, question))
        
        print(f"🎯 Found {len(main_questions)} main questions with marks allocation")
        
        # Process each main question with intelligent continuation search
        for page_num, question in main_questions:
            if page_num in processed_pages:
                continue
                
            q_num = question.get("question_number", "unknown")
            question_text = (question.get("question_text") or "").strip()
            answer_text = (question.get("answer_text") or "").strip()
            marks_allocated = question.get("marks_allocated", "")
            
            expected_pages = self.get_expected_pages_for_marks(marks_allocated)
            question_key = f"page_{page_num}_question_{q_num}"
            
            print(f"📝 Processing Q{q_num} ({marks_allocated} marks) - expecting {expected_pages} pages")
            
            # Collect answer from current page and expected continuation pages
            complete_answer = answer_text
            pages_spanned = [page_num]
            
            # If we expect multiple pages, collect content from expected range
            if expected_pages > 1:
                print(f"   🎯 Marks-based search: Looking for {expected_pages-1} continuation pages after page {page_num}")
                
                # Search for consecutive continuation pages
                pages_found = 1  # Already have the main page
                for page_offset in range(1, expected_pages + 2):  # +2 to allow for small gaps
                    next_page = page_num + page_offset
                    
                    if next_page in page_content_map and next_page not in processed_pages:
                        next_page_questions = page_content_map[next_page]
                        print(f"      🔍 Checking page {next_page} for Q{q_num} continuation...")
                        
                        # Check if this page has content that could be continuation
                        page_continuation_content = []
                        has_new_question = False
                        
                        for next_q in next_page_questions:
                            next_answer = (next_q.get("answer_text") or "").strip()
                            next_question_text = (next_q.get("question_text") or "").strip()
                            next_question_num = next_q.get("question_number", "")
                            next_marks = next_q.get("marks_allocated", "")
                            
                            # Check if this is clearly a NEW question (different number with marks)
                            if (next_question_num and str(next_question_num) != str(q_num) and 
                                str(next_question_num).isdigit() and next_marks and 
                                next_question_text and len(next_question_text) > 20):
                                print(f"      🛑 Found new Q{next_question_num} on page {next_page} - stopping search for Q{q_num}")
                                has_new_question = True
                                break
                            
                            # If it has answer content and no clear new question markers, treat as continuation
                            if next_answer and len(next_answer) > 15:
                                # Additional checks to avoid wrong content
                                is_likely_continuation = (
                                    not next_question_text or len(next_question_text) < 30 or  # No clear question
                                    not next_marks or  # No marks allocation
                                    (next_question_num and str(next_question_num) == str(q_num))  # Same question number
                                )
                                
                                if is_likely_continuation:
                                    page_continuation_content.append(next_answer)
                                    print(f"      📝 Found continuation content on page {next_page}")
                        
                        # If we found continuation content and no new question, add this page
                        if page_continuation_content and not has_new_question:
                            page_answer = "\n".join(page_continuation_content)
                            complete_answer += f"\n{page_answer}"
                            pages_spanned.append(next_page)
                            processed_pages.add(next_page)
                            pages_found += 1
                            print(f"   🔗 Added page {next_page} to Q{q_num} ({len(page_continuation_content)} content blocks)")
                            
                            # If we have enough pages, stop searching
                            if pages_found >= expected_pages:
                                print(f"   ✅ Q{q_num} complete: found {pages_found} pages")
                                break
                        elif has_new_question:
                            # Stop searching if we hit a new question
                            break
                        else:
                            print(f"   ⚠️ Page {next_page} has no relevant content for Q{q_num}")
                            # Don't break here - might be a gap, continue searching
                    else:
                        if next_page > page_num + expected_pages + 1:
                            # Stop if we're searching too far beyond expected range
                            print(f"   ⚠️ Stopping search at page {next_page} - beyond expected range")
                            break
                
                if pages_found < expected_pages:
                    print(f"   ⚠️ Q{q_num} incomplete: expected {expected_pages} pages, found {pages_found}")
                else:
                    print(f"   ✅ Q{q_num} complete: expected {expected_pages} pages, found {pages_found}")
            
            # Create consolidated question entry
            consolidated_questions[question_key] = {
                "question_text": question_text,
                "metadata": {
                    "question_number": q_num,
                    "marks_allocated": marks_allocated,
                    "word_limit": question.get("word_limit", ""),
                    "pages_spanned": pages_spanned,
                    "is_multi_page": len(pages_spanned) > 1,
                    "expected_pages": expected_pages,
                    "actual_pages": len(pages_spanned),
                    "handwriting_quality": question.get("handwriting_quality", "moderate"),
                    "estimated_word_count": len(complete_answer.split()) if complete_answer else 0,
                    "marks_based_consolidation": True
                },
                "complete_answer": complete_answer
            }
            
            processed_pages.add(page_num)
            print(f"✅ Q{q_num}: Expected {expected_pages} pages, got {len(pages_spanned)} pages, {len(complete_answer.split())} words")
        
        # Handle any remaining unprocessed content as orphans (should be minimal now)
        for page_num in sorted(page_content_map.keys()):
            if page_num in processed_pages:
                continue
                
            questions = page_content_map[page_num]
            for question in questions:
                answer_text = (question.get("answer_text") or "").strip()
                if answer_text:
                    q_num = question.get("question_number", "unknown")
                    orphan_key = f"page_{page_num}_orphan_{q_num}"
                    consolidated_questions[orphan_key] = {
                        "question_text": f"[Orphaned content - Q{q_num}]",
                        "metadata": {
                            "question_number": q_num,
                            "marks_allocated": question.get("marks_allocated", ""),
                            "word_limit": question.get("word_limit", ""),
                            "pages_spanned": [page_num],
                            "is_multi_page": False,
                            "expected_pages": 1,
                            "handwriting_quality": question.get("handwriting_quality", "moderate"),
                            "estimated_word_count": len(answer_text.split()) if answer_text else 0,
                            "note": "Orphaned content - could not consolidate with main question"
                        },
                        "complete_answer": answer_text
                    }
                    print(f"⚠️ Orphaned content: {orphan_key}")
        
        print(f"✅ Consolidated into {len(consolidated_questions)} questions using improved marks-based logic")
        return consolidated_questions
    
    def save_extraction_results(self, pdf_metadata, consolidated_questions, output_dir, pdf_name):
        """Save results in clean JSON format"""
        
        # Create final structure
        final_result = {
            "pdf_metadata": pdf_metadata,
            "extraction_summary": {
                "total_questions": len(consolidated_questions),
                "multi_page_questions": sum(1 for q in consolidated_questions.values() 
                                          if q["metadata"]["is_multi_page"]),
                "total_pages_processed": len(set(
                    page for q in consolidated_questions.values() 
                    for page in q["metadata"]["pages_spanned"]
                )) if consolidated_questions else 0
            },
            "questions": consolidated_questions
        }
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_pdf_name = Path(pdf_name).stem
        output_filename = f"{clean_pdf_name}_FIXED_V2_extracted_{timestamp}.json"
        output_path = output_dir / output_filename
        
        # Save JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Results saved to: {output_path}")
        return output_path
    
    async def process_single_pdf(self, pdf_path, year=None, batch_size=5):
        """Process a single PDF and save results"""
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return None
        
        print(f"🚀 Starting FIXED extraction (V2 - One Page at a Time) for: {pdf_path.name}")
        print(f"📄 File size: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
        print(f"⚙️ Batch size: {batch_size} pages")
        
        # Extract metadata
        pdf_metadata = self.extract_pdf_metadata(pdf_path)
        if year:
            pdf_metadata["year"] = year
        pdf_metadata["batch_size"] = batch_size
        
        # Create output directory
        extraction_year = year or pdf_metadata.get("year", datetime.now().year)
        output_dir = self.create_output_structure(extraction_year)
        
        # Extract questions and answers
        start_time = datetime.now()
        all_page_results = await self.extract_questions_and_answers(pdf_path, batch_size)
        extraction_time = (datetime.now() - start_time).total_seconds()
        
        print(f"⏱️ Extraction completed in {extraction_time:.2f} seconds")
        
        if not all_page_results:
            print("❌ No pages processed successfully")
            return None
        
        # Smart consolidation using marks-based logic
        consolidated_questions = self.marks_based_consolidation(all_page_results)
        
        # Add timing to metadata
        pdf_metadata["extraction_time_seconds"] = round(extraction_time, 2)
        pdf_metadata["pages_processed"] = len(all_page_results)
        pdf_metadata["consolidated_questions"] = len(consolidated_questions)
        
        # Save results
        output_path = self.save_extraction_results(
            pdf_metadata, consolidated_questions, output_dir, pdf_path.name
        )
        
        # Print summary
        print("\n" + "="*60)
        print("📊 FIXED EXTRACTION SUMMARY (V2)")
        print("="*60)
        print(f"📁 PDF: {pdf_path.name}")
        print(f"📅 Year: {extraction_year}")
        print(f"⚙️ Batch size: {batch_size} pages")
        print(f"⏱️ Processing time: {extraction_time:.2f} seconds")
        print(f"📄 Pages processed: {len(all_page_results)}")
        print(f"🔍 Questions found: {len(consolidated_questions)}")
        print(f"📄 Multi-page questions: {sum(1 for q in consolidated_questions.values() if q['metadata']['is_multi_page'])}")
        print(f"💾 Saved to: {output_path}")
        print("="*60)
        
        return output_path

async def main():
    parser = argparse.ArgumentParser(description="Extract questions/answers from a single topper PDF (FIXED VERSION V2)")
    parser.add_argument("--pdf_path", required=True, help="Path to the PDF file")
    parser.add_argument("--year", type=int, help="Year for organizing output (e.g., 2024)")
    parser.add_argument("--batch_size", type=int, default=3, help="Number of pages to process in each batch (default: 3)")
    
    args = parser.parse_args()
    
    extractor = FixedTopperExtractor()
    result = await extractor.process_single_pdf(args.pdf_path, args.year, args.batch_size)
    
    if result:
        print(f"\n🎯 SUCCESS: Fixed extraction complete!")
        print(f"📂 This version processes pages one at a time to avoid token limits")
        print(f"🔄 Next: Use this fixed version for all future extractions")
    else:
        print(f"\n❌ FAILED: Extraction unsuccessful")

if __name__ == "__main__":
    asyncio.run(main())
