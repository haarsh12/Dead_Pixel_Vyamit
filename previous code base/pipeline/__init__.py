"""
RAG Pipeline Package
Production-grade Retrieval-Augmented Generation pipeline
"""

from .orchestrator import orchestrator
from .embedding_pipeline import embedding_pipeline
from .config import config
from .logger import logger

__all__ = [
    'orchestrator',
    'embedding_pipeline',
    'config',
    'logger'
]

__version__ = '1.0.0'
__status__ = 'Production Ready'
