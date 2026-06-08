# routers/catalog.py
import os
import boto3
import uuid
from botocore.exceptions import ClientError
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional, List
from dependencies import get_current_user, check_page_permission

router = APIRouter(prefix="/catalog_admin", tags=["catalog_admin"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

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

# ========== Вспомогательная функция для проверки прав ==========
def require_catalog_edit(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на редактирование каталога"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "catalog", "edit"):
        raise HTTPException(
            status_code=403,
            detail="No edit rights for catalog"
        )
    return current_user

def require_catalog_view(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на просмотр каталога в админке"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "catalog", "view"):
        raise HTTPException(
            status_code=403,
            detail="No view rights for catalog"
        )
    return current_user

# ========== ОБРАБОТКА OPTIONS ЗАПРОСОВ ДЛЯ CORS ==========
@router.options("/upload")
async def options_upload():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/cards")
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

@router.options("/cards/{card_id}")
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

@router.options("/settings")
async def options_settings():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# ========== Загрузка файлов в облако ==========
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_catalog_edit)
):
    allowed = {'.pdf', '.htm', '.html', '.zip'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if not YC_ACCESS_KEY or not YC_SECRET_KEY or not YC_BUCKET:
        raise HTTPException(status_code=500, detail="Yandex Cloud credentials not configured")
    
    try:
        session = boto3.session.Session()
        s3 = session.client(
            service_name='s3',
            endpoint_url=YC_ENDPOINT,
            aws_access_key_id=YC_ACCESS_KEY,
            aws_secret_access_key=YC_SECRET_KEY,
            region_name='ru-central1'
        )
        
        unique_filename = f"{uuid.uuid4()}{ext}"
        key = f"catalog/{unique_filename}"
        content = await file.read()
        
        content_type = 'application/pdf' if ext == '.pdf' else 'application/zip' if ext == '.zip' else 'text/html'
        
        s3.put_object(
            Bucket=YC_BUCKET,
            Key=key,
            Body=content,
            ContentType=content_type,
            ACL='public-read'
        )
        
        return {"url": f"https://storage.yandexcloud.net/{YC_BUCKET}/{key}"}
        
    except ClientError as e:
        print(f"Yandex Cloud upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except Exception as e:
        print(f"Upload exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# ========== Публичные эндпоинты (без авторизации) ==========

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

# ========== Админские эндпоинты (с проверкой прав) ==========

@router.get("/cards/admin")
def get_catalog_cards_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_catalog_view)
):
    """Получить все карточки каталога для админки (включая неактивные)"""
    cards = db.query(models.CatalogCard).order_by(models.CatalogCard.order).all()
    
    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "title_ru": card.title_ru,
            "title_en": card.title_en,
            "description_ru": card.description_ru,
            "description_en": card.description_en,
            "file_url": card.file_url,
            "icon_type": card.icon_type,
            "order": card.order,
            "is_active": card.is_active
        })
    return result

@router.post("/cards")
def create_catalog_card(
    card: CatalogCardCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_catalog_edit)
):
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
    current_user: models.User = Depends(require_catalog_edit)
):
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
    current_user: models.User = Depends(require_catalog_edit)
):
    db_card = db.query(models.CatalogCard).filter(models.CatalogCard.id == card_id).first()
    if not db_card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    db.delete(db_card)
    db.commit()
    
    return {"message": "Card deleted"}

@router.put("/settings")
def update_catalog_settings(
    settings_data: CatalogSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_catalog_edit)
):
    settings = db.query(models.CatalogSettings).first()
    if not settings:
        settings = models.CatalogSettings(updated_by=current_user.id)
        db.add(settings)
    
    for field, value in settings_data.dict(exclude_unset=True).items():
        setattr(settings, field, value)
    
    settings.updated_by = current_user.id
    db.commit()
    
    return {"message": "Settings updated"}