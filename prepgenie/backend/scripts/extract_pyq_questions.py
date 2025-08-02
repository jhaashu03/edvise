#!/usr/bin/env python3
"""
PYQ Question Extractor - Parses DOCX files and extracts questions with proper labeling
This script focuses on parsing without embedding generation to avoid SSL issues
"""

import os
import re
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from docx import Document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PYQExtractor:
    def __init__(self):
        self.pyq_dir = "/Users/a0j0agc/Desktop/Personal/Dump/PYQ/MAINS"
        self.output_file = "./pyq_questions.json"
    
    def parse_docx_files(self):
        """Parse all DOCX files in directory"""
        logger.info("📂 Scanning directory for DOCX files...")
        
        all_questions = []
        file_count = 0
        
        for filename in os.listdir(self.pyq_dir):
            # Skip hidden files and temp files
            if filename.startswith('.') or filename.startswith('~'):
                continue
            
            # Only process DOCX files
            if not filename.lower().endswith('.docx'):
                continue
            
            file_path = os.path.join(self.pyq_dir, filename)
            
            # Extract year from filename
            year_match = re.search(r'(\d{4})', filename)
            if not year_match:
                logger.warning(f"⚠️ Could not extract year from filename: {filename}")
                continue
            
            year = int(year_match.group(1))
            logger.info(f"📄 Processing {filename} (Year: {year})")
            
            # Parse DOCX file
            questions = self.parse_single_docx(file_path, year)
            all_questions.extend(questions)
            file_count += 1
            
            logger.info(f"✅ Extracted {len(questions)} questions from {filename}")
            
        logger.info(f"📊 Processed {file_count} files, found {len(all_questions)} questions")
        return all_questions
    
    def parse_single_docx(self, file_path: str, year: int) -> List[Dict[str, Any]]:
        """Parse a single DOCX file"""
        try:
            doc = Document(file_path)
            questions = []
            
            current_paper = None
            current_section = None
            question_number = 0
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Detect paper headers (GS Paper 1, etc.)
                paper_match = re.search(r'(?:G\.?S\.?|General Studies)\s*Paper\s*(\d+)', text, re.IGNORECASE)
                if paper_match:
                    paper_num = paper_match.group(1)
                    current_paper = f"GS{paper_num}"
                    logger.info(f"  📑 Found {current_paper}")
                    question_number = 0  # Reset question numbering for new paper
                    continue
                
                # Detect section headers if any
                section_match = re.search(r'Section\s+([A-Z])', text, re.IGNORECASE)
                if section_match:
                    current_section = section_match.group(1)
                    continue
                
                # Detect questions (Q.1, Q.2, etc.)
                question_match = re.search(r'Q\.?\s*(\d+)\.?\s*(.*)', text, re.IGNORECASE)
                if question_match and current_paper:
                    question_number = int(question_match.group(1))
                    question_text = question_match.group(2).strip()
                    
                    # Extract marks and word limit
                    marks = self.extract_marks(question_text)
                    word_limit = self.extract_word_limit(question_text)
                    
                    # Clean question text
                    clean_text = self.clean_question_text(question_text)
                    
                    if clean_text and len(clean_text) > 10:
                        # Generate unique ID
                        pyq_id = f"{year}_{current_paper}_Q{question_number}"
                        
                        # Create question object
                        question = {
                            "id": pyq_id,
                            "question_text": clean_text,
                            "year": year,
                            "paper": current_paper,
                            "subject": self.get_subject_for_paper(current_paper),
                            "topics": self.extract_topics(clean_text),
                            "difficulty": self.get_difficulty(marks),
                            "marks": marks,
                            "word_limit": word_limit,
                            "question_number": f"Q.{question_number}"
                        }
                        
                        questions.append(question)
            
            return questions
            
        except Exception as e:
            logger.error(f"❌ Error parsing file {file_path}: {e}")
            return []
    
    def extract_marks(self, text: str) -> int:
        """Extract marks from question text"""
        marks_match = re.search(r'(\d+)\s*marks', text, re.IGNORECASE)
        if marks_match:
            return int(marks_match.group(1))
        return 10  # Default if not specified
    
    def extract_word_limit(self, text: str) -> int:
        """Extract word limit from question text"""
        words_match = re.search(r'(\d+)\s*words', text, re.IGNORECASE)
        if words_match:
            return int(words_match.group(1))
        return 150  # Default if not specified
    
    def clean_question_text(self, text: str) -> str:
        """Clean question text by removing marks/words info"""
        # Remove marks and word limit patterns
        text = re.sub(r'\(\d+\s*words?,?\s*\d+\s*marks?\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\d+\s*marks?,?\s*\d+\s*words?\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*marks?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*words?', '', text, flags=re.IGNORECASE)
        
        # Clean up remaining parentheses
        text = re.sub(r'\(\s*\)', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_subject_for_paper(self, paper: str) -> str:
        """Map paper to subject area"""
        paper_subjects = {
            "GS1": "History, Geography, Society",
            "GS2": "Governance, Constitution, International Relations",
            "GS3": "Economy, Environment, Science & Technology",
            "GS4": "Ethics, Integrity, Aptitude"
        }
        return paper_subjects.get(paper, "General Studies")
    
    def extract_topics(self, text: str) -> str:
        """Extract potential topics from text"""
        # Simple keyword extraction - this can be enhanced
        topics = []
        
        # Check for common UPSC keywords
        keywords = {
            "history": ["history", "ancient", "medieval", "modern", "independence", "freedom", "movement"],
            "polity": ["constitution", "governance", "democracy", "rights", "parliament", "executive"],
            "economy": ["economy", "economic", "finance", "banking", "poverty", "development"],
            "geography": ["geography", "climate", "resources", "disaster", "environment"],
            "international": ["foreign", "relations", "international", "bilateral", "global"],
            "science": ["science", "technology", "innovation", "research", "digital"],
            "society": ["society", "women", "gender", "social", "empowerment", "caste"],
            "environment": ["environment", "ecology", "pollution", "conservation", "biodiversity"],
            "ethics": ["ethics", "integrity", "values", "attitude", "aptitude", "governance"]
        }
        
        text_lower = text.lower()
        for category, words in keywords.items():
            for word in words:
                if word in text_lower:
                    topics.append(category)
                    break
        
        # If no topics found, use paper subject
        if not topics:
            topics = ["general"]
        
        return ", ".join(set(topics))
    
    def get_difficulty(self, marks: int) -> str:
        """Determine difficulty based on marks"""
        if marks <= 10:
            return "Easy"
        elif marks <= 15:
            return "Medium"
        else:
            return "Hard"
    
    def save_to_json(self, questions: List[Dict[str, Any]]):
        """Save questions to JSON file"""
        try:
            with open(self.output_file, 'w') as f:
                json.dump(questions, f, indent=2)
            
            logger.info(f"✅ Saved {len(questions)} questions to {self.output_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save questions to JSON: {e}")
            return False
    
    def print_sample_stats(self, questions: List[Dict[str, Any]]):
        """Print sample statistics"""
        logger.info("\n📊 QUESTION STATISTICS:")
        
        # Count by year
        years = {}
        for q in questions:
            year = q["year"]
            if year not in years:
                years[year] = 0
            years[year] += 1
        
        # Count by paper
        papers = {}
        for q in questions:
            paper = q["paper"]
            if paper not in papers:
                papers[paper] = 0
            papers[paper] += 1
        
        # Print stats
        logger.info("  Years:")
        for year in sorted(years.keys()):
            logger.info(f"    {year}: {years[year]} questions")
        
        logger.info("  Papers:")
        for paper in sorted(papers.keys()):
            logger.info(f"    {paper}: {papers[paper]} questions")
        
        # Print a few sample questions
        logger.info("\n📝 SAMPLE QUESTIONS:")
        for i, q in enumerate(questions[:3]):
            logger.info(f"  {i+1}. [{q['year']} {q['paper']}] {q['question_text'][:100]}...")
    
    def run(self):
        """Run the extraction process"""
        try:
            logger.info("🚀 Starting PYQ question extraction...")
            
            # Parse DOCX files
            questions = self.parse_docx_files()
            if not questions:
                logger.error("❌ No questions found!")
                return False
            
            # Print statistics
            self.print_sample_stats(questions)
            
            # Save to JSON
            self.save_to_json(questions)
            
            logger.info(f"🎉 Extraction complete! {len(questions)} questions extracted.")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False

if __name__ == "__main__":
    extractor = PYQExtractor()
    success = extractor.run()
    
    if success:
        print("\n✅ PYQ questions successfully extracted!")
        print("📄 Questions saved to pyq_questions.json")
        print("\n🚀 Next steps:")
        print("1. Import these questions to your database")
        print("2. Use them to build your search index")
    else:
        print("\n❌ Failed to extract PYQ questions. See logs for details.")
