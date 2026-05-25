from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
from pydantic import BaseModel
from dependencies import get_current_user

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

# Получить все адреса
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

# Создать адрес (только админ)
@router.post("/addresses")
def create_address(
    address: AddressCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
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

# Обновить адрес (только админ)
@router.put("/addresses/{address_id}")
def update_address(
    address_id: int,
    address: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
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

# Удалить адрес (только админ)
@router.delete("/addresses/{address_id}")
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_address = db.query(models.RealtyAddress).filter(models.RealtyAddress.id == address_id).first()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    db.delete(db_address)
    db.commit()
    
    return {"message": "Address deleted"}