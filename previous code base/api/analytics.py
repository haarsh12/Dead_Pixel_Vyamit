from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, func, and_
from datetime import datetime, timedelta
from app.db.database import get_session
from app.db.models import Bill, SaleItem, Item
from app.api.items import get_current_user
from app.utils.debug_logger import DebugLogger
import json
import time

router = APIRouter()
analytics_logger = DebugLogger("ANALYTICS")

class BillCreate(BaseModel):
    total_amount: float
    items: List[Dict[str, Any]]
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    payment_method: str = "cash"

@router.post("/bills")
def create_bill(
    bill_data: BillCreate,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """Save a new bill"""
    analytics_logger.section(f"CREATE BILL - User {user_id}")
    start_time = time.time()
    
    try:
        analytics_logger.info(f"Total Amount: ₹{bill_data.total_amount}")
        analytics_logger.info(f"Items Count: {len(bill_data.items)}")
        analytics_logger.info(f"Customer: {bill_data.customer_name or 'N/A'}")
        analytics_logger.info(f"Payment: {bill_data.payment_method}")
        
        # Log items
        analytics_logger.subsection("BILL ITEMS")
        for i, item in enumerate(bill_data.items[:10], 1):
            analytics_logger.debug(f"  {i}. {item.get('name')} - {item.get('qty_display')} @ ₹{item.get('rate')} = ₹{item.get('total')}")
        
        # Create bill
        bill = Bill(
            owner_id=user_id,
            total_amount=bill_data.total_amount,
            total_items=len(bill_data.items),
            items_json=json.dumps(bill_data.items),
            customer_phone=bill_data.customer_phone,
            customer_name=bill_data.customer_name,
            payment_method=bill_data.payment_method,
            bill_date=datetime.utcnow()
        )
        
        session.add(bill)
        session.flush()  # Get bill ID
        
        analytics_logger.success(f"Bill created with ID: {bill.id}")
        
        # Create sale items for analytics
        current_hour = datetime.utcnow().hour
        
        for item in bill_data.items:
            sale_item = SaleItem(
                owner_id=user_id,
                bill_id=bill.id,
                item_name=item.get('name', ''),
                item_category=item.get('category', 'Other'),
                quantity=item.get('quantity', 0),
                unit=item.get('unit', ''),
                price_per_unit=item.get('price', 0),
                total_price=item.get('total', 0),
                sale_date=datetime.utcnow(),
                hour_of_day=current_hour
            )
            session.add(sale_item)
        
        session.commit()
        session.refresh(bill)
        
        return {
            "success": True,
            "bill_id": bill.id,
            "message": "Bill saved successfully"
        }
        
    except Exception as e:
        session.rollback()
        print(f"Error saving bill: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bills")
def get_bills(
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """Get bill history"""
    statement = select(Bill).where(
        Bill.owner_id == user_id
    ).order_by(Bill.bill_date.desc()).offset(offset).limit(limit)
    
    bills = session.exec(statement).all()
    
    return {
        "success": True,
        "bills": [
            {
                "id": bill.id,
                "total_amount": bill.total_amount,
                "total_items": bill.total_items,
                "items": json.loads(bill.items_json),
                "customer_phone": bill.customer_phone,
                "customer_name": bill.customer_name,
                "payment_method": bill.payment_method,
                "bill_date": bill.bill_date.isoformat(),
                "created_at": bill.created_at.isoformat()
            }
            for bill in bills
        ]
    }

@router.get("/dashboard")
def get_dashboard(
    days: int = 30,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """Get dashboard analytics"""
    try:
        # Date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Total revenue
        revenue_stmt = select(func.sum(Bill.total_amount)).where(
            and_(
                Bill.owner_id == user_id,
                Bill.bill_date >= start_date
            )
        )
        total_revenue = session.exec(revenue_stmt).first() or 0.0
        
        # Total bills
        bills_stmt = select(func.count(Bill.id)).where(
            and_(
                Bill.owner_id == user_id,
                Bill.bill_date >= start_date
            )
        )
        total_bills = session.exec(bills_stmt).first() or 0
        
        # Average bill value
        avg_bill_value = total_revenue / total_bills if total_bills > 0 else 0.0
        
        # Total inventory items
        inventory_stmt = select(func.count(Item.id)).where(Item.owner_id == user_id)
        total_inventory = session.exec(inventory_stmt).first() or 0
        
        # Top selling items
        top_items_stmt = select(
            SaleItem.item_name,
            SaleItem.unit,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.count(SaleItem.id).label('times_sold')
        ).where(
            and_(
                SaleItem.owner_id == user_id,
                SaleItem.sale_date >= start_date
            )
        ).group_by(SaleItem.item_name, SaleItem.unit).order_by(
            func.sum(SaleItem.quantity).desc()
        ).limit(5)
        
        top_items = session.exec(top_items_stmt).all()
        
        # Category wise sales (for pie chart)
        category_stmt = select(
            SaleItem.item_category,
            func.sum(SaleItem.total_price).label('total_sales'),
            func.sum(SaleItem.quantity).label('total_quantity')
        ).where(
            and_(
                SaleItem.owner_id == user_id,
                SaleItem.sale_date >= start_date
            )
        ).group_by(SaleItem.item_category)
        
        categories = session.exec(category_stmt).all()
        
        # Peak hour sales
        peak_hours_stmt = select(
            SaleItem.hour_of_day,
            func.count(SaleItem.id).label('sales_count'),
            func.sum(SaleItem.total_price).label('total_sales')
        ).where(
            and_(
                SaleItem.owner_id == user_id,
                SaleItem.sale_date >= start_date
            )
        ).group_by(SaleItem.hour_of_day).order_by(SaleItem.hour_of_day)
        
        peak_hours = session.exec(peak_hours_stmt).all()
        
        # Peak day of week
        day_stmt = select(
            func.extract('dow', Bill.bill_date).label('day_of_week'),
            func.count(Bill.id).label('bill_count'),
            func.sum(Bill.total_amount).label('total_sales')
        ).where(
            and_(
                Bill.owner_id == user_id,
                Bill.bill_date >= start_date
            )
        ).group_by('day_of_week').order_by(func.sum(Bill.total_amount).desc())
        
        days_data = session.exec(day_stmt).all()
        peak_day = days_data[0] if days_data else None
        
        # Day names
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        return {
            "success": True,
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_bills": total_bills,
                "average_bill_value": round(avg_bill_value, 2),
                "total_inventory_items": total_inventory
            },
            "top_selling_items": [
                {
                    "name": item[0],
                    "unit": item[1],
                    "quantity": float(item[2]),
                    "times_sold": item[3]
                }
                for item in top_items
            ],
            "category_breakdown": [
                {
                    "category": cat[0],
                    "total_sales": float(cat[1]),
                    "quantity": float(cat[2]),
                    "percentage": round((float(cat[1]) / total_revenue * 100) if total_revenue > 0 else 0, 1)
                }
                for cat in categories
            ],
            "peak_hours": [
                {
                    "hour": int(hour[0]),
                    "sales_count": hour[1],
                    "total_sales": float(hour[2])
                }
                for hour in peak_hours
            ],
            "peak_day": {
                "day": day_names[int(peak_day[0])] if peak_day else "N/A",
                "bill_count": peak_day[1] if peak_day else 0,
                "total_sales": float(peak_day[2]) if peak_day else 0.0
            } if peak_day else None
        }
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
