import os
import hashlib
import time
import uuid
import aiohttp
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional, List
from dependencies import get_current_user

router = APIRouter(prefix="/license", tags=["license"])

# ========== Настройки Cloudinary ==========
CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
API_KEY = os.getenv("CLOUDINARY_API_KEY")
API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# ========== Схемы для качества ==========
class QualityCardCreate(BaseModel):
    image_url: str
    title_ru: str
    title_en: str
    description_ru: str
    description_en: str
    certificate_url: str = ""
    order: int = 0

class QualityCardUpdate(BaseModel):
    image_url: Optional[str] = None
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    certificate_url: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

# ========== Схемы для лицензий ==========
class LicenseContentUpdate(BaseModel):
    text_ru: Optional[str] = None
    text_en: Optional[str] = None
    link_text_ru: Optional[str] = None
    link_text_en: Optional[str] = None
    link_description_ru: Optional[str] = None
    link_description_en: Optional[str] = None
    image_1_url: Optional[str] = None
    image_2_url: Optional[str] = None
    quality_title_ru: Optional[str] = None
    quality_title_en: Optional[str] = None
    licenses_title_ru: Optional[str] = None
    licenses_title_en: Optional[str] = None

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    # Проверка типа файла
    allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.pdf'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    # Проверка настроек
    if not CLOUD_NAME or not API_KEY or not API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Cloudinary not configured"
        )
    
    try:
        # Читаем файл
        content = await file.read()
        
        # Кодируем в base64 (облачный метод без сложной подписи)
        import base64
        b64_content = base64.b64encode(content).decode()
        
        # Формируем data URL
        data_url = f"data:{file.content_type};base64,{b64_content}"
        
        # Простой запрос к Cloudinary (без ручной подписи)
        upload_url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/auto/upload"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                upload_url,
                data={
                    "file": data_url,
                    "api_key": API_KEY,
                    "timestamp": str(int(time.time())),
                    "folder": "vbf_licenses"
                }
            ) as response:
                result = await response.json()
                
                # Логируем ответ для отладки
                print(f"Cloudinary response: {result}")
                
                if response.status == 200 and result.get("secure_url"):
                    return {"url": result["secure_url"]}
                else:
                    error_msg = result.get("error", {}).get("message", str(result))
                    raise HTTPException(
                        status_code=500,
                        detail=f"Cloudinary error: {error_msg}"
                    )
                    
    except Exception as e:
        print(f"Upload exception: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload error: {str(e)}"
        )
                    

# ========== CRUD для карточек качества ==========
@router.get("/quality")
def get_quality_cards(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    cards = db.query(models.QualityCard).filter(
        models.QualityCard.is_active == True
    ).order_by(models.QualityCard.order).all()
    
    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "image_url": card.image_url,
            "title": card.title_ru if lang == "ru" else card.title_en,
            "title_ru": card.title_ru,
            "title_en": card.title_en,
            "description": card.description_ru if lang == "ru" else card.description_en,
            "description_ru": card.description_ru,
            "description_en": card.description_en,
            "certificate_url": card.certificate_url,
            "order": card.order
        })
    return result

@router.post("/quality")
def create_quality_card(
    card: QualityCardCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    new_card = models.QualityCard(
        image_url=card.image_url,
        title_ru=card.title_ru,
        title_en=card.title_en,
        description_ru=card.description_ru,
        description_en=card.description_en,
        certificate_url=card.certificate_url,
        order=card.order,
        updated_by=current_user.id
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return {"id": new_card.id, "message": "Card created"}

@router.put("/quality/{card_id}")
def update_quality_card(
    card_id: int,
    card: QualityCardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_card = db.query(models.QualityCard).filter(models.QualityCard.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    for field, value in card.dict(exclude_unset=True).items():
        setattr(db_card, field, value)
    
    db_card.updated_by = current_user.id
    db.commit()
    
    return {"message": "Card updated"}

@router.delete("/quality/{card_id}")
def delete_quality_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_card = db.query(models.QualityCard).filter(models.QualityCard.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(db_card)
    db.commit()
    
    return {"message": "Card deleted"}

# ========== Управление контентом лицензий ==========
@router.get("/content")
def get_license_content(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    content = db.query(models.LicenseContent).first()
    if not content:
        return {
            "text": "",
            "text_ru": "",
            "text_en": "",
            "link_text": "",
            "link_text_ru": "",
            "link_text_en": "",
            "link_description": "",
            "link_description_ru": "",
            "link_description_en": "",
            "image_1_url": "",
            "image_2_url": "",
            "quality_title": "",
            "quality_title_ru": "",
            "quality_title_en": "",
            "licenses_title": "",
            "licenses_title_ru": "",
            "licenses_title_en": ""
        }
    
    return {
        "id": content.id,
        "text": content.text_ru if lang == "ru" else content.text_en,
        "text_ru": content.text_ru,
        "text_en": content.text_en,
        "link_text": content.link_text_ru if lang == "ru" else content.link_text_en,
        "link_text_ru": content.link_text_ru,
        "link_text_en": content.link_text_en,
        "link_description": content.link_description_ru if lang == "ru" else content.link_description_en,
        "link_description_ru": content.link_description_ru,
        "link_description_en": content.link_description_en,
        "image_1_url": content.image_1_url,
        "image_2_url": content.image_2_url,
        "quality_title": content.quality_title_ru if lang == "ru" else content.quality_title_en,
        "quality_title_ru": content.quality_title_ru,
        "quality_title_en": content.quality_title_en,
        "licenses_title": content.licenses_title_ru if lang == "ru" else content.licenses_title_en,
        "licenses_title_ru": content.licenses_title_ru,
        "licenses_title_en": content.licenses_title_en
    }

@router.put("/content")
def update_license_content(
    content_data: LicenseContentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    content = db.query(models.LicenseContent).first()
    if not content:
        content = models.LicenseContent(updated_by=current_user.id)
        db.add(content)
    
    for field, value in content_data.dict(exclude_unset=True).items():
        setattr(content, field, value)
    
    content.updated_by = current_user.id
    db.commit()
    
    return {"message": "Content updated"}