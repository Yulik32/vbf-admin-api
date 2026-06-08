# routers/cards.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from dependencies import get_current_user, check_page_permission

router = APIRouter(prefix="/cards", tags=["cards"])

# ========== Вспомогательная функция для проверки прав ==========
def require_cards_edit(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на редактирование карточек"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "main_page", "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No edit rights for cards"
        )
    return current_user

def require_cards_view(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на просмотр карточек в админке"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "main_page", "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No view rights for cards"
        )
    return current_user

# ========== ОБРАБОТКА OPTIONS ЗАПРОСОВ ДЛЯ CORS ==========
@router.options("/")
async def options_cards():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/{card_id}")
async def options_card(card_id: int):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# ========== Публичные эндпоинты (без авторизации) ==========

# GET /cards (публичный — для React фронта)
@router.get("/", response_model=list[schemas.CardOut])
def get_cards(
    skip: int = 0,
    limit: int = 100,
    only_active: bool = True,
    db: Session = Depends(get_db),
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

# ========== Админские эндпоинты (с проверкой прав) ==========

# GET /cards/admin (для админки)
@router.get("/admin/")
def get_cards_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cards_view)
):
    """Получить все карточки для админки (включая неактивные)"""
    cards = db.query(models.Card).order_by(models.Card.order).all()
    
    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "title": card.title,
            "description": card.description,
            "image_url": card.image_url,
            "is_active": card.is_active,
            "order": card.order,
            "created_by": card.created_by,
            "created_at": card.created_at,
            "updated_at": card.updated_at
        })
    return result

# POST /cards (только с правами на редактирование)
@router.post("/", response_model=schemas.CardOut)
def create_card(
    card: schemas.CardCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cards_edit)
):
    db_card = models.Card(**card.model_dump(), created_by=current_user.id)
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

# PUT /cards/{id} (только с правами на редактирование)
@router.put("/{card_id}", response_model=schemas.CardOut)
def update_card(
    card_id: int,
    card_update: schemas.CardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cards_edit)
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

# DELETE /cards/{id} (только с правами на редактирование)
@router.delete("/{card_id}")
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_cards_edit)
):
    db_card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(db_card)
    db.commit()
    return {"message": "Card deleted successfully"}