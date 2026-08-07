import os
import json
import time
import asyncio
import google.generativeai as genai
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Dict, Any, Optional, List, AsyncGenerator
from pydantic import BaseModel
from sqlmodel import Session, select
from app.db.database import engine, get_session
from app.db.models import Item, User
from app.services.ai_service import AIService
from app.core.security import jwt, SECRET_KEY, ALGORITHM, get_current_user

router = APIRouter()
ai_service = AIService()

# Qwen → Gemini → Gemma hybrid. Set VYAMIT_HYBRID_LLM=false for Gemini-only.
# Hybrid LLM disabled to save memory (langchain removed)
_HYBRID = False
hybrid_voice = None

# Session cache for faster processing - avoid DB query on every message
_session_cache: Dict[int, Dict[str, Any]] = {}

# Logging helpers
def log_ws_event(event_type: str, user_id: int, msg: str):
    print(f"[WS {event_type}] User {user_id}: {msg}")

def log_input_received(source: str, user_id: int, text: str, extra: Dict = None):
    print(f"[INPUT] {source} | User {user_id}: {text[:50]}... | {extra or {}}")

def log_db_payload(user_id: int, shop_category: str, total_items: int, passed_items: List):
    print(f"[DB] User {user_id} | Category: {shop_category} | Items: {total_items} | Passed: {len(passed_items)}")

class VoiceRequest(BaseModel):
    text: str
    shop_category: Optional[str] = None

class PremiumVoiceRequest(BaseModel):
    transcript: str
    user_id: int
    inventory: List[Dict[str, Any]]

# Configure Gemini for streaming
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

# Configure Mistral AI for streaming (mistralai 1.2.5)
Mistral = None
try:
    from mistralai import Mistral
    print("[OK] Mistral client imported from mistralai")
except ImportError as e:
    print(f"[WARN] Cannot import Mistral: {e}")
    print("[WARN] Mistral AI not available - install with: pip install mistralai==1.2.5")

mistral_client_ = None

def get_mistral_client_stream():
    global mistral_client_
    if mistral_client_ is not None:
        return mistral_client_
    key = os.getenv("MISTRAL_API_KEY")
    if key and Mistral is not None:
        try:
            mistral_client_ = Mistral(api_key=key)
            print("[OK] Mistral AI Streaming Client initialized.")
            return mistral_client_
        except Exception as e:
            print(f"[WARN] Could not initialize Mistral client: {e}")
            mistral_client_ = None
    return None

# Session cache for streaming conversation history
_streaming_session_cache: Dict[int, list] = {}

def log_ws(event: str, user_id: int, msg: str):
    """Enhanced WebSocket logging"""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [WS-{event}] User {user_id}: {msg}")

