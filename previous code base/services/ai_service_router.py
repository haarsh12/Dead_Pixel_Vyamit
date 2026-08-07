import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, List, Tuple
from collections import deque
from app.db.models import Item

class QueryAnalyzer:
    """Intelligent query analyzer for model routing decisions"""
    
    def __init__(self):
        self.complexity_keywords = {
            'high': ['analyze', 'trend', 'compare', 'explain', 'why', 'how', 'market', 'forecast', 'strategy'],
            'medium': ['calculate', 'convert', 'suggest', 'recommend', 'find', 'search'],
            'low': ['price', 'cost', 'kya hai', 'kitna', 'add', 'bill', 'total']
        }
        
        self.language_patterns = {
            'hinglish': ['kilo', 'rupaye', 'wala', 'wali', 'hai', 'ka', 'ki', 'ke', 'aur', 'main'],
            'hindi': ['किलो', 'रुपये', 'है', 'का', 'की', 'के', 'और', 'में'],
            'english': ['kg', 'rupees', 'price', 'cost', 'total', 'bill']
        }
    
    def analyze_query(self, text: str) -> Dict[str, Any]:
        """Analyze query and return routing features"""
        words = text.lower().split()
        word_count = len(words)
        
        # Detect language
        language = self._detect_language(text.lower())
        
        # Detect complexity
        complexity = self._detect_complexity(text.lower(), word_count)
        
        # Detect task type
        task_type = self._detect_task_type(text.lower())
        
        return {
            'word_count': word_count,
            'language': language,
            'complexity': complexity,
            'task_type': task_type,
            'has_numbers': any(char.isdigit() for char in text),
            'has_price_keywords': any(keyword in text.lower() for keyword in ['price', 'cost', 'rupaye', 'rs']),
            'is_billing': any(keyword in text.lower() for keyword in ['kilo', 'kg', 'litre', 'piece', 'packet'])
        }
    
    def _detect_language(self, text: str) -> str:
        """Detect primary language of the text"""
        hinglish_score = sum(1 for word in self.language_patterns['hinglish'] if word in text)
        hindi_score = sum(1 for word in self.language_patterns['hindi'] if word in text)
        english_score = sum(1 for word in self.language_patterns['english'] if word in text)
        
        if hinglish_score > 0:
            return 'hinglish'
        elif hindi_score > english_score:
            return 'hindi'
        else:
            return 'english'
    
    def _detect_complexity(self, text: str, word_count: int) -> str:
        """Detect query complexity level"""
        high_score = sum(1 for word in self.complexity_keywords['high'] if word in text)
        medium_score = sum(1 for word in self.complexity_keywords['medium'] if word in text)
        low_score = sum(1 for word in self.complexity_keywords['low'] if word in text)
        
        if high_score > 0 or word_count > 25:
            return 'high'
        elif medium_score > 0 or word_count > 15:
            return 'medium'
        else:
            return 'low'
    
    def _detect_task_type(self, text: str) -> str:
        """Detect the type of task"""
        if any(word in text for word in ['kilo', 'kg', 'litre', 'piece', 'packet', 'bill']):
            return 'billing'
        elif any(word in text for word in ['price', 'cost', 'kitna', 'kya hai']):
            return 'price_query'
        elif any(word in text for word in ['analyze', 'trend', 'market', 'explain']):
            return 'analysis'
        else:
            return 'general'

