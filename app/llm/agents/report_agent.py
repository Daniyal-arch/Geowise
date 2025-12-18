"""Report Generation Agent"""

from typing import Dict, Any
from groq import AsyncGroq

from app.config import settings
from app.llm.prompts.system_prompts import REPORT_AGENT_PROMPT
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReportAgent:
    """Generates human-readable insights from analysis results"""
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    async def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate natural language report from analysis results"""
        
        import json
        prompt = REPORT_AGENT_PROMPT.replace(
            "{{results}}", 
            json.dumps(results, indent=2)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an environmental data analyst. Generate clear, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            report = response.choices[0].message.content
            
            logger.info("Report generated successfully")
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"Error generating report: {str(e)}"