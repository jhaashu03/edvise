#!/usr/bin/env python3
"""
PYQ DOCX Parser and Database Builder
Parses DOCX files from PYQ/MAINS directory and builds Milvus database with proper labeling
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import time
from docx import Document
from sentence_transformers import SentenceTransformer
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PYQDocxParser:
    def __init__(self):
        self.pyq_dir = "/Users/a0j0agc/Desktop/Personal/Dump/PYQ/MAINS"
        self.collection_name = "pyq_embeddings"
        self.db_path = "./milvus_lite_local.db"
        self.embedding_model = None
        self.collection = None
        
    def load_embedding_model(self):
        """Load embedding model"""
        try:
            logger.info("🧠 Loading embedding model...")
            
            # Use offline mode to avoid SSL certificate issues
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            logger.info("✅ Embedding model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            return False
    
    def connect_to_database(self):
        """Connect to Milvus database"""
        try:
            logger.info("🔌 Connecting to database...")
            
            # Remove existing database if exists for a fresh start
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"🗑️ Removed existing database: {self.db_path}")
            
            connections.connect(
                alias="default",
                uri=self.db_path
            )
            logger.info("✅ Connected to database")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def create_collection(self):
        """Create collection with schema"""
        try:
            logger.info("📊 Creating collection schema...")
            
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="pyq_id", dtype=DataType.INT64),
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="year", dtype=DataType.INT64),
                FieldSchema(name="paper", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="topics", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="difficulty", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            
            schema = CollectionSchema(fields, "PYQ embeddings for semantic search")
            
            # Create collection
            self.collection = Collection(self.collection_name, schema)
            logger.info("✅ Created collection")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create collection: {e}")
            return False
    
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
                        pyq_id = int(f"{year}{int(current_paper[2])}{question_number:02d}")
                        
                        # Create question object
                        question = {
                            "pyq_id": pyq_id,
                            "question_text": clean_text,
                            "year": year,
                            "paper": current_paper,
                            "subject": self.get_subject_for_paper(current_paper),
                            "topics": self.extract_topics(clean_text),
                            "difficulty": self.get_difficulty(marks),
                            "marks": marks,
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
        # Remove marks info
        text = re.sub(r'\(\d+\s*marks\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*marks', '', text, flags=re.IGNORECASE)
        
        # Remove word limit info
        text = re.sub(r'\(\d+\s*words\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*words', '', text, flags=re.IGNORECASE)
        
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
    
    def generate_embeddings(self, questions: List[Dict[str, Any]]):
        """Generate embeddings for all questions"""
        logger.info("🧠 Generating embeddings for questions...")
        
        # Create a list of question texts
        texts = [q["question_text"] for q in questions]
        
        # Generate embeddings in batches to avoid memory issues
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logger.info(f"  📊 Processing batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            batch_embeddings = self.embedding_model.encode(batch_texts, show_progress_bar=True)
            all_embeddings.extend(batch_embeddings)
        
        # Add embeddings to questions
        for i, question in enumerate(questions):
            question["embedding"] = all_embeddings[i].tolist()
        
        logger.info("✅ Generated embeddings for all questions")
        return questions
    
    def insert_questions(self, questions: List[Dict[str, Any]]):
        """Insert questions into collection"""
        logger.info(f"💾 Inserting {len(questions)} questions into database...")
        
        # Prepare data for insertion
        pyq_ids = [q["pyq_id"] for q in questions]
        question_texts = [q["question_text"] for q in questions]
        subjects = [q["subject"] for q in questions]
        years = [q["year"] for q in questions]
        papers = [q["paper"] for q in questions]
        topics = [q["topics"] for q in questions]
        difficulties = [q["difficulty"] for q in questions]
        marks = [q["marks"] for q in questions]
        embeddings = [q["embedding"] for q in questions]
        
        # Insert data
        self.collection.insert([
            pyq_ids, question_texts, subjects, years, papers, 
            topics, difficulties, marks, embeddings
        ])
        
        self.collection.flush()
        logger.info("✅ Inserted all questions")
    
    def create_index(self):
        """Create vector search index"""
        logger.info("🔍 Creating search index...")
        
        # Create FLAT index (exact search)
        index_params = {
            "metric_type": "COSINE",
            "index_type": "FLAT",
            "params": {}
        }
        
        self.collection.create_index("embedding", index_params)
        self.collection.load()
        
        logger.info("✅ Created search index")
    
    def test_search(self):
        """Test search functionality"""
        logger.info("🔍 Testing search...")
        
        test_query = "women leadership"
        logger.info(f"  🔎 Searching for: '{test_query}'")
        
        # Create embedding for query
        query_embedding = self.embedding_model.encode([test_query])[0].tolist()
        
        # Search parameters
        search_params = {
            "metric_type": "COSINE"
        }
        
        # Search
        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=3,
            output_fields=["pyq_id", "question_text", "year", "paper", "subject"]
        )
        
        # Display results
        logger.info("  📊 Search results:")
        for i, hit in enumerate(results[0]):
            logger.info(f"    {i+1}. {hit.entity.get('year')} {hit.entity.get('paper')}: {hit.score:.4f}")
            logger.info(f"       {hit.entity.get('question_text')[:80]}...")
    
    def run(self):
        """Run the full pipeline"""
        try:
            logger.info("🚀 Starting PYQ DOCX parser and database builder...")
            
            # Load embedding model
            if not self.load_embedding_model():
                return False
            
            # Connect to database
            if not self.connect_to_database():
                return False
            
            # Create collection
            if not self.create_collection():
                return False
            
            # Parse DOCX files
            questions = self.parse_docx_files()
            if not questions:
                logger.error("❌ No questions found!")
                return False
            
            # Generate embeddings
            questions = self.generate_embeddings(questions)
            
            # Insert questions
            self.insert_questions(questions)
            
            # Create index
            self.create_index()
            
            # Test search
            self.test_search()
            
            # Print stats
            count = self.collection.num_entities
            logger.info(f"🎉 Database build complete! {count} questions added.")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False
        
        finally:
            # Disconnect
            try:
                connections.disconnect("default")
            except:
                pass

if __name__ == "__main__":
    parser = PYQDocxParser()
    success = parser.run()
    
    if success:
        print("\n✅ PYQ database successfully built!")
        print("🚀 Now restart your backend server to use the new database.")
    else:
        print("\n❌ Failed to build PYQ database. See logs for details.")
