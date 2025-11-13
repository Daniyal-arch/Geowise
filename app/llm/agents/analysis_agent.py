"""Analysis Planning Agent"""

import json
from typing import Dict, Any
from groq import AsyncGroq

from app.config import settings
from app.llm.prompts.system_prompts import ANALYSIS_AGENT_PROMPT
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisAgent:
    """Determines best analysis approach for given parameters"""
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    async def plan_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create analysis plan from query parameters"""
        
        prompt = ANALYSIS_AGENT_PROMPT.replace(
            "{{parameters}}", 
            json.dumps(parameters, indent=2)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an analysis planning expert. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            plan = json.loads(content)
            
            logger.info(f"Analysis plan: {plan['analysis_type']}")
            return plan
            
        except Exception as e:
            logger.error(f"Analysis planning failed: {e}")
            return {
                "analysis_type": "simple_query",
                "error": str(e)
            }