async def stream_mistral_response(
    user_text: str,
    inventory: list,
    shop_category: str,
    user_id: int,
    conversation_history: list
) -> AsyncGenerator[str, None]:
    """Stream Mistral AI responses token by token - PRIMARY MODEL"""
    try:
        log_ws("STREAM-INIT", user_id, f"Starting Mistral stream for: '{user_text[:50]}...'")

        # Build inventory context string
        inventory_context = ""
        if inventory:
            items_text = []
            for item in inventory[:50]:
                try:
                    names = json.loads(item.names) if isinstance(item.names, str) else item.names
                    name = names[0] if names else "Unknown"
                except Exception:
                    name = str(item.names)
                items_text.append(f"{name}: {item.price}/{item.unit}")
            inventory_context = "\n".join(items_text)
            log_ws("INVENTORY", user_id, f"Loaded {len(inventory[:50])} items into context")
        else:
            log_ws("INVENTORY", user_id, "No inventory found in DB for this user")

        # Compact system prompt using system role (Mistral supports this properly)
        system_prompt = f"""Vyamit AI voice billing assistant for a {shop_category} shop. Hinglish responses.

INVENTORY:
{inventory_context if inventory_context else "No inventory loaded"}

RULES:
1. Extract items, quantities and prices from user speech.
2. Price mentioned → calculate total and add to bill.
3. Item in inventory → use inventory price.
4. Item missing price & not in inventory → ask for price (type ERROR).
5. Greeting → type GREETING.
6. Bill confirm → type BILL.
7. Return ONLY valid JSON, no markdown, no extra text.

RESPONSE FORMAT:
{{"type": "BILL|GREETING|QUERY|CONFIRM|ERROR", "customer_name": "name or empty", "items": [{{"name": "Item", "qty_display": "1kg", "rate": 50.0, "total": 50.0, "unit": "kg"}}], "msg": "Short Hinglish reply", "should_stop": false}}

EXAMPLES:
"1 kilo aloo 20 rupaye" → {{"type": "BILL", "customer_name": "", "items": [{{"name": "Aloo", "qty_display": "1kg", "rate": 20.0, "total": 20.0, "unit": "kg"}}], "msg": "Aloo bill mein add kar diya", "should_stop": false}}
"hello" → {{"type": "GREETING", "customer_name": "", "items": [], "msg": "Namaste! Kya chahiye?", "should_stop": false}}"""

        # Build messages with system role at top, then conversation history
        messages = [{"role": "system", "content": system_prompt}]
        for entry in conversation_history[-6:]:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["assistant"]})

        log_ws("HISTORY", user_id, f"Context: {len(conversation_history)} past exchanges")
        messages.append({"role": "user", "content": user_text})

        log_ws("LLM-START", user_id, "Mistral AI streaming...")
        stream_start_time = time.time()

        active_client = get_mistral_client_stream()
        if not active_client:
            raise RuntimeError("Mistral client not initialized")

        stream_response = active_client.chat.stream(
            model="mistral-large-latest",
            messages=messages,
            temperature=0.1,
            top_p=0.8,
            max_tokens=500,
        )

        full_text = ""
        token_count = 0
        for chunk in stream_response:
            try:
                if chunk.data.choices[0].delta.content:
                    token = chunk.data.choices[0].delta.content
                    full_text += token
                    token_count += 1
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            except Exception:
                pass

        stream_duration = time.time() - stream_start_time
        log_ws("LLM-COMPLETE", user_id, f"Generated {len(full_text)} chars, {token_count} chunks in {stream_duration:.2f}s")
        yield f"data: {json.dumps({'type': 'done', 'full_text': full_text})}\n\n"

    except Exception as e:
        log_ws("MISTRAL-ERROR", user_id, str(e))
        yield f"data: {json.dumps({'type': 'fallback', 'error': str(e)})}\n\n"

