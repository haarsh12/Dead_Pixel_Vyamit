"""
RAG Pipeline Logger
Real-time terminal logging for debugging and monitoring
"""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from .config import config


class RAGLogger:
    """Production-grade logger for RAG pipeline with colored output"""
    
    # ANSI color codes
    COLORS = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'GRAY': '\033[90m',
    }
    
    @staticmethod
    def _colorize(text: str, color: str) -> str:
        """Add color to text"""
        if not config.logging.enabled:
            return text
        return f"{RAGLogger.COLORS.get(color, '')}{text}{RAGLogger.COLORS['RESET']}"
    
    @staticmethod
    def _timestamp() -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    @staticmethod
    def _header(title: str, char: str = "=", width: int = 80):
        """Print section header"""
        if not config.logging.enabled:
            return
        print(f"\n{RAGLogger._colorize(char * width, 'CYAN')}")
        print(RAGLogger._colorize(f"  {title}", 'BOLD'))
        print(RAGLogger._colorize(char * width, 'CYAN'))
    
    @staticmethod
    def _subheader(title: str):
        """Print subsection header"""
        if not config.logging.enabled:
            return
        print(RAGLogger._colorize(f"\n▶ {title}", 'YELLOW'))
        print(RAGLogger._colorize("─" * 60, 'GRAY'))
    
    @staticmethod
    def log_request(user_id: int, query: str, request_id: str):
        """Log incoming user request"""
        if not config.logging.enabled:
            return
        
        RAGLogger._header(f"🎤 NEW REQUEST #{request_id}", "═")
        print(f"{RAGLogger._colorize('Timestamp:', 'GRAY')} {RAGLogger._timestamp()}")
        print(f"{RAGLogger._colorize('User ID:', 'GRAY')}   {user_id}")
        print(f"{RAGLogger._colorize('Query:', 'BOLD')}     \"{query}\"")
    
    @staticmethod
    def log_embedding(query: str, embedding_time: float, dimension: int):
        """Log embedding generation"""
        if not config.logging.enabled or not config.logging.log_embeddings:
            return
        
        RAGLogger._subheader("🧠 QUERY EMBEDDING")
        print(f"   Query: \"{query[:100]}{'...' if len(query) > 100 else ''}\"")
        print(f"   Model: {config.embedding.model_name}")
        print(f"   Dimension: {dimension}D")
        print(f"   {RAGLogger._colorize(f'⏱ Time: {embedding_time:.3f}s', 'GREEN')}")
    
    @staticmethod
    def log_retrieval_start(retrieval_type: str):
        """Log retrieval start"""
        if not config.logging.enabled or not config.logging.log_retrieval:
            return
        print(f"\n{RAGLogger._colorize(f'🔍 {retrieval_type.upper()} RETRIEVAL', 'BLUE')}")
    
    @staticmethod
    def log_item_retrieval(items: List[Dict], retrieval_time: float):
        """Log item retrieval results"""
        if not config.logging.enabled or not config.logging.log_retrieval:
            return
        
        RAGLogger._subheader("📦 ITEM CONTEXT (Vector Search)")
        print(f"   Retrieved: {len(items)} items")
        print(f"   {RAGLogger._colorize(f'⏱ Time: {retrieval_time:.3f}s', 'GREEN')}")
        
        if items:
            print(f"\n   {RAGLogger._colorize('Top Matches:', 'BOLD')}")
            for i, item in enumerate(items[:5], 1):
                name = item.get('primary_name', 'Unknown')
                score = item.get('similarity', 0.0)
                price = item.get('price', 0.0)
                unit = item.get('unit', '')
                category = item.get('category', '')
                
                score_color = 'GREEN' if score > 0.7 else 'YELLOW' if score > 0.5 else 'RED'
                score_str = RAGLogger._colorize(f"{score:.3f}", score_color)
                
                print(f"   {i}. [{score_str}] {name} - ₹{price}/{unit} ({category})")
        else:
            print(RAGLogger._colorize("   ⚠ No matching items found", 'YELLOW'))
    
    @staticmethod
    def log_analytics(metrics: Dict, retrieval_time: float):
        """Log analytics metrics"""
        if not config.logging.enabled or not config.logging.log_retrieval:
            return
        
        RAGLogger._subheader("📊 ANALYTICS CONTEXT (Business Metrics)")
        print(f"   {RAGLogger._colorize(f'⏱ Time: {retrieval_time:.3f}s', 'GREEN')}")
        
        print(f"\n   {RAGLogger._colorize('Key Metrics:', 'BOLD')}")
        
        summary = metrics.get('summary', {})
        print(f"   • Revenue: ₹{summary.get('total_revenue', 0):.2f}")
        print(f"   • Bills: {summary.get('total_bills', 0)}")
        print(f"   • Avg Bill: ₹{summary.get('average_bill_value', 0):.2f}")
        print(f"   • Inventory Items: {summary.get('total_inventory_items', 0)}")
        
        top_items = metrics.get('top_selling_items', [])
        if top_items:
            print(f"\n   {RAGLogger._colorize('Top Selling:', 'BOLD')}")
            for i, item in enumerate(top_items[:3], 1):
                print(f"   {i}. {item.get('name')} - {item.get('quantity')}{item.get('unit')} sold")
    
    @staticmethod
    def log_customer_retrieval(customers: List[Dict], retrieval_time: float):
        """Log customer retrieval results"""
        if not config.logging.enabled or not config.logging.log_retrieval:
            return
        
        RAGLogger._subheader("👥 CUSTOMER CONTEXT (Vector Search + History)")
        print(f"   Retrieved: {len(customers)} customers")
        print(f"   {RAGLogger._colorize(f'⏱ Time: {retrieval_time:.3f}s', 'GREEN')}")
        
        if customers:
            print(f"\n   {RAGLogger._colorize('Matched Customers:', 'BOLD')}")
            for i, customer in enumerate(customers[:5], 1):
                name = customer.get('customer_name', 'Unknown')
                score = customer.get('similarity', 0.0)
                bills = customer.get('bills', [])
                total_spent = customer.get('total_spent', 0.0)
                
                score_color = 'GREEN' if score > 0.7 else 'YELLOW' if score > 0.5 else 'RED'
                score_str = RAGLogger._colorize(f"{score:.3f}", score_color)
                
                print(f"   {i}. [{score_str}] {name} - {len(bills)} bills, ₹{total_spent:.2f} spent")
                
                if bills:
                    recent = bills[0]
                    print(f"      Last: {recent.get('bill_date', 'N/A')[:10]} - ₹{recent.get('total_amount', 0):.2f}")
        else:
            print(RAGLogger._colorize("   ℹ No customer history available", 'GRAY'))
    
    @staticmethod
    def log_context_summary(item_count: int, has_analytics: bool, customer_count: int):
        """Log context assembly summary"""
        if not config.logging.enabled or not config.logging.log_context:
            return
        
        RAGLogger._subheader("📝 CONTEXT ASSEMBLY")
        print(f"   Items: {item_count} products")
        print(f"   Analytics: {'✓ Included' if has_analytics else '✗ Skipped'}")
        print(f"   Customers: {customer_count} profiles")
    
    @staticmethod
    def log_prompt(prompt: str, prompt_length: int):
        """Log final prompt sent to LLM"""
        if not config.logging.enabled or not config.logging.log_context:
            return
        
        RAGLogger._subheader("💬 PROMPT TO LLM")
        print(f"   Total Length: {prompt_length} characters")
        
        if config.logging.max_context_preview > 0:
            preview = prompt[:config.logging.max_context_preview]
            print(f"\n   {RAGLogger._colorize('Preview:', 'GRAY')}")
            print(RAGLogger._colorize(f"   {preview}...", 'GRAY'))
    
    @staticmethod
    def log_llm_request(model: str, is_primary: bool):
        """Log LLM request"""
        if not config.logging.enabled or not config.logging.log_llm:
            return
        
        model_type = "PRIMARY" if is_primary else "FALLBACK"
        RAGLogger._subheader(f"🤖 LLM REQUEST ({model_type})")
        print(f"   Model: {model}")
        print(f"   Temperature: {config.llm.primary_temperature if is_primary else config.llm.fallback_temperature}")
        print(f"   Max Tokens: {config.llm.primary_max_tokens if is_primary else config.llm.fallback_max_tokens}")
    
    @staticmethod
    def log_llm_response(response: str, tokens: Optional[int], response_time: float):
        """Log LLM response"""
        if not config.logging.enabled or not config.logging.log_llm:
            return
        
        print(f"   {RAGLogger._colorize(f'✓ Response received', 'GREEN')}")
        print(f"   {RAGLogger._colorize(f'⏱ Time: {response_time:.3f}s', 'GREEN')}")
        if tokens:
            print(f"   Tokens: {tokens}")
        
        if config.logging.max_context_preview > 0:
            preview = response[:config.logging.max_context_preview]
            print(f"\n   {RAGLogger._colorize('Response Preview:', 'GRAY')}")
            print(RAGLogger._colorize(f"   {preview}...", 'GRAY'))
    
    @staticmethod
    def log_llm_error(model: str, error: str):
        """Log LLM error"""
        if not config.logging.enabled:
            return
        print(RAGLogger._colorize(f"   ✗ Error with {model}: {error}", 'RED'))
    
    @staticmethod
    def log_pipeline_complete(total_time: float, success: bool):
        """Log pipeline completion"""
        if not config.logging.enabled:
            return
        
        status = RAGLogger._colorize("✓ SUCCESS", 'GREEN') if success else RAGLogger._colorize("✗ FAILED", 'RED')
        RAGLogger._header(f"🏁 PIPELINE COMPLETE - {status}", "═")
        print(f"{RAGLogger._colorize('Total Time:', 'BOLD')} {total_time:.3f}s")
        
        if config.logging.log_latency:
            RAGLogger._breakdown_latency()
        print()
    
    @staticmethod
    def _breakdown_latency():
        """Show latency breakdown (placeholder for future enhancement)"""
        print(RAGLogger._colorize("\n   Latency Breakdown:", 'GRAY'))
        print(RAGLogger._colorize("   (tracked per request in production)", 'GRAY'))
    
    @staticmethod
    def log_error(stage: str, error: Exception):
        """Log error"""
        if not config.logging.enabled:
            return
        print(RAGLogger._colorize(f"\n❌ ERROR in {stage}:", 'RED'))
        print(RAGLogger._colorize(f"   {type(error).__name__}: {str(error)}", 'RED'))


# Singleton instance
logger = RAGLogger()
