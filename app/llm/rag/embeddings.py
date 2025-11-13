"""Document Embeddings for RAG"""

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Generate embeddings for documents and queries"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model for embeddings
                       all-MiniLM-L6-v2: Fast, 384 dimensions
                       all-mpnet-base-v2: Better quality, 768 dimensions
        """
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        emb1 = np.array(self.embed_text(text1))
        emb2 = np.array(self.embed_text(text2))
        
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)


# Global embedding service instance
embedding_service = EmbeddingService()