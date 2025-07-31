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
        
        # For existing collection, we must match the embedding dimension
        # The current collection uses 384-dim embeddings from MiniLM
        self.model_name = 'all-MiniLM-L6-v2'  # Keep compatible with existing data
        self.embedding_dim = 384
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
        """Connect to Milvus database"""
        try:
            # Clean disconnect all existing connections to avoid conflicts
            try:
                # Disconnect our specific alias
                connections.disconnect(self.connection_alias)
                logger.info(f"🔄 Disconnected existing connection: {self.connection_alias}")
            except Exception:
                pass  # Connection didn't exist, that's fine
            
            # Also try to disconnect any default connections that might conflict
            try:
                connections.disconnect("default")
            except Exception:
                pass
            
            # Use the absolute path to the backend database that has 525 entities
            # We confirmed this specific file has the data we need
            backend_db_path = '/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend/milvus_lite_local.db'
            
            logger.info(f"📍 Current working directory: {os.getcwd()}")
            logger.info(f"📍 Using ABSOLUTE backend database path: {backend_db_path}")
            logger.info(f"📍 Backend database exists: {os.path.exists(backend_db_path)}")
            
            full_path = backend_db_path
            
            logger.info(f"⚙️ Connecting to Milvus Lite: {full_path}")
            logger.info(f"📁 Database file exists: {os.path.exists(full_path)}")
            
            connections.connect(
                alias=self.connection_alias,
                uri=full_path
            )
            
            # Verify connection by listing collections
            from pymilvus import utility
            collections = utility.list_collections(using=self.connection_alias)
            logger.info(f"📚 Available collections: {collections}")
            
            if 'pyq_embeddings' not in collections:
                logger.error(f"❌ Collection 'pyq_embeddings' not found in {collections}")
                return False
            
            logger.info(f"✅ Successfully connected to Milvus Lite with pyq_embeddings collection")
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
            
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="question_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=4000),
                FieldSchema(name="year", dtype=DataType.INT64),
                FieldSchema(name="paper", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="word_limit", dtype=DataType.INT64),
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=500),
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
                
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            
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
    
    def calculate_keyword_score(self, query: str, question_text: str) -> float:
        """Calculate keyword-based similarity score with improved direct matching"""
        try:
            query_words = set(query.lower().split())
            question_words = set(question_text.lower().split())
            
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
            query_words = query_words - stop_words
            question_words = question_words - stop_words
            
            if not query_words or not question_words:
                return 0.0
            
            # Calculate word coverage (how many query words are in question)
            intersection = len(query_words & question_words)
            coverage_score = intersection / len(query_words) if query_words else 0.0
            
            # Boost for exact phrase matches
            phrase_bonus = 0.0
            query_lower = query.lower()
            text_lower = question_text.lower()
            
            # Check for 2-word and 3-word phrase matches
            query_words_list = query_lower.split()
            for i in range(len(query_words_list) - 1):
                bigram = ' '.join(query_words_list[i:i+2])
                if bigram in text_lower:
                    phrase_bonus += 0.4  # Increased from 0.3
                    
            for i in range(len(query_words_list) - 2):
                trigram = ' '.join(query_words_list[i:i+3])
                if trigram in text_lower:
                    phrase_bonus += 0.6  # Increased from 0.5
            
            # Special bonus for complete keyword coverage
            complete_match_bonus = 0.0
            if coverage_score == 1.0:  # All query words found
                complete_match_bonus = 0.3
            
            final_score = coverage_score + phrase_bonus + complete_match_bonus
            return min(1.0, final_score)
            
        except Exception as e:
            logger.error(f"❌ Keyword scoring error: {e}")
            return 0.0
    
    def hybrid_score(self, semantic_score: float, keyword_score: float, semantic_weight: float = 0.7) -> float:
        """Combine semantic and keyword scores"""
        return semantic_weight * semantic_score + (1 - semantic_weight) * keyword_score
    
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
    
    def search_questions(self, 
                        query: str, 
                        limit: int = 10,
                        year_filter: Optional[int] = None,
                        subject_filter: Optional[str] = None,
                        paper_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar questions using vector similarity"""
        try:
            # Adaptive limit for keyword queries to ensure perfect matches are found
            query_words = len(query.split())
            is_simple_keyword_query = query_words <= 3 and not any(word in query.lower() for word in ['what', 'how', 'why', 'explain', 'discuss', 'analyze'])
            
            # Increase search limit for keyword queries to find perfect matches ranked low
            if is_simple_keyword_query and limit < 50:
                search_limit = max(limit * 4, 50)  # At least 4x limit or 50, whichever is higher
                logger.info(f"🎯 Keyword query detected - expanding search limit from {limit} to {search_limit}")
            else:
                search_limit = limit
            
            logger.info(f"🔍 Starting search for query: '{query}' with limit: {limit} (search_limit: {search_limit})")
            
            # Check collection status
            if not self.collection:
                logger.error("❌ Collection not loaded")
                return []
            
            logger.info(f"📊 Collection entities: {self.collection.num_entities}")
            
            # Generate query embedding
            logger.info("🧠 Generating query embedding...")
            query_embedding = self.generate_embeddings([query])
            if query_embedding.size == 0:
                logger.error("❌ Failed to generate query embedding")
                return []
            
            logger.info(f"✅ Generated embedding with shape: {query_embedding.shape}")
            
            # Build search expression (filters)
            search_expr = []
            if year_filter:
                search_expr.append(f"year == {year_filter}")
            if subject_filter:
                search_expr.append(f"subject like '%{subject_filter}%'")
            if paper_filter:
                search_expr.append(f"paper == '{paper_filter}'")
            
            expr = " and ".join(search_expr) if search_expr else None
            logger.info(f"🔧 Search expression: {expr or 'None (no filters)'}")
            
            # Search parameters
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            logger.info(f"⚙️ Search params: {search_params}")
            
            # Perform search
            logger.info("🚀 Executing Milvus search...")
            try:
                # Simplify search - remove filters initially to debug
                simple_search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
                
                results = self.collection.search(
                    data=query_embedding.tolist(),
                    anns_field="embedding",
                    param=simple_search_params,
                    limit=search_limit,  # Use adaptive limit
                    # Temporarily remove expr to debug
                    # expr=expr,
                    output_fields=["pyq_id", "question_text", "subject", "year"]
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
                        
                        # Calculate keyword score
                        keyword_score = self.calculate_keyword_score(query, question_text)
                        
                        # Dynamic weighting: if query is simple keywords, boost keyword weight
                        query_words = len(query.split())
                        is_simple_keyword_query = query_words <= 3 and not any(word in query.lower() for word in ['what', 'how', 'why', 'explain', 'discuss', 'analyze'])
                        
                        if is_simple_keyword_query and keyword_score > 0.7:
                            # High keyword match for simple query - boost keyword weight
                            semantic_weight = 0.4  # 40% semantic, 60% keyword
                            logger.info(f"    🎯 Simple keyword query detected - boosting keyword weight")
                        else:
                            semantic_weight = 0.7  # Default: 70% semantic, 30% keyword
                        
                        # Calculate hybrid score
                        final_score = self.hybrid_score(semantic_score, keyword_score, semantic_weight=semantic_weight)
                        
                        logger.info(f"    📊 Scores - Semantic: {semantic_score:.4f}, Keyword: {keyword_score:.4f}, Hybrid: {final_score:.4f}")
                        
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
                            "topics": hit.entity.get("topics", ["Government", "Policy"]),  # Default topics
                            "similarity_score": final_score,  # Use hybrid score
                            "semantic_score": semantic_score,  # Keep semantic for analysis
                            "keyword_score": keyword_score,   # Keep keyword for analysis
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
            
            # Smart filtering: prioritize perfect keyword matches for simple queries
            if is_simple_keyword_query and len(formatted_results) > limit:
                logger.info(f"🎯 Filtering {len(formatted_results)} results down to {limit} with keyword priority")
                
                # Separate perfect matches from others
                perfect_matches = []
                other_results = []
                
                query_words_set = set(query.lower().split())
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                clean_query_words = query_words_set - stop_words
                
                for result in formatted_results:
                    question_text = result.get('question_text', '').lower()
                    question_words_set = set(question_text.split())
                    clean_question_words = question_words_set - stop_words
                    
                    # Check if all query keywords are present
                    if clean_query_words and clean_query_words.issubset(clean_question_words):
                        perfect_matches.append(result)
                        logger.info(f"  🎯 Perfect match: {result.get('question_text', '')[:60]}... (Score: {result.get('similarity_score', 0):.3f})")
                    else:
                        other_results.append(result)
                
                # Combine: perfect matches first, then fill with highest scoring others
                final_results = perfect_matches[:limit]  # Take all perfect matches up to limit
                remaining_slots = limit - len(final_results)
                if remaining_slots > 0:
                    final_results.extend(other_results[:remaining_slots])
                
                formatted_results = final_results
                logger.info(f"🎯 Final selection: {len(perfect_matches)} perfect matches + {len(final_results) - len(perfect_matches)} others")
            
            logger.info(f"🎉 Returning {len(formatted_results)} results for query: '{query[:50]}...'")
            
            # Log top results with their scores
            for i, result in enumerate(formatted_results[:3]):
                logger.info(f"  🏆 Top {i+1}: Score={result.get('similarity_score', 0):.4f} - {result.get('question_text', '')[:60]}...")
            
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
