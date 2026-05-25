import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional, List
from dependencies import get_current_user

router = APIRouter(prefix="/catalog_admin", tags=["catalog_admin"])

UPLOAD_DIR = "uploads/catalog"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ========== Схемы для карточек ==========
class CatalogCardCreate(BaseModel):
    title_ru: str
    title_en: str
    description_ru: str = ""
    description_en: str = ""
    file_url: str = ""
    icon_type: str = "one"
    order: int = 0

class CatalogCardUpdate(BaseModel):
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    file_url: Optional[str] = None
    icon_type: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

# ========== Схемы для настроек ==========
class CatalogSettingsUpdate(BaseModel):
    design_dept_phone_ru: Optional[str] = None
    design_dept_phone_en: Optional[str] = None
    planning_dept_phone_ru: Optional[str] = None
    planning_dept_phone_en: Optional[str] = None

# ========== Загрузка файлов ==========
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    allowed = {'.pdf', '.htm', '.html', '.zip'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"url": f"/uploads/catalog/{filename}"}

# ========== CRUD для карточек каталога ==========
@router.get("/cards")
def get_catalog_cards(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    cards = db.query(models.CatalogCard).filter(
        models.CatalogCard.is_active == True
    ).order_by(models.CatalogCard.order).all()
    
    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "title": card.title_ru if lang == "ru" else card.title_en,
            "title_ru": card.title_ru,
            "title_en": card.title_en,
            "description": card.description_ru if lang == "ru" else card.description_en,
            "description_ru": card.description_ru,
            "description_en": card.description_en,
            "file_url": card.file_url,
            "icon_type": card.icon_type,
            "order": card.order
        })
    return result

@router.post("/cards")
def create_catalog_card(
    card: CatalogCardCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    new_card = models.CatalogCard(
        title_ru=card.title_ru,
        title_en=card.title_en,
        description_ru=card.description_ru,
        description_en=card.description_en,
        file_url=card.file_url,
        icon_type=card.icon_type,
        order=card.order,
        updated_by=current_user.id
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return {"id": new_card.id, "message": "Card created"}

@router.put("/cards/{card_id}")
def update_catalog_card(
    card_id: int,
    card: CatalogCardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_card = db.query(models.CatalogCard).filter(models.CatalogCard.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    for field, value in card.dict(exclude_unset=True).items():
        setattr(db_card, field, value)
    
    db_card.updated_by = current_user.id
    db.commit()
    
    return {"message": "Card updated"}

@router.delete("/cards/{card_id}")
def delete_catalog_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_card = db.query(models.CatalogCard).filter(models.CatalogCard.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(db_card)
    db.commit()
    
    return {"message": "Card deleted"}

# ========== Настройки каталога (телефоны) ==========
@router.get("/settings")
def get_catalog_settings(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    settings = db.query(models.CatalogSettings).first()
    if not settings:
        return {
            "design_dept_phone": "",
            "planning_dept_phone": "",
            "design_dept_phone_ru": "",
            "design_dept_phone_en": "",
            "planning_dept_phone_ru": "",
            "planning_dept_phone_en": ""
        }
    
    return {
        "id": settings.id,
        "design_dept_phone": settings.design_dept_phone_ru if lang == "ru" else settings.design_dept_phone_en,
        "design_dept_phone_ru": settings.design_dept_phone_ru,
        "design_dept_phone_en": settings.design_dept_phone_en,
        "planning_dept_phone": settings.planning_dept_phone_ru if lang == "ru" else settings.planning_dept_phone_en,
        "planning_dept_phone_ru": settings.planning_dept_phone_ru,
        "planning_dept_phone_en": settings.planning_dept_phone_en
    }

@router.put("/settings")
def update_catalog_settings(
    settings_data: CatalogSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    settings = db.query(models.CatalogSettings).first()
    if not settings:
        settings = models.CatalogSettings(updated_by=current_user.id)
        db.add(settings)
    
    for field, value in settings_data.dict(exclude_unset=True).items():
        setattr(settings, field, value)
    
    settings.updated_by = current_user.id
    db.commit()
    
    return {"message": "Settings updated"}