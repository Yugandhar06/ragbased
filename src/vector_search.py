"""
Vector Search interface for Qdrant
"""

import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import openai
import logging

logger = logging.getLogger(__name__)


class VectorSearch:
    """Interface for vector similarity search using Qdrant"""
    
    def __init__(
        self,
        qdrant_host: str = "qdrant",
        qdrant_port: int = 6333,
        collection_name: str = "rag_documents",
        embedding_model: str = "text-embedding-3-small",
    ):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Initialize clients
        self.qdrant_client = QdrantClient(
            host=qdrant_host,
            port=qdrant_port,
        )
        
        # Initialize OpenAI for embeddings
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - embeddings will fail")
        
        logger.info(f"Vector search initialized for collection: {collection_name}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text query"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            response = client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query text
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
            filters: Optional metadata filters
        
        Returns:
            List of documents with text, metadata, and scores
        """
        
        try:
            # Generate query embedding
            query_vector = self._generate_embedding(query)
            
            # Build filter if provided
            query_filter = None
            if filters:
                conditions = [
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                    for key, value in filters.items()
                ]
                query_filter = Filter(must=conditions) if conditions else None
            
            # Perform search
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=False,
            )
            
            # Format results
            results = []
            if search_results:
                for result in search_results:
                    results.append({
                        "id": result.id,
                        "text": result.payload.get("text", ""),
                        "metadata": result.payload.get("metadata", {}),
                        "score": result.score,
                    })
            
            logger.info(f"Found {len(results)} documents for query: '{query[:50]}...'")
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return []
    
    def get_collection_size(self) -> int:
        """Get the number of documents in the collection"""
        try:
            info = self.qdrant_client.get_collection(self.collection_name)
            return info.points_count
        except Exception as e:
            logger.error(f"Error getting collection size: {e}")
            return 0
    
    def search_by_metadata(
        self,
        metadata_filters: Dict[str, Any],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search documents by metadata without vector similarity
        
        Args:
            metadata_filters: Dictionary of metadata key-value pairs
            top_k: Maximum number of results
        
        Returns:
            List of matching documents
        """
        
        try:
            conditions = [
                FieldCondition(
                    key=f"metadata.{key}",
                    match=MatchValue(value=value)
                )
                for key, value in metadata_filters.items()
            ]
            
            query_filter = Filter(must=conditions)
            
            # Use scroll to get filtered results
            results, _ = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=query_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
            
            formatted_results = []
            for point in results:
                formatted_results.append({
                    "id": point.id,
                    "text": point.payload.get("text", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "score": 1.0,  # No similarity score for metadata search
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Metadata search error: {e}")
            return []