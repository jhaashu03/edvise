"""
Topper Vector Service
Enhanced vector search for topper content using Milvus
Handles 100-200+ topper PDFs with efficient similarity search
"""
from typing import List, Dict, Any, Optional
import json
import logging
import asyncio
import os
from datetime import datetime
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.topper_reference import TopperReference, TopperPattern

logger = logging.getLogger(__name__)

class TopperVectorService:
    """Enhanced vector service specifically for topper content"""
    
    def __init__(self):
        self.collection_name = "topper_embeddings"
        self.pattern_collection_name = "topper_patterns"
        self.model = None
        self.dimension = 384  # Using same model as main vector service
        self.connection_alias = "topper_search"
        self._connected = False
        self._topper_collection = None
        self._pattern_collection = None
        
        # Use same local/remote logic as main vector service  
        # Check if we should use local Milvus (development or local environment)
        environment = getattr(settings, 'ENVIRONMENT', 'production').lower()
        self.use_local = environment in ['local', 'development']
        if self.use_local:
            self.local_db_path = getattr(settings, 'MILVUS_LOCAL_PATH', './milvus_lite_local.db')
        else:
            self.local_db_path = None
        
        # Check if vector service is disabled
        if getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
            logger.info("Vector service is disabled, topper search will use basic text matching")
            return
            
        # Initialize model (reuse from main vector service if available)
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Initialized SentenceTransformer for topper analysis")
        except Exception as e:
            logger.warning(f"Failed to initialize SentenceTransformer for toppers: {e}")
    
    async def initialize(self) -> bool:
        """Initialize vector database connections and collections"""
        try:
            # Check if vector service is disabled
            if getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
                logger.info("Vector service disabled - skipping initialization")
                return True
            
            # Connect to Milvus
            await self.connect()
            
            # Create collections if they don't exist
            await self._ensure_collections_exist()
            
            logger.info("✅ Topper vector service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize topper vector service: {e}")
            return False

    async def connect(self):
        """Connect to Milvus for topper search using shared connection"""
        try:
            if getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
                logger.info("Vector service disabled, skipping topper vector connection")
                return
                
            if not self._connected:
                # Use shared connection manager to prevent file locking
                from app.services.shared_vector_connection import shared_connection
                
                shared_alias = await shared_connection.get_connection()
                if shared_alias:
                    self.connection_alias = shared_alias
                    self._connected = True
                    logger.info(f"✅ Using shared connection for topper vector service: {shared_alias}")
                    self._ensure_collections_exist()  # Remove await since this is not an async method
                else:
                    logger.error("❌ Failed to get shared vector connection")
                    raise ConnectionError("Could not establish shared vector connection")
                
        except Exception as e:
            logger.error(f"Failed to connect topper vector service: {e}")
            raise

    def _ensure_collections_exist(self):
        """Ensure both topper collections exist and are properly loaded"""
        try:
            # Check for existing topper_embeddings collection first
            collections = utility.list_collections(using=self.connection_alias)
            logger.info(f"Available collections: {collections}")
            
            if "topper_embeddings" in collections:
                logger.info("Loading existing collection: topper_embeddings")
                
                # Create connection to the topper_embeddings collection
                self._topper_collection = Collection("topper_embeddings", using=self.connection_alias)
                
                # Legacy property for backward compatibility
                self.topper_collection = self._topper_collection
                
                # Force load to ensure fresh data
                try:
                    self._topper_collection.load()
                except Exception as e:
                    logger.warning(f"Collection load warning: {e}")
                
                # Get REAL entity count by forcing a fresh query
                try:
                    # Use query to get actual count since num_entities might be cached
                    count_results = self._topper_collection.query(
                        expr="topper_id >= 0",
                        output_fields=["topper_id"],
                        limit=1000  # Get a large number to count
                    )
                    entity_count = len(count_results)
                    logger.info(f"Real collection entity count (via query): {entity_count}")
                except Exception as e:
                    entity_count = self._topper_collection.num_entities
                    logger.info(f"Collection entity count (via num_entities): {entity_count}")
                
                schema_fields = [f.name for f in self._topper_collection.schema.fields]
                logger.info(f"Collection schema fields: {schema_fields}")
                logger.info(f"Collection name from object: {self._topper_collection.name}")
                
                # Validate the schema has the expected fields
                if 'question_text' in schema_fields and 'answer_text' in schema_fields:
                    logger.info("✅ Using existing topper_embeddings collection with correct schema")
                    if entity_count == 0:
                        logger.warning("⚠️ Collection has correct schema but is empty")
                else:
                    logger.error(f"⚠️ Collection has unexpected schema! Fields: {schema_fields}")
                    logger.error("Expected 'question_text' and 'answer_text' fields")
                    raise ValueError("Wrong collection schema")
            else:
                logger.info("topper_embeddings collection not found - creating new collection")
                self._create_topper_collection()
                self._topper_collection = Collection("topper_embeddings", using=self.connection_alias)
                self.topper_collection = self._topper_collection
                logger.info("✅ Created new topper_embeddings collection with correct schema")
                
        except Exception as e:
            logger.error(f"Error ensuring collections exist: {e}")
            raise

    def _create_topper_collection(self):
        """Create topper_embeddings collection with proper schema"""
        try:
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="topper_id", dtype=DataType.INT64),
                FieldSchema(name="topper_name", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="institute", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="rank", dtype=DataType.INT64),
                FieldSchema(name="exam_year", dtype=DataType.INT64),
                FieldSchema(name="question_id", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=5000),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="topic", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="answer_text", dtype=DataType.VARCHAR, max_length=10000),
                FieldSchema(name="word_count", dtype=DataType.INT64),
                FieldSchema(name="source_document", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="page_number", dtype=DataType.INT64),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
            ]

            schema = CollectionSchema(
                fields=fields,
                description="Topper answer embeddings for semantic search",
                enable_dynamic_field=False
            )

            # Create collection
            collection = Collection(
                name="topper_embeddings",
                schema=schema, 
                using=self.connection_alias
            )

            # Create index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            
            logger.info("Created topper collection with index: topper_embeddings")

        except Exception as e:
            logger.error(f"Failed to create topper collection: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if not self.model:
            return [0.0] * self.dimension
            
        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def insert_topper_answer(self, topper_data: Dict[str, Any]) -> str:
        """Insert topper answer with embedding"""
        if not self._connected:
            await self.connect()
        
        try:
            # Generate embedding from question + answer text
            text_for_embedding = f"{topper_data['question_text']} {topper_data['answer_text']}"
            embedding = self.generate_embedding(text_for_embedding)
            
            # Prepare data for insertion
            insert_data = {
                "topper_id": topper_data['topper_id'],
                "topper_name": topper_data['topper_name'],
                "institute": topper_data.get('institute', ''),
                "rank": topper_data.get('rank', 0),
                "exam_year": topper_data.get('exam_year', 0),
                "question_id": topper_data['question_id'],
                "question_text": topper_data['question_text'],
                "subject": topper_data['subject'],
                "topic": topper_data.get('topic', ''),
                "marks": topper_data['marks'],
                "answer_text": topper_data['answer_text'],
                "word_count": topper_data.get('word_count', 0),
                "source_document": topper_data.get('source_document', ''),
                "page_number": topper_data.get('page_number', 0),
                "created_at": datetime.now().isoformat(),
                "embedding": embedding
            }
            
            # Insert into collection
            result = self._topper_collection.insert([insert_data])
            self._topper_collection.flush()
            
            logger.info(f"Inserted topper answer: {topper_data['topper_name']} - {topper_data['question_id']}")
            return str(result.primary_keys[0])
            
        except Exception as e:
            logger.error(f"Failed to insert topper answer: {e}")
            raise

    async def store_topper_content(
        self,
        topper_name: str,
        institute: str,
        exam_year: str,
        question_text: str,
        answer_text: str,
        subject: str = "General Studies",
        marks: int = 10,
        question_number: str = "Q1",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Simplified method to store topper content using existing add_topper_answer"""
        
        # Convert exam_year to int if needed
        year = int(exam_year) if isinstance(exam_year, str) and exam_year.isdigit() else 2024
        
        # Create numeric topper ID (hash of name + year for uniqueness)
        import hashlib
        topper_id_str = f"{topper_name.replace(' ', '_').lower()}_{year}"
        topper_id = int(hashlib.md5(topper_id_str.encode()).hexdigest()[:10], 16) % (2**31)  # Convert to 32-bit int
        
        # Create topper data dictionary
        topper_data = {
            'topper_id': topper_id,
            'topper_name': topper_name,
            'institute': institute,
            'rank': 1,  # Default rank
            'exam_year': year,
            'question_id': str(question_number),  # Convert to string for VARCHAR schema
            'question_text': question_text,
            'subject': subject,
            'topic': subject,  # Use subject as topic for now
            'marks': marks,
            'answer_text': answer_text,
            'word_count': len(answer_text.split()) if answer_text else 0,
            'source_document': metadata.get('source_file', '') if metadata else '',
            'page_number': 1,  # Convert page reference to int
            'created_at': datetime.now().isoformat()[:50]  # Truncate to fit field size
        }
        
        # Use existing method
        return await self.insert_topper_answer(topper_data)

    async def search_similar_topper_answers(
        self,
        query_question: str,
        student_answer: str = "",
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar topper answers based on question and student answer"""
        if not self._connected:
            await self.connect()
        
        if not self.model:
            # Try to initialize the model if it's not available
            logger.info("Attempting to initialize SentenceTransformer model...")
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Successfully initialized SentenceTransformer model")
            except Exception as e:
                logger.error(f"Failed to initialize SentenceTransformer model: {e}")
                # Still return empty results if model can't be initialized
                return []
        
        try:
            # Create search query embedding
            search_text = f"{query_question} {student_answer}" if student_answer else query_question
            query_embedding = self.generate_embedding(search_text)
            
            # Build filter expression
            filter_expr = ""
            if filters:
                filter_conditions = []
                if filters.get('subject'):
                    filter_conditions.append(f'subject == "{filters["subject"]}"')
                if filters.get('exam_year'):
                    filter_conditions.append(f'exam_year == {filters["exam_year"]}')
                if filters.get('marks_min'):
                    filter_conditions.append(f'marks >= {filters["marks_min"]}')
                if filters.get('rank_max'):
                    filter_conditions.append(f'rank <= {filters["rank_max"]}')
                    
                if filter_conditions:
                    filter_expr = " && ".join(filter_conditions)
            
            # Search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Output fields - match actual topper_embeddings collection schema  
            output_fields = [
                "topper_id", "topper_name", "institute", "rank", "exam_year",
                "question_id", "question_text", "answer_text", "subject", "topic", "marks", 
                "word_count", "source_document", "page_number"
            ]
            
            # Check collection status before search
            try:
                entity_count = self._topper_collection.num_entities
                logger.info(f"🔍 Searching collection '{self.collection_name}' with {entity_count} total entities")
                logger.info(f"📊 Search params - Limit: {limit}, Filter: {filter_expr or 'None'}")
            except Exception as e:
                logger.warning(f"Could not check collection entity count: {e}")

            # Perform search
            results = self._topper_collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=filter_expr if filter_expr else None,
                output_fields=output_fields
            )
            
            logger.info(f"🔎 Raw search results: {len(results)} result sets returned")
            
            # Format results
            formatted_results = []
            for result_set_idx, hits in enumerate(results):
                logger.info(f"📝 Processing result set {result_set_idx + 1} with {len(hits)} hits")
                for hit_idx, hit in enumerate(hits):
                    result_data = {
                        "topper_id": hit.entity.get("topper_id"),
                        "topper_name": hit.entity.get("topper_name"),
                        "institute": hit.entity.get("institute"),
                        "rank": hit.entity.get("rank"),  # Map to rank for consistency
                        "exam_year": hit.entity.get("exam_year"),
                        "question_id": hit.entity.get("question_id"),  # Use question_id field
                        "question_text": hit.entity.get("question_text"),  # Use correct field name
                        "subject": hit.entity.get("subject"),
                        "topic": hit.entity.get("subject"),  # Use subject as topic for now
                        "marks": hit.entity.get("marks"),
                        "answer_text": hit.entity.get("answer_text"),  # Use correct field name
                        "word_count": len(hit.entity.get("answer_text", "").split()) if hit.entity.get("answer_text") else 0,
                        "source_document": f"Topper {hit.entity.get('topper_name', 'Unknown')}",
                        "page_number": 1,  # Default page number
                        "similarity_score": hit.score,
                        "relevance_rank": len(formatted_results) + 1
                    }
                    formatted_results.append(result_data)
                    # Log individual similarity scores for debugging
                    logger.info(f"🎯 Result {len(formatted_results)}: [{hit.entity.get('topper_name')}] Q{hit.entity.get('question_id')} - Similarity: {hit.score:.4f}")
            
            if len(formatted_results) == 0:
                logger.warning(f"❌ Vector search returned 0 results for query: '{query_question[:100]}...'")
                logger.warning(f"🔍 Search parameters - Limit: {limit}, Filter: {filter_expr or 'None'}")
                # Enhanced collection diagnostics
                try:
                    entity_count = self._topper_collection.num_entities
                    logger.warning(f"📊 Collection '{self.collection_name}' contains {entity_count} total entities")
                    if entity_count == 0:
                        logger.error("🚨 CRITICAL: Vector database is empty! No topper data found.")
                        logger.error("💡 Solution: Run topper processing pipeline to populate database")
                    else:
                        logger.warning(f"🤔 Database has {entity_count} entities but search returned 0 results")
                        logger.warning("💡 Possible issues: Filter too restrictive, similarity threshold too high, or embedding mismatch")
                except Exception as e:
                    logger.error(f"❌ Could not check collection diagnostics: {e}")
            else:
                logger.info(f"✅ Found {len(formatted_results)} similar topper answers")
                scores_list = [f"{r['similarity_score']:.4f}" for r in formatted_results[:3]]
                logger.info(f"📊 Top similarity scores: {scores_list}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search topper answers: {e}")
            return []

    async def search_relevant_patterns(
        self,
        question_type: str,
        subject: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for relevant writing patterns"""
        if not self._connected:
            await self.connect()
            
        if not self.model:
            return []
        
        try:
            # Create query for patterns
            query_text = f"{subject} {question_type}"
            query_embedding = self.generate_embedding(query_text)
            
            search_params = {
                "metric_type": "COSINE", 
                "params": {"nprobe": 10}
            }
            
            results = self._pattern_collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                output_fields=["pattern_id", "pattern_type", "pattern_name", "description", 
                              "subjects", "frequency", "effectiveness_score", "examples"]
            )
            
            formatted_results = []
            for hits in results:
                for hit in hits:
                    result_data = {
                        "pattern_id": hit.entity.get("pattern_id"),
                        "pattern_type": hit.entity.get("pattern_type"),
                        "pattern_name": hit.entity.get("pattern_name"),
                        "description": hit.entity.get("description"),
                        "subjects": json.loads(hit.entity.get("subjects", "[]")),
                        "frequency": hit.entity.get("frequency"),
                        "effectiveness_score": hit.entity.get("effectiveness_score"),
                        "examples": json.loads(hit.entity.get("examples", "[]")),
                        "relevance_score": hit.score
                    }
                    formatted_results.append(result_data)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search patterns: {e}")
            return []

    async def bulk_insert_toppers(self, topper_list: List[Dict[str, Any]]) -> List[str]:
        """Bulk insert multiple topper answers for efficiency"""
        if not self._connected:
            await self.connect()
        
        try:
            batch_data = {
                "topper_id": [],
                "topper_name": [],
                "institute": [],
                "rank": [],
                "exam_year": [],
                "question_id": [],
                "question_text": [],
                "subject": [],
                "topic": [],
                "marks": [],
                "answer_text": [],
                "word_count": [],
                "source_document": [],
                "page_number": [],
                "created_at": [],
                "embedding": []
            }
            
            # Process each topper entry
            for topper_data in topper_list:
                text_for_embedding = f"{topper_data['question_text']} {topper_data['answer_text']}"
                embedding = self.generate_embedding(text_for_embedding)
                
                batch_data["topper_id"].append(topper_data['topper_id'])
                batch_data["topper_name"].append(topper_data['topper_name'])
                batch_data["institute"].append(topper_data.get('institute', ''))
                batch_data["rank"].append(topper_data.get('rank', 0))
                batch_data["exam_year"].append(topper_data.get('exam_year', 0))
                batch_data["question_id"].append(topper_data['question_id'])
                batch_data["question_text"].append(topper_data['question_text'])
                batch_data["subject"].append(topper_data['subject'])
                batch_data["topic"].append(topper_data.get('topic', ''))
                batch_data["marks"].append(topper_data['marks'])
                batch_data["answer_text"].append(topper_data['answer_text'])
                batch_data["word_count"].append(topper_data.get('word_count', 0))
                batch_data["source_document"].append(topper_data.get('source_document', ''))
                batch_data["page_number"].append(topper_data.get('page_number', 0))
                batch_data["created_at"].append(datetime.now().isoformat())
                batch_data["embedding"].append(embedding)
            
            # Bulk insert
            result = self._topper_collection.insert(batch_data)
            self._topper_collection.flush()
            
            logger.info(f"Bulk inserted {len(topper_list)} topper answers")
            return [str(pk) for pk in result.primary_keys]
            
        except Exception as e:
            logger.error(f"Failed to bulk insert toppers: {e}")
            raise

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about topper collections"""
        if not self._connected:
            await self.connect()
        
        try:
            topper_count = self._topper_collection.num_entities if self._topper_collection else 0
            pattern_count = self._pattern_collection.num_entities if self._pattern_collection else 0
            
            return {
                "topper_answers_count": topper_count,
                "topper_patterns_count": pattern_count,
                "collections_loaded": self._connected,
                "embedding_dimension": self.dimension,
                "model_name": "all-MiniLM-L6-v2" if self.model else "disabled"
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

# Global instance
topper_vector_service = TopperVectorService()
