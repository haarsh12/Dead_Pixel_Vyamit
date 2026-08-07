"""
Debug Logger - Comprehensive logging for all backend processes
Provides colored, timestamped logs for debugging
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import json


class DebugLogger:
    """Enhanced debug logger with colored output and detailed tracking"""
    
    # ANSI color codes
    COLORS = {
        'RESET': '\033[0m',
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'GRAY': '\033[90m',
    }
    
    def __init__(self, component: str):
        """Initialize logger for a specific component"""
        self.component = component
    
    def _timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def _format_log(self, level: str, message: str, color: str = 'WHITE') -> str:
        """Format log message with timestamp and color"""
        timestamp = self._timestamp()
        colored_msg = f"{self.COLORS[color]}[{timestamp}] [{self.component}] [{level}] {message}{self.COLORS['RESET']}"
        return colored_msg
    
    def debug(self, message: str):
        """Debug level log (gray)"""
        print(self._format_log('DEBUG', message, 'GRAY'))
    
    def info(self, message: str):
        """Info level log (cyan)"""
        print(self._format_log('INFO', message, 'CYAN'))
    
    def success(self, message: str):
        """Success level log (green)"""
        print(self._format_log('✓ SUCCESS', message, 'GREEN'))
    
    def warning(self, message: str):
        """Warning level log (yellow)"""
        print(self._format_log('⚠ WARN', message, 'YELLOW'))
    
    def error(self, message: str):
        """Error level log (red)"""
        print(self._format_log('✗ ERROR', message, 'RED'))
    
    def section(self, title: str):
        """Section header (magenta)"""
        separator = "═" * 80
        print(f"\n{self.COLORS['MAGENTA']}{separator}")
        print(f"  {title}")
        print(f"{separator}{self.COLORS['RESET']}\n")
    
    def subsection(self, title: str):
        """Subsection header (blue)"""
        print(f"\n{self.COLORS['BLUE']}┌─ {title} ─┐{self.COLORS['RESET']}")
    
    def query_received(self, user_id: int, query: str):
        """Log incoming user query"""
        self.section(f"NEW QUERY - User {user_id}")
        self.info(f"Query: '{query}'")
        self.info(f"Length: {len(query)} characters")
    
    def embedding_start(self, text: str, provider: str):
        """Log embedding generation start"""
        self.subsection("EMBEDDING GENERATION")
        self.info(f"Provider: {provider}")
        self.info(f"Text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
    
    def embedding_complete(self, dimension: int, duration: float, sample: List[float]):
        """Log embedding generation complete"""
        self.success(f"Dimension: {dimension}D")
        self.success(f"Duration: {duration*1000:.2f}ms")
        self.debug(f"Sample: [{', '.join([f'{x:.4f}' for x in sample[:5]])}...]")
    
    def database_query(self, query_type: str, params: Dict[str, Any]):
        """Log database query"""
        self.subsection(f"DATABASE QUERY - {query_type}")
        for key, value in params.items():
            if isinstance(value, list) and len(value) > 5:
                self.debug(f"{key}: [{value[0]}, ..., {value[-1]}] (len={len(value)})")
            else:
                self.debug(f"{key}: {value}")
    
    def retrieval_results(self, source: str, count: int, duration: float, items: Optional[List] = None):
        """Log retrieval results"""
        self.success(f"{source}: Found {count} items in {duration*1000:.2f}ms")
        if items and count > 0:
            for i, item in enumerate(items[:3], 1):
                if hasattr(item, 'names'):
                    name = item.names[0] if isinstance(item.names, list) else item.names
                    self.debug(f"  {i}. {name} - ₹{getattr(item, 'price', 'N/A')}")
    
    def context_summary(self, context: Dict[str, Any]):
        """Log context summary being sent to LLM"""
        self.subsection("CONTEXT SUMMARY")
        for key, value in context.items():
            if isinstance(value, list):
                self.info(f"{key}: {len(value)} items")
            elif isinstance(value, dict):
                self.info(f"{key}: {len(value)} fields")
            else:
                self.info(f"{key}: {value}")
    
    def prompt_details(self, prompt: str, token_count: Optional[int] = None):
        """Log prompt being sent to LLM"""
        self.subsection("LLM PROMPT")
        self.info(f"Length: {len(prompt)} chars")
        if token_count:
            self.info(f"Tokens: ~{token_count}")
        self.debug("Preview (first 300 chars):")
        preview = prompt[:300].replace('\n', '\\n')
        print(f"{self.COLORS['GRAY']}{preview}...{self.COLORS['RESET']}")
    
    def llm_request(self, model: str, is_primary: bool):
        """Log LLM request"""
        model_type = "PRIMARY" if is_primary else "FALLBACK"
        self.subsection(f"LLM REQUEST - {model_type}")
        self.info(f"Model: {model}")
    
    def llm_response(self, response: str, duration: float, model: str):
        """Log LLM response"""
        self.success(f"Response received in {duration:.2f}s from {model}")
        self.info(f"Length: {len(response)} chars")
        try:
            parsed = json.loads(response) if isinstance(response, str) else response
            self.info(f"Type: {parsed.get('type', 'UNKNOWN')}")
            self.info(f"Items: {len(parsed.get('items', []))}")
            self.debug(f"Message: {parsed.get('msg', 'N/A')}")
        except:
            self.debug("Preview: " + response[:200])
    
    def metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics"""
        self.subsection("PERFORMANCE METRICS")
        for key, value in metrics.items():
            if isinstance(value, float):
                self.info(f"{key}: {value*1000:.2f}ms")
            else:
                self.info(f"{key}: {value}")
    
    def separator(self):
        """Print separator line"""
        print(f"{self.COLORS['GRAY']}{'─' * 80}{self.COLORS['RESET']}")


# Create logger instances for different components
voice_logger = DebugLogger("VOICE-API")
rag_logger = DebugLogger("RAG-PIPELINE")
embedding_logger = DebugLogger("EMBEDDING")
retrieval_logger = DebugLogger("RETRIEVAL")
llm_logger = DebugLogger("LLM")
db_logger = DebugLogger("DATABASE")