async def stream_gemini_response(
    user_text: str,
    inventory: list,
    shop_category: str,
    user_id: int,
    conversation_history: list
) -> AsyncGenerator[str, None]:
    """Stream Gemini responses token by token - FALLBACK MODEL
    
    NOTE: Using non-streaming mode due to deprecated google.generativeai streaming issues.
    Simulates streaming by yielding the response in chunks.
    """
    try:
        log_ws("STREAM-INIT", user_id, f"Starting Gemini fallback for: '{user_text[:50]}...'")

        # Build inventory context string
        inventory_context = ""
        if inventory:
            items_text = []
            for item in inventory[:50]:
                try:
                    names = json.loads(item.names) if isinstance(item.names, str) else item.names
                    name = names[0] if names else "Unknown"
                except Exception:
                    name = str(item.names)
                items_text.append(f"{name}: {item.price}/{item.unit}")
            inventory_context = "\n".join(items_text)
            log_ws("INVENTORY", user_id, f"Loaded {len(inventory[:50])} items into context")
        else:
            log_ws("INVENTORY", user_id, "No inventory found in DB for this user")

        # Compact prompt
        system_prompt = f"""Vyamit AI voice billing assistant for a {shop_category} shop. Hinglish responses.

INVENTORY:
{inventory_context if inventory_context else "No inventory loaded"}

RULES:
1. Extract items, quantities and prices from user speech.
2. Price mentioned → calculate total and add to bill.
3. Item in inventory → use inventory price.
4. Item missing price & not in inventory → ask for price (type ERROR).
5. Greeting → type GREETING.
6. Bill confirm → type BILL.
7. Return ONLY valid JSON, no markdown, no extra text.

RESPONSE FORMAT:
{{"type": "BILL|GREETING|QUERY|CONFIRM|ERROR", "customer_name": "name or empty", "items": [{{"name": "Item", "qty_display": "1kg", "rate": 50.0, "total": 50.0, "unit": "kg"}}], "msg": "Short Hinglish reply", "should_stop": false}}

EXAMPLES:
"1 kilo aloo 20 rupaye" → {{"type": "BILL", "customer_name": "", "items": [{{"name": "Aloo", "qty_display": "1kg", "rate": 20.0, "total": 20.0, "unit": "kg"}}], "msg": "Aloo bill mein add kar diya", "should_stop": false}}
"hello" → {{"type": "GREETING", "customer_name": "", "items": [], "msg": "Namaste! Kya chahiye?", "should_stop": false}}
"aloo ka rate kya hai" → {{"type": "QUERY", "customer_name": "", "items": [], "msg": "Aloo ka rate 20 rupaye kilo hai", "should_stop": false}}"""

        # Build full prompt with history
        full_prompt = system_prompt + "\n\n"
        for entry in conversation_history[-6:]:
            full_prompt += f"User: {entry['user']}\nAssistant: {entry['assistant']}\n\n"
        full_prompt += f"User: {user_text}\nAssistant:"

        log_ws("HISTORY", user_id, f"Context: {len(conversation_history)} past exchanges")

        # Model fallback chain - using NON-streaming for reliability
        candidate_models = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
        response_text = None
        used_model = None
        last_err = None

        stream_start_time = time.time()
        for model_name in candidate_models:
            try:
                log_ws("LLM-START", user_id, f"Gemini {model_name} (non-streaming)...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "top_k": 40,
                        "max_output_tokens": 500,
                    }
                )
                response_text = response.text
                used_model = model_name
                break
            except Exception as ex:
                last_err = ex
                log_ws("GEMINI-MODEL-WARN", user_id, f"Gemini model '{model_name}' failed: {ex}")
                continue

        if not response_text:
            raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")

        # Simulate streaming by yielding chunks
        chunk_size = 10  # characters per chunk
        token_count = 0
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i+chunk_size]
            token_count += 1
            yield f"data: {json.dumps({'type': 'token', 'text': chunk})}\n\n"
            await asyncio.sleep(0.01)  # Small delay to simulate streaming

        stream_duration = time.time() - stream_start_time
        log_ws("LLM-COMPLETE", user_id, f"Generated {len(response_text)} chars, {token_count} chunks in {stream_duration:.2f}s ({used_model})")
        yield f"data: {json.dumps({'type': 'done', 'full_text': response_text})}\n\n"

    except Exception as e:
        log_ws("STREAM-ERROR", user_id, str(e))
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.websocket("/ws/stream")
async def streaming_voice_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
):
    """
    True concurrent streaming WebSocket endpoint. Handles 'process' and 'interrupt' actions in real time.
    """
    await websocket.accept()
    
    authenticated_user_id = user_id or 1
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            authenticated_user_id = int(payload.get("sub", 1))
        except:
            pass
            
    log_ws("CONNECTED", authenticated_user_id, f"Client Connected.")
    
    if authenticated_user_id not in _streaming_session_cache:
        _streaming_session_cache[authenticated_user_id] = []
        
    await websocket.send_json({
        "type": "connected",
        "user_id": authenticated_user_id,
        "msg": "Streaming voice AI ready (Mistral → Gemini)"
    })
    
    current_stream_task: Optional[asyncio.Task] = None
    
    async def process_and_stream(user_text: str):
        try:
            from app.utils.debug_logger import voice_logger
            
            voice_logger.section(f"NEW VOICE QUERY - User {authenticated_user_id}")
            voice_logger.info(f"Query: '{user_text}'")
            voice_logger.info(f"Length: {len(user_text)} chars")
            
            await websocket.send_json({
                "type": "processing",
                "msg": "Processing..."
            })
            
            # Fetch inventory from database
            voice_logger.subsection("DATABASE RETRIEVAL")
            db_start = time.time()
            
            with Session(engine) as session:
                statement = select(Item).where(Item.owner_id == authenticated_user_id)
                inventory = session.exec(statement).all()
                db_user = session.get(User, authenticated_user_id)
                shop_category = getattr(db_user, "shop_category", "Kirana") if db_user else "Kirana"
            
            db_duration = time.time() - db_start
            voice_logger.success(f"Retrieved {len(inventory)} items in {db_duration*1000:.2f}ms")
            voice_logger.info(f"Shop Category: {shop_category}")
            
            # Log inventory details
            if inventory:
                voice_logger.debug("Top 5 items:")
                for i, item in enumerate(inventory[:5], 1):
                    try:
                        names = json.loads(item.names) if isinstance(item.names, str) else item.names
                        name = names[0] if names else "Unknown"
                    except:
                        name = str(item.names)
                    voice_logger.debug(f"  {i}. {name}: ₹{item.price}/{item.unit}")
            
            log_ws("DB-QUERY", authenticated_user_id, f"Category: {shop_category}, Items: {len(inventory)}")
            
            full_response = ""
            token_counter = 0
            log_ws("▼ STREAM-START", authenticated_user_id, "="*60)
            
            mistral_failed = False
            model_used = "unknown"
            active_mistral = get_mistral_client_stream()
            
            if active_mistral:
                voice_logger.subsection("LLM CALL - PRIMARY (Mistral)")
                log_ws("MODEL", authenticated_user_id, "Trying Mistral AI (Primary)")
                model_used = "mistral"
                async for chunk in stream_mistral_response(
                    user_text, inventory, shop_category, authenticated_user_id, _streaming_session_cache[authenticated_user_id]
                ):
                    if chunk.startswith("data: "):
                        chunk_data = json.loads(chunk[6:])
                        if chunk_data["type"] == "fallback":
                            mistral_failed = True
                            voice_logger.warning("Mistral failed, switching to Gemini fallback")
                            break
                        if chunk_data["type"] == "token":
                            full_response += chunk_data["text"]
                            token_counter += 1
                            await websocket.send_json({
                                "type": "stream_token",
                                "token": chunk_data["text"],
                                "accumulated": full_response,
                                "model": "mistral"
                            })
                        elif chunk_data["type"] == "done":
                            voice_logger.success(f"Mistral completed: {len(full_response)} chars, {token_counter} tokens")
                            log_ws("▲ STREAM-END", authenticated_user_id, "="*60)
                            break
            else:
                mistral_failed = True
                voice_logger.warning("Mistral client not available")
                
            if mistral_failed:
                voice_logger.subsection("LLM CALL - FALLBACK (Gemini)")
                log_ws("MODEL", authenticated_user_id, "Using Gemini (Fallback)")
                model_used = "gemini"
                full_response = ""
                token_counter = 0
                async for chunk in stream_gemini_response(
                    user_text, inventory, shop_category, authenticated_user_id, _streaming_session_cache[authenticated_user_id]
                ):
                    if chunk.startswith("data: "):
                        chunk_data = json.loads(chunk[6:])
                        if chunk_data["type"] == "token":
                            full_response += chunk_data["text"]
                            token_counter += 1
                            await websocket.send_json({
                                "type": "stream_token",
                                "token": chunk_data["text"],
                                "accumulated": full_response,
                                "model": "gemini"
                            })
                        elif chunk_data["type"] == "done":
                            voice_logger.success(f"Gemini completed: {len(full_response)} chars, {token_counter} tokens")
                            log_ws("▲ STREAM-END", authenticated_user_id, "="*60)
                            break
                        elif chunk_data["type"] == "error":
                            voice_logger.error(f"Gemini error: {chunk_data['message']}")
                            log_ws("❌ LLM-ERROR", authenticated_user_id, chunk_data["message"])
                            await websocket.send_json({
                                "type": "error",
                                "message": chunk_data["message"],
                                "model": "gemini"
                            })
                            break
                            
            if full_response:
                voice_logger.subsection("RESPONSE PARSING")
                voice_logger.debug(f"Raw response ({len(full_response)} chars):")
                voice_logger.debug(full_response[:300] + ("..." if len(full_response) > 300 else ""))
                
                try:
                    json_start = full_response.find("{")
                    json_end = full_response.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = full_response[json_start:json_end]
                        try:
                            parsed_response = json.loads(json_str)
                            voice_logger.success("JSON parsed successfully")
                        except json.JSONDecodeError:
                            voice_logger.warning("JSON truncated, attempting repair...")
                            log_ws("REPAIR", authenticated_user_id, "JSON truncated, attempting repair...")
                            repaired = json_str
                            open_braces = repaired.count('{') - repaired.count('}')
                            open_brackets = repaired.count('[') - repaired.count(']')
                            last_good = max(repaired.rfind(','), repaired.rfind(':'))
                            if last_good > 0:
                                repaired = repaired[:last_good]
                            repaired += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
                            try:
                                parsed_response = json.loads(repaired)
                                voice_logger.success("JSON repaired successfully")
                                log_ws("REPAIR-OK", authenticated_user_id, "JSON repaired successfully")
                            except Exception:
                                voice_logger.error("JSON unrecoverable, using fallback QUERY")
                                log_ws("REPAIR-FAIL", authenticated_user_id, "JSON unrecoverable, sending fallback QUERY")
                                parsed_response = {
                                    "type": "QUERY",
                                    "customer_name": "",
                                    "items": [],
                                    "msg": "Dobara boliye please",
                                    "should_stop": False
                                }
                    else:
                        voice_logger.error("No JSON braces found in response")
                        log_ws("PARSE-NOJSON", authenticated_user_id, "No JSON braces found in response")
                        parsed_response = {
                            "type": "QUERY",
                            "customer_name": "",
                            "items": [],
                            "msg": "Dobara boliye please",
                            "should_stop": False
                        }
                    
                    # Log parsed response details
                    voice_logger.subsection("PARSED RESPONSE")
                    voice_logger.info(f"Type: {parsed_response.get('type')}")
                    voice_logger.info(f"Model: {model_used}")
                    voice_logger.info(f"Items: {len(parsed_response.get('items', []))}")
                    voice_logger.info(f"Message: {parsed_response.get('msg', 'N/A')}")
                    
                    if parsed_response.get('items'):
                        voice_logger.debug("Items breakdown:")
                        for i, item in enumerate(parsed_response['items'][:5], 1):
                            voice_logger.debug(f"  {i}. {item.get('name')} - {item.get('qty_display')} @ ₹{item.get('rate')} = ₹{item.get('total')}")
                    
                    log_ws("PARSE-OK", authenticated_user_id, f"Type: {parsed_response.get('type')}, Model: {model_used}")
                    _streaming_session_cache[authenticated_user_id].append({
                        "user": user_text,
                        "assistant": json.dumps(parsed_response)
                    })
                    if len(_streaming_session_cache[authenticated_user_id]) > 10:
                        _streaming_session_cache[authenticated_user_id] = _streaming_session_cache[authenticated_user_id][-10:]
                    
                    await websocket.send_json({
                        "type": "complete",
                        "response": parsed_response,
                        "raw_text": full_response,
                        "model": model_used
                    })
                except Exception as ex:
                    voice_logger.error(f"Parse error: {ex}")
                    log_ws("❌ PARSE-ERROR", authenticated_user_id, str(ex))
                    await websocket.send_json({
                        "type": "complete",
                        "response": {
                            "type": "QUERY",
                            "customer_name": "",
                            "items": [],
                            "msg": "Dobara boliye please",
                            "should_stop": False
                        },
                        "model": model_used
                    })
        except asyncio.CancelledError:
            log_ws("CANCELLED", authenticated_user_id, "Active stream task cancelled cleanly.")
            raise
        except Exception as e:
            log_ws("TASK-ERROR", authenticated_user_id, str(e))
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except:
                pass

    try:
        while True:
            raw_message = await websocket.receive_text()
            log_ws("◄ RECV", authenticated_user_id, f"RAW: '{raw_message[:100]}'")
            try:
                data = json.loads(raw_message)
            except:
                data = {"action": "process", "text": raw_message}
                
            action = data.get("action", "process")
            if action == "ping":
                await websocket.send_json({"type": "pong"})
                continue
                
            if action == "interrupt":
                if current_stream_task and not current_stream_task.done():
                    current_stream_task.cancel()
                    log_ws("INTERRUPT-OK", authenticated_user_id, "Cancelled active streaming task")
                await websocket.send_json({"type": "interrupted"})
                continue
                
            if action == "process":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue
                if current_stream_task and not current_stream_task.done():
                    current_stream_task.cancel()
                    log_ws("CANCEL-PREV", authenticated_user_id, "Cancelled previous active stream for new query")
                current_stream_task = asyncio.create_task(process_and_stream(user_text))
                
    except WebSocketDisconnect:
        log_ws("DISCONNECTED", authenticated_user_id, "Client disconnected cleanly")
    except Exception as e:
        log_ws("ERROR", authenticated_user_id, str(e))
    finally:
        if current_stream_task and not current_stream_task.done():
            current_stream_task.cancel()


