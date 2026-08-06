"""
Items API - Inventory Management
Handles CRUD operations for shop inventory
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
import json
import logging
from datetime import datetime
from db.database import get_session
from db.models import Item
from db.schemas import ItemCreate, ItemUpdate, ItemResponse
from core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ItemResponse)
def create_item(
    item: ItemCreate,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Create or update item in inventory
    If item with same master_id exists, it will be updated
    """
    try:
        # Check if item already exists
        statement = select(Item).where(
            Item.master_id == item.id,
            Item.owner_id == user_id
        )
        existing_item = session.exec(statement).first()
        
        if existing_item:
            # Update existing item
            existing_item.names = json.dumps(item.names, ensure_ascii=False)
            existing_item.price = item.price
            existing_item.unit = item.unit
            existing_item.category = item.category
            existing_item.updated_at = datetime.utcnow()
            
            session.add(existing_item)
            session.commit()
            session.refresh(existing_item)
            
            logger.info(f"Updated item {item.id} for user {user_id}")
            
            return ItemResponse(
                id=existing_item.master_id,
                names=item.names,
                price=existing_item.price,
                unit=existing_item.unit,
                category=existing_item.category,
                owner_id=existing_item.owner_id,
                master_id=existing_item.master_id,
                created_at=existing_item.created_at,
                updated_at=existing_item.updated_at
            )
        
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
        
        logger.info(f"Created item {item.id} for user {user_id}")
        
        return ItemResponse(
            id=new_item.master_id,
            names=item.names,
            price=new_item.price,
            unit=new_item.unit,
            category=new_item.category,
            owner_id=new_item.owner_id,
            master_id=new_item.master_id,
            created_at=new_item.created_at,
            updated_at=new_item.updated_at
        )
        
    except Exception as e:
        logger.error(f"Failed to create/update item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save item"
        )


@router.get("/", response_model=List[ItemResponse])
def get_items(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all items for current user"""
    try:
        statement = select(Item).where(Item.owner_id == user_id)
        items = session.exec(statement).all()
        
        response_items = []
        for item in items:
            try:
                names_array = json.loads(item.names) if item.names else []
                response_items.append(
                    ItemResponse(
                        id=item.master_id,
                        names=names_array,
                        price=item.price,
                        unit=item.unit,
                        category=item.category,
                        owner_id=item.owner_id,
                        master_id=item.master_id,
                        created_at=item.created_at,
                        updated_at=item.updated_at
                    )
                )
            except Exception as e:
                logger.error(f"Error processing item {item.id}: {e}")
                continue
        
        logger.info(f"Fetched {len(response_items)} items for user {user_id}")
        return response_items
        
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        return []  # Return empty list to prevent frontend crash


@router.put("/{item_id}", response_model=ItemResponse)
@router.put("/{item_id}/", response_model=ItemResponse, include_in_schema=False)
def update_item(
    item_id: str,
    item: ItemUpdate,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update existing item"""
    try:
        statement = select(Item).where(
            Item.master_id == item_id,
            Item.owner_id == user_id
        )
        existing_item = session.exec(statement).first()
        
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Update fields
        existing_item.names = json.dumps(item.names, ensure_ascii=False)
        existing_item.price = item.price
        existing_item.unit = item.unit
        existing_item.category = item.category
        existing_item.updated_at = datetime.utcnow()
        
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)
        
        logger.info(f"Updated item {item_id} for user {user_id}")
        
        return ItemResponse(
            id=existing_item.master_id,
            names=item.names,
            price=existing_item.price,
            unit=existing_item.unit,
            category=existing_item.category,
            owner_id=existing_item.owner_id,
            master_id=existing_item.master_id,
            created_at=existing_item.created_at,
            updated_at=existing_item.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item"
        )


@router.delete("/{item_id}")
@router.delete("/{item_id}/", include_in_schema=False)
def delete_item(
    item_id: str,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete item from inventory"""
    try:
        statement = select(Item).where(
            Item.master_id == item_id,
            Item.owner_id == user_id
        )
        existing_item = session.exec(statement).first()
        
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        session.delete(existing_item)
        session.commit()
        
        logger.info(f"Deleted item {item_id} for user {user_id}")
        
        return {"success": True, "message": "Item deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )


@router.post("/bulk-embed")
async def bulk_embed_items(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Generate embeddings for all user items"""
    try:
        from pipeline.embedding_pipeline import embedding_pipeline
        
        statement = select(Item).where(Item.owner_id == user_id)
        items = session.exec(statement).all()
        
        if not items:
            return {
                "success": True,
                "message": "No items to embed",
                "total": 0,
                "updated": 0
            }
        
        # Prepare texts for batch embedding
        texts = []
        items_to_update = []
        
        for item in items:
            try:
                names = json.loads(item.names)
                # Combine all names for embedding
                text = " ".join(names) + f" {item.category}"
                texts.append(text)
                items_to_update.append(item)
            except Exception as e:
                logger.error(f"Error preparing item {item.id}: {e}")
                continue
        
        # Generate embeddings in batch
        embeddings = embedding_pipeline.generate_embeddings_batch(texts)
        
        # Update items
        updated_count = 0
        for item, embedding in zip(items_to_update, embeddings):
            item.embedding = embedding
            session.add(item)
            updated_count += 1
        
        session.commit()
        
        logger.info(f"Generated embeddings for {updated_count} items for user {user_id}")
        
        return {
            "success": True,
            "message": f"Generated embeddings for {updated_count} items",
            "total": len(items),
            "updated": updated_count
        }
        
    except Exception as e:
        logger.error(f"Bulk embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings"
        )
