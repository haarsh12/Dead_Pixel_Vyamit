"""
SMS Share API
Handles sending bills via Twilio SMS
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.sms_service import send_sms_bill

router = APIRouter()


class SMSShareRequest(BaseModel):
    mobile: str
    customer_name: str
    shop_name: str
    bill_items: List[Dict[str, Any]]
    total_amount: float
    date: str
    time: str


@router.post("/send-bill")
async def send_bill_via_sms(request: SMSShareRequest):
    """
    Send bill via Twilio SMS
    """
    
    try:
        print(f"📱 Sending SMS to: {request.mobile}")
        
        # Format bill text
        bill_text = _format_bill_text(
            shop_name=request.shop_name,
            customer_name=request.customer_name,
            date=request.date,
            time=request.time,
            items=request.bill_items,
            total=request.total_amount
        )
        
        # Send via Twilio
        result = send_sms_bill(
            to_number=request.mobile,
            message=bill_text
        )
        
        if result['success']:
            print(f"[OK] SMS sent successfully: {result['sid']}")
            return {
                "success": True,
                "message": "Bill sent via SMS",
                "sid": result['sid']
            }
        else:
            print(f"[ERROR] SMS failed: {result['error']}")
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        print(f"[ERROR] SMS share error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


def _format_bill_text(
    shop_name: str,
    customer_name: str,
    date: str,
    time: str,
    items: List[Dict[str, Any]],
    total: float
) -> str:
    """Format bill text with proper alignment"""
    
    def format_row(name: str, qty: str, rate: str, amount: str) -> str:
        """Format row with fixed-width columns"""
        name_pad = name[:15].ljust(15)
        qty_pad = qty[:6].ljust(6)
        rate_pad = rate[:7].ljust(7)
        amt_pad = amount.rjust(7)
        return f"{name_pad}{qty_pad}{rate_pad}{amt_pad}"
    
    buffer = []
    
    # Header
    buffer.append("🧾 SNAPBILL RECEIPT")
    buffer.append("")
    buffer.append(f"{shop_name.upper()}")
    buffer.append("Main Road, Sitabuldi, Nagpur")
    buffer.append("📞 9876543210")
    buffer.append("")
    buffer.append(f"Customer: {customer_name}")
    buffer.append(f"Date: {date}")
    buffer.append(f"Time: {time}")
    buffer.append("--------------------------------")
    
    # Column Headers
    buffer.append(format_row("Item", "Qty", "Rate", "Amt"))
    buffer.append("--------------------------------")
    
    # Items
    for item in items:
        name = item.get('name', item.get('en', 'Item'))
        qty_display = item.get('qty_display', item.get('qty', '1'))
        rate = str(int(item.get('rate', 0)))
        amount = str(int(item.get('total', 0)))
        
        buffer.append(format_row(name, qty_display, rate, amount))
    
    buffer.append("--------------------------------")
    buffer.append(f"TOTAL: ₹{int(total)}")
    buffer.append("--------------------------------")
    buffer.append("")
    buffer.append("🙏 Thank you! Visit Again")
    buffer.append("⚡ Powered by SnapBill")
    
    return "\n".join(buffer)
