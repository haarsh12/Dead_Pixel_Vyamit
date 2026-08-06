"""
Database Models
Clean, secure, and optimized for pgvector
"""
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Index
from pgvector.sqlalchemy import Vector
from typing import Optional
from datetime import datetime


class TimestampModel(SQLModel):
    """Base model with timestamps for all tables"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(TimestampModel, table=True):
    """Shop owner/user model"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(index=True, unique=True)  # Primary phone (read-only)
    shop_name: Optional[str] = None
    owner_name: Optional[str] = None
    address: Optional[str] = None
    phone2: Optional[str] = None  # Secondary phone (editable)
    shop_category: str = Field(default="General", index=True)
    is_active: bool = Field(default=True)
    role: str = Field(default="owner")


class OTP(SQLModel, table=True):
    """OTP codes for authentication"""
    __tablename__ = "otps"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str = Field(index=True)
    otp_code: str
    expires_at: datetime
    is_used: bool = Field(default=False)


class Item(TimestampModel, table=True):
    """Inventory items with vector embeddings.

    ``shop_category`` is the inventory namespace.  It is deliberately
    separate from ``category``, which remains the product group shown inside
    the inventory UI (for example, ``Masale`` or ``Plumbing``).
    """
    __tablename__ = "items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    master_id: str = Field(index=True)  # Frontend master list ID
    names: str  # JSON array of multi-language names
    category: str = Field(index=True)
    shop_category: str = Field(default="General", index=True, max_length=60)
    price: float
    unit: str
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    
    # Vector embedding for semantic search (768D for Gemini)
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(Vector(768))
    )
    
    __table_args__ = (
        Index(
            "idx_items_owner_shop_category",
            "owner_id",
            "shop_category",
        ),
        Index(
            "idx_items_owner_shop_category_master",
            "owner_id",
            "shop_category",
            "master_id",
        ),
        Index(
            "idx_items_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )


class Bill(TimestampModel, table=True):
    """Saved bills shared by a user, with an immutable category snapshot."""
    __tablename__ = "bills"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    # Dashboard and bill history aggregate all categories, while AI context
    # filters this snapshot to prevent cross-category sales context.
    shop_category: str = Field(default="General", index=True, max_length=60)
    
    # Bill details
    total_amount: float
    total_items: int
    items_json: str  # JSON array of bill items
    
    # Customer info
    customer_phone: Optional[str] = Field(default=None, index=True)
    customer_name: Optional[str] = None
    
    # Metadata
    bill_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    payment_method: Optional[str] = "cash"

    __table_args__ = (
        Index(
            "idx_bills_owner_shop_category_date",
            "owner_id",
            "shop_category",
            "bill_date",
        ),
    )


class SaleItem(TimestampModel, table=True):
    """Individual sale items for analytics and category-scoped AI context."""
    __tablename__ = "sale_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    bill_id: int = Field(foreign_key="bills.id", index=True)
    shop_category: str = Field(default="General", index=True, max_length=60)
    
    # Item details
    item_name: str
    item_category: str = Field(index=True)
    quantity: float
    unit: str
    price_per_unit: float
    total_price: float
    
    # Analytics
    sale_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    hour_of_day: int = Field(index=True)  # 0-23

    __table_args__ = (
        Index(
            "idx_sale_items_owner_shop_category_date",
            "owner_id",
            "shop_category",
            "sale_date",
        ),
    )


class Customer(TimestampModel, table=True):
    """Customer profiles with purchase history embeddings"""
    __tablename__ = "customers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    
    # Customer info
    phone_number: str = Field(index=True)
    name: Optional[str] = None
    
    # Purchase summary
    total_bills: int = Field(default=0)
    total_spent: float = Field(default=0.0)
    last_purchase_date: Optional[datetime] = None
    
    # Vector embedding for customer purchase patterns (768D)
    embedding: Optional[list] = Field(
        default=None,
        sa_column=Column(Vector(768))
    )
    
    __table_args__ = (
        Index(
            "idx_customers_owner_phone",
            "owner_id",
            "phone_number",
            unique=True
        ),
        Index(
            "idx_customers_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
    )
