"""
PYQ (Previous Year Questions) Search API endpoints
Provides semantic search functionality for UPSC PYQ questions
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from app.services.pyq_vector_service import PYQVectorService, PYQQuestion
from app.services.advanced_pyq_search import AdvancedPYQSearch, create_advanced_pyq_search, initialize_advanced_search

logger = logging.getLogger(__name__)
router = APIRouter()

# Global service instances
pyq_service: Optional[PYQVectorService] = None
advanced_pyq_service: Optional[AdvancedPYQSearch] = None

# Request/Response Models
class PYQSearchRequest(BaseModel):
    """Request model for PYQ search"""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    limit: int = Field(default=10, ge=1, le=50, description="Number of results to return per page")
    offset: int = Field(default=0, ge=0, description="Number of results to skip (for pagination)")
    min_score_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum similarity score threshold (default 10%)")
    year_filter: Optional[int] = Field(None, ge=2013, le=2024, description="Filter by specific year")
    subject_filter: Optional[str] = Field(None, max_length=100, description="Filter by subject")
    paper_filter: Optional[str] = Field(None, description="Filter by paper (GS1, GS2, GS3, GS4_Ethics)")
    strategy: str = Field(default="enhanced", description="Search strategy: basic, enhanced, premium")
    semantic_search_only: Optional[bool] = Field(default=False, description="Use semantic search only (backward compatibility)")

class PYQSearchResult(BaseModel):
    """Single PYQ search result"""
    id: int
    question_id: str
    question: str  # Frontend expects this field
    question_text: str  # Keep for backward compatibility
    year: int
    paper: str
    subject: str
    word_limit: Optional[int]
    marks: Optional[int]
    tags: List[str]
    similarity_score: float
    distance: float
    # Advanced search metadata
    semantic_rerank_score: Optional[float] = None
    combined_score: Optional[float] = None
    search_strategy: Optional[str] = None
    enhanced_processed: Optional[bool] = None
    diversity_applied: Optional[bool] = None

class PYQSearchResponse(BaseModel):
    """Response model for PYQ search"""
    results: List[PYQSearchResult]
    total_found: int
    query: str
    filters: Dict[str, Any]
    processing_time_ms: float
    # Pagination metadata
    pagination: Dict[str, Any]

class PYQStatsResponse(BaseModel):
    """Response model for PYQ statistics"""
    collection_name: str
    total_questions: int
    embedding_dimension: int
    status: str
    years_available: List[int]
    subjects_available: List[str]
    papers_available: List[str]

class InitializationResponse(BaseModel):
    """Response model for database initialization"""
    success: bool
    message: str
    questions_loaded: int
    processing_time_ms: float

# Initialize PYQ service
def get_pyq_service() -> PYQVectorService:
    """Get or initialize PYQ service"""
    global pyq_service
    if pyq_service is None:
        logger.info("Initializing PYQ Vector Service...")
        pyq_service = PYQVectorService()
        if not pyq_service.connect():
            raise HTTPException(status_code=500, detail="Failed to connect to Milvus database")
        if not pyq_service.load_collection():
            raise HTTPException(status_code=500, detail="Failed to load PYQ collection")
    return pyq_service

def get_advanced_pyq_service() -> AdvancedPYQSearch:
    """Get the Advanced PYQ service initialized in main.py"""
    global advanced_pyq_service
    
    # Try to get the service initialized in main.py
    try:
        import app.api.api_v1.endpoints.advanced_search as advanced_search_module
        if hasattr(advanced_search_module, 'advanced_search_service') and advanced_search_module.advanced_search_service is not None:
            logger.info("✅ Using Advanced PYQ service initialized in main.py")
            return advanced_search_module.advanced_search_service
    except Exception as e:
        logger.warning(f"⚠️ Could not get advanced service from main.py: {e}")
    
    # Fallback: create basic advanced service without enhanced features
    if advanced_pyq_service is None:
        try:
            logger.info("🚀 Creating basic Advanced PYQ Search Service...")
            advanced_pyq_service = create_advanced_pyq_search()
            logger.info("✅ Basic Advanced PYQ service created (enhanced features may not be available)")
        except Exception as e:
            logger.error(f"❌ Failed to create Advanced PYQ service: {e}")
            logger.info("Falling back to basic PYQ service")
            # Return basic service as fallback
            raise Exception("Advanced service not available")
            
    return advanced_pyq_service

@router.post("/initialize", response_model=InitializationResponse)
async def initialize_pyq_database():
    """Initialize PYQ database with questions from documents"""
    import time
    start_time = time.time()
    
    try:
        logger.info("Starting PYQ database initialization...")
        
        # Parse PYQ documents
        pyq_dir = "/Users/a0j0agc/Desktop/Personal/Dump/PYQ/MAINS"
        parser = PYQParser(pyq_dir)
        questions = parser.parse_all_files()
        
        if not questions:
            raise HTTPException(status_code=400, detail="No questions found in PYQ directory")
        
        # Initialize vector service
        from app.services.pyq_vector_service import initialize_pyq_vector_db
        global pyq_service
        pyq_service = initialize_pyq_vector_db(questions)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"PYQ database initialized successfully with {len(questions)} questions")
        
        return InitializationResponse(
            success=True,
            message=f"Successfully initialized PYQ database with {len(questions)} questions from {len(set(q.year for q in questions))} years",
            questions_loaded=len(questions),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize PYQ database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {str(e)}")

@router.post("/search", response_model=PYQSearchResponse)
async def search_pyq_questions(search_request: PYQSearchRequest):
    """Search PYQ questions using advanced semantic vector search"""
    import time
    start_time = time.time()
    
    try:
        # Calculate search limit for pagination (get more results to apply threshold and pagination)
        search_limit = min(search_request.limit + search_request.offset + 50, 200)  # Get extra results for filtering
        
        # Try to use advanced service first, fallback to basic if needed
        try:
            advanced_service = get_advanced_pyq_service()
            logger.info(f"🔍 Using advanced search with strategy: {search_request.strategy}, limit: {search_limit}")
            
            # Use advanced search with strategy (get more results for pagination)
            all_results = advanced_service.search_questions_advanced(
                query=search_request.query,
                limit=search_limit,
                strategy=search_request.strategy,
                year_filter=search_request.year_filter,
                subject_filter=search_request.subject_filter,
                paper_filter=search_request.paper_filter
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Advanced search failed, falling back to basic: {e}")
            # Fallback to basic service
            service = get_pyq_service()
            all_results = service.search_questions(
                query=search_request.query,
                limit=search_limit,
                year_filter=search_request.year_filter,
                subject_filter=search_request.subject_filter,
                paper_filter=search_request.paper_filter
            )
        
        # Apply score threshold filtering
        filtered_results = [
            result for result in all_results 
            if result.get("similarity_score", 0) >= search_request.min_score_threshold or 
               result.get("combined_score", 0) >= search_request.min_score_threshold
        ]
        
        # Apply pagination
        total_filtered = len(filtered_results)
        paginated_results = filtered_results[search_request.offset:search_request.offset + search_request.limit]
        
        logger.info(f"📊 Pagination: {len(all_results)} total -> {total_filtered} after threshold -> {len(paginated_results)} after pagination")
        
        # Convert to response format
        search_results = [
            PYQSearchResult(
                id=result["id"],
                question_id=result["question_id"],
                question=result.get("question", result.get("question_text", "Question not available")),  # Frontend field
                question_text=result.get("question_text", result.get("question", "Question not available")),  # Backward compatibility
                year=result["year"],
                paper=result["paper"],
                subject=result["subject"],
                word_limit=result.get("word_limit", 150),  # Default to 150 words for UPSC questions
                marks=result["marks"] if result["marks"] > 0 else None,
                tags=result.get("topics", []),  # Use topics field from our search results
                similarity_score=result["similarity_score"],
                distance=result["distance"],
                # Advanced search metadata (if available)
                semantic_rerank_score=result.get("semantic_rerank_score"),
                combined_score=result.get("combined_score"),
                search_strategy=result.get("search_strategy"),
                enhanced_processed=result.get("enhanced_processed"),
                diversity_applied=result.get("diversity_applied")
            )
            for result in paginated_results  # Use paginated results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        # Calculate pagination metadata
        current_page = (search_request.offset // search_request.limit) + 1
        total_pages = (total_filtered + search_request.limit - 1) // search_request.limit  # Ceiling division
        has_next = search_request.offset + search_request.limit < total_filtered
        has_previous = search_request.offset > 0
        
        return PYQSearchResponse(
            results=search_results,
            total_found=total_filtered,  # Total after threshold filtering
            query=search_request.query,
            filters={
                "year": search_request.year_filter,
                "subject": search_request.subject_filter,
                "paper": search_request.paper_filter,
                "strategy": search_request.strategy,
                "semantic_search_only": search_request.semantic_search_only,
                "min_score_threshold": search_request.min_score_threshold
            },
            processing_time_ms=processing_time,
            pagination={
                "current_page": current_page,
                "total_pages": total_pages,
                "page_size": search_request.limit,
                "offset": search_request.offset,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_results_after_threshold": total_filtered,
                "results_on_current_page": len(search_results)
            }
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/stats", response_model=PYQStatsResponse)
async def get_pyq_stats():
    """Get PYQ database statistics"""
    try:
        service = get_pyq_service()
        stats = service.get_collection_stats()
        
        # Get available filters from a sample search
        sample_results = service.search_questions("sample", limit=100)
        
        years = sorted(list(set(r["year"] for r in sample_results)))
        subjects = sorted(list(set(r["subject"] for r in sample_results)))
        papers = sorted(list(set(r["paper"] for r in sample_results)))
        
        return PYQStatsResponse(
            collection_name=stats.get("collection_name", ""),
            total_questions=stats.get("total_questions", 0),
            embedding_dimension=stats.get("embedding_dimension", 0),
            status=stats.get("status", "unknown"),
            years_available=years,
            subjects_available=subjects,
            papers_available=papers
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.get("/search/suggestions")
async def get_search_suggestions(q: str = Query(..., min_length=1, max_length=100)):
    """Get search suggestions based on partial query"""
    try:
        # Common UPSC topics and keywords for suggestions
        suggestions = [
            "secularism principles",
            "women in freedom struggle",
            "climate change agriculture",
            "constitutional amendments",
            "economic reforms India",
            "foreign policy challenges",
            "governance reforms",
            "social justice issues",
            "environmental conservation",
            "cultural heritage preservation",
            "urbanization problems",
            "education policy reforms",
            "healthcare system improvements",
            "judicial reforms needed",
            "electoral reforms democracy"
        ]
        
        # Filter suggestions based on query
        filtered_suggestions = [s for s in suggestions if q.lower() in s.lower()]
        
        return {"suggestions": filtered_suggestions[:5]}
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if pyq_service:
            stats = pyq_service.get_collection_stats()
            return {
                "status": "healthy",
                "service": "pyq_search",
                "database_connected": True,
                "total_questions": stats.get("total_questions", 0)
            }
        else:
            return {
                "status": "not_initialized",
                "service": "pyq_search",
                "database_connected": False,
                "message": "PYQ service not initialized. Call /initialize first."
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "pyq_search",
            "error": str(e)
        }

# Advanced search endpoints
@router.post("/search/advanced", response_model=PYQSearchResponse)
async def advanced_search_pyq_questions(
    query: str = Query(..., min_length=3, max_length=500),
    limit: int = Query(default=10, ge=1, le=50),
    years: Optional[str] = Query(None, description="Comma-separated years e.g., '2020,2021,2022'"),
    subjects: Optional[str] = Query(None, description="Comma-separated subjects"),
    papers: Optional[str] = Query(None, description="Comma-separated papers"),
    min_marks: Optional[int] = Query(None, ge=0, le=30),
    max_marks: Optional[int] = Query(None, ge=0, le=30),
    min_words: Optional[int] = Query(None, ge=0, le=500),
    max_words: Optional[int] = Query(None, ge=0, le=500)
):
    """Advanced search with multiple filters"""
    import time
    start_time = time.time()
    
    try:
        service = get_pyq_service()
        
        # Parse filter parameters
        year_list = [int(y.strip()) for y in years.split(",")] if years else None
        subject_list = [s.strip() for s in subjects.split(",")] if subjects else None
        paper_list = [p.strip() for p in papers.split(",")] if papers else None
        
        # For advanced search, we'll do multiple searches and combine results
        all_results = []
        
        # If no year filter specified, search without year filter
        if not year_list:
            results = service.search_questions(
                query=query,
                limit=limit,
                subject_filter=subject_list[0] if subject_list else None,
                paper_filter=paper_list[0] if paper_list else None
            )
            all_results.extend(results)
        else:
            # Search for each year and combine results
            for year in year_list[:3]:  # Limit to 3 years for performance
                results = service.search_questions(
                    query=query,
                    limit=limit//len(year_list) + 1,
                    year_filter=year,
                    subject_filter=subject_list[0] if subject_list else None,
                    paper_filter=paper_list[0] if paper_list else None
                )
                all_results.extend(results)
        
        # Apply additional filters
        filtered_results = []
        for result in all_results:
            # Apply marks filter
            if min_marks and result.get("marks", 0) < min_marks:
                continue
            if max_marks and result.get("marks", 0) > max_marks:
                continue
                
            # Apply word limit filter
            if min_words and result.get("word_limit", 0) < min_words:
                continue
            if max_words and result.get("word_limit", 0) > max_words:
                continue
            
            filtered_results.append(result)
        
        # Remove duplicates and sort by similarity
        seen_ids = set()
        unique_results = []
        for result in sorted(filtered_results, key=lambda x: x["similarity_score"], reverse=True):
            if result["question_id"] not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result["question_id"])
        
        # Limit results
        final_results = unique_results[:limit]
        
        # Convert to response format
        search_results = [
            PYQSearchResult(
                id=result["id"],
                question_id=result["question_id"],
                question_text=result["question_text"],
                year=result["year"],
                paper=result["paper"],
                subject=result["subject"],
                word_limit=result["word_limit"] if result["word_limit"] > 0 else None,
                marks=result["marks"] if result["marks"] > 0 else None,
                tags=result["tags"],
                similarity_score=result["similarity_score"],
                distance=result["distance"]
            )
            for result in final_results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return PYQSearchResponse(
            results=search_results,
            total_found=len(search_results),
            query=query,
            filters={
                "years": year_list,
                "subjects": subject_list,
                "papers": paper_list,
                "min_marks": min_marks,
                "max_marks": max_marks,
                "min_words": min_words,
                "max_words": max_words
            },
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Advanced search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Advanced search failed: {str(e)}")
