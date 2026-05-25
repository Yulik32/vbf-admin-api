from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional, List
from dependencies import get_current_user

router = APIRouter(prefix="/service", tags=["service"])

# Схемы
class ServicePhoneCreate(BaseModel):
    section_key: str
    title_ru: str
    title_en: str
    phone: str = ""
    order: int = 0

class ServicePhoneUpdate(BaseModel):
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    phone: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

# Получить все телефоны
@router.get("/phones")
def get_service_phones(
    section_key: str = None,
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    query = db.query(models.ServicePhone).filter(models.ServicePhone.is_active == True)
    if section_key:
        query = query.filter(models.ServicePhone.section_key == section_key)
    
    phones = query.order_by(models.ServicePhone.order).all()
    
    result = []
    for p in phones:
        result.append({
            "id": p.id,
            "section_key": p.section_key,
            "title": p.title_ru if lang == "ru" else p.title_en,
            "title_ru": p.title_ru,
            "title_en": p.title_en,
            "phone": p.phone,
            "order": p.order
        })
    return result

# Создать телефон (только админ)
@router.post("/phones")
def create_service_phone(
    phone: ServicePhoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    new_phone = models.ServicePhone(
        section_key=phone.section_key,
        title_ru=phone.title_ru,
        title_en=phone.title_en,
        phone=phone.phone,
        order=phone.order,
        updated_by=current_user.id
    )
    db.add(new_phone)
    db.commit()
    db.refresh(new_phone)
    return {"id": new_phone.id, "message": "Phone created"}

# Обновить телефон
@router.put("/phones/{phone_id}")
def update_service_phone(
    phone_id: int,
    phone: ServicePhoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_phone = db.query(models.ServicePhone).filter(models.ServicePhone.id == phone_id).first()
    if not db_phone:
        raise HTTPException(status_code=404, detail="Phone not found")
    
    for field, value in phone.dict(exclude_unset=True).items():
        setattr(db_phone, field, value)
    
    db_phone.updated_by = current_user.id
    db.commit()
    
    return {"message": "Phone updated"}

# Удалить телефон
@router.delete("/phones/{phone_id}")
def delete_service_phone(
    phone_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_phone = db.query(models.ServicePhone).filter(models.ServicePhone.id == phone_id).first()
    if not db_phone:
        raise HTTPException(status_code=404, detail="Phone not found")
    
    db.delete(db_phone)
    db.commit()
    
    return {"message": "Phone deleted"}