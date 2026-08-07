"""
SMS Service using Fast2SMS — OTP and bill sharing.
"""
import logging
import os
import requests
from app.core.term_logger import log_otp_event

logger = logging.getLogger("sms")

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY")


def _phone_tail(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else "****"


class SMSService:
    def __init__(self):
        if FAST2SMS_API_KEY:
            self.api_key = FAST2SMS_API_KEY
            logger.info("[OK] Fast2SMS service initialized.")
        else:
            self.api_key = None
            logger.warning("[WARN] FAST2SMS_API_KEY not set — SMS will be mocked.")

    def send_otp(self, phone_number: str, otp: str):
        """Send OTP via Fast2SMS OTP route."""
        tail = _phone_tail(phone_number)
        if not self.api_key:
            log_otp_event(phone_number, otp, f"MOCKED (Key not set, ending in {tail}) — USE OTP: {otp} FOR LOGIN!")
            return True

        try:
            clean_phone = phone_number.replace("+91", "").replace(" ", "").strip()
            url = "https://www.fast2sms.com/dev/bulkV2"
            params = {
                "authorization": self.api_key,
                "route": "otp",
                "variables_values": otp,
                "numbers": clean_phone,
                "flash": "0",
            }

            log_otp_event(phone_number, otp, f"Sending via Fast2SMS network API to {clean_phone}...")
            response = requests.get(url, params=params, timeout=10)
            logger.info("[INFO] Fast2SMS HTTP status: %s", response.status_code)

            if response.text.startswith("<!DOCTYPE") or response.text.startswith("<html"):
                log_otp_event(phone_number, otp, "ERROR: Fast2SMS returned HTML response")
                return True

            if not response.text or not response.text.strip():
                log_otp_event(phone_number, otp, "ERROR: Fast2SMS returned empty body")
                return True

            try:
                result = response.json()
            except ValueError:
                log_otp_event(phone_number, otp, f"ERROR: Invalid JSON response ({response.text[:100]})")
                return True

            if result.get("return"):
                log_otp_event(phone_number, otp, "SUCCESS: Fast2SMS accepted OTP request!")
                return True
            log_otp_event(phone_number, otp, f"ERROR: Fast2SMS returned {result.get('message')}")
            return True

        except Exception as e:
            log_otp_event(phone_number, otp, f"EXCEPTION: {e}")
            return True


def send_sms_bill(to_number: str, message: str) -> dict:
    """Send bill text via Fast2SMS quick route."""
    tail = _phone_tail(to_number)
    if not FAST2SMS_API_KEY:
        log_otp_event(to_number, "BILL SMS", f"MOCKED (Key not set) - Body length: {len(message)} chars")
        return {
            "success": True,
            "message_id": "MOCK_MSG_12345",
            "error": None,
        }

    try:
        clean_phone = to_number.replace("+91", "").replace(" ", "").strip()
        url = "https://www.fast2sms.com/dev/bulkV2"
        params = {
            "authorization": FAST2SMS_API_KEY,
            "route": "q",
            "message": message,
            "language": "english",
            "flash": 0,
            "numbers": clean_phone,
        }

        log_otp_event(to_number, "BILL SMS", f"Sending Bill SMS via Fast2SMS to {clean_phone}...")
        response = requests.get(url, params=params, timeout=10)

        if not response.text or not response.text.strip():
            log_otp_event(to_number, "BILL SMS", "ERROR: Empty response from Fast2SMS")
            return {
                "success": False,
                "message_id": None,
                "error": "Empty response from Fast2SMS",
            }

        result = response.json()
        if result.get("return"):
            log_otp_event(to_number, "BILL SMS", "SUCCESS: Bill SMS delivered!")
            return {
                "success": True,
                "message_id": result.get("request_id"),
                "error": None,
            }
        log_otp_event(to_number, "BILL SMS", f"ERROR: {result.get('message')}")
        return {
            "success": False,
            "message_id": None,
            "error": result.get("message"),
        }

    except Exception as e:
        log_otp_event(to_number, "BILL SMS", f"EXCEPTION: {e}")
        return {
            "success": False,
            "message_id": None,
            "error": str(e),
        }