class ModelRouter:
    """Intelligent model routing system"""
    
    def __init__(self):
        self.analyzer = QueryAnalyzer()
        self.routing_rules = {
            # Qwen: Fast, multilingual, simple tasks
            'qwen': {
                'complexity': ['low'],
                'task_type': ['billing', 'price_query'],
                'language': ['hinglish', 'hindi'],
                'priority': 1
            },
            # Gemma: Balanced, medium complexity
            'gemma': {
                'complexity': ['medium'],
                'task_type': ['general', 'price_query'],
                'language': ['english', 'hinglish'],
                'priority': 2
            },
            # Gemini: Smart, complex reasoning
            'gemini': {
                'complexity': ['high'],
                'task_type': ['analysis', 'general'],
                'language': ['english', 'hinglish', 'hindi'],
                'priority': 3
            }
        }
    
    def route_query(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """Route query to appropriate model"""
        features = self.analyzer.analyze_query(text)
        
        # Score each model
        model_scores = {}
        for model_name, rules in self.routing_rules.items():
            score = self._calculate_model_score(features, rules)
            model_scores[model_name] = score
        
        # Select best model
        selected_model = max(model_scores, key=model_scores.get)
        
        # Add routing decision to features
        features['model_scores'] = model_scores
        features['selected_model'] = selected_model
        features['routing_reason'] = self._get_routing_reason(features, selected_model)
        
        return selected_model, features
    
    def _calculate_model_score(self, features: Dict[str, Any], rules: Dict[str, Any]) -> float:
        """Calculate compatibility score for a model"""
        score = 0.0
        
        # Complexity match
        if features['complexity'] in rules['complexity']:
            score += 3.0
        
        # Task type match
        if features['task_type'] in rules['task_type']:
            score += 2.0
        
        # Language match
        if features['language'] in rules['language']:
            score += 1.0
        
        # Special bonuses
        if features['is_billing'] and 'qwen' in rules:
            score += 1.0  # Qwen bonus for billing
        
        if features['complexity'] == 'high' and 'gemini' in rules:
            score += 2.0  # Gemini bonus for complex queries
        
        return score
    
    def _get_routing_reason(self, features: Dict[str, Any], selected_model: str) -> str:
        """Generate human-readable routing reason"""
        reasons = []
        
        if features['complexity'] == 'low':
            reasons.append("Low complexity")
        elif features['complexity'] == 'high':
            reasons.append("High complexity")
        
        if features['is_billing']:
            reasons.append("Billing task")
        
        if features['language'] == 'hinglish':
            reasons.append("Hinglish input")
        
        return f"{selected_model.upper()} selected: {', '.join(reasons)}"

class StructuredLogger:
    """Advanced logging system for hackathon demo"""
    
    def __init__(self):
        self.logs = deque(maxlen=1000)  # Keep last 1000 logs
    
    def log_request(self, user_input: str, features: Dict[str, Any], 
                   model_name: str, response: Any, latency_ms: float, 
                   success: bool = True, error: str = None) -> Dict[str, Any]:
        """Log complete request-response cycle"""
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': f"req_{int(time.time() * 1000)}",
            'user_input': user_input,
            'analysis': {
                'word_count': features.get('word_count', 0),
                'language': features.get('language', 'unknown'),
                'complexity': features.get('complexity', 'unknown'),
                'task_type': features.get('task_type', 'unknown'),
                'has_numbers': features.get('has_numbers', False),
                'is_billing': features.get('is_billing', False)
            },
            'routing': {
                'selected_model': model_name,
                'model_scores': features.get('model_scores', {}),
                'routing_reason': features.get('routing_reason', 'Unknown')
            },
            'execution': {
                'success': success,
                'latency_ms': round(latency_ms, 2),
                'error': error
            },
            'response': {
                'type': 'success' if success else 'error',
                'content': str(response)[:500] if response else None  # Truncate long responses
            }
        }
        
        # Store log
        self.logs.append(log_entry)
        
        # Print formatted log to terminal
        self._print_terminal_log(log_entry)
        
        return log_entry
    
    def _print_terminal_log(self, log_entry: Dict[str, Any]):
        """Print beautifully formatted log to terminal"""
        print("\n" + "="*80)
        print(f"🎯 VYAMIT AI - MULTI-LLM ROUTING SYSTEM")
        print("="*80)
        
        # Request Info
        print(f"📝 REQUEST ID: {log_entry['request_id']}")
        print(f"⏰ TIMESTAMP: {log_entry['timestamp']}")
        print(f"👤 USER INPUT: \"{log_entry['user_input']}\"")
        
        # Analysis
        analysis = log_entry['analysis']
        print(f"\n[INFO] QUERY ANALYSIS:")
        print(f"   • Language: {analysis['language'].upper()}")
        print(f"   • Complexity: {analysis['complexity'].upper()}")
        print(f"   • Task Type: {analysis['task_type'].upper()}")
        print(f"   • Word Count: {analysis['word_count']}")
        print(f"   • Has Numbers: {'yes' if analysis['has_numbers'] else 'no'}")
        print(f"   • Is Billing: {'yes' if analysis['is_billing'] else 'no'}")
        
        # Routing Decision
        routing = log_entry['routing']
        print(f"\n[INFO] MODEL ROUTING:")
        print(f"   • Selected: {routing['selected_model'].upper()}")
        print(f"   • Reason: {routing['routing_reason']}")
        print(f"   • Scores: {routing['model_scores']}")
        
        # Execution
        execution = log_entry['execution']
        status_icon = "OK" if execution['success'] else "FAIL"
        print(f"\n⚡ EXECUTION:")
        print(f"   • Status: {status_icon} {'SUCCESS' if execution['success'] else 'FAILED'}")
        print(f"   • Latency: {execution['latency_ms']}ms")
        if execution['error']:
            print(f"   • Error: {execution['error']}")
        
        # Response Preview
        response = log_entry['response']
        print(f"\n📤 RESPONSE:")
        print(f"   • Type: {response['type'].upper()}")
        if response['content']:
            preview = response['content'][:100] + "..." if len(response['content']) > 100 else response['content']
            print(f"   • Content: {preview}")
        
        print("="*80 + "\n")
    
    def get_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs"""
        return list(self.logs)[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        if not self.logs:
            return {'total_requests': 0}
        
        total = len(self.logs)
        successful = sum(1 for log in self.logs if log['execution']['success'])
        
        model_usage = {}
        avg_latency_by_model = {}
        
        for log in self.logs:
            model = log['routing']['selected_model']
            model_usage[model] = model_usage.get(model, 0) + 1
            
            if model not in avg_latency_by_model:
                avg_latency_by_model[model] = []
            avg_latency_by_model[model].append(log['execution']['latency_ms'])
        
        # Calculate averages
        for model in avg_latency_by_model:
            latencies = avg_latency_by_model[model]
            avg_latency_by_model[model] = sum(latencies) / len(latencies)
        
        return {
            'total_requests': total,
            'success_rate': (successful / total) * 100 if total > 0 else 0,
            'model_usage': model_usage,
            'avg_latency_by_model': avg_latency_by_model
        }

class AdaptiveMultiLLMService:
    """Main service implementing the Adaptive Multi-LLM Routing System"""
    
    def __init__(self):
        # Initialize components
        self.router = ModelRouter()
        self.logger = StructuredLogger()
        
        # Initialize models with fallback chains
        self._initialize_models()
        
        # Chat memory
        self.memory = deque(maxlen=20)
        
        print("[INFO] Adaptive Multi-LLM Routing System initialized")
        print("[INFO] Models: Qwen (fast) | Gemini (smart)")
    
    def _initialize_models(self):
        """Initialize all AI models with fallback chains"""
        # Qwen - Fast multilingual model
        self.qwen_available = bool(os.getenv("HUGGINGFACE_API_TOKEN"))
        self.qwen_models = [
            "Qwen/Qwen3.5-9B",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2-7B-Instruct"
        ]
        
        # Gemma - Balanced model (removed as per user request)
        # self.gemma_available = False
        # self.gemma_models = []
        
        # Gemini - Smart model (using ACTUALLY AVAILABLE models from API)
        self.gemini_available = bool(os.getenv("GEMINI_API_KEY"))
        self.gemini_models = [
            "gemini-2.5-flash",          # Available and fast
            "gemini-2.0-flash",          # Available backup
            "gemini-flash-latest",       # Available latest
            "gemini-pro-latest",         # Available pro
            "gemini-2.0-flash-001",      # Available alternative
            "gemini-2.5-pro"             # Available pro version
        ]
        
        if self.gemini_available:
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"), transport="rest")
                self.genai = genai
                print("[OK] Gemini API initialized")
            except Exception as e:
                print(f"[WARN] Gemini initialization failed: {e}")
                self.gemini_available = False
        
        print(f"[INFO] Model status: Qwen={'OK' if self.qwen_available else 'OFF'} | "
              f"Gemini={'OK' if self.gemini_available else 'OFF'}")
    
    def process_with_qwen_fallback(self, prompt: str) -> str:
        """Process using Qwen with model fallback chain - FIXED VERSION"""
        last_error = ""
        
        for model_name in self.qwen_models:
            try:
                print(f"[INFO] Trying Qwen model: {model_name}")
                url = f"https://router.huggingface.co/models/{model_name}"
                headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_TOKEN')}"}
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 300,
                        "temperature": 0.1,
                        "return_full_text": False,
                        "do_sample": True,
                        "top_p": 0.9
                    },
                    "options": {
                        "wait_for_model": True,
                        "use_cache": False
                    }
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=20)
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get("generated_text", "").strip()
                        if generated_text:
                            print(f"[OK] Qwen model '{model_name}' succeeded.")
                            return generated_text
                    elif isinstance(result, dict) and "generated_text" in result:
                        generated_text = result["generated_text"].strip()
                        if generated_text:
                            print(f"[OK] Qwen model '{model_name}' succeeded.")
                            return generated_text
                    
                    print(f"[WARN] {model_name} returned empty response")
                    last_error = f"Empty response from {model_name}"
                    continue
                    
                elif response.status_code == 503:
                    print(f"[WARN] {model_name} is loading, trying next...")
                    last_error = f"Model {model_name} is loading"
                    continue
                elif response.status_code == 429:
                    print(f"[WARN] {model_name} rate limited, trying next...")
                    last_error = f"Rate limited for {model_name}"
                    continue
                else:
                    print(f"[WARN] {model_name} failed: HTTP {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"   Error details: {error_detail}")
                        last_error = f"HTTP {response.status_code}: {error_detail}"
                    except:
                        last_error = f"HTTP {response.status_code}"
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"[WARN] {model_name} timed out")
                last_error = f"Timeout for {model_name}"
                continue
            except Exception as e:
                print(f"[WARN] {model_name} error: {e}")
                last_error = str(e)
                continue
        
        print(f"\n[ERROR] All Qwen models failed. Last error: {last_error}\n")
        raise Exception(f"All Qwen models failed: {last_error}")
    
    # Gemma processing removed as per user request - only using Qwen → Gemini → Fallback
    
    def process_with_gemini_fallback(self, prompt: str) -> str:
        """Process using Gemini with model fallback chain (EXACT copy from working ai_service_fast.py)"""
        last_error = ""
        
        for model_name in self.gemini_models:
            try:
                print(f"[INFO] Trying Gemini model: {model_name}")
                model = self.genai.GenerativeModel(model_name)
                
                # Add generation config to avoid MessageToJson issues
                generation_config = {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
                
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                if response and response.text:
                    print(f"[OK] Gemini model '{model_name}' succeeded.")
                    return response.text
                else:
                    print(f"[WARN] {model_name} returned empty response")
                    last_error = f"Empty response from {model_name}"
                    continue
                    
            except Exception as e:
                print(f"[WARN] {model_name} failed: {e}")
                last_error = str(e)
                continue
        
        print(f"\n[ERROR] All Gemini models failed. Last error: {last_error}\n")
        raise Exception(f"All Gemini models failed: {last_error}")
    
    def get_vyamit_prompt(self, user_text: str, inventory_json: str = "") -> str:
        """Get the COMPACT Vyamit AI prompt that actually works (like ai_service_fast.py)"""
        return f"""Vyamit AI voice assistant. Hinglish (Latin script).