# ==========================================================
# REALTIME CONTINUOUS WEBSOCKET ROUTE FOR FRONTEND VOICE CIRCLE (LEGACY / NON-STREAMING)
# ==========================================================
@router.websocket("/ws")
async def voice_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
):
    """
    WebSocket endpoint connecting frontend Voice Circle directly to backend LLM pipeline.
    Provides real-time continuous streaming voice AI processing.
    """
    await websocket.accept()

    # Authenticate user from query parameter token or user_id
    authenticated_user_id = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            sub = payload.get("sub")
            if sub:
                authenticated_user_id = int(sub)
        except Exception as e:
            print(f"[WS] Token authentication warning: {e}")

    if not authenticated_user_id and user_id:
        authenticated_user_id = int(user_id)

    if not authenticated_user_id:
        authenticated_user_id = 1  # Default fallback user if unauthenticated in dev

    log_ws_event("CONNECTED", authenticated_user_id, f"Client Connected from {websocket.client.host if websocket.client else 'Phone/Remote'}")

    # Send handshake confirmation
    await websocket.send_json({
        "type": "CONNECTED",
        "status": "ok",
        "msg": "Connected to Vyamit AI Voice Stream",
        "user_id": authenticated_user_id
    })

    try:
        while True:
            raw_text = await websocket.receive_text()
            if not raw_text or not raw_text.strip():
                continue

            t0 = time.perf_counter()

            try:
                data = json.loads(raw_text)
            except Exception:
                data = {"action": "process_voice", "text": raw_text}

            action = data.get("action", "process_voice")

            # Handle ping heartbeat
            if action == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            user_text = data.get("text", "").strip()
            shop_category_hint = data.get("shop_category", "General")
            req_user_id = data.get("user_id") or authenticated_user_id

            if not user_text:
                continue

            log_input_received(
                source="WebSocket Continuous Voice Stream",
                user_id=req_user_id,
                text=user_text,
                extra={"shop_category_hint": shop_category_hint, "action": action}
            )

            # 1. Send immediate status acknowledgement to Voice Circle UI
            await websocket.send_json({
                "type": "PROCESSING",
                "msg": "Vyamit AI is processing..."
            })

            # 2. Fetch user's inventory from DB within a fresh session context
            with Session(engine) as session:
                statement = select(Item).where(Item.owner_id == req_user_id)
                inventory = session.exec(statement).all()

                db_user = session.get(User, req_user_id)
                shop_category = (
                    (getattr(db_user, "shop_category", None) or shop_category_hint or "General")
                    if db_user
                    else shop_category_hint
                )

                passed_items = []
                for item in inventory:
                    if item.price > 0:
                        names_array = json.loads(item.names) if isinstance(item.names, str) else item.names
                        passed_items.append({
                            "names": names_array,
                            "price": item.price,
                            "unit": item.unit,
                            "category": item.category
                        })

                log_db_payload(
                    user_id=req_user_id,
                    shop_category=shop_category,
                    total_items=len(inventory),
                    passed_items=passed_items
                )

            # 3. Call fast LLM service (Hybrid or Gemini)
            if hybrid_voice is not None:
                ai_response = hybrid_voice.process_voice_command(
                    user_text, inventory, req_user_id, shop_category=shop_category
                )
            else:
                ai_response = ai_service.process_voice_command(
                    user_text, inventory, shop_category=shop_category
                )

            dt = time.perf_counter() - t0

            # 4. Stream response back to frontend Voice Circle
            ai_response["success"] = True
            ai_response["processing_time_sec"] = round(dt, 2)
            await websocket.send_json(ai_response)

    except WebSocketDisconnect:
        log_ws_event("DISCONNECTED", authenticated_user_id, "Client disconnected cleanly.")
    except Exception as e:
        log_ws_event("EXCEPTION", authenticated_user_id, f"WebSocket error: {e}")


