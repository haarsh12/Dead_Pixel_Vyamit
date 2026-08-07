"""
RAG Pipeline Configuration
All configurable parameters in one place
"""

import os
from typing import Optional
from pydantic import BaseModel


class EmbeddingConfig(BaseModel):
    """Embedding model configuration"""
    model_name: str = "intfloat/multilingual-e5-small"
    dimension: int = 384
    batch_size: int = 32
    cache_dir: Optional[str] = None


class RetrievalConfig(BaseModel):
    """Retrieval configuration"""
    # Item retrieval
    item_top_k: int = 5
    item_similarity_threshold: float = 0.3
    
    # Customer retrieval
    customer_top_k: int = 5
    customer_similarity_threshold: float = 0.4
    
    # Customer history
    max_bills_per_customer: int = 10
    history_days: int = 90


class AnalyticsConfig(BaseModel):
    """Analytics metrics configuration"""
    default_period_days: int = 30
    top_items_count: int = 10
    low_stock_threshold: float = 10.0
    out_of_stock_threshold: float = 0.0


class LLMConfig(BaseModel):
    """LLM configuration"""
    # Primary model (Mistral)
    primary_model: str = "mistral-large-latest"
    primary_temperature: float = 0.1
    primary_max_tokens: int = 500
    
    # Fallback model (Gemini)
    fallback_models: list = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest"
    ]
    fallback_temperature: float = 0.1
    fallback_max_tokens: int = 500
    
    # Timeout
    timeout_seconds: int = 30


class LoggingConfig(BaseModel):
    """Logging configuration"""
    enabled: bool = True
    log_embeddings: bool = True
    log_retrieval: bool = True
    log_context: bool = True
    log_llm: bool = True
    log_latency: bool = True
    
    # Context truncation for logs
    max_context_preview: int = 200


class RAGPipelineConfig(BaseModel):
    """Master RAG Pipeline Configuration"""
    embedding: EmbeddingConfig = EmbeddingConfig()
    retrieval: RetrievalConfig = RetrievalConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()
    llm: LLMConfig = LLMConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # Parallel execution
    enable_parallel_retrieval: bool = True
    
    # Database
    database_url: Optional[str] = None


# Global configuration instance - DATABASE_URL loaded lazily
config = RAGPipelineConfig()
