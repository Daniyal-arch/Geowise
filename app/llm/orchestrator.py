"""LLM Orchestrator - Main AI Controller"""

from typing import Dict, Any, Optional
from datetime import date

from app.llm.agents import QueryAgent, AnalysisAgent, ReportAgent
from app.llm.rag import vector_store
from app.database import get_db
from app.core.aggregation import fire_aggregator
from app.core.correlation import correlation_analyzer
from app.services.nasa_firms import NASAFIRMSService
from app.models.forest import ForestMonitor
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMOrchestrator:
    """
    Main AI orchestrator that coordinates all agents
    
    Flow:
    1. User query → QueryAgent (parse intent & parameters)
    2. Parameters → AnalysisAgent (plan analysis)
    3. Execute analysis (fetch data, run correlations)
    4. Results → ReportAgent (generate insights)
    5. Return to user
    """
    
    def __init__(self):
        self.query_agent = QueryAgent()
        self.analysis_agent = AnalysisAgent()
        self.report_agent = ReportAgent()
        self.nasa_service = NASAFIRMSService(api_key=settings.NASA_FIRMS_API_KEY)
        self.forest_monitor = ForestMonitor()
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process natural language query end-to-end
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            Dict with analysis results and generated report
        """
        
        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Parse query
        parsed = await self.query_agent.parse_query(user_query)
        
        if parsed.get("error"):
            return {
                "status": "error",
                "message": "Failed to understand query",
                "error": parsed["error"]
            }
        
        intent = parsed.get("intent")
        parameters = parsed.get("parameters", {})
        
        logger.info(f"Intent: {intent}, Parameters: {parameters}")
        
        # Step 2: Execute based on intent
        if intent == "query_fires":
            result = await self._query_fires(parameters)
        
        elif intent == "analyze_correlation":
            result = await self._analyze_correlation(parameters)
        
        elif intent == "generate_report":
            result = await self._generate_report(parameters)
        
        else:
            result = {"status": "error", "message": f"Unknown intent: {intent}"}
        
        # Step 3: Generate natural language report
        if result.get("status") != "error":
            report = await self.report_agent.generate_report(result)
            result["report"] = report
        
        return result
    
    async def _query_fires(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Query fire data based on parameters"""
        
        country_iso = parameters.get("country_iso")
        date_range = parameters.get("date_range", {})
        
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            async with self.nasa_service:
                fires = await self.nasa_service.get_fires_by_country(
                    country_iso=country_iso,
                    days=7
                )
            
            return {
                "status": "success",
                "intent": "query_fires",
                "data": {
                    "country": country_iso,
                    "fire_count": len(fires),
                    "fires": [
                        {
                            "latitude": f.latitude,
                            "longitude": f.longitude,
                            "frp": f.frp,
                            "confidence": f.confidence,
                            "date": f.acq_date.isoformat() if f.acq_date else None
                        }
                        for f in fires[:10]  # Limit to 10 for report
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Fire query failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _analyze_correlation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run correlation analysis"""
        
        country_iso = parameters.get("country_iso")
        
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            # Get fire data
            async with self.nasa_service:
                fires = await self.nasa_service.get_fires_by_country(country_iso, days=7)
            
            # Get forest data
            forest_stats = self.forest_monitor.get_country_forest_stats(country_iso)
            
            # Simple correlation (placeholder - needs DB data for proper analysis)
            fire_count = len(fires)
            forest_loss = forest_stats.get("tree_cover_loss", {}).get("total_loss_ha", 0) if forest_stats else 0
            
            return {
                "status": "success",
                "intent": "analyze_correlation",
                "data": {
                    "country": country_iso,
                    "fire_count": fire_count,
                    "forest_loss_ha": forest_loss,
                    "analysis": "Correlation analysis requires historical data in database"
                }
            }
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _generate_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive report"""
        
        country_iso = parameters.get("country_iso")
        
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            # Gather all data
            async with self.nasa_service:
                fires = await self.nasa_service.get_fires_by_country(country_iso, days=7)
            
            forest_stats = self.forest_monitor.get_country_forest_stats(country_iso)
            forest_trend = self.forest_monitor.analyze_deforestation_trend(country_iso)
            
            return {
                "status": "success",
                "intent": "generate_report",
                "data": {
                    "country": country_iso,
                    "fire_summary": {
                        "total_fires": len(fires),
                        "avg_frp": sum(f.frp for f in fires if f.frp) / len([f for f in fires if f.frp]) if fires else 0
                    },
                    "forest_summary": forest_stats,
                    "forest_trend": forest_trend
                }
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def query_with_rag(self, question: str) -> str:
        """
        Answer question using RAG (Retrieval Augmented Generation)
        
        Args:
            question: User question
            
        Returns:
            Answer generated using retrieved context
        """
        
        # Search for relevant documents
        relevant_docs = vector_store.search(question, n_results=3)
        
        if not relevant_docs:
            return "I don't have enough context to answer this question."
        
        # Build context from retrieved documents
        context = "\n\n".join([doc["document"] for doc in relevant_docs])
        
        # Generate answer using ReportAgent
        from app.llm.prompts.system_prompts import RAG_CONTEXT_PROMPT
        from groq import AsyncGroq
        
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        
        prompt = RAG_CONTEXT_PROMPT.replace("{{context}}", context).replace("{{question}}", question)
        
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer based only on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content


# Global orchestrator instance
orchestrator = LLMOrchestrator()