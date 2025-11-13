"""Query Understanding Agent"""

import json
from typing import Dict, Any
from groq import AsyncGroq

from app.config import settings
from app.llm.prompts.system_prompts import QUERY_AGENT_PROMPT
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryAgent:
    """Understands natural language queries and extracts parameters"""
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    async def parse_query(self, user_query: str) -> Dict[str, Any]:
        """Parse natural language query into structured parameters"""
        
        prompt = QUERY_AGENT_PROMPT.replace("{{query}}", user_query)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a geospatial query parser. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            
            logger.info(f"Query parsed: {parsed['intent']}")
            return parsed
            
        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            return {
                "intent": "unknown",
                "parameters": {},
                "error": str(e)
            }