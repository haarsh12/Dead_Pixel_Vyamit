"""
Embedding Pipeline - Gemini API Only
Clean implementation with proper error handling
"""
import os
import time
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 768  # Gemini embedding-001 dimension


class GeminiEmbeddingPipeline:
    """Gemini API embedding service (768D)"""
    
    def __init__(self):
        self._genai = None
        self._initialized = False
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.error("GEMINI_API_KEY not found in environment")
            raise ValueError(
                "GEMINI_API_KEY is required. Add it to .env file. "
                "Get API key from: https://makersuite.google.com/app/apikey"
            )
    
    def _ensure_initialized(self):
        """Lazy initialization of Gemini client"""
        if self._initialized:
            return
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai
            self._initialized = True
            logger.info(f"[OK] Gemini embedding API initialized ({EMBEDDING_DIMENSION}D)")
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini API: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text
        
        Args:
            text: Input text
        
        Returns:
            768-dimensional embedding vector
        """
        self._ensure_initialized()
        
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIMENSION
        
        try:
            start = time.time()
            
            result = self._genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_query"
            )
            
            duration = time.time() - start
            embedding = result['embedding']
            
            logger.debug(f"Generated embedding in {duration*1000:.2f}ms")
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * EMBEDDING_DIMENSION
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
        
        Returns:
            List of 768-dimensional embeddings
        """
        self._ensure_initialized()
        
        if not texts:
            return []
        
        try:
            results = []
            batch_size = 100  # Gemini's batch limit
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                result = self._genai.embed_content(
                    model="models/embedding-001",
                    content=batch,
                    task_type="retrieval_document"
                )
                
                # Handle single or batch response
                if isinstance(result['embedding'][0], list):
                    results.extend(result['embedding'])
                else:
                    results.append(result['embedding'])
            
            logger.info(f"Generated {len(results)} embeddings in batch")
            return results
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [[0.0] * EMBEDDING_DIMENSION for _ in texts]
    
    def generate_query_embedding(self, query: str) -> Tuple[List[float], float]:
        """
        Generate embedding with timing
        
        Args:
            query: Query text
        
        Returns:
            (embedding, time_taken_seconds)
        """
        start = time.time()
        embedding = self.generate_embedding(query)
        duration = time.time() - start
        return embedding, duration
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return EMBEDDING_DIMENSION
    
    def get_info(self) -> dict:
        """Get pipeline information"""
        return {
            "provider": "gemini_api",
            "model": "embedding-001",
            "dimension": EMBEDDING_DIMENSION,
            "initialized": self._initialized,
            "api_key_set": bool(self.api_key)
        }


# Global singleton instance
embedding_pipeline = GeminiEmbeddingPipeline()
