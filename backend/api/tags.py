from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import TagDictionary, User
from schemas import TagOut

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=List[TagOut])
def list_tags(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(TagDictionary).filter(TagDictionary.is_active == True)
    if category:
        q = q.filter(TagDictionary.category == category)
    return q.order_by(TagDictionary.category, TagDictionary.sort_order).all()


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    cats = (
        db.query(TagDictionary.category)
        .filter(TagDictionary.is_active == True)
        .distinct()
        .all()
    )
    return {"categories": [c[0] for c in cats]}
