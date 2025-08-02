#!/usr/bin/env python3
"""
PYQ Database Rebuilder
Parses individual questions from organized PYQ DOCX files and rebuilds Milvus database
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import asyncio
from docx import Document
import sqlite3
from sentence_transformers import SentenceTransformer
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import uuid

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PYQDatabaseRebuilder:
    def __init__(self):
        self.pyq_dir = "/Users/a0j0agc/Desktop/Personal/Dump/PYQ/MAINS"
        self.embedding_model = None
        self.collection = None
        
    def initialize_embedding_model(self):
        """Initialize the sentence transformer model"""
        try:
            logger.info("🧠 Loading embedding model...")
            
            # Try to bypass SSL verification for HuggingFace downloads
            import ssl
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # Try to load the model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load online model: {e}")
            logger.info("🔄 Trying to use cached model...")
            
            try:
                # Try to use cached model
                import os
                cache_dir = os.path.expanduser('~/.cache/huggingface/transformers')
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder=cache_dir)
                logger.info("✅ Cached embedding model loaded successfully")
            except Exception as e2:
                logger.error(f"❌ Failed to load cached model: {e2}")
                logger.info("💡 Please run: pip install --upgrade certifi")
                raise
    
    def connect_to_milvus(self):
        """Connect to Milvus and create collection"""
        try:
            logger.info("🔌 Connecting to Milvus...")
            connections.connect(alias="default", uri="./milvus_lite_local.db")
            
            # Define collection schema
            fields = [
                FieldSchema(name="pyq_id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=5000),
                FieldSchema(name="year", dtype=DataType.INT64),
                FieldSchema(name="paper", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="question_number", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="word_limit", dtype=DataType.INT64),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="topics", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="difficulty", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            
            schema = CollectionSchema(fields, "PYQ Questions Collection")
            
            # Drop existing collection if exists
            if utility.has_collection("pyq_embeddings"):
                utility.drop_collection("pyq_embeddings")
                logger.info("🗑️ Dropped existing collection")
            
            # Create new collection
            self.collection = Collection("pyq_embeddings", schema)
            logger.info("✅ Created new Milvus collection")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Milvus: {e}")
            raise
    
    def parse_docx_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a DOCX file and extract individual questions"""
        try:
            logger.info(f"📖 Parsing {os.path.basename(file_path)}...")
            
            # Extract year from filename
            year_match = re.search(r'(\d{4})', os.path.basename(file_path))
            year = int(year_match.group(1)) if year_match else 2024
            
            doc = Document(file_path)
            questions = []
            current_paper = None
            current_section = None
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # Detect paper sections
                paper_match = re.match(r'GS\s*Paper\s*(\d+)', text, re.IGNORECASE)
                if paper_match:
                    current_paper = f"GS{paper_match.group(1)}"
                    logger.info(f"  📄 Found {current_paper}")
                    continue
                
                # Detect section headers
                if re.match(r'Section\s*[A-Z]', text, re.IGNORECASE):
                    current_section = text
                    continue
                
                # Detect questions (Q.1, Q.2, etc.)
                question_match = re.match(r'Q\.?(\d+)\.?\s*(.*)', text, re.IGNORECASE)
                if question_match and current_paper:
                    question_num = question_match.group(1)
                    question_text = question_match.group(2).strip()
                    
                    # Extract marks and word limit
                    marks = self.extract_marks(question_text)
                    word_limit = self.extract_word_limit(question_text)
                    
                    # Clean question text (remove marks/word limit info)
                    clean_question = self.clean_question_text(question_text)
                    
                    if clean_question and len(clean_question) > 10:  # Valid question
                        question_data = {
                            'pyq_id': f"{year}_{current_paper}_Q{question_num}",
                            'question_text': clean_question,
                            'year': year,
                            'paper': current_paper,
                            'question_number': f"Q.{question_num}",
                            'marks': marks,
                            'word_limit': word_limit,
                            'subject': self.determine_subject(current_paper),
                            'topics': self.extract_topics(clean_question),
                            'difficulty': self.determine_difficulty(marks)
                        }
                        questions.append(question_data)
                        logger.info(f"    ✅ Q.{question_num}: {clean_question[:60]}...")
            
            logger.info(f"📊 Extracted {len(questions)} questions from {year}")
            return questions
            
        except Exception as e:
            logger.error(f"❌ Failed to parse {file_path}: {e}")
            return []
    
    def extract_marks(self, text: str) -> int:
        """Extract marks from question text"""
        marks_match = re.search(r'(\d+)\s*marks?', text, re.IGNORECASE)
        return int(marks_match.group(1)) if marks_match else 10  # Default 10 marks
    
    def extract_word_limit(self, text: str) -> int:
        """Extract word limit from question text"""
        word_match = re.search(r'(\d+)\s*words?', text, re.IGNORECASE)
        return int(word_match.group(1)) if word_match else 150  # Default 150 words
    
    def clean_question_text(self, text: str) -> str:
        """Clean question text by removing marks/word limit info"""
        # Remove marks and word limit patterns
        text = re.sub(r'\(\d+\s*words?,?\s*\d+\s*marks?\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(\d+\s*marks?,?\s*\d+\s*words?\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*marks?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\s*words?', '', text, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def determine_subject(self, paper: str) -> str:
        """Determine subject based on paper"""
        subject_map = {
            'GS1': 'History, Geography, Society',
            'GS2': 'Governance, Constitution, Social Justice',
            'GS3': 'Technology, Economy, Environment',
            'GS4': 'Ethics, Integrity, Aptitude'
        }
        return subject_map.get(paper, 'General Studies')
    
    def extract_topics(self, question_text: str) -> str:
        """Extract potential topics from question text"""
        # Simple keyword extraction - can be enhanced
        keywords = []
        
        # Common UPSC topics
        topic_patterns = [
            r'\b(constitution|fundamental rights|dpsp)\b',
            r'\b(governance|administration|bureaucracy)\b',
            r'\b(economy|economic|gdp|inflation)\b',
            r'\b(environment|climate|pollution)\b',
            r'\b(technology|digital|cyber)\b',
            r'\b(ethics|integrity|corruption)\b',
            r'\b(women|gender|empowerment)\b',
            r'\b(education|health|welfare)\b'
        ]
        
        for pattern in topic_patterns:
            matches = re.findall(pattern, question_text.lower())
            keywords.extend(matches)
        
        return ', '.join(list(set(keywords))) if keywords else 'general'
    
    def determine_difficulty(self, marks: int) -> str:
        """Determine difficulty based on marks"""
        if marks <= 10:
            return 'Easy'
        elif marks <= 15:
            return 'Medium'
        else:
            return 'Hard'
    
    def generate_embeddings(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for questions"""
        logger.info(f"🧠 Generating embeddings for {len(questions)} questions...")
        
        question_texts = [q['question_text'] for q in questions]
        embeddings = self.embedding_model.encode(question_texts, show_progress_bar=True)
        
        # Add embeddings to question data
        for i, question in enumerate(questions):
            question['embedding'] = embeddings[i].tolist()
        
        logger.info("✅ Embeddings generated successfully")
        return questions
    
    def insert_to_milvus(self, questions: List[Dict[str, Any]]):
        """Insert questions into Milvus collection"""
        logger.info(f"💾 Inserting {len(questions)} questions into Milvus...")
        
        # Prepare data for insertion
        data = [
            [q['pyq_id'] for q in questions],
            [q['question_text'] for q in questions],
            [q['year'] for q in questions],
            [q['paper'] for q in questions],
            [q['question_number'] for q in questions],
            [q['marks'] for q in questions],
            [q['word_limit'] for q in questions],
            [q['subject'] for q in questions],
            [q['topics'] for q in questions],
            [q['difficulty'] for q in questions],
            [q['embedding'] for q in questions]
        ]
        
        # Insert data
        self.collection.insert(data)
        self.collection.flush()
        
        logger.info("✅ Data inserted successfully")
    
    def create_index(self):
        """Create index for efficient search"""
        logger.info("🔍 Creating search index...")
        
        index_params = {
            "metric_type": "COSINE",
            "index_type": "FLAT",
            "params": {}
        }
        
        self.collection.create_index("embedding", index_params)
        self.collection.load()
        
        logger.info("✅ Index created and collection loaded")
    
    def rebuild_database(self):
        """Main function to rebuild the entire database"""
        try:
            logger.info("🚀 Starting PYQ database rebuild...")
            
            # Initialize components
            self.initialize_embedding_model()
            self.connect_to_milvus()
            
            all_questions = []
            
            # Process each DOCX file
            for filename in os.listdir(self.pyq_dir):
                if filename.endswith('.docx') and not filename.startswith('~'):
                    file_path = os.path.join(self.pyq_dir, filename)
                    questions = self.parse_docx_file(file_path)
                    all_questions.extend(questions)
            
            if not all_questions:
                logger.error("❌ No questions found!")
                return
            
            logger.info(f"📊 Total questions parsed: {len(all_questions)}")
            
            # Generate embeddings
            all_questions = self.generate_embeddings(all_questions)
            
            # Insert into Milvus
            self.insert_to_milvus(all_questions)
            
            # Create index
            self.create_index()
            
            # Final stats
            entity_count = self.collection.num_entities
            logger.info(f"🎉 Database rebuild complete! Total entities: {entity_count}")
            
            # Show sample questions by year and paper
            self.show_sample_stats(all_questions)
            
        except Exception as e:
            logger.error(f"❌ Database rebuild failed: {e}")
            raise
        finally:
            connections.disconnect("default")
    
    def show_sample_stats(self, questions: List[Dict[str, Any]]):
        """Show sample statistics"""
        logger.info("\n📊 DATABASE STATISTICS:")
        
        # Group by year and paper
        stats = {}
        for q in questions:
            year = q['year']
            paper = q['paper']
            if year not in stats:
                stats[year] = {}
            if paper not in stats[year]:
                stats[year][paper] = 0
            stats[year][paper] += 1
        
        for year in sorted(stats.keys()):
            logger.info(f"  {year}: {sum(stats[year].values())} questions")
            for paper in sorted(stats[year].keys()):
                logger.info(f"    {paper}: {stats[year][paper]} questions")

if __name__ == "__main__":
    rebuilder = PYQDatabaseRebuilder()
    rebuilder.rebuild_database()