CUSTOMER: Extract from "customer [name]" or "naam [name]". Default: "Walk-in"

INVENTORY: {inventory_json}
USER: "{user_text}"

RULES:
1. Price mentioned → Extract, calculate, add to bill
2. Item in inventory → Use inventory price
3. Multiple items, one missing → Add known to "items", ask in "msg", type: "BILL"
4. One item, not in inventory, no price → Ask price, type: "ERROR"
5. Greeting → type: "GREETING"
6. Business query → Use data, type: "QUERY"

JSON OUTPUT:
{{"type": "BILL/ERROR/GREETING/QUERY", "customer_name": "Name", "items": [{{"name": "Item", "qty_display": "1kg", "rate": 50.0, "total": 50.0, "unit": "kg"}}], "msg": "Short Hinglish"}}

If OK: msg "Saaman Bill mein jod diya gaya hai"

EXAMPLES:
- "customer raju 5rs wali 6 maggie" → {{"type": "BILL", "customer_name": "Raju", "items": [{{"name": "Maggie", "qty_display": "6pic", "rate": 5.0, "total": 30.0, "unit": "pic"}}], "msg": "Raju ke liye 6 Maggie add"}}
- "1kg chawal aur aam" → {{"type": "BILL", "items": [{{"name": "Chawal", "qty_display": "1kg", "rate": 120.0, "total": 120.0, "unit": "kg"}}], "msg": "Chawal add. Aam ki keemat?"}}
- "hello" → {{"type": "GREETING", "items": [], "msg": "Namaste! Main Vyamit AI"}}"""
    

    
    def get_enhanced_fallback_response(self, user_text: str, features: Dict[str, Any]) -> str:
        """Enhanced rule-based fallback system - IMPROVED VERSION"""
        user_lower = user_text.lower()
        
        # Extract customer name if present
        customer_name = "Walk-in"
        if "customer" in user_lower:
            parts = user_text.split()
            try:
                customer_idx = [p.lower() for p in parts].index("customer")
                if customer_idx + 1 < len(parts):
                    customer_name = " ".join(parts[customer_idx + 1:customer_idx + 3]).title()
            except:
                pass
        
        # Handle greetings
        if any(greeting in user_lower for greeting in ['hello', 'hi', 'namaste', 'helo', 'hey']):
            return json.dumps({
                "type": "GREETING", 
                "customer_name": customer_name, 
                "items": [], 
                "msg": "Namaste! Main Vyamit AI hoon. Kaise madad kar sakti hoon?", 
                "should_stop": False
            })
        
        # Enhanced item recognition with quantity and price extraction
        import re
        
        # Common item mappings
        items_map = {
            'chawal': {'name': 'Chawal', 'rate': 120.0, 'unit': 'kg'},
            'rice': {'name': 'Chawal', 'rate': 120.0, 'unit': 'kg'},
            'basmati': {'name': 'Chawal', 'rate': 120.0, 'unit': 'kg'},
            'maggie': {'name': 'Maggie', 'rate': 5.0, 'unit': 'pic'},
            'noodles': {'name': 'Maggie', 'rate': 5.0, 'unit': 'pic'},
            'sugar': {'name': 'Sugar', 'rate': 45.0, 'unit': 'kg'},
            'cheeni': {'name': 'Sugar', 'rate': 45.0, 'unit': 'kg'},
            'oil': {'name': 'Oil', 'rate': 150.0, 'unit': 'litre'},
            'tel': {'name': 'Oil', 'rate': 150.0, 'unit': 'litre'},
            'atta': {'name': 'Atta', 'rate': 40.0, 'unit': 'kg'},
            'flour': {'name': 'Atta', 'rate': 40.0, 'unit': 'kg'},
            'doodh': {'name': 'Milk', 'rate': 60.0, 'unit': 'litre'},
            'milk': {'name': 'Milk', 'rate': 60.0, 'unit': 'litre'},
            'pyaz': {'name': 'Onion', 'rate': 30.0, 'unit': 'kg'},
            'onion': {'name': 'Onion', 'rate': 30.0, 'unit': 'kg'},
            'aloo': {'name': 'Potato', 'rate': 25.0, 'unit': 'kg'},
            'potato': {'name': 'Potato', 'rate': 25.0, 'unit': 'kg'}
        }
        
        # Find matching items
        found_items = []
        for item_key, item_data in items_map.items():
            if item_key in user_lower:
                found_items.append((item_key, item_data))
        
        if found_items:
            # Process each found item
            bill_items = []
            
            for item_key, item_data in found_items:
                # Extract quantity
                qty_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:kg|kilo)',
                    r'(\d+(?:\.\d+)?)\s*(?:pic|piece|packet)',
                    r'(\d+(?:\.\d+)?)\s*(?:litre|liter)',
                    r'(\d+(?:\.\d+)?)\s*' + re.escape(item_key)
                ]
                
                qty = 1.0
                qty_display = f"1{item_data['unit']}"
                
                for pattern in qty_patterns:
                    qty_match = re.search(pattern, user_lower)
                    if qty_match:
                        qty = float(qty_match.group(1))
                        if 'kg' in pattern or 'kilo' in pattern:
                            qty_display = f"{qty}kg"
                        elif 'pic' in pattern or 'piece' in pattern or 'packet' in pattern:
                            qty_display = f"{int(qty)}pic"
                        elif 'litre' in pattern or 'liter' in pattern:
                            qty_display = f"{qty}litre"
                        else:
                            qty_display = f"{qty}{item_data['unit']}"
                        break
                
                # Extract custom price if mentioned
                price_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:rs|rupay|rupee)',
                    r'(\d+(?:\.\d+)?)\s*(?:wali|wala)',
                    r'(\d+(?:\.\d+)?)\s*per\s*(?:kg|kilo|pic|piece|litre)'
                ]
                
                rate = item_data['rate']
                for pattern in price_patterns:
                    price_match = re.search(pattern, user_lower)
                    if price_match:
                        rate = float(price_match.group(1))
                        break
                
                total = qty * rate
                
                bill_items.append({
                    "name": item_data['name'],
                    "qty_display": qty_display,
                    "rate": rate,
                    "total": total,
                    "unit": item_data['unit']
                })
            
            # Return billing response
            return json.dumps({
                "type": "BILL", 
                "customer_name": customer_name, 
                "items": bill_items, 
                "msg": "Saaman Bill mein jod diya gaya hai", 
                "should_stop": False
            })
        
        # Handle price queries
        if any(word in user_lower for word in ['price', 'keemat', 'kitna', 'kya hai']):
            # Try to find item in price query
            for item_key, item_data in items_map.items():
                if item_key in user_lower:
                    return json.dumps({
                        "type": "QUERY", 
                        "customer_name": customer_name, 
                        "items": [],
                        "msg": f"{item_data['name']} ka price hai {item_data['rate']} rupaye per {item_data['unit']}", 
                        "should_stop": False
                    })
        
        # Default fallback
        return json.dumps({
            "type": "ERROR", 
            "customer_name": customer_name, 
            "items": [], 
            "msg": "Samajh nahi aaya, phir se boliye", 
            "should_stop": False
        })
    
    def process_voice_command(self, user_text: str, inventory: List[Item], user_id: str = "default") -> Dict[str, Any]:
        """Main processing function with intelligent routing"""
        start_time = time.time()
        
        # Step 1: Route query to appropriate model
        selected_model, features = self.router.route_query(user_text)
        
        # Step 2: Prepare inventory data
        filtered_inventory = [item for item in inventory if item.price > 0]
        inventory_list = []
        for item in filtered_inventory:
            names_array = json.loads(item.names) if isinstance(item.names, str) else item.names
            inventory_list.append({
                "names": names_array,
                "price": item.price,
                "unit": item.unit,
                "category": item.category
            })
        inventory_json = json.dumps(inventory_list, ensure_ascii=False)
        
        # Step 3: Generate prompt using Vyamit AI format
        prompt = self.get_vyamit_prompt(user_text, inventory_json)
        
        # Step 4: Execute with intelligent fallback chain
        response_text = None
        error = None
        final_model_used = selected_model
        
        # Priority order: Gemini (working) → Qwen (if available) → Enhanced Fallback
        fallback_chain = ['gemini', 'qwen', 'enhanced_fallback']
        
        print(f"🎯 Fallback chain: {' → '.join(fallback_chain)}")
        
        for attempt_model in fallback_chain:
            try:
                if attempt_model == 'gemini' and self.gemini_available:
                    print(f"[INFO] Attempting GEMINI (smart reasoning)")
                    response_text = self.process_with_gemini_fallback(prompt)
                    final_model_used = 'gemini'
                    break
                    
                elif attempt_model == 'qwen' and self.qwen_available:
                    print(f"[INFO] Attempting QWEN (fast multilingual)")
                    response_text = self.process_with_qwen_fallback(prompt)
                    final_model_used = 'qwen'
                    break
                    
                elif attempt_model == 'enhanced_fallback':
                    print(f"[INFO] Using enhanced fallback (rule-based)")
                    response_text = self.get_enhanced_fallback_response(user_text, features)
                    final_model_used = 'enhanced_fallback'
                    break
                    
            except Exception as e:
                print(f"[ERROR] {attempt_model.upper()} failed: {e}")
                error = str(e)
                continue
        
        # If somehow nothing worked, use basic fallback
        if not response_text:
            print(f"[INFO] Using basic fallback (last resort)")
            response_text = '{"type": "ERROR", "customer_name": "Walk-in", "items": [], "msg": "System busy, please try again", "should_stop": false}'
            final_model_used = 'basic_fallback'
        
        # Step 5: Parse response
        try:
            # Clean response
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            
            # Find JSON
            json_start = clean_text.find('{')
            json_end = clean_text.rfind('}') + 1
            
            if json_start == -1:
                json_start = clean_text.find('[')
                json_end = clean_text.rfind(']') + 1
            
            if json_start != -1 and json_end > json_start:
                clean_text = clean_text[json_start:json_end]
            
            result = json.loads(clean_text)
            
            # Ensure proper format
            if isinstance(result, list):
                # Billing response
                final_result = {
                    "type": "BILL",
                    "customer_name": "Walk-in",
                    "items": result,
                    "msg": "Saaman Bill mein jod diya gaya hai",
                    "should_stop": False
                }
            else:
                final_result = result
                
        except json.JSONDecodeError:
            final_result = {
                "type": "ERROR",
                "customer_name": "Walk-in",
                "items": [],
                "msg": "Samajh nahi aaya, phir se boliye",
                "should_stop": False
            }
        
        # Step 6: Calculate latency and log
        latency_ms = (time.time() - start_time) * 1000
        
        # Add memory
        self.memory.append({"role": "user", "content": user_text})
        self.memory.append({"role": "assistant", "content": final_result.get("msg", "")})
        
        # Log the complete transaction
        self.logger.log_request(
            user_input=user_text,
            features=features,
            model_name=final_model_used,
            response=final_result,
            latency_ms=latency_ms,
            success=error is None,
            error=error
        )
        
        return final_result
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get chat history"""
        return list(self.memory)
    
    def clear_chat_history(self):
        """Clear chat history"""
        self.memory.clear()
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        stats = self.logger.get_stats()
        
        return {
            "service": "Adaptive Multi-LLM Routing System",
            "models": {
                "qwen": {"available": self.qwen_available, "role": "Fast multilingual"},
                "gemini": {"available": self.gemini_available, "role": "Complex reasoning"}
            },
            "memory_enabled": True,
            "chat_history_available": True,
            "max_messages": 20,
            "current_messages": len(self.memory),
            "statistics": stats
        }
    
    def get_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent logs"""
        return self.logger.get_logs(limit)