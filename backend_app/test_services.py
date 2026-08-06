"""Local checks for OTP, security, category, and configuration services."""

import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import delete
from sqlmodel import select

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log(message: str, level: str = "INFO") -> None:
    color = {"INFO": BLUE, "SUCCESS": GREEN, "ERROR": RED, "WARNING": YELLOW}[level]
    print(f"{color}[{level}]{RESET} {message}")


def test_otp_service() -> bool:
    """Verify OTP invalidation, one-time use, and cleanup using an isolated phone."""
    try:
        from db.database import get_session
        from db.models import OTP
        from services.otp_service import otp_service

        session = next(get_session())
        phone = f"+91{uuid.uuid4().int % 10**10:010d}"
        try:
            first_code = otp_service.create_otp(session, phone)
            second_code = otp_service.create_otp(session, phone)
            records = session.exec(
                select(OTP).where(OTP.phone_number == phone).order_by(OTP.id)
            ).all()
            if len(records) != 2 or not records[0].is_used or records[1].is_used:
                log("A replacement OTP did not invalidate the older record.", "ERROR")
                return False
            if not otp_service.verify_otp(session, phone, second_code):
                log("A newly issued OTP was rejected.", "ERROR")
                return False
            if otp_service.verify_otp(session, phone, second_code):
                log("An OTP was accepted more than once.", "ERROR")
                return False
            if otp_service.verify_otp(session, phone, "000000"):
                log("An invalid OTP was accepted.", "ERROR")
                return False
            # Keep this assertion meaningful outside demo mode as well.
            if first_code != second_code and otp_service.verify_otp(session, phone, first_code):
                log("A superseded OTP was accepted.", "ERROR")
                return False
            log("OTP invalidation and single-use checks passed", "SUCCESS")
            return True
        finally:
            session.execute(delete(OTP).where(OTP.phone_number == phone))
            session.commit()
            session.close()
    except Exception as exc:
        log(f"OTP service check failed: {exc}", "ERROR")
        return False


def test_sms_configuration() -> bool:
    """Check SMS configuration without sending an external message."""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if sid and token:
        log("Twilio credentials are configured; send tests remain opt-in.", "SUCCESS")
    else:
        log("Twilio credentials are not configured; SMS demo mode is available.", "WARNING")
    return True


def test_security_module() -> bool:
    try:
        from core.security import create_access_token, verify_token

        token = create_access_token({"sub": "123"})
        if verify_token(token) != 123 or verify_token("invalid.token.here") is not None:
            log("JWT validation returned an unexpected result.", "ERROR")
            return False
        log("JWT creation and validation work", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Security check failed: {exc}", "ERROR")
        return False


def test_shop_categories() -> bool:
    try:
        from core.shop_categories import normalise_category, validate_category

        checks = {
            "Kirana": "Kirana",
            "kirana": "Kirana",
            "Dairy": "Dairy",
            "stationary": "Stationery",
            "Medical": "Pharmacy",
        }
        if any(validate_category(value) != expected for value, expected in checks.items()):
            log("Shop category validation returned an unexpected value.", "ERROR")
            return False
        if normalise_category("InvalidCategory") is not None:
            log("Invalid category unexpectedly received a namespace.", "ERROR")
            return False
        try:
            validate_category("")
            log("Blank category unexpectedly passed validation.", "ERROR")
            return False
        except ValueError:
            pass
        log("Shop category validation works", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Category check failed: {exc}", "ERROR")
        return False


def test_pipeline_config() -> bool:
    try:
        from pipeline.config import config

        valid = (
            config.embedding.dimension == 768
            and bool(config.embedding.model)
            and bool(config.llm.primary_model)
            and bool(config.llm.fallback_models)
            and config.retrieval.item_top_k > 0
        )
        if not valid:
            log("Pipeline configuration is incomplete.", "ERROR")
            return False
        log("Pipeline configuration is valid", "SUCCESS")
        return True
    except Exception as exc:
        log(f"Pipeline configuration check failed: {exc}", "ERROR")
        return False


def main() -> bool:
    results = {
        "otp_service": test_otp_service(),
        "sms_configuration": test_sms_configuration(),
        "security": test_security_module(),
        "categories": test_shop_categories(),
        "pipeline_config": test_pipeline_config(),
    }
    print(f"\nTotal: {sum(results.values())}/{len(results)} passed")
    return all(results.values())


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
