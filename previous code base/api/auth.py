import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db.database import get_session
from app.db.models import User
from app.db.schemas import OTPRequest, VerifyOTPRequest, TokenResponse, UpdateProfileRequest
from app.core.shop_categories import (
    normalize_shop_category,
    validate_shop_category_required,
)
from app.services.otp_service import OTPService
from app.services.sms_service import SMSService
from app.core.security import create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
otp_service = OTPService()
sms_service = SMSService()

@router.post("/send-otp")
def send_otp(request: OTPRequest, session: Session = Depends(get_session)):
    """
    Smart OTP Sender:
    - If is_login=True: Fails if user NOT found.
    - If is_login=False (Register): Fails if user ALREADY exists.
    """
    # FIX 1: Sanitize Input (Remove spaces)
    clean_phone = request.phone_number.strip()
    if not clean_phone:
        raise HTTPException(status_code=400, detail="Phone number cannot be empty")

    # 1. Check if user exists in our Database
    statement = select(User).where(User.phone_number == clean_phone)
    existing_user = session.exec(statement).first()

    logger.debug(
        "send_otp is_login=%s user_exists=%s",
        request.is_login,
        existing_user is not None,
    )

    # 2. Logic for REGISTRATION (User wants to sign up)
    if not request.is_login:
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login user already exist"
            )
    
    # 3. Logic for LOGIN (User wants to sign in)
    else:
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Create account first"
            )

    # 4. If check passes, Generate and Save OTP
    otp_code = otp_service.create_otp(session, clean_phone)
    
    # 5. Send SMS
    sms_service.send_otp(clean_phone, otp_code)
    
    return {"message": "OTP sent successfully", "dev_hint": otp_code}

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(request: VerifyOTPRequest, session: Session = Depends(get_session)):
    """
    Verifies OTP and Logs in/Registers the user.
    Returns Token AND User Profile Details INCLUDING phone2.
    """
    # FIX 1: Sanitize Input
    clean_phone = request.phone_number.strip()

    # 1. Verify OTP
    is_valid = otp_service.verify_otp(session, clean_phone, request.otp_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid OTP"
        )
    
    # 2. Check DB
    statement = select(User).where(User.phone_number == clean_phone)
    user = session.exec(statement).first()
    
    is_new_user = False
    
    # 3. Create User if not exists (Registration Final Step)
    if not user:
        if not request.shop_name or not request.owner_name:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Shop Name and Owner Name are required for new registration"
            )
        try:
            category = validate_shop_category_required(request.shop_category)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
            
        is_new_user = True
        logger.debug("register: new user category=%s", category)
        
        user = User(
            phone_number=clean_phone,
            shop_name=request.shop_name,
            owner_name=request.owner_name,
            address=request.address,
            phone2=None,  # Initialize as None for new users
            shop_category=category,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        logger.debug("login: existing user_id=%s", user.id)
    
    # 4. Generate Token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    # 5. Return COMPLETE user profile including phone2 and shop_category
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_new_user": is_new_user,
        "user_id": user.id,
        "shop_name": user.shop_name,
        "owner_name": user.owner_name,
        "address": user.address,
        "phone2": user.phone2,  # IMPORTANT: Include phone2 in response
        "shop_category": getattr(user, "shop_category", None) or "General",
    }

@router.put("/update-profile", response_model=TokenResponse)
def update_profile(
    request: UpdateProfileRequest,
    session: Session = Depends(get_session),
    user_stub = Depends(get_current_user)
):
    """
    Updates user profile details.
    Only allows updating: shop_name, owner_name, address, phone2
    Phone1 (phone_number) is READ-ONLY as it's the account identifier.
    """
    # Fetch the actual user from database using the ID from token
    statement = select(User).where(User.id == user_stub.id)
    current_user = session.exec(statement).first()
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update allowed fields
    if request.shop_name is not None:
        current_user.shop_name = request.shop_name.strip()

    if request.owner_name is not None:
        current_user.owner_name = request.owner_name.strip()

    if request.address is not None:
        current_user.address = request.address.strip()

    if request.phone2 is not None:
        current_user.phone2 = request.phone2.strip()

    if request.shop_category is not None:
        normalized = normalize_shop_category(request.shop_category)
        if normalized is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid shop_category",
            )
        current_user.shop_category = normalized

    # Save changes to database
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    logger.info("profile updated user_id=%s", current_user.id)
    
    # Generate new token (optional, but ensures fresh data)
    access_token = create_access_token(data={"sub": str(current_user.id)})
    
    # Return updated user data including phone2
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_new_user": False,
        "user_id": current_user.id,
        "shop_name": current_user.shop_name,
        "owner_name": current_user.owner_name,
        "address": current_user.address,
        "phone2": current_user.phone2,  # IMPORTANT: Include phone2 in response
        "shop_category": getattr(current_user, "shop_category", None) or "General",
    }