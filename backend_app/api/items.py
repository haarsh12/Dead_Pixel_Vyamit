"""Category-scoped inventory API.

The active scope is always read from the authenticated user's profile.  A
client can choose a product group (``Item.category``), but can never send a
shop category to read, overwrite, or delete another inventory namespace.
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from core.security import get_current_user
from core.shop_categories import stored_category
from db.database import get_session
from db.models import Item, User
from db.schemas import ItemCreate, ItemResponse, ItemUpdate


logger = logging.getLogger(__name__)
router = APIRouter()


def _active_inventory_scope(session: Session, user_id: int) -> str:
    """Return the profile-selected namespace for this authenticated user."""
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is unavailable",
        )
    return stored_category(user.shop_category)


def _to_response(item: Item) -> ItemResponse:
    try:
        names = json.loads(item.names) if item.names else []
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning("Skipping malformed inventory names for item=%s", item.id)
        raise ValueError("Stored inventory item has malformed names") from exc
    if not isinstance(names, list) or not names:
        raise ValueError("Stored inventory item has no names")
    return ItemResponse(
        id=item.master_id,
        names=names,
        price=item.price,
        unit=item.unit,
        category=item.category,
        owner_id=item.owner_id,
        master_id=item.master_id,
        shop_category=item.shop_category,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _find_item_in_scope(
    session: Session, user_id: int, inventory_scope: str, master_id: str
) -> Item | None:
    return session.exec(
        select(Item).where(
            Item.master_id == master_id,
            Item.owner_id == user_id,
            Item.shop_category == inventory_scope,
        )
    ).first()


def _apply_item_changes(target: Item, payload: ItemCreate | ItemUpdate) -> None:
    """Apply only client-controlled product fields; scope and owner stay server-owned."""
    target.names = json.dumps(payload.names, ensure_ascii=False)
    target.price = payload.price
    target.unit = payload.unit
    target.category = payload.category
    target.updated_at = datetime.utcnow()


@router.post("/", response_model=ItemResponse)
def create_item(
    item: ItemCreate,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Create or update an item inside the user's currently selected category."""
    try:
        inventory_scope = _active_inventory_scope(session, user_id)
        existing_item = _find_item_in_scope(session, user_id, inventory_scope, item.id)

        if existing_item:
            _apply_item_changes(existing_item, item)
            session.add(existing_item)
            session.commit()
            session.refresh(existing_item)
            logger.info("Updated item=%s user=%s scope=%s", item.id, user_id, inventory_scope)
            return _to_response(existing_item)

        new_item = Item(
            master_id=item.id,
            names=json.dumps(item.names, ensure_ascii=False),
            category=item.category,
            shop_category=inventory_scope,
            price=item.price,
            unit=item.unit,
            owner_id=user_id,
        )
        session.add(new_item)
        session.commit()
        session.refresh(new_item)

        logger.info("Created item=%s user=%s scope=%s", item.id, user_id, inventory_scope)
        return _to_response(new_item)
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Failed to create/update item user=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save item",
        )


@router.get("/", response_model=List[ItemResponse])
def get_items(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List only the inventory owned by the active profile category."""
    inventory_scope = _active_inventory_scope(session, user_id)
    try:
        items = session.exec(
            select(Item).where(
                Item.owner_id == user_id,
                Item.shop_category == inventory_scope,
            )
        ).all()
        response_items: List[ItemResponse] = []
        for stored_item in items:
            try:
                response_items.append(_to_response(stored_item))
            except ValueError:
                continue
        logger.info(
            "Fetched items=%s user=%s scope=%s",
            len(response_items),
            user_id,
            inventory_scope,
        )
        return response_items
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch inventory user=%s scope=%s", user_id, inventory_scope)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch inventory",
        )


@router.put("/{item_id}", response_model=ItemResponse)
@router.put("/{item_id}/", response_model=ItemResponse, include_in_schema=False)
def update_item(
    item_id: str,
    item: ItemUpdate,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Update an item only when it belongs to the active category namespace."""
    try:
        inventory_scope = _active_inventory_scope(session, user_id)
        existing_item = _find_item_in_scope(session, user_id, inventory_scope, item_id)
        if not existing_item:
            # Do not disclose whether this id exists in a different category.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        _apply_item_changes(existing_item, item)
        session.add(existing_item)
        session.commit()
        session.refresh(existing_item)
        logger.info("Updated item=%s user=%s scope=%s", item_id, user_id, inventory_scope)
        return _to_response(existing_item)
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Failed to update item=%s user=%s", item_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item",
        )


@router.delete("/{item_id}")
@router.delete("/{item_id}/", include_in_schema=False)
def delete_item(
    item_id: str,
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Delete an item only from the currently selected category namespace."""
    try:
        inventory_scope = _active_inventory_scope(session, user_id)
        existing_item = _find_item_in_scope(session, user_id, inventory_scope, item_id)
        if not existing_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        session.delete(existing_item)
        session.commit()
        logger.info("Deleted item=%s user=%s scope=%s", item_id, user_id, inventory_scope)
        return {"success": True, "message": "Item deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Failed to delete item=%s user=%s", item_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item",
        )


@router.post("/bulk-embed")
async def bulk_embed_items(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Generate embeddings only for the inventory in the active category scope."""
    try:
        from pipeline.embedding_pipeline import embedding_pipeline

        inventory_scope = _active_inventory_scope(session, user_id)
        items = session.exec(
            select(Item).where(
                Item.owner_id == user_id,
                Item.shop_category == inventory_scope,
            )
        ).all()
        if not items:
            return {
                "success": True,
                "message": "No items to embed in this category",
                "scope": inventory_scope,
                "total": 0,
                "updated": 0,
            }

        texts: list[str] = []
        items_to_update: list[Item] = []
        for stored_item in items:
            try:
                names = json.loads(stored_item.names)
                if not isinstance(names, list) or not names:
                    continue
                # The item's own product metadata is embedded; retrieval is
                # still constrained by shop_category in SQL.
                texts.append(" ".join(map(str, names)) + f" {stored_item.category}")
                items_to_update.append(stored_item)
            except (TypeError, json.JSONDecodeError):
                logger.warning("Cannot embed malformed item=%s", stored_item.id)

        embeddings = embedding_pipeline.generate_embeddings_batch(texts)
        for stored_item, embedding in zip(items_to_update, embeddings):
            stored_item.embedding = embedding
            stored_item.updated_at = datetime.utcnow()
            session.add(stored_item)
        session.commit()

        logger.info(
            "Generated embeddings=%s user=%s scope=%s",
            len(items_to_update),
            user_id,
            inventory_scope,
        )
        return {
            "success": True,
            "message": f"Generated embeddings for {len(items_to_update)} items",
            "scope": inventory_scope,
            "total": len(items),
            "updated": len(items_to_update),
        }
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Bulk embedding failed user=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate embeddings",
        )
