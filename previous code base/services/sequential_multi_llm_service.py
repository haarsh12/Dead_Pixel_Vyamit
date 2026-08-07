"""
Sequential Multi-LLM Orchestration System with Memory & Logging
Hackathon Implementation for Vyamit AI

This system implements a sequential model execution pipeline:
1. Qwen (fast primary)
2. Gemini (smart fallback) 
3. Gemma (final fallback)

Features:
- Memory-enabled chatbot with conversation history
- Detailed structured logging to terminal
- Unified master prompt for all models
- Response validation and retry logic
- Performance metrics and  debugging
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import asyncio
import time

# LangChain imports
from langchain_huggingface import HuggingFaceEndpoint
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Environment
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ModelResponse:
    """Structured response from a model"""
    model_name: str
    response: str
    success: bool
    execution_time: float
    error: Optional[str] = None
    confidence_score: Optional[float] = None

@dataclass
class ProcessingLog:
    """Complete processing log entry"""
    timestamp: str
    user_input: str
    preprocessed_input: str
    models_tried: List[str]
    successful_model: str
    final_response: str
    execution_time: float
    memory_context: List[Dict[str, str]]
    validation_passed: bool
    error_details: Optional[str] = None

class SequentialMultiLLMService:
    """
    Sequential Multi-LLM Orchestration System
    
    Implements the hackathon pipeline:
    User Input → Preprocessing → Master Prompt → Sequential Model Execution → 
    Memory Store → Structured Logs
    """
    
    def __init__(self):
        self.setup_logging()
        self.initialize_models()
        self.initialize_memory()
        self.processing_logs: List[ProcessingLog] = []
        self.performance_stats = {
            "total_requests": 0,
            "qwen_success": 0,
            "gemini_success": 0, 
            "gemma_success": 0,
            "total_failures": 0,
            "avg_response_time": 0.0
        }
        
        print("\n[INFO] Sequential Multi-LLM Orchestration System initialized")
        print("=" * 60)
        print("SYSTEM: Sequential Multi-LLM Orchestration with memory and logging")
        print("EXECUTION ORDER: Qwen -> Gemini -> Gemma")
        print("MEMORY: Conversation buffer enabled")
        print("LOGGING: Structured terminal output enabled")
        print("=" * 60)
    
    def setup_logging(self):
        """Setup detailed logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def initialize_models(self):
        """Initialize all three models with proper configuration"""
        print("\n[INFO] Initializing models...")
        
        # Get API keys
        hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if not hf_token:
            raise ValueError("HUGGINGFACE_API_TOKEN not found in environment")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        try:
            # 1. Qwen (Primary - Fast)
            print("   [..] Initializing Qwen/Qwen2.5-7B-Instruct...")
            self.qwen = HuggingFaceEndpoint(
                repo_id="Qwen/Qwen2.5-7B-Instruct",
                max_new_tokens=512,
                temperature=0.3,
                top_p=0.9,
                do_sample=True,
                huggingfacehub_api_token=hf_token,
                model_kwargs={
                    "max_length": 2048
                }
            )
            print("   [OK] Qwen initialized successfully")
            
            # 2. Gemini (Smart Fallback)
            print("   [..] Initializing Gemini-2.5-Flash...")
            self.gemini = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.3,
                google_api_key=gemini_key,
                max_output_tokens=512
            )
            print("   [OK] Gemini initialized successfully")
            
            # 3. Gemma (Final Fallback)
            print("   [..] Initializing Google/Gemma-2B...")
            self.gemma = HuggingFaceEndpoint(
                repo_id="google/gemma-2b",
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                huggingfacehub_api_token=hf_token,
                model_kwargs={
                    "max_length": 1024
                }
            )
            print("   [OK] Gemma initialized successfully")
            
            # Model execution order
            self.models = [
                ("QWEN", self.qwen),
                ("GEMINI", self.gemini),
                ("GEMMA", self.gemma)
            ]
            
            print("   [OK] All models ready for sequential execution")
            
        except Exception as e:
            print(f"   [ERROR] Model initialization failed: {str(e)}")
            raise
    
    def initialize_memory(self):
        """Initialize conversation memory system"""
        print("\n[INFO] Initializing memory system...")
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )
        print("   [OK] Conversation buffer memory initialized")
    
    def get_master_prompt(self, user_input: str, include_history: bool = True) -> str:
        """
        MASTER PROMPT - Used for ALL models
        Unified prompt ensuring consistent behavior across Qwen, Gemini, and Gemma
        """
        
        # Get conversation history if requested
        history_context = ""
        if include_history and self.memory.chat_memory.messages:
            history_context = "\n\nCONVERSATION HISTORY:\n"
            for msg in self.memory.chat_memory.messages[-6:]:  # Last 3 exchanges
                if isinstance(msg, HumanMessage):
                    history_context += f"User: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    history_context += f"Assistant: {msg.content}\n"
        
        master_prompt = f"""You are VYAMIT AI - a multilingual intelligent assistant for grocery and market systems.

LANGUAGE SUPPORT:
- English
- Hindi  
- Hinglish (Hindi-English mix)

CORE CAPABILITIES:
1. BILLING TASKS → Return structured JSON
2. PRICE QUERIES → Return price information
3. GENERAL QUERIES → Provide helpful responses

BILLING TASK RULES:
- Extract: item name, quantity, price per unit
- Convert to standard units (kg, liter, piece)
- Calculate total price accurately
- Output ONLY clean JSON format:
[
  {{
    "item": "item_name",
    "quantity": "number_with_unit",
    "price_per_unit": number_or_null,
    "total_price": number_or_null
  }}
]

PRICE QUERY RULES:
Return structured format:
{{
  "item": "item_name",
  "price": "price_with_currency",
  "unit": "kg/liter/piece",
  "source": "market_info"
}}

GENERAL QUERY RULES:
- Provide short, practical answers
- Focus on grocery/market context
- Be helpful and conversational

STRICT REQUIREMENTS:
- No extra text in JSON responses
- No hallucination of prices
- Clean, structured output only
- Maintain conversation context{history_context}

USER INPUT: {user_input}

RESPONSE:"""
        
        return master_prompt
    
    def preprocess_input(self, user_input: str) -> str:
        """Preprocess user input for better model understanding"""
        # Basic preprocessing
        processed = user_input.strip()
        
        # Log preprocessing
        print(f"\n[INFO] PREPROCESSING:")
        print(f"   Raw Input: '{user_input}'")
        print(f"   Processed: '{processed}'")
        
        return processed
    
    def validate_response(self, response: str, user_input: str) -> Tuple[bool, float]:
        """
        Validate model response quality and assign confidence score
        """
        if not response or len(response.strip()) < 5:
            return False, 0.0
        
        confidence = 0.5  # Base confidence
        
        # Check for JSON structure in billing tasks
        if any(keyword in user_input.lower() for keyword in ['kilo', 'kg', 'rupee', 'price', 'bill']):
            try:
                # Try to parse as JSON
                json.loads(response.strip())
                confidence += 0.3  # JSON structure bonus
            except:
                # Check if it contains structured information
                if '{' in response and '}' in response:
                    confidence += 0.1
        
        # Length and completeness check
        if len(response) > 20:
            confidence += 0.1
        if len(response) > 50:
            confidence += 0.1
        
        # Avoid generic responses
        generic_phrases = ['i cannot', 'i don\'t know', 'sorry', 'unable to']
        if not any(phrase in response.lower() for phrase in generic_phrases):
            confidence += 0.1
        
        is_valid = confidence > 0.6
        return is_valid, min(confidence, 1.0)
    
    def execute_model_sequential(self, prompt: str) -> ModelResponse:
        """
        Execute models in sequential order: Qwen → Gemini → Gemma
        Return first successful response
        """
        print(f"\n[INFO] Sequential model execution started")
        print("=" * 50)
        
        for model_name, model in self.models:
            print(f"\n[TRYING MODEL]: {model_name}")
            print(f"[TIME] Execution started at: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            start_time = time.time()
            
            try:
                # Execute model
                if model_name == "GEMINI":
                    # Gemini uses different invoke method
                    response = model.invoke(prompt)
                    response_text = response.content if hasattr(response, 'content') else str(response)
                else:
                    # Qwen and Gemma
                    response_text = model.invoke(prompt)
                
                execution_time = time.time() - start_time
                
                print(f"[TIME] Execution completed in: {execution_time:.3f}s")
                print(f"[INFO] Raw response length: {len(str(response_text))} characters")
                print(f"[INFO] Response preview: {str(response_text)[:100]}...")
                
                # Validate response
                is_valid, confidence = self.validate_response(str(response_text), prompt)
                
                print(f"[OK] Validation: {'PASSED' if is_valid else 'FAILED'}")
                print(f"[INFO] Confidence score: {confidence:.2f}")
                
                if is_valid:
                    print(f"[OK] Success with {model_name}")
                    return ModelResponse(
                        model_name=model_name,
                        response=str(response_text),
                        success=True,
                        execution_time=execution_time,
                        confidence_score=confidence
                    )
                else:
                    print(f"[WARN] Response quality insufficient, trying next model...")
                    
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)
                print(f"[ERROR] In {model_name}: {error_msg}")
                print(f"[TIME] Failed after: {execution_time:.3f}s")
                
                # Continue to next model
                continue
        
        # All models failed
        print(f"\n[ERROR] All models failed — no valid response generated")
        return ModelResponse(
            model_name="NONE",
            response="I apologize, but I'm unable to process your request at the moment. Please try again.",
            success=False,
            execution_time=0.0,
            error="All models failed to generate valid response"
        )
    
    def save_to_memory(self, user_input: str, response: str):
        """Save conversation to memory"""
        self.memory.save_context(
            {"input": user_input},
            {"output": response}
        )
        print(f"\n[INFO] Memory updated:")
        print(f"   Total conversations: {len(self.memory.chat_memory.messages) // 2}")
    
    def create_structured_log(self, user_input: str, preprocessed_input: str, 
                            model_response: ModelResponse, total_time: float) -> ProcessingLog:
        """Create comprehensive structured log"""
        
        # Get current memory context
        memory_context = []
        for msg in self.memory.chat_memory.messages[-4:]:  # Last 2 exchanges
            if isinstance(msg, HumanMessage):
                memory_context.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                memory_context.append({"role": "assistant", "content": msg.content})
        
        log_entry = ProcessingLog(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            user_input=user_input,
            preprocessed_input=preprocessed_input,
            models_tried=[name for name, _ in self.models],
            successful_model=model_response.model_name,
            final_response=model_response.response,
            execution_time=total_time,
            memory_context=memory_context,
            validation_passed=model_response.success,
            error_details=model_response.error
        )
        
        self.processing_logs.append(log_entry)
        return log_entry
    
    def print_detailed_terminal_log(self, log_entry: ProcessingLog):
        """Print comprehensive debug information to terminal"""
        
        print("\n" + "=" * 80)
        print("DETAILED PROCESSING LOG")
        print("=" * 80)
        
        # Basic Information
        print(f"TIMESTAMP: {log_entry.timestamp}")
        print(f"USER INPUT: '{log_entry.user_input}'")
        print(f"PREPROCESSED: '{log_entry.preprocessed_input}'")
        print(f"TOTAL EXECUTION TIME: {log_entry.execution_time:.3f}s")
        
        # Model Execution Details
        print(f"\nMODEL EXECUTION:")
        print(f"   Models available: {', '.join(log_entry.models_tried)}")
        print(f"   Successful model: {log_entry.successful_model}")
        print(f"   Validation status: {'PASSED' if log_entry.validation_passed else 'FAILED'}")
        
        # Response Details
        print(f"\nRESPONSE DETAILS:")
        print(f"   Length: {len(log_entry.final_response)} characters")
        print(f"   Content: {log_entry.final_response[:200]}{'...' if len(log_entry.final_response) > 200 else ''}")
        
        # Memory Context
        print(f"\nCONVERSATION CONTEXT:")
        if log_entry.memory_context:
            for i, msg in enumerate(log_entry.memory_context[-4:]):  # Show last 2 exchanges
                role_label = "User" if msg["role"] == "user" else "Assistant"
                print(f"   [{role_label}] {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
        else:
            print("   No previous context")
        
        # Error Details (if any)
        if log_entry.error_details:
            print(f"\nERROR DETAILS:")
            print(f"   {log_entry.error_details}")
        
        print("=" * 80)
    
    def update_performance_stats(self, model_name: str, execution_time: float):
        """Update performance statistics"""
        self.performance_stats["total_requests"] += 1
        
        if model_name == "QWEN":
            self.performance_stats["qwen_success"] += 1
        elif model_name == "GEMINI":
            self.performance_stats["gemini_success"] += 1
        elif model_name == "GEMMA":
            self.performance_stats["gemma_success"] += 1
        else:
            self.performance_stats["total_failures"] += 1
        
        # Update average response time
        total_time = self.performance_stats["avg_response_time"] * (self.performance_stats["total_requests"] - 1)
        self.performance_stats["avg_response_time"] = (total_time + execution_time) / self.performance_stats["total_requests"]
    
    async def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        MAIN PROCESSING PIPELINE
        
        Complete flow:
        User Input → Preprocessing → Master Prompt → Sequential Execution → 
        Memory Storage → Structured Logging → Response
        """
        
        print(f"\n[INFO] Processing pipeline started")
        print(f"Raw user input: '{user_input}'")
        
        start_time = time.time()
        
        try:
            # Step 1: Preprocessing
            preprocessed_input = self.preprocess_input(user_input)
            
            # Step 2: Generate Master Prompt
            master_prompt = self.get_master_prompt(preprocessed_input)
            print(f"\n[INFO] Master prompt generated ({len(master_prompt)} chars)")
            
            # Step 3: Sequential Model Execution
            model_response = self.execute_model_sequential(master_prompt)
            
            # Step 4: Save to Memory
            if model_response.success:
                self.save_to_memory(user_input, model_response.response)
            
            # Step 5: Calculate total time
            total_execution_time = time.time() - start_time
            
            # Step 6: Create and Log Structured Entry
            log_entry = self.create_structured_log(
                user_input, preprocessed_input, model_response, total_execution_time
            )
            
            # Step 7: Print Detailed Terminal Log
            self.print_detailed_terminal_log(log_entry)
            
            # Step 8: Update Performance Stats
            self.update_performance_stats(model_response.model_name, total_execution_time)
            
            # Step 9: Return Structured Response
            return {
                "success": model_response.success,
                "response": model_response.response,
                "model_used": model_response.model_name,
                "execution_time": total_execution_time,
                "confidence_score": model_response.confidence_score,
                "timestamp": log_entry.timestamp,
                "conversation_length": len(self.memory.chat_memory.messages) // 2
            }
            
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            print(f"\n[ERROR] Pipeline error: {error_msg}")
            
            return {
                "success": False,
                "response": "I encountered an error processing your request. Please try again.",
                "model_used": "ERROR",
                "execution_time": time.time() - start_time,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get formatted conversation history"""
        history = []
        messages = self.memory.chat_memory.messages
        
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                user_msg = messages[i]
                ai_msg = messages[i + 1]
                
                history.append({
                    "user": user_msg.content if isinstance(user_msg, HumanMessage) else str(user_msg),
                    "assistant": ai_msg.content if isinstance(ai_msg, AIMessage) else str(ai_msg),
                    "timestamp": datetime.now().isoformat()  # Simplified for demo
                })
        
        return history
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        return {
            **self.performance_stats,
            "total_logs": len(self.processing_logs),
            "memory_conversations": len(self.memory.chat_memory.messages) // 2
        }
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        print("\n[INFO] Memory cleared")
    
    def get_recent_logs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent processing logs"""
        recent_logs = self.processing_logs[-limit:] if self.processing_logs else []
        
        return [
            {
                "timestamp": log.timestamp,
                "user_input": log.user_input,
                "successful_model": log.successful_model,
                "execution_time": log.execution_time,
                "validation_passed": log.validation_passed
            }
            for log in recent_logs
        ]

# Global service instance
sequential_service = None

def get_sequential_service() -> SequentialMultiLLMService:
    """Get or create the global sequential service instance"""
    global sequential_service
    if sequential_service is None:
        sequential_service = SequentialMultiLLMService()
    return sequential_service