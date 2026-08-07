"""
RAG Pipeline - Embedding Provider
Flexible embedding generation supporting multiple providers:
1. Local E5 Model (intfloat/multilingual-e5-small)
2. Google Gemini API (text-embedding-004)

Configure via EMBEDDING_PROVIDER env variable:
- EMBEDDING_PROVIDER=1 → Local model (default, no API key needed)
- EMBEDDING_PROVIDER=2 → Google Gemini API (requires GEMINI_API_KEY)
"""

import os
import time
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod


class EmbeddingProviderBase(ABC):
    """Base class for embedding providers"""
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        pass
    
    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass
    
    @abstractmethod
    def get_info(self) -> dict:
        """Get provider information"""
        pass


class LocalE5Provider(EmbeddingProviderBase):
    """Local E5 multilingual embedding model (384D) - OPTIONAL"""
    
    def __init__(self):
        self._model = None
        self._dimension = 384
        self._unavailable = False
    
    def _ensure_initialized(self):
        """Lazy load model only when needed - gracefully handles missing dependency"""
        if self._unavailable:
            raise RuntimeError(
                "sentence-transformers not available. "
                "Use EMBEDDING_PROVIDER=2 for Gemini API embeddings, "
                "or install: pip install sentence-transformers torch"
            )
        
        if self._model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
            print(f"[INFO] Loading local embedding model: {model_name}...")
            start = time.time()
            self._model = SentenceTransformer(model_name)
            duration = time.time() - start
            self._dimension = self._model.get_sentence_embedding_dimension()
            print(f"[OK] Local model loaded in {duration:.2f}s ({self._dimension}D)")
        except ImportError as e:
            self._unavailable = True
            print(f"[WARN] sentence-transformers not installed: {e}")
            print("[INFO] Set EMBEDDING_PROVIDER=2 to use Gemini API embeddings")
            raise ImportError(
                "sentence-transformers not installed. "
                "Use EMBEDDING_PROVIDER=2 for Gemini API, "
                "or run: pip install sentence-transformers torch"
            )
        except Exception as e:
            self._unavailable = True
            print(f"[ERROR] Failed to load local embedding model: {e}")
            raise RuntimeError(f"Failed to load local embedding model: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        self._ensure_initialized()
        
        if not text or not text.strip():
            return [0.0] * self._dimension
        
        try:
            from app.utils.debug_logger import embedding_logger
            
            start = time.time()
            embedding_logger.info(f"Generating embedding (Local E5)")
            embedding_logger.debug(f"Input: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            embedding = self._model.encode(text, normalize_embeddings=True)
            duration = time.time() - start
            
            embedding_list = embedding.tolist()
            embedding_logger.success(f"Generated {self._dimension}D embedding in {duration*1000:.2f}ms")
            embedding_logger.debug(f"Sample: [{', '.join([f'{x:.4f}' for x in embedding_list[:5]])}...]")
            
            return embedding_list
        except Exception as e:
            print(f"[ERROR] Local embedding generation failed: {e}")
            return [0.0] * self._dimension
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        self._ensure_initialized()
        
        if not texts:
            return []
        
        try:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False
            )
            return embeddings.tolist()
        except Exception as e:
            print(f"[ERROR] Batch embedding generation failed: {e}")
            return [[0.0] * self._dimension for _ in texts]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self._dimension
    
    def get_info(self) -> dict:
        """Get provider information"""
        return {
            'provider': 'local_e5',
            'model_name': os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small"),
            'dimension': self._dimension,
            'status': 'loaded' if self._model else 'not_loaded',
            'lazy_loading': True,
            'cost': 'free',
            'ram_usage': '~100MB'
        }


class GeminiEmbeddingProvider(EmbeddingProviderBase):
    """Google Gemini API embedding provider (768D)"""
    
    def __init__(self):
        self._dimension = 768
        self._api_key = os.getenv("GEMINI_API_KEY")
        self._genai = None
        
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment. "
                "Set it in .env file to use Gemini embeddings."
            )
    
    def _ensure_initialized(self):
        """Initialize Gemini API client"""
        if self._genai is not None:
            return
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._genai = genai
            print(f"[OK] Gemini embedding API initialized (embedding-001, {self._dimension}D)")
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Run: pip install google-generativeai"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini API: {e}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        self._ensure_initialized()
        
        if not text or not text.strip():
            return [0.0] * self._dimension
        
        try:
            from app.utils.debug_logger import embedding_logger
            
            start = time.time()
            embedding_logger.info(f"Generating embedding (Gemini API)")
            embedding_logger.debug(f"Input: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            # Use embedding_model endpoint (v1 API, not v1beta)
            result = self._genai.embed_content(
                model="models/embedding-001",  # v1 stable model
                content=text,
                task_type="retrieval_query"
            )
            duration = time.time() - start
            
            embedding = result['embedding']
            embedding_logger.success(f"Generated {self._dimension}D embedding in {duration*1000:.2f}ms")
            embedding_logger.debug(f"Sample: [{', '.join([f'{x:.4f}' for x in embedding[:5]])}...]")
            
            return embedding
        except Exception as e:
            print(f"[ERROR] Gemini embedding generation failed: {e}")
            return [0.0] * self._dimension
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        self._ensure_initialized()
        
        if not texts:
            return []
        
        try:
            # Gemini supports batch embedding with embedding-001
            results = []
            # Process in batches of 100 (Gemini's limit)
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                result = self._genai.embed_content(
                    model="models/embedding-001",
                    content=batch,
                    task_type="retrieval_document"
                )
                # Handle both single and batch responses
                if isinstance(result['embedding'][0], list):
                    results.extend(result['embedding'])
                else:
                    results.append(result['embedding'])
            return results
        except Exception as e:
            print(f"[ERROR] Batch Gemini embedding generation failed: {e}")
            return [[0.0] * self._dimension for _ in texts]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self._dimension
    
    def get_info(self) -> dict:
        """Get provider information"""
        return {
            'provider': 'gemini_api',
            'model_name': 'embedding-001',
            'dimension': self._dimension,
            'status': 'initialized' if self._genai else 'not_initialized',
            'lazy_loading': True,
            'cost': 'free (1500 req/min)',
            'ram_usage': '~5MB'
        }


class UnifiedEmbeddingPipeline:
    """
    Unified embedding pipeline with provider switching
    
    Environment Configuration:
    - EMBEDDING_PROVIDER=1 → Local E5 model (default)
    - EMBEDDING_PROVIDER=2 → Gemini API
    - GEMINI_API_KEY=your_key → Required for provider=2
    """
    
    def __init__(self):
        self._provider: Optional[EmbeddingProviderBase] = None
        self._provider_type = None
    
    def _ensure_initialized(self):
        """Lazy initialization based on EMBEDDING_PROVIDER setting"""
        if self._provider is not None:
            return
        
        provider_choice = os.getenv("EMBEDDING_PROVIDER", "1")
        
        print(f"\n{'='*60}")
        print("EMBEDDING PIPELINE INITIALIZATION")
        print(f"{'='*60}")
        
        try:
            if provider_choice == "2":
                print("[INFO] Selected provider: Gemini API (embedding-001)")
                self._provider = GeminiEmbeddingProvider()
                self._provider_type = "gemini"
            else:
                print("[INFO] Selected provider: Local E5 Model")
                try:
                    self._provider = LocalE5Provider()
                    self._provider_type = "local"
                except (ImportError, RuntimeError) as e:
                    print(f"[WARN] Local E5 unavailable: {e}")
                    print("[INFO] Attempting fallback to Gemini API...")
                    try:
                        self._provider = GeminiEmbeddingProvider()
                        self._provider_type = "gemini"
                        print("[OK] Fallback to Gemini API successful")
                    except Exception as fallback_err:
                        print(f"[ERROR] Gemini fallback also failed: {fallback_err}")
                        raise RuntimeError(
                            "No embedding provider available. "
                            "Either install sentence-transformers or set GEMINI_API_KEY"
                        )
            
            # Trigger lazy loading
            _ = self._provider.get_dimension()
            
            info = self._provider.get_info()
            print(f"[OK] Provider: {info['provider']}")
            print(f"[OK] Model: {info['model_name']}")
            print(f"[OK] Dimension: {info['dimension']}")
            print(f"[OK] RAM Usage: {info['ram_usage']}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize any embedding provider: {e}")
            print("[WARN] Embedding features will be unavailable")
            self._provider = None
            self._provider_type = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if self._provider is None:
            print("[WARN] No embedding provider available, returning zero vector")
            return [0.0] * 384  # Default dimension
        
        self._ensure_initialized()
        return self._provider.generate_embedding(text)
    
    def generate_query_embedding(self, query: str) -> Tuple[List[float], float]:
        """
        Generate embedding for a query with timing
        
        Returns:
            (embedding, time_taken)
        """
        start = time.time()
        embedding = self.generate_embedding(query)
        duration = time.time() - start
        return embedding, duration
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self._provider is None:
            print("[WARN] No embedding provider available, returning zero vectors")
            return [[0.0] * 384 for _ in texts]  # Default dimension
        
        self._ensure_initialized()
        return self._provider.generate_embeddings_batch(texts)
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        if self._provider is None:
            return 384  # Default dimension
        self._ensure_initialized()
        return self._provider.get_dimension()
    
    def get_model_info(self) -> dict:
        """Get model information"""
        if self._provider is None:
            provider_choice = os.getenv("EMBEDDING_PROVIDER", "1")
            return {
                'status': 'not_loaded',
                'selected_provider': 'gemini' if provider_choice == "2" else 'local',
                'lazy_loading': True
            }
        
        info = self._provider.get_info()
        info['selected_via'] = 'EMBEDDING_PROVIDER=' + os.getenv("EMBEDDING_PROVIDER", "1")
        return info


# Global singleton instance
embedding_pipeline = UnifiedEmbeddingPipeline()
