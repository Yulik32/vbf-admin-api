# routers/realty.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
from pydantic import BaseModel
from dependencies import get_current_user, check_page_permission

router = APIRouter(prefix="/realty", tags=["realty"])

# Схемы для валидации
class AddressCreate(BaseModel):
    address_ru: str
    address_en: str
    map_link: str = ""
    order: int = 0

class AddressUpdate(BaseModel):
    address_ru: str = None
    address_en: str = None
    map_link: str = None
    order: int = None
    is_active: bool = None

# ========== Вспомогательная функция для проверки прав ==========
def require_realty_edit(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на редактирование адресов недвижимости"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "realty", "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No edit rights for realty addresses"
        )
    return current_user

def require_realty_view(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на просмотр адресов недвижимости в админке"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "realty", "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No view rights for realty addresses"
        )
    return current_user

# ========== ОБРАБОТКА OPTIONS ЗАПРОСОВ ДЛЯ CORS ==========
@router.options("/addresses")
async def options_addresses():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/addresses/{address_id}")
async def options_address():
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

# Получить все адреса (публичный)
@router.get("/addresses")
def get_addresses(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    addresses = db.query(models.RealtyAddress).filter(
        models.RealtyAddress.is_active == True
    ).order_by(models.RealtyAddress.order).all()
    
    result = []
    for addr in addresses:
        result.append({
            "id": addr.id,
            "address": addr.address_ru if lang == "ru" else addr.address_en,
            "map_link": addr.map_link,
            "address_ru": addr.address_ru,
            "address_en": addr.address_en,
            "order": addr.order
        })
    return result

# ========== Админские эндпоинты (с проверкой прав) ==========

# Получить все адреса для админки (включая неактивные)
@router.get("/addresses/admin")
def get_addresses_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_realty_view)
):
    """Получить все адреса для админки"""
    addresses = db.query(models.RealtyAddress).order_by(models.RealtyAddress.order).all()
    
    result = []
    for addr in addresses:
        result.append({
            "id": addr.id,
            "address_ru": addr.address_ru,
            "address_en": addr.address_en,
            "map_link": addr.map_link,
            "order": addr.order,
            "is_active": addr.is_active
        })
    return result

# Создать адрес
@router.post("/addresses")
def create_address(
    address: AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_realty_edit)
):
    new_address = models.RealtyAddress(
        address_ru=address.address_ru,
        address_en=address.address_en,
        map_link=address.map_link,
        order=address.order,
        updated_by=current_user.id
    )
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return {"id": new_address.id, "message": "Address created"}

# Обновить адрес
@router.put("/addresses/{address_id}")
def update_address(
    address_id: int,
    address: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_realty_edit)
):
    db_address = db.query(models.RealtyAddress).filter(models.RealtyAddress.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    if address.address_ru is not None:
        db_address.address_ru = address.address_ru
    if address.address_en is not None:
        db_address.address_en = address.address_en
    if address.map_link is not None:
        db_address.map_link = address.map_link
    if address.order is not None:
        db_address.order = address.order
    if address.is_active is not None:
        db_address.is_active = address.is_active
    
    db_address.updated_by = current_user.id
    db.commit()
    
    return {"message": "Address updated"}

# Удалить адрес
@router.delete("/addresses/{address_id}")
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_realty_edit)
):
    db_address = db.query(models.RealtyAddress).filter(models.RealtyAddress.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    db.delete(db_address)
    db.commit()
    
    return {"message": "Address deleted"}