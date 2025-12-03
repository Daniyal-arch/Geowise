"""Chroma Vector Store for RAG"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from app.llm.rag.embeddings import embedding_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Chroma DB vector store for domain knowledge"""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        """Initialize Chroma DB"""
        
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.client.get_or_create_collection(
                name="geowise_knowledge",
                metadata={"description": "GEOWISE domain knowledge base"}
            )
            
            logger.info(f"Vector store initialized: {persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ):
        """Add documents to vector store"""
        
        if not ids:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        embeddings = embedding_service.embed_texts(documents)
        
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas or [{} for _ in documents],
            ids=ids
        )
        
        logger.info(f"Added {len(documents)} documents to vector store")
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        
        query_embedding = embedding_service.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        documents = []
        for i in range(len(results['ids'][0])):
            documents.append({
                "id": results['ids'][0][i],
                "document": results['documents'][0][i],
                "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                "distance": results['distances'][0][i] if results['distances'] else None
            })
        
        logger.info(f"Found {len(documents)} relevant documents")
        return documents
    
    def clear(self):
        """Clear all documents from collection"""
        self.client.delete_collection("geowise_knowledge")
        self.collection = self.client.create_collection("geowise_knowledge")
        logger.info("Vector store cleared")
    
    def get_count(self) -> int:
        """Get number of documents in store"""
        return self.collection.count()


# Global vector store instance
vector_store = VectorStore()