# ==========================================================
# REST ENDPOINTS (HTTP Fallback / Legacy Support)
# ==========================================================
@router.post("/process")
def process_voice(
    request: VoiceRequest,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """
    Receives text from the App -> Fetches Inventory -> Calls AI -> Returns Bill JSON
    """
    statement = select(Item).where(Item.owner_id == user_id)
    inventory = session.exec(statement).all()

    db_user = session.get(User, user_id)
    shop_category = (
        (getattr(db_user, "shop_category", None) or "General")
        if db_user
        else "General"
    )

    if hybrid_voice is not None:
        ai_response = hybrid_voice.process_voice_command(
            request.text, inventory, user_id, shop_category=shop_category
        )
    else:
        ai_response = ai_service.process_voice_command(
            request.text, inventory, shop_category=shop_category
        )
    
    return ai_response

@router.post("/process-query")
def process_query(request: PremiumVoiceRequest):
    try:
        transcript_lower = request.transcript.lower()
        if any(word in transcript_lower for word in ['kitna', 'price', 'rate', 'cost', 'kya hai']):
            item_name = _extract_item_from_query(transcript_lower)
            if item_name:
                matching_item = None
                for item in request.inventory:
                    if any(item_name in name.lower() for name in item.get('names', [])):
                        matching_item = item
                        break
                
                if matching_item:
                    answer = f"{matching_item['names'][0]} ka price hai {matching_item['price']} rupaye per {matching_item['unit']}"
                    if any(word in transcript_lower for word in ['de do', 'dena', 'chahiye', 'add']):
                        return {"success": True, "answer": answer, "continue_listening": True, "mode": "billing"}
                    else:
                        return {"success": True, "answer": answer, "continue_listening": False, "mode": "query"}
                else:
                    return {"success": True, "answer": f"{item_name} inventory mein nahi hai", "continue_listening": False, "mode": "query"}
        
        return {"success": True, "answer": "Kripya apna sawal dobara puchiye", "continue_listening": False, "mode": "query"}
    except Exception as e:
        return {"success": False, "error": str(e), "continue_listening": False}

@router.post("/process-billing")
def process_billing(
    request: PremiumVoiceRequest,
    session: Session = Depends(get_session),
):
    try:
        inventory_items = []
        for item_data in request.inventory:
            item = type('Item', (), {
                'id': item_data.get('id'),
                'names': item_data.get('names', []),
                'price': item_data.get('price'),
                'unit': item_data.get('unit'),
                'category': item_data.get('category', '')
            })()
            inventory_items.append(item)
        
        db_user = session.get(User, request.user_id)
        shop_category = (
            (getattr(db_user, "shop_category", None) or "General")
            if db_user
            else "General"
        )
        if hybrid_voice is not None:
            uid = int(request.user_id)
            ai_response = hybrid_voice.process_voice_command(
                request.transcript, inventory_items, uid, shop_category=shop_category
            )
        else:
            ai_response = ai_service.process_voice_command(
                request.transcript, inventory_items, shop_category=shop_category
            )
        
        bill_updates = []
        if ai_response.get('success') and 'bill' in ai_response:
            for item in ai_response['bill']:
                bill_updates.append({
                    'name': item.get('item_name'),
                    'quantity': item.get('quantity', 1.0),
                    'unit': item.get('unit', ''),
                    'price': item.get('price_per_unit', 0.0),
                    'total': item.get('total_price', 0.0)
                })
        
        return {
            "success": True,
            "bill_updates": bill_updates,
            "total_items": len(bill_updates)
        }
    except Exception as e:
        return {"success": False, "error": str(e), "bill_updates": []}

def _extract_item_from_query(query: str) -> Optional[str]:
    remove_words = ['kitna', 'kya', 'hai', 'ka', 'ki', 'ke', 'price', 'rate', 'cost', 'batao', 'bata', 'do']
    words = query.split()
    item_words = [w for w in words if w not in remove_words and len(w) > 1]
    return ' '.join(item_words) if item_words else None