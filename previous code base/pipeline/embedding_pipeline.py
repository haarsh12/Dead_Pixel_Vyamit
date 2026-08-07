"""
RAG Pipeline - Embedding Generation
DEPRECATED: Use embedding_provider.py instead
This file is kept for backward compatibility and imports from the new provider
"""

# Import from new unified provider
from .embedding_provider import embedding_pipeline

# Re-export for backward compatibility
__all__ = ['embedding_pipeline']

