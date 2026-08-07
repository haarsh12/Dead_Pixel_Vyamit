"""
RAG Pipeline Orchestrator
Main entry point for the RAG pipeline
Coordinates: Embedding → Parallel Retrieval → Prompt Building → LLM → Response
"""

import time
import uuid
from typing import Dict, Any, Optional
from sqlalchemy import create_engine
import os

from .embedding_pipeline import embedding_pipeline
from .retrieval_pipeline import RetrievalPipeline
from .prompt_pipeline import PromptPipeline
from .llm_pipeline import LLMPipeline
from .config import config
from .logger import logger


class RAGOrchestrator:
    """
    Main RAG Pipeline Orchestrator
    
    Flow:
    1. Receive user query
    2. Generate query embedding (E5)
    3. Parallel retrieval (Items, Analytics, Customers)
    4. Build structured prompt
    5. Invoke LLM (Mistral → Gemini)
    6. Return response
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGOrchestrator, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize without connecting - lazy initialization"""
        pass
    
    def _ensure_initialized(self):
        """Lazy initialization - only connect when first used"""
        if self._initialized:
            return
        
        self._initialize()
    
    def _initialize(self):
        """Initialize orchestrator and all pipelines"""
        if self._initialized:
            return
            
        print("\n" + "="*80)
        print("RAG PIPELINE ORCHESTRATOR - INITIALIZATION")
        print("="*80)
        
        try:
            # Database connection
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not found in environment")
            
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            self.engine = create_engine(
                database_url, 
                pool_pre_ping=True, 
                pool_recycle=300,
                echo=False
            )
            print("[OK] Database connection established")
            
            # Initialize pipelines
            self.embedding_pipeline = embedding_pipeline
            print("[OK] Embedding pipeline ready")
            
            self.retrieval_pipeline = RetrievalPipeline(self.engine, self.embedding_pipeline)
            print("[OK] Retrieval pipeline ready")
            
            self.prompt_pipeline = PromptPipeline()
            print("[OK] Prompt pipeline ready")
            
            self.llm_pipeline = LLMPipeline()
            print("[OK] LLM pipeline ready")
            
            self._initialized = True
            RAGOrchestrator._initialized = True
            
            print("="*80)
            print("RAG PIPELINE READY FOR REQUESTS")
            print("="*80 + "\n")
            
        except Exception as e:
            print(f"[ERROR] Orchestrator initialization failed: {e}")
            raise
    
    async def process_query(
        self,
        user_query: str,
        user_id: int,
        shop_category: str = "General",
        include_analytics: bool = True,
        include_customers: bool = True,
        use_simple_prompt: bool = False
    ) -> Dict[str, Any]:
        """
        Main processing pipeline
        
        Args:
            user_query: User's natural language query
            user_id: User ID for context filtering
            shop_category: Shop category for context
            include_analytics: Include business metrics
            include_customers: Include customer history
            use_simple_prompt: Use simplified prompt (faster)
            
        Returns:
            {
                'success': bool,
                'response': dict,  # LLM response
                'metadata': {
                    'request_id': str,
                    'timings': {...},
                    'context_counts': {...},
                    'model_used': str
                }
            }
        """
        
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        pipeline_start = time.time()
        
        # Ensure initialized
        self._ensure_initialized()
        
        # Log request
        logger.log_request(user_id, user_query, request_id)
        
        try:
            # ===== STEP 1: GENERATE QUERY EMBEDDING =====
            query_embedding, embedding_time = self.embedding_pipeline.generate_query_embedding(user_query)
            
            # ===== STEP 2: PARALLEL RETRIEVAL =====
            retrieval_start = time.time()
            
            retrieval_results = await self.retrieval_pipeline.retrieve_all_parallel(
                query_embedding=query_embedding,
                user_id=user_id,
                include_analytics=include_analytics,
                include_customers=include_customers
            )
            
            items = retrieval_results['items']
            analytics = retrieval_results['analytics']
            customers = retrieval_results['customers']
            retrieval_timings = retrieval_results['timings']
            
            retrieval_total_time = time.time() - retrieval_start
            
            # Log retrieval results
            logger.log_item_retrieval(items, retrieval_timings['items'])
            if include_analytics:
                logger.log_analytics(analytics, retrieval_timings['analytics'])
            if include_customers:
                logger.log_customer_retrieval(customers, retrieval_timings['customers'])
            
            logger.log_context_summary(
                len(items),
                bool(analytics),
                len(customers)
            )
            
            # ===== STEP 3: BUILD PROMPT =====
            prompt_start = time.time()
            
            if use_simple_prompt:
                prompt = self.prompt_pipeline.build_simple_billing_prompt(
                    user_query=user_query,
                    items=items,
                    shop_category=shop_category
                )
            else:
                prompt = self.prompt_pipeline.build_rag_prompt(
                    user_query=user_query,
                    items=items,
                    analytics=analytics,
                    customers=customers,
                    shop_category=shop_category
                )
            
            prompt_time = time.time() - prompt_start
            
            logger.log_prompt(prompt, len(prompt))
            
            # ===== STEP 4: INVOKE LLM =====
            llm_start = time.time()
            
            llm_response, llm_time, model_used = self.llm_pipeline.invoke(prompt)
            
            # ===== STEP 5: VALIDATE RESPONSE =====
            is_valid = self.llm_pipeline.validate_response(llm_response)
            
            if not is_valid:
                print("[WARN] LLM response validation failed, using error response")
                llm_response = {
                    "type": "ERROR",
                    "items": [],
                    "msg": "Unable to process request. Please try again.",
                    "should_stop": False
                }
            
            # ===== PIPELINE COMPLETE =====
            total_time = time.time() - pipeline_start
            
            logger.log_pipeline_complete(total_time, is_valid)
            
            # Assemble metadata
            metadata = {
                'request_id': request_id,
                'model_used': model_used,
                'timings': {
                    'embedding': embedding_time,
                    'retrieval_items': retrieval_timings['items'],
                    'retrieval_analytics': retrieval_timings.get('analytics', 0.0),
                    'retrieval_customers': retrieval_timings.get('customers', 0.0),
                    'retrieval_parallel': retrieval_timings['total_parallel'],
                    'prompt_building': prompt_time,
                    'llm_execution': llm_time,
                    'total_pipeline': total_time
                },
                'context_counts': {
                    'items_retrieved': len(items),
                    'customers_retrieved': len(customers),
                    'analytics_included': bool(analytics)
                },
                'prompt_length': len(prompt)
            }
            
            return {
                'success': True,
                'response': llm_response,
                'metadata': metadata
            }
            
        except Exception as e:
            total_time = time.time() - pipeline_start
            logger.log_error("Pipeline Execution", e)
            logger.log_pipeline_complete(total_time, False)
            
            return {
                'success': False,
                'response': {
                    "type": "ERROR",
                    "items": [],
                    "msg": "System error occurred. Please try again.",
                    "should_stop": False
                },
                'metadata': {
                    'request_id': request_id,
                    'error': str(e),
                    'timings': {
                        'total_pipeline': total_time
                    }
                }
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        if not self._initialized:
            return {
                'initialized': False,
                'message': 'Orchestrator not yet initialized (lazy loading)'
            }
        
        return {
            'initialized': self._initialized,
            'embedding_model': self.embedding_pipeline.get_model_info(),
            'config': {
                'parallel_retrieval': config.enable_parallel_retrieval,
                'item_top_k': config.retrieval.item_top_k,
                'customer_top_k': config.retrieval.customer_top_k,
                'analytics_period': config.retrieval.default_period_days,
                'primary_llm': config.llm.primary_model,
                'fallback_llms': config.llm.fallback_models
            }
        }


# Global singleton instance
orchestrator = RAGOrchestrator()
