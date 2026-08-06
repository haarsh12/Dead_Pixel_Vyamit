"""
LLM Pipeline - Multi-Model LLM with Fallback
Mistral (primary) → Gemini (fallback)
"""
import os
import time
import json
import logging
from typing import Tuple, Dict, Any
from .config import config

logger = logging.getLogger(__name__)


class LLMPipeline:
    """LLM service with automatic fallback"""
    
    def __init__(self):
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        self._mistral_client = None
        self._gemini_client = None
    
    def _init_mistral(self):
        """Initialize Mistral client"""
        if self._mistral_client or not self.mistral_api_key:
            return False
        
        try:
            from mistralai import Mistral
            self._mistral_client = Mistral(api_key=self.mistral_api_key)
            logger.info("[OK] Mistral client initialized")
            return True
        except Exception as e:
            logger.error(f"Mistral initialization failed: {e}")
            return False
    
    def _init_gemini(self):
        """Initialize Gemini client"""
        if self._gemini_client or not self.gemini_api_key:
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_client = genai
            logger.info("[OK] Gemini client initialized")
            return True
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")
            return False
    
    def invoke_mistral(self, prompt: str) -> Tuple[Dict[str, Any], float]:
        """
        Invoke Mistral LLM
        
        Returns:
            (response_dict, time_taken)
        """
        start = time.time()
        
        try:
            if not self._init_mistral():
                raise ValueError("Mistral client not available")
            
            response = self._mistral_client.chat.complete(
                model=config.llm.primary_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.llm.primary_temperature,
                max_tokens=config.llm.primary_max_tokens
            )
            
            content = response.choices[0].message.content
            duration = time.time() - start
            
            # Parse JSON response
            parsed = json.loads(content)
            logger.info(f"Mistral response in {duration*1000:.2f}ms")
            return parsed, duration
            
        except Exception as e:
            logger.error(f"Mistral invocation failed: {e}")
            raise
    
    def invoke_gemini(self, prompt: str) -> Tuple[Dict[str, Any], float]:
        """
        Invoke Gemini LLM
        
        Returns:
            (response_dict, time_taken)
        """
        start = time.time()
        
        try:
            if not self._init_gemini():
                raise ValueError("Gemini client not available")
            
            # Try fallback models in order
            for model_name in config.llm.fallback_models:
                try:
                    model = self._gemini_client.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": config.llm.fallback_temperature,
                            "max_output_tokens": config.llm.fallback_max_tokens
                        }
                    )
                    
                    content = response.text
                    duration = time.time() - start
                    
                    # Parse JSON response
                    parsed = json.loads(content)
                    logger.info(f"Gemini ({model_name}) response in {duration*1000:.2f}ms")
                    return parsed, duration
                    
                except Exception as model_error:
                    logger.warning(f"Gemini model {model_name} failed: {model_error}")
                    continue
            
            raise ValueError("All Gemini models failed")
            
        except Exception as e:
            logger.error(f"Gemini invocation failed: {e}")
            raise
    
    def invoke(self, prompt: str) -> Tuple[Dict[str, Any], float, str]:
        """
        Invoke LLM with automatic fallback
        
        Returns:
            (response_dict, time_taken, model_used)
        """
        # Try Mistral first
        if self.mistral_api_key:
            try:
                response, duration = self.invoke_mistral(prompt)
                return response, duration, config.llm.primary_model
            except Exception as e:
                logger.warning(f"Mistral failed, trying Gemini fallback: {e}")
        
        # Fallback to Gemini
        if self.gemini_api_key:
            try:
                response, duration = self.invoke_gemini(prompt)
                return response, duration, "gemini-fallback"
            except Exception as e:
                logger.error(f"All LLM models failed: {e}")
        
        # All models failed
        return {
            "type": "ERROR",
            "items": [],
            "msg": "AI service temporarily unavailable. Please try again.",
            "should_stop": False
        }, 0.0, "error"
    
    @staticmethod
    def validate_response(response: Dict[str, Any]) -> bool:
        """
        Validate LLM response structure
        
        Args:
            response: LLM response dict
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["type", "items", "msg", "should_stop"]
        
        if not all(field in response for field in required_fields):
            logger.warning("Invalid response structure - missing fields")
            return False
        
        if response["type"] not in ["BILL", "QUERY", "ERROR"]:
            logger.warning(f"Invalid response type: {response['type']}")
            return False
        
        if not isinstance(response["items"], list):
            logger.warning("Items field is not a list")
            return False
        
        return True


# Global instance
llm_pipeline = LLMPipeline()
