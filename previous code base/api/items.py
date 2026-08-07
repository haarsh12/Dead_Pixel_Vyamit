from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.db.database import get_session
from app.db.models import Item
from app.db.schemas import ItemCreate, ItemUpdate, ItemResponse
from app.core.security import jwt, SECRET_KEY, ALGORITHM
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json

security = HTTPBearer()

router = APIRouter()

# Helper: Get current user from Token
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), session: Session = Depends(get_session)):
    token = credentials.credentials  # Extract the token string
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
            
        return int(user_id)
    except Exception as e:
        print(f"DEBUG: Token Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@router.post("/", response_model=ItemResponse)
def create_item(
    item: ItemCreate, 
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """
    Adds a new item to the user's inventory.
    MODIFIED: Now accepts 'names' array and 'id' from frontend
    """
    
    # Check if item already exists for this user
    statement = select(Item).where(
        Item.master_id == item.id,
        Item.owner_id == user_id
    )
    existing_item = session.exec(statement).first()
    
    if existing_item:
        # Item already exists, update it instead
        existing_item.names = json.dumps(item.names, ensure_ascii=False)
        existing_item.price = item.price
        existing_item.unit = item.unit
        existing_item.category = item.category
        
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)
        
        print(f"[OK] Updated existing item: {item.id}")
        
        return {
            "id": existing_item.master_id,  # Return master_id as id
            "names": item.names,
            "price": existing_item.price,
            "unit": existing_item.unit,
            "category": existing_item.category,
            "owner_id": existing_item.owner_id,
            "master_id": existing_item.master_id
        }
    
    # Create new item
    names_json = json.dumps(item.names, ensure_ascii=False)
    
    new_item = Item(
        master_id=item.id,
        names=names_json,
        category=item.category,
        price=item.price,
        unit=item.unit,
        owner_id=user_id
    )
    
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    
    print(f"[OK] Created new item: {item.id}")
    
    # Return with names as array
    return {
        "id": new_item.master_id,  # Return master_id as id
        "names": item.names,
        "price": new_item.price,
        "unit": new_item.unit,
        "category": new_item.category,
        "owner_id": new_item.owner_id,
        "master_id": new_item.master_id
    }

@router.get("/")
def get_items(
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """
    Gets ALL items belonging to the logged-in user.
    MODIFIED: Returns items as objects with 'names' array
    """
    try:
        statement = select(Item).where(Item.owner_id == user_id)
        items = session.exec(statement).all()
        
        # Convert items to response format
        response_items = []
        for item in items:
            try:
                names_array = json.loads(item.names) if item.names else []
                response_items.append({
                    "id": item.master_id,  # CRITICAL: Return master_id as id
                    "names": names_array,
                    "price": item.price,
                    "unit": item.unit,
                    "category": item.category,
                    "owner_id": item.owner_id,
                    "master_id": item.master_id
                })
            except Exception as e:
                print(f"[ERROR] Error processing item {item.id}: {e}")
                continue
        
        print(f"[INFO] Fetched {len(response_items)} items for user {user_id}")
        return response_items
    except Exception as e:
        print(f"[ERROR] Error in get_items: {e}")
        # Return empty list instead of error to prevent frontend crash
        return []

@router.put("/{item_id}/", response_model=ItemResponse)
def update_item(
    item_id: str,  # This is the master_id from frontend
    item: ItemUpdate,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """
    Updates an existing item's price.
    NEW ENDPOINT: Allows updating item prices
    """
    
    # Find item by master_id and owner_id
    statement = select(Item).where(
        Item.master_id == item_id,
        Item.owner_id == user_id
    )
    existing_item = session.exec(statement).first()
    
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update fields
    existing_item.names = json.dumps(item.names, ensure_ascii=False)
    existing_item.price = item.price
    existing_item.unit = item.unit
    existing_item.category = item.category
    
    session.add(existing_item)
    session.commit()
    session.refresh(existing_item)
    
    print(f"[OK] Updated item: {item_id}")
    
    # Return updated item
    return {
        "id": existing_item.master_id,
        "names": item.names,
        "price": existing_item.price,
        "unit": existing_item.unit,
        "category": existing_item.category,
        "owner_id": existing_item.owner_id,
        "master_id": existing_item.master_id
    }

@router.delete("/{item_id}/")
def delete_item(
    item_id: str,  # This is the master_id from frontend
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user)
):
    """
    Deletes an item from user's inventory.
    NEW ENDPOINT: Allows deleting items
    """
    
    # Find item by master_id and owner_id
    statement = select(Item).where(
        Item.master_id == item_id,
        Item.owner_id == user_id
    )
    existing_item = session.exec(statement).first()
    
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    session.delete(existing_item)
    session.commit()
    
    print(f"[OK] Deleted item: {item_id}")
    
    return {"message": "Item deleted successfully"}