from pydantic import BaseModel
from typing import Optional, List

# 1. Login/OTP Request
class OTPRequest(BaseModel):
    phone_number: str
    is_login: bool = True

# 2. Verification Request
class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str
    # Optional fields for Registration
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    shop_category: Optional[str] = None  # Required when creating a new account

# 3. Token Response (Updated to include phone2)
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    is_new_user: bool
    # User profile data
    user_id: int
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    phone2: Optional[str] = None  # NEW: Added phone2
    shop_category: Optional[str] = "General"

# 4. Update Profile Request
class UpdateProfileRequest(BaseModel):
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    phone2: Optional[str] = None
    shop_category: Optional[str] = None

# 5. Item Schemas - MODIFIED TO SUPPORT NAMES ARRAY
class ItemBase(BaseModel):
    names: List[str]  # CHANGED: Now accepts array like ["Rice", "Chawal", "चावल"]
    price: float
    unit: str
    category: Optional[str] = "General"

class ItemCreate(ItemBase):
    id: str  # ADDED: Frontend sends the master list ID

class ItemUpdate(ItemBase):
    """Schema for updating existing items"""
    pass

class ItemResponse(ItemBase):
    id: str  # master_id - frontend identifier (e.g. "101", "FB1")
    owner_id: int
    master_id: str