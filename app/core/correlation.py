"""
GEOWISE Spatial Correlation Analysis
Statistical correlation between fire, climate, and deforestation data
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from scipy import stats
from datetime import date

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CorrelationAnalyzer:
    """Spatial correlation analysis."""
    
    @staticmethod
    def pearson_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
        """Calculate Pearson correlation coefficient."""
        if len(x) < 3 or len(y) < 3:
            raise ValueError("Need at least 3 data points")
        
        corr, p_value = stats.pearsonr(x, y)
        return float(corr), float(p_value)
    
    @staticmethod
    def spearman_correlation(x: List[float], y: List[float]) -> Tuple[float, float]:
        """Calculate Spearman rank correlation."""
        if len(x) < 3 or len(y) < 3:
            raise ValueError("Need at least 3 data points")
        
        corr, p_value = stats.spearmanr(x, y)
        return float(corr), float(p_value)
    
    @staticmethod
    def linear_regression(x: List[float], y: List[float]) -> Dict[str, float]:
        """Calculate linear regression."""
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "std_error": float(std_err)
        }
    
    @staticmethod
    def analyze_fire_temperature(
        fire_data: List[Dict[str, Any]],
        temperature_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze correlation between fires and temperature."""
        
        fire_counts = [cell["fire_count"] for cell in fire_data]
        temperatures = [cell["temperature"] for cell in temperature_data]
        
        if len(fire_counts) != len(temperatures):
            raise ValueError("Data length mismatch")
        
        corr, p_value = CorrelationAnalyzer.pearson_correlation(fire_counts, temperatures)
        regression = CorrelationAnalyzer.linear_regression(temperatures, fire_counts)
        
        return {
            "correlation_coefficient": corr,
            "p_value": p_value,
            "is_significant": p_value < 0.05,
            "r_squared": regression["r_squared"],
            "slope": regression["slope"],
            "sample_size": len(fire_counts)
        }


correlation_analyzer = CorrelationAnalyzer()