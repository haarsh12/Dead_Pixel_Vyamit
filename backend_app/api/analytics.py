"""
Analytics API - Business Insights and Bill Management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
from db.database import get_session
from core.shop_categories import stored_category
from db.models import Bill, SaleItem, Item, User
from db.schemas import BillCreate, BillResponse
from core.security import get_current_user
from services.customer_service import record_customer_purchase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/bills", response_model=Dict[str, Any])
def create_bill(
    bill_data: BillCreate,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Save a new bill and create sale items for analytics"""
    try:
        for item in bill_data.items:
            expected_line_total = round(item.quantity * item.price, 2)
            if abs(expected_line_total - item.total) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"total for '{item.name}' must equal quantity multiplied by price",
                )
        calculated_total = round(sum(item.total for item in bill_data.items), 2)
        if abs(calculated_total - bill_data.total_amount) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="total_amount must equal the sum of item totals",
            )
        logger.info("Creating bill for user=%s items=%s", user_id, len(bill_data.items))

        # Preserve category analytics for known inventory items instead of
        # assigning every sale to the catch-all General category.
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is unavailable",
            )
        inventory_scope = stored_category(user.shop_category)
        category_by_name = {}
        for inventory_item in session.exec(
            select(Item).where(
                Item.owner_id == user_id,
                Item.shop_category == inventory_scope,
            )
        ).all():
            try:
                names = json.loads(inventory_item.names)
            except (TypeError, json.JSONDecodeError):
                names = [inventory_item.names]
            for name in names:
                category_by_name[str(name).strip().casefold()] = inventory_item.category or "General"
        
        # Create bill
        bill = Bill(
            owner_id=user_id,
            shop_category=inventory_scope,
            total_amount=calculated_total,
            total_items=len(bill_data.items),
            items_json=json.dumps([item.model_dump() for item in bill_data.items]),
            customer_phone=bill_data.customer_phone,
            customer_name=bill_data.customer_name,
            payment_method=bill_data.payment_method,
            bill_date=datetime.utcnow()
        )
        
        session.add(bill)
        session.flush()
        
        # Create sale items for analytics
        current_hour = datetime.utcnow().hour
        
        for item in bill_data.items:
            sale_item = SaleItem(
                owner_id=user_id,
                bill_id=bill.id,
                shop_category=inventory_scope,
                item_name=item.name,
                item_category=category_by_name.get(item.name.strip().casefold(), "General"),
                quantity=item.quantity,
                unit=item.unit,
                price_per_unit=item.price,
                total_price=item.total,
                sale_date=datetime.utcnow(),
                hour_of_day=current_hour
            )
            session.add(sale_item)

        record_customer_purchase(
            session,
            owner_id=user_id,
            phone_number=bill_data.customer_phone,
            name=bill_data.customer_name,
            amount=calculated_total,
            purchased_at=bill.bill_date,
        )
        
        session.commit()
        session.refresh(bill)
        
        logger.info(f"Bill {bill.id} created successfully")
        
        return {
            "success": True,
            "bill_id": bill.id,
            "message": "Bill saved successfully"
        }
        
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create bill: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save bill"
        )


@router.get("/bills")
def get_bills(
    limit: int = 50,
    offset: int = 0,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get bill history"""
    try:
        statement = (
            select(Bill)
            .where(Bill.owner_id == user_id)
            .order_by(Bill.bill_date.desc())
            .offset(offset)
            .limit(limit)
        )
        
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
            ],
            "total": len(bills),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch bills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch bills"
        )


@router.get("/dashboard")
def get_dashboard(
    days: int = 30,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get comprehensive dashboard analytics"""
    try:
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
        top_items_stmt = (
            select(
                SaleItem.item_name,
                SaleItem.unit,
                func.sum(SaleItem.quantity).label('total_quantity'),
                func.sum(SaleItem.total_price).label('total_revenue'),
                func.count(SaleItem.id).label('times_sold')
            )
            .where(
                and_(
                    SaleItem.owner_id == user_id,
                    SaleItem.sale_date >= start_date
                )
            )
            .group_by(SaleItem.item_name, SaleItem.unit)
            .order_by(func.sum(SaleItem.total_price).desc())
            .limit(10)
        )
        
        top_items = session.exec(top_items_stmt).all()
        
        # Category breakdown
        category_stmt = (
            select(
                SaleItem.item_category,
                func.sum(SaleItem.total_price).label('total_sales'),
                func.sum(SaleItem.quantity).label('total_quantity')
            )
            .where(
                and_(
                    SaleItem.owner_id == user_id,
                    SaleItem.sale_date >= start_date
                )
            )
            .group_by(SaleItem.item_category)
            .order_by(func.sum(SaleItem.total_price).desc())
        )
        
        categories = session.exec(category_stmt).all()
        
        # Peak hours
        peak_hours_stmt = (
            select(
                SaleItem.hour_of_day,
                func.count(SaleItem.id).label('sales_count'),
                func.sum(SaleItem.total_price).label('total_sales')
            )
            .where(
                and_(
                    SaleItem.owner_id == user_id,
                    SaleItem.sale_date >= start_date
                )
            )
            .group_by(SaleItem.hour_of_day)
            .order_by(SaleItem.hour_of_day)
        )
        
        peak_hours = session.exec(peak_hours_stmt).all()
        
        # Peak day of week
        day_stmt = (
            select(
                func.extract('dow', Bill.bill_date).label('day_of_week'),
                func.count(Bill.id).label('bill_count'),
                func.sum(Bill.total_amount).label('total_sales')
            )
            .where(
                and_(
                    Bill.owner_id == user_id,
                    Bill.bill_date >= start_date
                )
            )
            .group_by('day_of_week')
            .order_by(func.sum(Bill.total_amount).desc())
        )
        
        days_data = session.exec(day_stmt).all()
        peak_day = days_data[0] if days_data else None
        
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        return {
            "success": True,
            "period_days": days,
            "summary": {
                "total_revenue": round(float(total_revenue), 2),
                "total_bills": total_bills,
                "average_bill_value": round(avg_bill_value, 2),
                "total_inventory_items": total_inventory
            },
            "top_selling_items": [
                {
                    "name": item[0],
                    "unit": item[1],
                    "quantity": float(item[2]),
                    "revenue": float(item[3]),
                    "times_sold": item[4]
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
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard data"
        )


@router.get("/overview")
def get_overview(
    days: int = 7,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Quick overview for home screen"""
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Revenue
        revenue = session.exec(
            select(func.sum(Bill.total_amount)).where(
                and_(Bill.owner_id == user_id, Bill.bill_date >= start_date)
            )
        ).first() or 0.0
        
        # Bill count
        bill_count = session.exec(
            select(func.count(Bill.id)).where(
                and_(Bill.owner_id == user_id, Bill.bill_date >= start_date)
            )
        ).first() or 0
        
        return {
            "success": True,
            "period_days": days,
            "total_revenue": round(float(revenue), 2),
            "total_bills": bill_count,
            "average_bill": round(float(revenue) / bill_count if bill_count > 0 else 0, 2)
        }
        
    except Exception as e:
        logger.error(f"Overview error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch overview"
        )
