"""
Vector database service using Zilliz (Milvus) for semantic search
Supports both local Milvus Lite and remote Zilliz Cloud
"""
from typing import List, Dict, Any, Optional
import json
import logging
import os
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.collection_name = "pyq_embeddings"
        self.model = None  # Initialize later only if service is enabled
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.connection_alias = "default"
        self._connected = False
        self._collection = None
        
        # Check if vector service is disabled before initializing heavy components
        if getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
            logger.info("Vector service is disabled in settings, skipping initialization")
            return
            
        # Only initialize model if service is enabled
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Failed to initialize SentenceTransformer: {e}")
            logger.info("Vector service will be disabled due to model initialization failure")
            return
        
        # Determine if we're using local or remote Milvus
        self.use_local = getattr(settings, 'ENVIRONMENT', 'production') == 'local'
        
        # Get the appropriate connection details based on environment
        if self.use_local:
            # For local development, use the local file path
            self.local_db_path = getattr(settings, 'MILVUS_LOCAL_PATH', './milvus_lite_local.db')
            logger.info(f"Using Milvus Lite with path: {self.local_db_path}")
        else:
            # For production, we'll use the cloud URI and token from settings
            self.local_db_path = None
            logger.info("Using Zilliz Cloud for vector storage")

    async def connect(self):
        """Connect to Milvus (local or remote)"""
        try:
            # Check if vector service is disabled
            if getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
                logger.info("Vector service is disabled in settings, skipping connection")
                return
                
            if not self._connected:
                if self.use_local:
                    # Use Milvus Lite for local development
                    logger.info("Using Milvus Lite for local development")
                    connections.connect(
                        alias=self.connection_alias,
                        uri=os.path.abspath(self.local_db_path)
                    )
                    logger.info(f"Successfully connected to Milvus Lite at {self.local_db_path}")
                else:
                    # Use Zilliz Cloud for production
                    logger.info("Using Zilliz Cloud for production")
                    
                    # Validate that we have proper cloud credentials
                    if not settings.MILVUS_URI or not settings.MILVUS_TOKEN:
                        raise ValueError("MILVUS_URI and MILVUS_TOKEN must be set for production mode")
                    
                    connections.connect(
                        alias=self.connection_alias,
                        uri=settings.MILVUS_URI,
                        token=settings.MILVUS_TOKEN
                    )
                    logger.info("Successfully connected to Zilliz Cloud")
                
                self._connected = True
                
                # Initialize collection
                await self._ensure_collection_exists()
                
        except Exception as e:
            if self.use_local:
                logger.error(f"Failed to connect to Milvus Lite: {e}")
                logger.error("Make sure milvus-lite is properly installed: pip install milvus-lite")
            else:
                logger.error(f"Failed to connect to Zilliz Cloud: {e}")
                logger.error("Check your MILVUS_URI and MILVUS_TOKEN settings")
            raise

    async def disconnect(self):
        """Disconnect from Zilliz"""
        try:
            if self._connected:
                connections.disconnect(alias=self.connection_alias)
                self._connected = False
                logger.info("Disconnected from Zilliz Cloud")
        except Exception as e:
            logger.error(f"Error disconnecting from Zilliz: {e}")

    async def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            logger.info(f"Checking if collection '{self.collection_name}' exists...")
            if not utility.has_collection(self.collection_name):
                logger.info(f"Collection '{self.collection_name}' does not exist, creating...")
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
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
                ]
                
                schema = CollectionSchema(
                    fields=fields, 
                    description="PYQ embeddings for semantic search"
                )
                
                collection = Collection(self.collection_name, schema)
                
                # Create index
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024}
                }
                collection.create_index("embedding", index_params)
                
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")
            
            # Load the collection
            self._collection = Collection(self.collection_name)
            self._collection.load()
            logger.info(f"Collection {self.collection_name} loaded successfully. Collection object: {self._collection}")
            
        except Exception as e:
            logger.error(f"Failed to create/load collection: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformer"""
        if not self.model:
            logger.warning("Vector service is disabled or model failed to initialize")
            return [0.0] * self.dimension  # Return zero vector
            
        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def insert_pyq(self, pyq_data: Dict[str, Any]) -> str:
        """Insert a PYQ with its embedding"""
        if getattr(settings, 'DISABLE_VECTOR_SERVICE', False) or not self.model:
            logger.info("Vector service is disabled, skipping PYQ insertion")
            return "disabled"
            
        try:
            if not self._connected:
                await self.connect()
            
            # Generate embedding
            question_text = pyq_data.get('question', '')
            embedding = self.generate_embedding(question_text)
            
            # Prepare data for insertion
            entities = [
                [pyq_data.get('id')],  # pyq_id
                [question_text],       # question_text
                [pyq_data.get('subject', '')],  # subject
                [pyq_data.get('year', 0)],      # year
                [pyq_data.get('paper', '')],    # paper
                [json.dumps(pyq_data.get('topics', []))],  # topics as JSON string
                [pyq_data.get('difficulty', 'medium')],    # difficulty
                [pyq_data.get('marks', 0)],     # marks
                [embedding]            # embedding
            ]
            
            # Insert data
            result = self._collection.insert(entities)
            self._collection.flush()
            
            # Return the auto-generated ID
            return str(result.primary_keys[0])
            
        except Exception as e:
            logger.error(f"Failed to insert PYQ: {e}")
            raise

    async def search_similar_pyqs(
        self, 
        query: str, 
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar PYQs using semantic search"""
        if getattr(settings, 'DISABLE_VECTOR_SERVICE', False) or not self.model:
            logger.info("Vector service is disabled, returning empty search results")
            return []
            
        try:
            if not self._connected:
                await self.connect()
            
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Prepare search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Build filter expression
            filter_expr = ""
            if filters:
                filter_conditions = []
                if filters.get('subject'):
                    filter_conditions.append(f'subject == "{filters["subject"]}"')
                if filters.get('year'):
                    filter_conditions.append(f'year == {filters["year"]}')
                if filters.get('difficulty'):
                    filter_conditions.append(f'difficulty == "{filters["difficulty"]}"')
                
                if filter_conditions:
                    filter_expr = " && ".join(filter_conditions)
            
            # Perform search
            results = self._collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=filter_expr if filter_expr else None,
                output_fields=["pyq_id", "question_text", "subject", "year", "paper", "topics", "difficulty", "marks"]
            )
            
            # Format results
            formatted_results = []
            for hits in results:
                for hit in hits:
                    result_data = {
                        "id": hit.entity.get("pyq_id"),
                        "question": hit.entity.get("question_text"),
                        "subject": hit.entity.get("subject"),
                        "year": hit.entity.get("year"),
                        "paper": hit.entity.get("paper"),
                        "topics": json.loads(hit.entity.get("topics", "[]")),
                        "difficulty": hit.entity.get("difficulty"),
                        "marks": hit.entity.get("marks"),
                        "similarity_score": hit.score
                    }
                    formatted_results.append(result_data)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search PYQs: {e}")
            raise

    async def delete_pyq(self, pyq_id: int):
        """Delete a PYQ from the vector database"""
        try:
            if not self._connected:
                await self.connect()
            
            # Delete by pyq_id
            self._collection.delete(f'pyq_id == {pyq_id}')
            self._collection.flush()
            
            logger.info(f"Deleted PYQ with ID: {pyq_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete PYQ: {e}")
            raise

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            if not self._connected:
                await self.connect()
            
            # Use num_entities property instead of get_stats()
            return {
                "total_entities": self._collection.num_entities,
                "collection_name": self.collection_name,
                "dimension": self.dimension
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

# Global instance
vector_service = VectorService()
