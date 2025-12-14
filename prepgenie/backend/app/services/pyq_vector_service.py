"""
PYQ Vector Service for Milvus Integration
Handles vector storage and semantic search for Previous Year Questions
"""
from typing import List, Dict, Optional, Any
from pymilvus import Collection, connections, FieldSchema, CollectionSchema, DataType, utility
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os
from app.core.config import settings
import json
from typing import Optional
from dataclasses import dataclass

# Minimal PYQQuestion class definition (to avoid dependency on pyq_parser)
@dataclass
class PYQQuestion:
    question_text: str
    subject: str = "General Studies"
    year: int = 2023
    paper: str = "Paper I"
    marks: int = 5
    difficulty: str = "medium"
    topic: Optional[str] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PYQVectorService:
    """Service for handling PYQ vector operations with Milvus"""
    
    def __init__(self, use_local: bool = True, model_name: str = None):
        self.use_local = use_local
        self.collection_name = "pyq_embeddings"
        
        # Result caching for optimized pagination with LRU eviction
        from collections import OrderedDict
        self.search_cache = OrderedDict()
        self.max_cache_size = 50  # Maximum 50 cached queries
        self.cache_ttl = 300  # 5 minutes cache
        import time
        self._time = time
        
        # Use BGE model for high-quality embeddings
        self.model_name = "BAAI/bge-large-en-v1.5"
        self.embedding_dim = 1024
        logger.info(f"🤖 Using embedding model: {self.model_name} (dim: {self.embedding_dim})")
        
        try:
            # Use offline mode to avoid SSL certificate issues
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            os.environ['HF_HUB_OFFLINE'] = '1'
            
            self.embedding_model = SentenceTransformer(self.model_name, device='cpu')
            logger.info("✅ Embedding model loaded successfully from cache")
        except Exception as e:
            logger.error(f"❌ Failed to load model {self.model_name}: {e}")
            # Don't raise - allow service to continue without embedding model for direct Milvus access
            self.embedding_model = None
        
        self.collection = None
        self.connection_alias = "pyq_default"
        
    def connect(self) -> bool:
        """Connect to Milvus database using direct connection"""
        try:
            # Clean disconnect any existing connection to avoid conflicts
            try:
                connections.disconnect("pyq_direct")
            except Exception:
                pass
            
            # Use absolute path to the UPDATED database file with 1024-dim embeddings
            backend_db_path = '/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend/milvus_lite_local.db'
            if not os.path.exists(backend_db_path):
                # Fallback to current directory
                backend_db_path = os.path.join(os.getcwd(), "milvus_lite_local.db")
            
            logger.info(f"📍 Using direct connection to: {backend_db_path}")
            logger.info(f"📍 Database exists: {os.path.exists(backend_db_path)}")
            
            # Create a direct connection
            connections.connect(
                alias="pyq_direct",
                uri=backend_db_path
            )
            self.connection_alias = "pyq_direct"
            
            logger.info(f"✅ Successfully connected to Milvus database with alias: {self.connection_alias}")
            
            # List all collections
            collections_list = utility.list_collections(using=self.connection_alias)
            logger.info(f"📚 Available collections: {collections_list}")
            
            if self.collection_name not in collections_list:
                logger.warning(f"⚠️ Collection '{self.collection_name}' not found - will need to be created")
            else:
                logger.info(f"✅ Collection '{self.collection_name}' found")
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Milvus: {str(e)}")
            import traceback
            logger.error(f"🔍 Connection traceback: {traceback.format_exc()}")
            return False
    
    def create_collection(self) -> bool:
        """Create PYQ collection with proper schema"""
        try:
            # Drop collection if it exists
            if utility.has_collection(self.collection_name, using=self.connection_alias):
                utility.drop_collection(self.collection_name, using=self.connection_alias)
                logger.info(f"Dropped existing collection: {self.collection_name}")
            
            # Define collection schema - MUST match imported data schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="pyq_id", dtype=DataType.INT64),  # Changed from question_id
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="year", dtype=DataType.INT64),
                FieldSchema(name="paper", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="topics", dtype=DataType.VARCHAR, max_length=1000),  # Changed from tags
                FieldSchema(name="difficulty", dtype=DataType.VARCHAR, max_length=50),  # Added
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            ]
            
            schema = CollectionSchema(fields, description="UPSC PYQ Questions Collection")
            collection = Collection(self.collection_name, schema, using=self.connection_alias)
            
            # Create index for vector search
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index("embedding", index_params)
            
            self.collection = collection
            logger.info(f"Created collection: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}")
            return False
    
    def load_collection(self) -> bool:
        """Load collection into memory"""
        try:
            logger.info(f"📚 Loading collection: {self.collection_name}")
            
            # Check if collection exists
            from pymilvus import utility
            if not utility.has_collection(self.collection_name, using=self.connection_alias):
                logger.error(f"🚫 Collection '{self.collection_name}' does not exist")
                return False
            
            # Create collection object if needed
            if not self.collection:
                logger.info(f"🏗️ Creating collection object for: {self.collection_name}")
                self.collection = Collection(self.collection_name, using=self.connection_alias)
            
            # Load collection into memory
            logger.info(f"📋 Loading collection into memory...")
            self.collection.load()
            
            # Verify collection is loaded with detailed diagnostics
            logger.info(f"📋 Checking collection entity count...")
            entity_count = self.collection.num_entities
            logger.info(f"📈 Collection {self.collection_name} has {entity_count} entities")
            
            # Double-check with a direct query
            try:
                query_result = self.collection.query(expr="", limit=1, output_fields=["pyq_id"])
                actual_count = len(query_result) if query_result else 0
                logger.info(f"🔍 Query verification: {actual_count} records accessible")
                
                if entity_count != actual_count and entity_count > 0:
                    logger.warning(f"⚠️ Entity count mismatch: num_entities={entity_count}, query_result={actual_count}")
            except Exception as query_error:
                logger.error(f"❌ Failed to verify with query: {query_error}")
            
            if entity_count == 0:
                logger.error(f"❌ Collection is empty: {self.collection_name}")
                logger.error(f"📊 This should contain ~525 PYQ questions. Data may have been lost or corrupted.")
                return False
            
            logger.info(f"✅ Collection loaded successfully: {self.collection_name} with {entity_count} entities")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load collection: {str(e)}")
            import traceback
            logger.error(f"🔍 Load collection traceback: {traceback.format_exc()}")
            return False
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for text list"""
        try:
            if not texts:
                logger.warning("Empty text list provided for embedding generation")
                return np.array([])
            
            logger.info(f"🧠 Generating embeddings for {len(texts)} texts...")
            
            # Ensure model is loaded
            if not hasattr(self, 'embedding_model') or self.embedding_model is None:
                logger.info("🔄 Reinitializing embedding model...")
                from sentence_transformers import SentenceTransformer
                
                # Use offline mode to avoid SSL issues
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                os.environ['HF_HUB_OFFLINE'] = '1'
                
                self.embedding_model = SentenceTransformer('BAAI/bge-large-en-v1.5', device='cpu')
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
            logger.info(f"✅ Generated embeddings with shape: {embeddings.shape}")
            
            # Validate embedding dimensions
            if embeddings.shape[1] != self.embedding_dim:
                logger.error(f"❌ Embedding dimension mismatch: expected {self.embedding_dim}, got {embeddings.shape[1]}")
                return np.array([])
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embeddings: {str(e)}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            return np.array([])
    
    # calculate_keyword_score method removed - BGE-large semantic scores are sufficient
    # hybrid_score method removed - using pure BGE-large semantic scores
    
    def _convert_topics_to_list(self, topics_str: str) -> list:
        """Convert topics string to list for Pydantic validation"""
        try:
            if isinstance(topics_str, list):
                return topics_str
            if isinstance(topics_str, str):
                # Split by comma and clean up
                topics_list = [topic.strip() for topic in topics_str.split(',') if topic.strip()]
                return topics_list if topics_list else ["general"]
            return ["general"]
        except Exception as e:
            logger.warning(f"⚠️ Topics conversion error: {e}")
            return ["general"]
    
    def _expand_query_for_search(self, query: str) -> str:
        """Use LLM to dynamically expand query for better semantic search"""
        try:
            # Use LLM to expand the query with UPSC context
            expanded_query = self._llm_expand_query(query)
            if expanded_query and expanded_query != query:
                logger.info(f"📝 LLM query expansion: '{query}' → expanded with context")
                return expanded_query
            else:
                # Fallback: add basic context prefix
                return f"UPSC questions about {query}"
                
        except Exception as e:
            logger.warning(f"⚠️ Query expansion error: {e}")
            return f"UPSC questions about {query}"
    
    def _llm_expand_query(self, query: str) -> str:
        """Use existing LLM service to intelligently expand query for better semantic search"""
        try:
            # Try to use LLM service directly with proper async handling
            import asyncio
            import threading
            from concurrent.futures import ThreadPoolExecutor
            
            def _run_llm_expansion():
                """Run LLM expansion in a separate thread with its own event loop"""
                async def _async_expand():
                    from app.core.llm_service import get_llm_service
                    
                    llm_service = get_llm_service()
                    
                    system_prompt = "You are an expert in UPSC examinations. Expand search queries to include related concepts and synonyms for finding relevant UPSC Previous Year Questions."
                    
                    user_message = f"""Expand this search query: "{query}"

