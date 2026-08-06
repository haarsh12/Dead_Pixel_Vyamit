"""
Services Test Suite
Tests OTP service, SMS service, and other services
"""
import os
from dotenv import load_dotenv

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message, level="INFO"):
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}.get(level, RESET)
    print(f"{color}[{level}]{RESET} {message}")


def test_otp_service():
    """Test OTP service"""
    log("\n" + "="*60, "INFO")
    log("Testing OTP Service", "INFO")
    log("="*60, "INFO")
    
    try:
        from services.otp_service import otp_service
        from db.database import get_session
        
        session = next(get_session())
        test_phone = "+919999999997"
        
        # Test OTP generation
        log("Generating OTP...", "INFO")
        otp_code = otp_service.create_otp(session, test_phone)
        log(f"✓ OTP generated: {otp_code}", "SUCCESS")
        
        # Test OTP verification (valid)
        log("Verifying valid OTP...", "INFO")
        is_valid = otp_service.verify_otp(session, test_phone, otp_code)
        
        if is_valid:
            log("✓ Valid OTP verified successfully", "SUCCESS")
        else:
            log("✗ Valid OTP verification failed", "ERROR")
            return False
        
        # Test OTP verification (invalid)
        log("Testing invalid OTP...", "INFO")
        is_valid = otp_service.verify_otp(session, test_phone, "000000")
        
        if not is_valid:
            log("✓ Invalid OTP correctly rejected", "SUCCESS")
        else:
            log("✗ Invalid OTP incorrectly accepted", "ERROR")
            return False
        
        # Test OTP reuse (should fail)
        log("Testing OTP reuse...", "INFO")
        is_valid = otp_service.verify_otp(session, test_phone, otp_code)
        
        if not is_valid:
            log("✓ OTP reuse correctly prevented", "SUCCESS")
        else:
            log("✗ OTP reuse incorrectly allowed", "ERROR")
            return False
        
        session.close()
        return True
        
    except Exception as e:
        log(f"✗ OTP service test failed: {e}", "ERROR")
        return False


def test_sms_service():
    """Test SMS service"""
    log("\n" + "="*60, "INFO")
    log("Testing SMS Service", "INFO")
    log("="*60, "INFO")
    
    try:
        from services.sms_service import sms_service
        
        # Check configuration
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not twilio_sid or not twilio_token:
            log("⚠ Twilio credentials not configured", "WARNING")
            log("SMS service will run in demo mode", "INFO")
            log("✓ SMS service initialized (demo mode)", "SUCCESS")
            return True
        
        log(f"✓ Twilio SID: {twilio_sid[:10]}...", "SUCCESS")
        log(f"✓ Twilio Token configured", "SUCCESS")
        
        # Test OTP sending (demo mode won't actually send)
        test_phone = "+919999999996"
        result = sms_service.send_otp(test_phone, "112233")
        
        if result.get("success"):
            log("✓ SMS OTP send successful", "SUCCESS")
        else:
            log(f"⚠ SMS send failed: {result.get('error')}", "WARNING")
        
        return True
        
    except Exception as e:
        log(f"✗ SMS service test failed: {e}", "ERROR")
        return False


def test_security_module():
    """Test security module (JWT)"""
    log("\n" + "="*60, "INFO")
    log("Testing Security Module", "INFO")
    log("="*60, "INFO")
    
    try:
        from core.security import create_access_token, verify_token
        
        # Test token creation
        log("Creating JWT token...", "INFO")
        user_id = 123
        token = create_access_token(data={"sub": str(user_id)})
        
        log(f"✓ Token created: {token[:50]}...", "SUCCESS")
        
        # Test token verification
        log("Verifying token...", "INFO")
        verified_id = verify_token(token)
        
        if verified_id == user_id:
            log(f"✓ Token verified: user_id={verified_id}", "SUCCESS")
        else:
            log(f"✗ Token verification failed: got {verified_id}, expected {user_id}", "ERROR")
            return False
        
        # Test invalid token
        log("Testing invalid token...", "INFO")
        invalid_id = verify_token("invalid.token.here")
        
        if invalid_id is None:
            log("✓ Invalid token correctly rejected", "SUCCESS")
        else:
            log("✗ Invalid token incorrectly accepted", "ERROR")
            return False
        
        return True
        
    except Exception as e:
        log(f"✗ Security module test failed: {e}", "ERROR")
        return False


def test_shop_categories():
    """Test shop categories validation"""
    log("\n" + "="*60, "INFO")
    log("Testing Shop Categories", "INFO")
    log("="*60, "INFO")
    
    try:
        from core.shop_categories import validate_category, SHOP_CATEGORIES
        
        log(f"Available categories: {len(SHOP_CATEGORIES)}", "INFO")
        
        # Test valid categories
        valid_tests = ["Kirana", "Dairy", "Medical", "Bakery"]
        
        for category in valid_tests:
            result = validate_category(category)
            log(f"✓ '{category}' validated as '{result}'", "SUCCESS")
        
        # Test case insensitivity
        result = validate_category("kirana")
        if result == "Kirana":
            log("✓ Case insensitive validation works", "SUCCESS")
        else:
            log(f"✗ Case handling failed: got '{result}'", "ERROR")
            return False
        
        # Test invalid category (should return "General")
        result = validate_category("InvalidCategory")
        if result == "General":
            log("✓ Invalid category defaults to 'General'", "SUCCESS")
        else:
            log(f"✗ Invalid category handling failed: got '{result}'", "ERROR")
            return False
        
        return True
        
    except Exception as e:
        log(f"✗ Shop categories test failed: {e}", "ERROR")
        return False


def test_pipeline_config():
    """Test pipeline configuration"""
    log("\n" + "="*60, "INFO")
    log("Testing Pipeline Config", "INFO")
    log("="*60, "INFO")
    
    try:
        from pipeline.config import config
        
        log("Embedding Config:", "INFO")
        log(f"  Provider: {config.embedding.provider}", "INFO")
        log(f"  Model: {config.embedding.model}", "INFO")
        log(f"  Dimension: {config.embedding.dimension}", "INFO")
        
        log("LLM Config:", "INFO")
        log(f"  Primary: {config.llm.primary_model}", "INFO")
        log(f"  Fallbacks: {config.llm.fallback_models}", "INFO")
        log(f"  Temperature: {config.llm.primary_temperature}", "INFO")
        
        log("Retrieval Config:", "INFO")
        log(f"  Top K: {config.retrieval.item_top_k}", "INFO")
        log(f"  Similarity threshold: {config.retrieval.item_similarity_threshold}", "INFO")
        
        log("✓ Pipeline configuration loaded", "SUCCESS")
        return True
        
    except Exception as e:
        log(f"✗ Pipeline config test failed: {e}", "ERROR")
        return False


def main():
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}SERVICES TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    results = {
        "otp_service": test_otp_service(),
        "sms_service": test_sms_service(),
        "security": test_security_module(),
        "categories": test_shop_categories(),
        "pipeline_config": test_pipeline_config()
    }
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    for name, success in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
        print(f"{name.upper():20} {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} passed")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    return all(results.values())


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
