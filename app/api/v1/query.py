"""Natural Language Query Endpoints (AI-Powered)"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.llm.orchestrator import orchestrator
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class NLQueryRequest(BaseModel):
    """Natural language query request"""
    query: str = Field(..., min_length=5, description="Natural language query")
    include_raw_data: bool = Field(default=False, description="Include raw analysis data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Show me fires in Pakistan from last 7 days",
                "include_raw_data": False
            }
        }


class NLQueryResponse(BaseModel):
    """Natural language query response"""
    status: str
    query: str
    intent: Optional[str] = None
    report: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RAGQueryRequest(BaseModel):
    """RAG-based question answering"""
    question: str = Field(..., min_length=5, description="Question about environmental data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What causes forest fires in tropical regions?"
            }
        }


@router.post("/nl", response_model=NLQueryResponse)
async def natural_language_query(request: NLQueryRequest):
    """
    🤖 AI-Powered Natural Language Query
    
    Process natural language queries using LLM orchestrator.
    
    **Examples:**
    - "Show me fires in Pakistan from last 7 days"
    - "Analyze correlation between fires and temperature in Brazil"
    - "Generate a report on deforestation trends in Indonesia"
    - "What are the fire hotspots in California?"
    
    **The AI will:**
    1. Parse your query to understand intent
    2. Extract parameters (country, dates, etc.)
    3. Fetch relevant data from APIs
    4. Run analysis if needed
    5. Generate human-readable insights
    """
    
    logger.info(f"Processing NL query: {request.query}")
    
    try:
        # Process query through LLM orchestrator
        result = await orchestrator.process_query(request.query)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Query processing failed")
            )
        
        # Build response
       # Build response
        response_data = {
            "status": "success",
            "query": request.query,
            "intent": result.get("intent"),
            "report": result.get("report"),
            "data": result.get("data")  # ✅ Always include data
        }
        
        logger.info(f"Query processed successfully: {result.get('intent')}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@router.post("/rag")
async def rag_query(request: RAGQueryRequest):
    """
    📚 RAG-Based Question Answering
    
    Answer questions using Retrieval Augmented Generation (RAG).
    Searches knowledge base for relevant context before answering.
    
    **Examples:**
    - "What are the main causes of wildfires?"
    - "How does deforestation affect climate?"
    - "What is H3 spatial indexing?"
    """
    
    logger.info(f"Processing RAG query: {request.question}")
    
    try:
        answer = await orchestrator.query_with_rag(request.question)
        
        return {
            "status": "success",
            "question": request.question,
            "answer": answer,
            "source": "RAG with vector store"
        }
        
    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"RAG query failed: {str(e)}"
        )


@router.get("/examples")
async def get_query_examples():
    """
    Get example queries to try
    
    Returns a list of example natural language queries
    """
    
    return {
        "fire_queries": [
            "Show me fires in Pakistan from last 7 days",
            "Find high-intensity fires in California",
            "How many fires were detected in Brazil this month?"
        ],
        "analysis_queries": [
            "Analyze correlation between fires and temperature in Pakistan",
            "Compare fire activity in India vs Pakistan",
            "What's the trend of fires in the last 30 days?"
        ],
        "report_queries": [
            "Generate a fire analysis report for Indonesia",
            "Create a summary of deforestation in Brazil",
            "Report on environmental conditions in Australia"
        ],
        "rag_questions": [
            "What causes forest fires?",
            "How does climate change affect wildfires?",
            "What is spatial correlation analysis?",
            "Explain H3 hexagonal indexing"
        ]
    }


@router.get("/health")
async def query_health():
    """Check if LLM services are available"""
    
    from app.config import settings
    
    if not settings.GROQ_API_KEY:
        return {
            "status": "unavailable",
            "message": "GROQ_API_KEY not configured",
            "llm_enabled": False
        }
    
    return {
        "status": "healthy",
        "llm_enabled": True,
        "model": settings.GROQ_MODEL,
        "provider": "Groq",
        "features": {
            "natural_language_query": True,
            "rag_qa": True,
            "report_generation": True
        }
    }