Include:
1. Related UPSC concepts
2. Alternative terminology
3. Indian governance context
4. Synonyms and variations

Return only the expanded query text, no explanations."""
                    
                    return await llm_service.simple_chat(
                        user_message=user_message,
                        system_prompt=system_prompt,
                        max_tokens=150,
                        temperature=0.3
                    )
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(_async_expand())
                finally:
                    loop.close()
            
            # Run in separate thread to avoid event loop conflicts
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_llm_expansion)
                expanded = future.result(timeout=30)  # 30 second timeout
                
                if expanded and expanded.strip():
                    logger.info(f"📝 LLM query expansion successful")
                    return expanded.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ LLM query expansion failed: {e}")
            
        # Fallback to simple contextual expansion when LLM is unavailable
        return f"UPSC questions about {query}, Indian governance, policy implementation, administration"
    
            
        # Fallback to basic keyword filtering when LLM is unavailable
        words = [word.strip().lower() for word in query.split() if len(word.strip()) > 2]
        if words:
            # Create basic AND filter for meaningful words
            filters = [f"question_text like '%{word}%'" for word in words[:3]]  # Limit to 3 words to avoid overly restrictive filtering
            return ' and '.join(filters)
        return None
    
    # _build_keyword_filter method removed - BGE-large-en-v1.5 provides excellent semantic relevance
    
    def _llm_rerank_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to intelligently rerank search results based on relevance to query"""
        try:
            if len(results) <= 1:
                return results
            
            # Limit to top results for reranking to avoid token limits
            max_rerank = min(20, len(results))
            top_results = results[:max_rerank]
            remaining_results = results[max_rerank:]
            
            import asyncio
            import threading
            from concurrent.futures import ThreadPoolExecutor
            
            def _run_llm_rerank():
                """Run LLM reranking in a separate thread with its own event loop"""
                async def _async_rerank():
                    from app.core.llm_service import get_llm_service
                    
                    llm_service = get_llm_service()
                    
                    system_prompt = "You are an expert at ranking UPSC questions by relevance to search queries. You understand contextual relevance, thematic connections, and conceptual relationships."
                    
                    # Prepare questions for ranking
                    questions_text = ""
                    for i, result in enumerate(top_results):
                        question_preview = result.get('question_text', '')[:200]  # First 200 chars
                        current_score = result.get('similarity_score', 0)
                        questions_text += f"{i+1}. [Score: {current_score:.3f}] {question_preview}...\n\n"
                    
                    user_message = f"""Rank these UPSC questions by relevance to the query: "{query}"

Questions to rank:
{questions_text}

Instructions:
1. Consider conceptual relevance, not just keyword matching
2. For "{query}", prioritize questions that actually discuss the core concepts
3. Rank by how well each question addresses the query's intent
4. Return ONLY the numbers in order of relevance (most relevant first)
5. Format: 1,3,2,4,5... (comma-separated, no spaces)

Example: If question 3 is most relevant, then 1, then 5: 3,1,5,2,4

Ranking (most to least relevant):"""
                    
                    response = await llm_service.simple_chat(
                        user_message=user_message,
                        system_message=system_prompt,
                        temperature=0.1  # Low temperature for consistent ranking
                    )
                    
                    return response.strip()
                
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop.run_until_complete(_async_rerank())
                except Exception as e:
                    logger.warning(f"⚠️ LLM reranking async error: {e}")
                    return None
                finally:
                    try:
                        loop.close()
                    except:
                        pass
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_llm_rerank)
                ranking_response = future.result(timeout=15)  # 15 second timeout
            
            if not ranking_response:
                logger.warning("⚠️ LLM reranking failed - keeping original order")
                return results
            
            # Parse ranking response
            try:
                ranking_str = ranking_response.replace(' ', '').strip()
                if ranking_str:
                    # Extract numbers from response
                    ranking_indices = []
                    for part in ranking_str.split(','):
                        try:
                            idx = int(part.strip()) - 1  # Convert to 0-based index
                            if 0 <= idx < len(top_results):
                                ranking_indices.append(idx)
                        except ValueError:
                            continue
                    
                    if ranking_indices:
                        # Reorder based on LLM ranking
                        reranked_results = []
                        used_indices = set()
                        
                        # Add questions in LLM-suggested order
                        for idx in ranking_indices:
                            if idx not in used_indices:
                                reranked_results.append(top_results[idx])
                                used_indices.add(idx)
                        
                        # Add any remaining questions that weren't ranked
                        for idx, result in enumerate(top_results):
                            if idx not in used_indices:
                                reranked_results.append(result)
                        
                        # Add remaining results that weren't considered for reranking
                        reranked_results.extend(remaining_results)
                        
                        logger.info(f"🎯 LLM reranked {len(ranking_indices)} results for query: '{query}'")
                        logger.info(f"📊 Reranking order: {ranking_str}")
                        
                        return reranked_results
            
            except Exception as parse_error:
                logger.warning(f"⚠️ Failed to parse LLM ranking: {parse_error}")
            
            return results
            
        except Exception as e:
            logger.warning(f"⚠️ LLM reranking failed: {e}")
            return results
    
    def insert_questions(self, questions: List[PYQQuestion]) -> bool:
        """Insert PYQ questions into Milvus collection"""
        try:
            if not questions:
                logger.warning("No questions provided for insertion")
                return False
            
            # Prepare data for insertion
            question_texts = [q.question_text for q in questions]
            embeddings = self.generate_embeddings(question_texts)
            
            if embeddings.size == 0:
                logger.error("Failed to generate embeddings")
                return False
            
            # Prepare insertion data
            data = {
                "question_id": [q.question_id for q in questions],
                "question_text": [q.question_text for q in questions],
                "year": [q.year for q in questions],
                "paper": [q.paper for q in questions],
                "subject": [q.subject for q in questions],
                "word_limit": [q.word_limit or 0 for q in questions],
                "marks": [q.marks or 0 for q in questions],
                "tags": [json.dumps(q.to_dict()['tags']) for q in questions],
                "embedding": embeddings.tolist()
            }
            
            # Insert data
            mr = self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"Successfully inserted {len(questions)} questions")
            logger.info(f"Inserted IDs: {mr.primary_keys[:5]}...")  # Show first 5 IDs
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert questions: {str(e)}")
            return False
    
    def _map_subject_filter(self, subject_filter: Optional[str]) -> Optional[str]:
        """Map frontend subject names to database subject values"""
        if not subject_filter:
            return None
            
        # Mapping from frontend filter names to database subject values
        subject_mapping = {
            "General Studies Paper 1": "History, Geography, Society",
            "General Studies Paper I": "History, Geography, Society",
            "GS1": "History, Geography, Society",
            "GS Paper 1": "History, Geography, Society",
            "History, Geography, Society": "History, Geography, Society",
            
            "General Studies Paper 2": "Governance, Constitution, International Relations", 
            "General Studies Paper II": "Governance, Constitution, International Relations",
            "GS2": "Governance, Constitution, International Relations",
            "GS Paper 2": "Governance, Constitution, International Relations", 
            "Governance, Constitution, International Relations": "Governance, Constitution, International Relations",
            
            "General Studies Paper 3": "Economy, Environment, Science & Technology",
            "General Studies Paper III": "Economy, Environment, Science & Technology",
            "GS3": "Economy, Environment, Science & Technology",
            "GS Paper 3": "Economy, Environment, Science & Technology",
            "Economy, Environment, Science & Technology": "Economy, Environment, Science & Technology",
            
            "General Studies Paper 4": "Ethics",  # Assuming GS4 is Ethics
            "General Studies Paper IV": "Ethics", 
            "GS4": "Ethics",
            "GS Paper 4": "Ethics",
            "Ethics": "Ethics"
        }
        
        # Try exact match first
        if subject_filter in subject_mapping:
            mapped_subject = subject_mapping[subject_filter]
            logger.info(f"🔗 Subject filter mapped: '{subject_filter}' → '{mapped_subject}'")
            return mapped_subject
        
        # If no exact match, try partial matching
        subject_lower = subject_filter.lower()
        if "paper 1" in subject_lower or "gs1" in subject_lower:
            logger.info(f"🔗 Subject filter mapped (partial): '{subject_filter}' → 'History, Geography, Society'")
            return "History, Geography, Society"
        elif "paper 2" in subject_lower or "gs2" in subject_lower:
            logger.info(f"🔗 Subject filter mapped (partial): '{subject_filter}' → 'Governance, Constitution, International Relations'")
            return "Governance, Constitution, International Relations"
        elif "paper 3" in subject_lower or "gs3" in subject_lower:
            logger.info(f"🔗 Subject filter mapped (partial): '{subject_filter}' → 'Economy, Environment, Science & Technology'")
            return "Economy, Environment, Science & Technology"
        elif "paper 4" in subject_lower or "gs4" in subject_lower:
            logger.info(f"🔗 Subject filter mapped (partial): '{subject_filter}' → 'Ethics'")
            return "Ethics"
        
        # If no mapping found, use as-is and log warning
        logger.warning(f"⚠️ No subject mapping found for: '{subject_filter}' - using as-is")
        return subject_filter

    def search_questions(self, 
                        query: str, 
                        limit: int = 10,
                        offset: int = 0,
                        year_filter: Optional[int] = None,
                        subject_filter: Optional[str] = None,
                        paper_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar questions using vector similarity with result caching"""
        try:
            # Map subject filter to database values
            mapped_subject_filter = self._map_subject_filter(subject_filter)
            # ⚡ CACHING OPTIMIZATION: Check if we have cached results
            filters = {
                'year_filter': year_filter,
                'subject_filter': mapped_subject_filter, 
                'paper_filter': paper_filter
            }
            cache_key = self._generate_cache_key(query, filters)
            logger.info(f"🔑 Cache key for query='{query}' filters={filters}: {cache_key[:16]}...")
            
            if cache_key in self.search_cache:
                cached_data = self.search_cache[cache_key]
                if self._is_cache_valid(cached_data):
                    # Move to end for LRU ordering
                    self.search_cache.move_to_end(cache_key)
                    logger.info(f"⚡ Using cached results for pagination - NO DB/LLM calls!")
                    return self._slice_results(cached_data['results'], offset, limit)
                else:
                    # Remove expired cache
                    del self.search_cache[cache_key]
            
            logger.info(f"🔍 Full search with caching - DB + LLM calls required")
            
            # Adaptive limit for keyword queries to ensure perfect matches are found
            query_words = len(query.split())
            is_simple_keyword_query = query_words <= 3 and not any(word in query.lower() for word in ['what', 'how', 'why', 'explain', 'discuss', 'analyze'])
            
            # Increase search limit significantly to get more diverse results
            # Always search for more results to allow for score-based filtering
            search_limit = max(limit * 10, 100)  # Search 10x the requested limit, minimum 100
            logger.info(f"🔍 Expanding search limit from {limit} to {search_limit} for diverse results")
            
            logger.info(f"🔍 Starting search for query: '{query}' with limit: {limit} (search_limit: {search_limit})")
            
            # Check collection status
            if not self.collection:
                logger.error("❌ Collection not loaded")
                return []
            
            logger.info(f"📊 Collection entities: {self.collection.num_entities}")
            
            # Generate query embedding with query expansion
            logger.info("🧠 Generating query embedding...")
            expanded_query = self._expand_query_for_search(query)
            logger.info(f"🔍 Expanded query: '{expanded_query}'")
            
            query_embedding = self.generate_embeddings([expanded_query])
            if query_embedding.size == 0:
                logger.error("❌ Failed to generate query embedding")
                return []
            
            logger.info(f"✅ Generated embedding with shape: {query_embedding.shape}")
            
            # Build search expression with keyword filtering for better relevance
            search_expr = []
            if year_filter:
                search_expr.append(f"year == {year_filter}")
            if mapped_subject_filter:
                search_expr.append(f"subject == '{mapped_subject_filter}'")
            if paper_filter:
                search_expr.append(f"paper == '{paper_filter}'")
            
            # BGE-large handles semantic relevance excellently - no keyword filtering needed
            logger.info("🧠 Using pure semantic search with BGE-large-en-v1.5")
            
            expr = " and ".join(search_expr) if search_expr else None
            logger.info(f"🔧 Search expression: {expr or 'None (no filters)'}")
            
            # Search parameters
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            logger.info(f"⚙️ Search params: {search_params}")
            
            # Perform search
            logger.info("🚀 Executing Milvus search...")
            try:
                # Enhanced search with keyword filtering for better relevance
                enhanced_search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
                
                results = self.collection.search(
                    data=query_embedding.tolist(),
                    anns_field="embedding",
                    param=enhanced_search_params,
                    limit=search_limit,  # Use adaptive limit
                    expr=expr,  # Enable keyword filtering for better precision
                    output_fields=["pyq_id", "question_text", "subject", "year", "paper", "topics", "difficulty", "marks"]
                )
                logger.info(f"✅ Search completed. Raw results: {len(results)} result sets")
                if results:
                    logger.info(f"📈 First result set has {len(results[0])} hits")
                    if len(results[0]) > 0:
                        logger.info(f"🎆 First hit score: {results[0][0].score:.6f}")
            except Exception as search_error:
                logger.error(f"❌ Search execution failed: {search_error}")
                logger.error(f"🔍 Query embedding shape: {query_embedding.shape}")
                logger.error(f"🔍 Search params: {simple_search_params}")
                raise
            
            # Format results
            formatted_results = []
            logger.info(f"🔄 Processing {len(results)} result sets...")
            
            for i, hits in enumerate(results):
                logger.info(f"📁 Processing result set {i} with {len(hits)} hits")
                for j, hit in enumerate(hits):
                    logger.info(f"  🎯 Hit {j}: ID={hit.id}, Score={hit.score:.4f}")
                    
                    # Log available entity fields
                    if hasattr(hit, 'entity') and hit.entity:
                        available_fields = list(hit.entity.keys()) if hasattr(hit.entity, 'keys') else 'unknown'
                        logger.info(f"    🗂 Available fields: {available_fields}")
                    
                    try:
                        # Enhanced question text extraction with debugging
                        logger.info(f"    🔍 Raw hit entity: {hit.entity}")
                        
                        # Try multiple methods to get question text
                        question_text = None
                        if hasattr(hit, 'entity') and hit.entity:
                            # Method 1: Direct key access
                            question_text = hit.entity.get("question_text")
                            logger.info(f"    📝 Method 1 question_text: {question_text[:50] if question_text else 'None'}...")
                            
                            # Method 2: Try alternative field names
                            if not question_text:
                                for field_name in ['question_text', 'question', 'text', 'content']:
                                    if field_name in hit.entity:
                                        question_text = hit.entity[field_name]
                                        logger.info(f"    📝 Found text in field '{field_name}': {question_text[:50] if question_text else 'None'}...")
                                        break
                        
                        # Fallback if still no text
                        if not question_text:
                            question_text = f"Question text not available for ID {hit.id}"
                            logger.warning(f"    ⚠️ Using fallback text for hit {hit.id}")
                        
                        semantic_score = float(hit.score)
                        
                        # BGE-large provides excellent semantic scores - no hybrid scoring needed
                        final_score = semantic_score  # Pure semantic scoring with BGE-large
                        
                        logger.info(f"    📊 BGE-large Semantic Score: {semantic_score:.4f} (Pure semantic, no keyword boost needed)")
                        
                        # Enhanced result format with hybrid scoring - match frontend types
                        # Ensure question field is properly set
                        logger.info(f"    📝 Final question_text for response: {question_text[:100] if question_text else 'EMPTY'}...")
                        
                        result = {
                            "id": hit.id,
                            "question_id": str(hit.entity.get("pyq_id", hit.id)),
                            "question": question_text,  # Frontend expects "question", not "question_text"
                            "question_text": question_text,  # Keep for backward compatibility
                            "year": hit.entity.get("year", 0),
                            "paper": hit.entity.get("paper", "GS Paper"),
                            "subject": hit.entity.get("subject", "General Studies"),
                            "difficulty": hit.entity.get("difficulty", "medium"),
                            "marks": hit.entity.get("marks", 10),  # Default UPSC marks
                            "topics": self._convert_topics_to_list(hit.entity.get("topics", "general")),
                            "similarity_score": final_score,  # Pure BGE-large semantic score
                            "semantic_score": semantic_score,  # Keep semantic for analysis
                            "distance": 1.0 - final_score
                        }
                        formatted_results.append(result)
                        logger.info(f"    ✅ Successfully processed hit {j}: {result['question_text'][:50]}...")
                    except Exception as hit_error:
                        logger.error(f"    ❌ Error processing hit {j}: {hit_error}")
                        # Add the hit anyway with minimal info
                        try:
                            minimal_result = {
                                "id": hit.id,
                                "question_id": str(hit.id),
                                "question": "Error loading question text",  # Frontend expects "question"
                                "question_text": "Error loading text",  # Backward compatibility
                                "year": 2020,
                                "paper": "GS Paper",
                                "subject": "General Studies",
                                "difficulty": "medium",
                                "marks": 10,
                                "topics": ["Error"],
                                "similarity_score": float(hit.score),
                                "distance": 1.0 - float(hit.score)
                            }
                            formatted_results.append(minimal_result)
                            logger.info(f"    ⚠️ Added minimal result for hit {j}")
                        except:
                            logger.error(f"    🚨 Complete failure for hit {j}")
            
            # Sort by hybrid score (highest first)
            formatted_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            # Filter by score threshold - show all results above 1% (0.01) for good relevance
            score_threshold = 0.01
            filtered_by_score = []
            for result in formatted_results:
                score = result.get('similarity_score', 0)
                if score >= score_threshold:
                    filtered_by_score.append(result)
                else:
                    logger.debug(f"  ⚠️ Filtered out low score: {score:.3f} - {result.get('question_text', '')[:50]}...")
            
            # Log score distribution for debugging
            all_scores = [r.get('similarity_score', 0) for r in formatted_results]
            if all_scores:
                max_score = max(all_scores)
                min_score = min(all_scores)
                avg_score = sum(all_scores) / len(all_scores)
                logger.info(f"📊 Score stats: min={min_score:.3f}, max={max_score:.3f}, avg={avg_score:.3f}")
            
            logger.info(f"📊 Score filtering: {len(formatted_results)} → {len(filtered_by_score)} results above {score_threshold*100}%")
            
            # Apply LLM reranking for better relevance (before pagination)
            if len(filtered_by_score) > 1:
                logger.info(f"🤖 Applying LLM reranking for query: '{query}'")
                filtered_by_score = self._llm_rerank_results(query, filtered_by_score)
                logger.info(f"✨ LLM reranking completed")
            
            # ⚡ CACHE RESULTS: Store for future pagination (after all processing)
            self.search_cache[cache_key] = {
                'results': filtered_by_score,
                'timestamp': self._time.time(),
                'query': query,
                'total_results': len(filtered_by_score)
            }
            
            # LRU eviction: Remove oldest entries if cache is full
            while len(self.search_cache) > self.max_cache_size:
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
                logger.info(f"🧹 Evicted oldest cache entry: {oldest_key[:16]}...")
            
            logger.info(f"💾 Cached {len(filtered_by_score)} results for future pagination ({len(self.search_cache)}/{self.max_cache_size} cache slots)")
            
            # Apply pagination with offset and limit
            total_above_threshold = len(filtered_by_score)
            start_idx = offset
            end_idx = offset + limit
            final_results = filtered_by_score[start_idx:end_idx]
            
            # Log pagination summary
            logger.info(f"📄 Pagination: Showing results {start_idx+1}-{min(end_idx, total_above_threshold)} of {total_above_threshold} total")
            if total_above_threshold > end_idx:
                logger.info(f"🔜 More results available: {total_above_threshold - end_idx} remaining")
            
            formatted_results = final_results
            
            logger.info(f"🎉 Returning {len(formatted_results)} results for query: '{query[:50]}...'")
            
            # Debug: Show years in final results to detect mixed-year bugs
            if formatted_results:
                years_in_results = [str(r.get('year', 'Unknown')) for r in formatted_results]
                unique_years = list(set(years_in_results))
                logger.info(f"📅 Years in final results: {unique_years} (Expected: {[str(year_filter)] if year_filter else 'Any year'})")
                if year_filter and str(year_filter) not in unique_years:
                    logger.warning(f"⚠️ POTENTIAL BUG: Expected year {year_filter} not found in results!")
                if year_filter and len(unique_years) > 1:
                    logger.warning(f"⚠️ POTENTIAL BUG: Multiple years found when filtering for {year_filter}: {unique_years}")
            
            # Log top results with their scores
            for i, result in enumerate(formatted_results[:3]):
                year_info = result.get('year', 'Unknown')
                logger.info(f"  🏆 Top {i+1}: Score={result.get('similarity_score', 0):.4f}, Year={year_info} - {result.get('question_text', '')[:60]}...")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            if not self.collection:
                return {}
            
            num_entities = self.collection.num_entities
            
            return {
                "collection_name": self.collection_name,
                "total_questions": num_entities,
                "embedding_dimension": self.embedding_dim,
                "status": "loaded" if self.collection else "not_loaded"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {"error": str(e)}
    
    def delete_collection(self) -> bool:
        """Delete the entire collection"""
        try:
            if utility.has_collection(self.collection_name, using=self.connection_alias):
                utility.drop_collection(self.collection_name, using=self.connection_alias)
                logger.info(f"Deleted collection: {self.collection_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            return False
    
    def _generate_cache_key(self, query: str, filters: dict) -> str:
        """Generate unique cache key for query + filters"""
        import hashlib
        key_data = f"{query}_{str(sorted(filters.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cached_data: dict) -> bool:
        """Check if cached data is still valid"""
        return (self._time.time() - cached_data['timestamp']) < self.cache_ttl
    
    def _slice_results(self, results: list, offset: int, limit: int) -> list:
        """Slice results for pagination"""
        return results[offset:offset + limit]

def initialize_pyq_vector_db(questions: List[PYQQuestion]) -> PYQVectorService:
    """Initialize PYQ vector database with questions"""
    logger.info("Initializing PYQ Vector Database...")
    
    # Create service instance
    service = PYQVectorService()
    
    # Connect to Milvus
    if not service.connect():
        raise Exception("Failed to connect to Milvus")
    
    # Create collection
    if not service.create_collection():
        raise Exception("Failed to create collection")
    
    # Load collection
    if not service.load_collection():
        raise Exception("Failed to load collection")
    
    # Insert questions
    if not service.insert_questions(questions):
        raise Exception("Failed to insert questions")
    
    logger.info("PYQ Vector Database initialization completed!")
    return service

if __name__ == "__main__":
    # Test the vector service directly (no parser dependency)
    print("Testing PYQ Vector Service...")
    
    # Test with existing service
    try:
        service = PYQVectorService()
        print(f"Service created, model loaded: {service.embedding_model is not None}")
        
        if service.connect():
            print("Connected to Milvus")
            if service.load_collection():
                print(f"Collection loaded with {service.collection.num_entities} entities")
            else:
                print("Failed to load collection")
        else:
            print("Failed to connect to Milvus")
        
        # Get stats
        stats = service.get_collection_stats()
        print(f"Collection Stats: {stats}")
        
        # Test search
        test_queries = [
            "What are the key principles of secularism?",
            "Explain the role of women in freedom struggle",
            "Climate change and its impact on agriculture"
        ]
        
        for query in test_queries:
            print(f"\nSearching for: '{query}'")
            results = service.search_questions(query, limit=3)
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['question_id']} (Score: {result['similarity_score']:.3f})")
                print(f"   {result['question_text'][:100]}...")
                print(f"   Year: {result['year']}, Subject: {result['subject']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
