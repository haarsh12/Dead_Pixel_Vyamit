"""
Authentication API Routes
OTP-based login and registration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from db.database import get_session
from db.models import User
from db.schemas import (
    OTPRequest,
    VerifyOTPRequest,
    TokenResponse,
    UpdateProfileRequest
)
from core.security import create_access_token, get_current_user
from core.shop_categories import validate_category
from services.otp_service import otp_service
from services.sms_service import sms_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/send-otp", status_code=status.HTTP_200_OK)
def send_otp(
    request: OTPRequest,
    session: Session = Depends(get_session)
):
    """
    Send OTP for login or registration
    
    - **phone_number**: User's phone number
    - **is_login**: True for login, False for new registration
    """
    try:
        phone = request.phone_number.strip()
        
        # Check if user exists
        statement = select(User).where(User.phone_number == phone)
        user = session.exec(statement).first()
        
        if request.is_login and not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not registered. Please sign up first."
            )
        
        if not request.is_login and user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered. Please login instead."
            )
        
        # Generate and save OTP
        otp_code = otp_service.create_otp(session, phone)
        
        # Send OTP via SMS
        sms_service.send_otp(phone, otp_code)
        
        return {
            "success": True,
            "message": "OTP sent successfully",
            "phone_number": phone
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again."
        )


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    request: VerifyOTPRequest,
    session: Session = Depends(get_session)
):
    """
    Verify OTP and login/register user
    
    For new users, provide shop details:
    - **shop_name**: Name of the shop
    - **owner_name**: Owner's name
    - **address**: Shop address
    - **shop_category**: Category (Kirana, Dairy, etc.)
    """
    try:
        phone = request.phone_number.strip()
        
        # Verify OTP
        is_valid = otp_service.verify_otp(session, phone, request.otp_code)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP"
            )
        
        # Check if user exists
        statement = select(User).where(User.phone_number == phone)
        user = session.exec(statement).first()
        
        is_new_user = False
        
        if not user:
            # Create new user
            if not request.shop_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="shop_category is required for new users"
                )
            
            user = User(
                phone_number=phone,
                shop_name=request.shop_name,
                owner_name=request.owner_name,
                address=request.address,
                shop_category=validate_category(request.shop_category)
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            is_new_user = True
            logger.info(f"New user registered: {user.id}")
        
        # Generate JWT token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            is_new_user=is_new_user,
            user_id=user.id,
            shop_name=user.shop_name,
            owner_name=user.owner_name,
            address=user.address,
            phone2=user.phone2,
            shop_category=user.shop_category
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Verification failed. Please try again."
        )


@router.get("/profile", status_code=status.HTTP_200_OK)
def get_profile(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get current user profile"""
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user_id": user.id,
        "phone_number": user.phone_number,
        "shop_name": user.shop_name,
        "owner_name": user.owner_name,
        "address": user.address,
        "phone2": user.phone2,
        "shop_category": user.shop_category,
        "created_at": user.created_at,
        "is_active": user.is_active
    }


@router.put("/profile", status_code=status.HTTP_200_OK)
def update_profile(
    request: UpdateProfileRequest,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update user profile"""
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if provided
    if request.shop_name is not None:
        user.shop_name = request.shop_name
    if request.owner_name is not None:
        user.owner_name = request.owner_name
    if request.address is not None:
        user.address = request.address
    if request.phone2 is not None:
        user.phone2 = request.phone2
    if request.shop_category is not None:
        user.shop_category = validate_category(request.shop_category)
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    logger.info(f"Profile updated for user {user.id}")
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "user": {
            "user_id": user.id,
            "shop_name": user.shop_name,
            "owner_name": user.owner_name,
            "address": user.address,
            "phone2": user.phone2,
            "shop_category": user.shop_category
        }
    }
