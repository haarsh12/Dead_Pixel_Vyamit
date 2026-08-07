from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# 1. Base Model (Fields every table should have)
class TimestampModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# 2. User Model (The Shop Owner)
class User(TimestampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(index=True, unique=True)  # This is phone1 - READ ONLY
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    phone2: Optional[str] = None  # Secondary phone number (EDITABLE)
    # Kirana, Dairy, Hardware, General, Stationary, Clothing, Doctor, Other
    shop_category: str = Field(default="General", index=True)
    is_active: bool = Field(default=True)
    role: str = Field(default="owner")

# 3. OTP Model (Temporary codes for login)
class OTP(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(index=True)
    otp_code: str
    expires_at: datetime
    is_used: bool = Field(default=False)

# 4. Item Model (Your Inventory) - MODIFIED FOR MULTI-LANGUAGE SUPPORT
class Item(TimestampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # NEW: Store the master list ID from frontend (e.g., "101", "202", "FB1")
    # This allows us to match items between frontend and backend uniquely
    master_id: str = Field(index=True)
    
    # NEW: Store all names as a JSON string array
    # Example: '["Chawal", "Rice", "चावल", "तांदूळ"]'
    # This replaces the old 'name' and 'hindi_name' fields
    names: str  # JSON string containing array of names
    
    category: str = Field(index=True)     # e.g., "Anaaj", "Dal", "Masale"
    price: float                          # e.g., 0.0 (unset) or 45.0 (set by user)
    unit: str                             # e.g., "kg", "litre", "plate"
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

# 5. Bill Model (Saved Bills)
class Bill(TimestampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    
    # Bill details
    total_amount: float
    total_items: int
    
    # Bill items stored as JSON string
    # Example: '[{"name":"Chawal","quantity":2,"unit":"kg","price":50,"total":100}]'
    items_json: str
    
    # Optional customer info
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    
    # Metadata
    bill_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    payment_method: Optional[str] = "cash"  # cash, upi, card

# 6. Sale Item Model (Individual items sold - for analytics)
class SaleItem(TimestampModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    bill_id: int = Field(foreign_key="bill.id", index=True)
    
    # Item details
    item_name: str
    item_category: str = Field(index=True)
    quantity: float
    unit: str
    price_per_unit: float
    total_price: float
    
    # Sale metadata
    sale_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    hour_of_day: int = Field(index=True)  # 0-23 for peak hour analysis