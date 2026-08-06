"""
Pydantic Schemas for API Request/Response
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---- Authentication Schemas ----

class OTPRequest(BaseModel):
    """Request OTP for login/register"""
    phone_number: str = Field(..., min_length=10, max_length=15)
    is_login: bool = True


class VerifyOTPRequest(BaseModel):
    """Verify OTP and optionally register"""
    phone_number: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=6, max_length=6)
    
    # Required for new user registration
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    shop_category: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
    
    # User profile
    user_id: int
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    phone2: Optional[str] = None
    shop_category: str = "General"


class UpdateProfileRequest(BaseModel):
    """Update user profile"""
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    phone2: Optional[str] = None
    shop_category: Optional[str] = None


# ---- Item Schemas ----

class ItemBase(BaseModel):
    """Base item schema"""
    names: List[str] = Field(..., min_items=1)
    price: float = Field(..., ge=0)
    unit: str
    category: Optional[str] = "General"


class ItemCreate(ItemBase):
    """Create new item"""
    id: str  # master_id from frontend


class ItemUpdate(ItemBase):
    """Update existing item"""
    pass


class ItemResponse(ItemBase):
    """Item response"""
    id: str  # master_id
    owner_id: int
    master_id: str
    created_at: datetime
    updated_at: datetime


# ---- Bill Schemas ----

class BillItem(BaseModel):
    """Individual item in a bill"""
    name: str
    quantity: float
    unit: str
    price: float
    total: float


class BillCreate(BaseModel):
    """Create new bill"""
    items: List[BillItem]
    total_amount: float
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    payment_method: Optional[str] = "cash"


class BillResponse(BaseModel):
    """Bill response"""
    id: int
    owner_id: int
    total_amount: float
    total_items: int
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    payment_method: str
    bill_date: datetime
    items: List[BillItem]


# ---- Analytics Schemas ----

class AnalyticsPeriod(BaseModel):
    """Analytics time period"""
    days: Optional[int] = 30


class TopItem(BaseModel):
    """Top selling item"""
    name: str
    category: str
    total_quantity: float
    total_revenue: float
    sale_count: int


class PeakHour(BaseModel):
    """Peak sales hour"""
    hour: int
    total_sales: float
    bill_count: int


class AnalyticsResponse(BaseModel):
    """Complete analytics response"""
    period_days: int
    total_revenue: float
    total_bills: int
    average_bill_value: float
    top_items: List[TopItem]
    peak_hours: List[PeakHour]
    category_breakdown: dict


# ---- RAG/Voice Schemas ----

class VoiceQueryRequest(BaseModel):
    """Voice query request"""
    query: str
    include_analytics: bool = True
    include_customers: bool = True


class VoiceQueryResponse(BaseModel):
    """Voice query response"""
    type: str  # BILL, QUERY, ERROR
    items: List[dict]
    msg: str
    should_stop: bool
    metadata: Optional[dict] = None
