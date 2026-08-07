import sys
import json
import time
from typing import Any, Dict, List, Optional

# ANSI Color Codes for clear, vivid terminal logging
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def log_box(title: str, content: str, color: str = CYAN):
    width = 75
    border = "=" * width
    print(f"\n{color}{border}")
    print(f"  {BOLD}{title.center(width - 4)}{RESET}{color}")
    print(f"{border}{RESET}")
    for line in content.split("\n"):
        print(f"  {color}│{RESET} {line}")
    print(f"{color}{border}{RESET}\n")

def log_ws_event(event_type: str, user_id: Any, details: str):
    print(f"{CYAN}{BOLD}🔌 [WEBSOCKET {event_type}]{RESET} User #{user_id} | {details}")

def log_input_received(source: str, user_id: Any, text: str, extra: Optional[Dict[str, Any]] = None):
    print(f"\n{MAGENTA}{BOLD}📥 [INPUT RECEIVED via {source}]{RESET}")
    print(f"   👤 User ID      : {user_id}")
    print(f"   🗣️ Speech Text  : \"{BOLD}{text}{RESET}{MAGENTA}\"")
    if extra:
        for k, v in extra.items():
            print(f"   🔹 {k:<13}: {v}")
    print(f"{MAGENTA}--------------------------------------------------{RESET}")

def log_db_payload(user_id: Any, shop_category: str, total_items: int, passed_items: List[Dict[str, Any]]):
    print(f"\n{BLUE}{BOLD}🗄️ [DATABASE -> LLM CONTEXT]{RESET}")
    print(f"   👤 Owner ID      : {user_id}")
    print(f"   🏪 Shop Category : {BOLD}{shop_category}{RESET}{BLUE}")
    print(f"   📦 DB Total Items: {total_items}")
    print(f"   🎯 Items to LLM  : {len(passed_items)} active priced items")
    if passed_items:
        print(f"   📋 Sample Items Sent to LLM:")
        for item in passed_items[:5]:
            names = item.get('names')
            if isinstance(names, list):
                name_str = " / ".join(names)
            else:
                name_str = str(names)
            print(f"      • {name_str} | ₹{item.get('price')} / {item.get('unit')} ({item.get('category')})")
        if len(passed_items) > 5:
            print(f"      ... and {len(passed_items) - 5} more items")
    print(f"{BLUE}--------------------------------------------------{RESET}")

def log_llm_start(model_chain: str, prompt_len: int, memory_history: str = ""):
    print(f"\n{YELLOW}{BOLD}🧠 [LLM PIPELINE STARTING]{RESET}")
    print(f"   🔗 Model Chain   : {model_chain}")
    print(f"   📝 Prompt Size   : {prompt_len} characters")
    if memory_history:
        print(f"   📜 Memory History:\n{memory_history}")
    print(f"{YELLOW}--------------------------------------------------{RESET}")

def log_llm_response(winner_model: str, duration_sec: float, response_data: Dict[str, Any]):
    print(f"\n{GREEN}{BOLD}⚡ [LLM RESPONSE SUCCESS] Winner: {winner_model}{RESET}")
    print(f"   ⏱️ Latency       : {duration_sec:.2f}s")
    print(f"   🏷️ Response Type : {response_data.get('type')}")
    print(f"   👤 Customer Name : {response_data.get('customer_name')}")
    print(f"   🗣️ Voice Message : \"{response_data.get('msg')}\"")
    items = response_data.get("items", [])
    print(f"   🛒 Bill Items ({len(items)}):")
    for it in items:
        print(f"      • {it.get('name')} | Qty: {it.get('qty_display')} | Rate: ₹{it.get('rate')} | Total: ₹{it.get('total')}")
    print(f"{GREEN}=================================================={RESET}\n")

def log_otp_event(phone_number: str, otp: str, status: str):
    print(f"\n{MAGENTA}{BOLD}📱 [SMS / OTP SERVICE]{RESET}")
    print(f"   📞 Phone Number  : {phone_number}")
    print(f"   🔑 Generated OTP : {BOLD}{otp}{RESET}{MAGENTA}")
    print(f"   📡 Fast2SMS Status: {status}")
    print(f"{MAGENTA}--------------------------------------------------{RESET}\n")

def log_api_call(method: str, path: str, user_id: Any = None, params: Any = None):
    print(f"\n{CYAN}{BOLD}🌐 [API CALL] {method} {path}{RESET}")
    if user_id:
        print(f"   👤 Authenticated User: {user_id}")
    if params:
        print(f"   📦 Parameters       : {params}")
    print(f"{CYAN}--------------------------------------------------{RESET}")
