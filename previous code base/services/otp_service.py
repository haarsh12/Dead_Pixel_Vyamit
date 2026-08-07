import logging
import os
import random
import string
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.db.models import OTP

logger = logging.getLogger(__name__)

# Set OTP_DEMO_MODE=true only for local/testing; never in production.
_OTP_DEMO = os.getenv("OTP_DEMO_MODE", "").lower() in ("1", "true", "yes")
# Only for emergency debugging; keep false on Render.
_LOG_OTP_CODES = os.getenv("LOG_OTP_CODES", "").lower() in ("1", "true", "yes")


class OTPService:
    def generate_otp(self) -> str:
        """Return a 6-digit OTP. Random by default; fixed 112233 only if OTP_DEMO_MODE=true."""
        if _OTP_DEMO:
            return "112233"
        return "".join(random.choices(string.digits, k=6))

    def create_otp(self, session: Session, phone_number: str) -> str:
        """Generates OTP, saves to DB, and returns it."""

        clean_phone = phone_number.strip()
        code = self.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        otp_record = OTP(
            phone_number=clean_phone,
            otp_code=code,
            expires_at=expires_at,
            is_used=False,
        )

        session.add(otp_record)
        session.commit()
        session.refresh(otp_record)

        tail = clean_phone[-4:] if len(clean_phone) >= 4 else "****"
        logger.info("OTP issued for phone ending %s", tail)
        if _LOG_OTP_CODES:
            logger.warning("LOG_OTP_CODES is enabled; OTP value logged for debugging only.")
            logger.warning("OTP code (debug): %s", code)

        return code

    def verify_otp(self, session: Session, phone_number: str, code: str) -> bool:
        """Checks if the OTP is valid and not expired."""

        clean_phone = phone_number.strip()
        tail = clean_phone[-4:] if len(clean_phone) >= 4 else "****"
        logger.info("OTP verification attempt for phone ending %s", tail)

        statement = select(OTP).where(
            OTP.phone_number == clean_phone,
            OTP.otp_code == code,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow(),
        )
        result = session.exec(statement).first()

        if not result:
            logger.warning("OTP verification failed for phone ending %s", tail)
            return False

        result.is_used = True
        session.add(result)
        session.commit()

        logger.info("OTP verification succeeded for phone ending %s", tail)

        return True
