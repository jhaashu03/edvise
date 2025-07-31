"""
PYQ (Previous Year Questions) Search API endpoints
Provides semantic search functionality for UPSC PYQ questions
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from app.services.pyq_vector_service import PYQVectorService, PYQQuestion

logger = logging.getLogger(__name__)
router = APIRouter()

# Global service instance
pyq_service: Optional[PYQVectorService] = None

# Request/Response Models
class PYQSearchRequest(BaseModel):
    """Request model for PYQ search"""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    limit: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    year_filter: Optional[int] = Field(None, ge=2013, le=2024, description="Filter by specific year")
    subject_filter: Optional[str] = Field(None, max_length=100, description="Filter by subject")
    paper_filter: Optional[str] = Field(None, description="Filter by paper (GS1, GS2, GS3, GS4_Ethics)")

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

class PYQSearchResponse(BaseModel):
    """Response model for PYQ search"""
    results: List[PYQSearchResult]
    total_found: int
    query: str
    filters: Dict[str, Any]
    processing_time_ms: float

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
    """Search PYQ questions using semantic vector search"""
    import time
    start_time = time.time()
    
    try:
        service = get_pyq_service()
        
        # Perform search
        results = service.search_questions(
            query=search_request.query,
            limit=search_request.limit,
            year_filter=search_request.year_filter,
            subject_filter=search_request.subject_filter,
            paper_filter=search_request.paper_filter
        )
        
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
                distance=result["distance"]
            )
            for result in results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return PYQSearchResponse(
            results=search_results,
            total_found=len(search_results),
            query=search_request.query,
            filters={
                "year": search_request.year_filter,
                "subject": search_request.subject_filter,
                "paper": search_request.paper_filter
            },
            processing_time_ms=processing_time
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
