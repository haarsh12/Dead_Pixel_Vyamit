"""
LLM Pipeline - LLM Invocation with Fallback Strategy
Handles primary (Mistral) and fallback (Gemini) LLM calls
"""

import time
import json
from typing import Dict, Any, Optional, Tuple
import os

from .config import config
from .logger import logger


class LLMPipeline:
    """
    Handles LLM invocation with fallback strategy:
    1. Primary: Mistral AI (mistral-large-latest)
    2. Fallback: Gemini (gemini-2.5-flash, gemini-2.0-flash, etc.)
    """
    
    def __init__(self):
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        self.mistral_client = None
        self.gemini_models = []
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize LLM clients"""
        
        # Initialize Mistral
        if self.mistral_api_key:
            try:
                from mistralai import Mistral
                self.mistral_client = Mistral(api_key=self.mistral_api_key)
                print("[OK] Mistral client initialized")
            except ImportError:
                print("[WARN] Mistral library not installed")
            except Exception as e:
                print(f"[WARN] Mistral initialization failed: {e}")
        
        # Initialize Gemini
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key, transport="rest")
                
                for model_name in config.llm.fallback_models:
                    try:
                        model = genai.GenerativeModel(model_name)
                        self.gemini_models.append((model_name, model))
                    except:
                        continue
                
                if self.gemini_models:
                    print(f"[OK] Gemini initialized with {len(self.gemini_models)} models")
            except Exception as e:
                print(f"[WARN] Gemini initialization failed: {e}")
    
    def call_mistral(self, prompt: str) -> Tuple[Optional[Dict[str, Any]], float, Optional[str]]:
        """
        Call Mistral AI (Primary LLM)
        
        Returns:
            (response_dict, execution_time, error_message)
        """
        if not self.mistral_client:
            return None, 0.0, "Mistral client not available"
        
        start_time = time.time()
        
        try:
            logger.log_llm_request(config.llm.primary_model, is_primary=True)
            
            response = self.mistral_client.chat.complete(
                model=config.llm.primary_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.llm.primary_temperature,
                max_tokens=config.llm.primary_max_tokens,
                response_format={"type": "json_object"}
            )
            
            execution_time = time.time() - start_time
            content = response.choices[0].message.content
            
            # Parse JSON
            clean_text = content.replace("```json", "").replace("```", "").strip()
            response_dict = json.loads(clean_text)
            
            logger.log_llm_response(clean_text, None, execution_time)
            
            return response_dict, execution_time, None
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            logger.log_llm_error(config.llm.primary_model, error_msg)
            return None, execution_time, error_msg
    
    def call_gemini(self, prompt: str) -> Tuple[Optional[Dict[str, Any]], float, Optional[str]]:
        """
        Call Gemini AI (Fallback LLM)
        Tries multiple Gemini models in sequence
        
        Returns:
            (response_dict, execution_time, error_message)
        """
        if not self.gemini_models:
            return None, 0.0, "Gemini models not available"
        
        last_error = ""
        
        for model_name, model in self.gemini_models:
            start_time = time.time()
            
            try:
                logger.log_llm_request(model_name, is_primary=False)
                
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': config.llm.fallback_temperature,
                        'max_output_tokens': config.llm.fallback_max_tokens,
                    }
                )
                
                execution_time = time.time() - start_time
                content = response.text
                
                # Parse JSON
                clean_text = content.replace("```json", "").replace("```", "").strip()
                response_dict = json.loads(clean_text)
                
                logger.log_llm_response(clean_text, None, execution_time)
                
                return response_dict, execution_time, None
                
            except Exception as e:
                execution_time = time.time() - start_time
                last_error = str(e)
                logger.log_llm_error(model_name, last_error)
                continue  # Try next model
        
        return None, 0.0, f"All Gemini models failed. Last error: {last_error}"
    
    def invoke(self, prompt: str) -> Tuple[Dict[str, Any], float, str]:
        """
        Invoke LLM with fallback strategy:
        1. Try Mistral (primary)
        2. Try Gemini (fallback)
        3. Return error response if all fail
        
        Returns:
            (response_dict, execution_time, model_used)
        """
        total_start = time.time()
        
        # Try Primary: Mistral
        response, exec_time, error = self.call_mistral(prompt)
        if response:
            return response, exec_time, "Mistral"
        
        # Try Fallback: Gemini
        response, exec_time, error = self.call_gemini(prompt)
        if response:
            return response, exec_time, "Gemini"
        
        # All failed - return error response
        total_time = time.time() - total_start
        
        error_response = {
            "type": "ERROR",
            "items": [],
            "msg": "System error. Please try again.",
            "should_stop": False,
            "error": "All LLM models failed"
        }
        
        return error_response, total_time, "None"
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate LLM response structure
        """
        if not isinstance(response, dict):
            return False
        
        # Must have type field
        if 'type' not in response:
            return False
        
        # Must have msg field
        if 'msg' not in response:
            return False
        
        # If type is BILL, must have items
        if response['type'] == 'BILL' and 'items' not in response:
            return False
        
        return True

