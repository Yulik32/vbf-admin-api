from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/cards", tags=["cards"])

# GET /cards (публичный — для React фронта)
@router.get("/", response_model=list[schemas.CardOut])
def get_cards(
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
    db: Session = Depends(get_db),
    # current_user — опционально, если хотим показывать draft для админов
):
    query = db.query(models.Card)
    if only_active:
        query = query.filter(models.Card.is_active == True)
    return query.order_by(models.Card.order).offset(skip).limit(limit).all()

# GET /cards/{id} (публичный)
@router.get("/{card_id}", response_model=schemas.CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

# POST /cards (только админ)
@router.post("/", response_model=schemas.CardOut)
def create_card(
    card: schemas.CardCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    db_card = models.Card(**card.model_dump(), created_by=admin.id)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

# PUT /cards/{id} (только админ)
@router.put("/{card_id}", response_model=schemas.CardOut)
def update_card(
    card_id: int,
    card_update: schemas.CardUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    update_data = card_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_card, field, value)
    
    db.commit()
    db.refresh(db_card)
    return db_card

# DELETE /cards/{id} (только админ)
@router.delete("/{card_id}")
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(db_card)
    db.commit()
    return {"message": "Card deleted successfully"}