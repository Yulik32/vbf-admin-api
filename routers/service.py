# routers/service.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional, List
from dependencies import get_current_user, check_page_permission

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

# ========== Вспомогательная функция для проверки прав ==========
def require_service_edit(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на редактирование телефонов службы"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    # Страница service в системе прав
    if not check_page_permission(current_user, "service", "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No edit rights for service phones"
        )
    return current_user

def require_service_view(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на просмотр телефонов службы в админке"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "service", "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No view rights for service phones"
        )
    return current_user

# ========== ОБРАБОТКА OPTIONS ЗАПРОСОВ ДЛЯ CORS ==========
@router.options("/phones")
async def options_phones():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/phones/{phone_id}")
async def options_phone():
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

# Получить все телефоны (публичный)
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

# ========== Админские эндпоинты (с проверкой прав) ==========

# Получить все телефоны для админки (включая неактивные)
@router.get("/phones/admin")
def get_service_phones_admin(
    section_key: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_service_view)
):
    """Получить все телефоны для админки"""
    query = db.query(models.ServicePhone)
    if section_key:
        query = query.filter(models.ServicePhone.section_key == section_key)
    
    phones = query.order_by(models.ServicePhone.order).all()
    
    result = []
    for p in phones:
        result.append({
            "id": p.id,
            "section_key": p.section_key,
            "title_ru": p.title_ru,
            "title_en": p.title_en,
            "phone": p.phone,
            "order": p.order,
            "is_active": p.is_active
        })
    return result

# Создать телефон
@router.post("/phones")
def create_service_phone(
    phone: ServicePhoneCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_service_edit)
):
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
    current_user: models.User = Depends(require_service_edit)
):
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
    current_user: models.User = Depends(require_service_edit)
):
    db_phone = db.query(models.ServicePhone).filter(models.ServicePhone.id == phone_id).first()
    if not db_phone:
        raise HTTPException(status_code=404, detail="Phone not found")
    
    db.delete(db_phone)
    db.commit()
    
    return {"message": "Phone deleted"}