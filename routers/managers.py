import os
import boto3
import uuid
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
from datetime import datetime
from pydantic import BaseModel
from dependencies import get_current_user

router = APIRouter(prefix="/managers", tags=["managers"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

# Схемы
class ManagerCreate(BaseModel):
    name_ru: str
    name_en: str
    position_ru: str
    position_en: str
    phone: str = ""
    photo_url: str = ""
    order: int = 0

class ManagerUpdate(BaseModel):
    name_ru: str = None
    name_en: str = None
    position_ru: str = None
    position_en: str = None
    phone: str = None
    photo_url: str = None
    order: int = None
    is_active: bool = None

# ========== Загрузка фото в облако ==========
@router.post("/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    # Проверка расширения
    allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if not YC_ACCESS_KEY or not YC_SECRET_KEY or not YC_BUCKET:
        raise HTTPException(
            status_code=500,
            detail="Yandex Cloud credentials not configured"
        )
    
    try:
        # Создаём клиент для Yandex Object Storage
        session = boto3.session.Session()
        s3 = session.client(
            service_name='s3',
            endpoint_url=YC_ENDPOINT,
            aws_access_key_id=YC_ACCESS_KEY,
            aws_secret_access_key=YC_SECRET_KEY,
            region_name='ru-central1'
        )
        
        # Генерируем уникальное имя файла
        unique_filename = f"{uuid.uuid4()}{ext}"
        folder = "managers"
        key = f"{folder}/{unique_filename}"
        
        # Читаем файл
        content = await file.read()
        
        # Загружаем в бакет
        s3.put_object(
            Bucket=YC_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type,
            ACL='public-read'
        )
        
        # Формируем публичную ссылку
        public_url = f"https://storage.yandexcloud.net/{YC_BUCKET}/{key}"
        
        return {"url": public_url}
        
    except ClientError as e:
        print(f"Yandex Cloud upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except Exception as e:
        print(f"Upload exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# ========== Остальные эндпоинты ==========

# Получить всех руководителей
@router.get("/")
def get_managers(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    managers = db.query(models.Manager).filter(
        models.Manager.is_active == True
    ).order_by(models.Manager.order).all()
    
    result = []
    for m in managers:
        result.append({
            "id": m.id,
            "name": m.name_ru if lang == "ru" else m.name_en,
            "position": m.position_ru if lang == "ru" else m.position_en,
            "phone": m.phone,
            "photo_url": m.photo_url,
            "name_ru": m.name_ru,
            "name_en": m.name_en,
            "position_ru": m.position_ru,
            "position_en": m.position_en,
            "order": m.order
        })
    return result

# Создать руководителя (только админ)
@router.post("/")
def create_manager(
    manager: ManagerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    new_manager = models.Manager(
        name_ru=manager.name_ru,
        name_en=manager.name_en,
        position_ru=manager.position_ru,
        position_en=manager.position_en,
        phone=manager.phone,
        photo_url=manager.photo_url,
        order=manager.order,
        updated_by=current_user.id
    )
    db.add(new_manager)
    db.commit()
    db.refresh(new_manager)
    return {"id": new_manager.id, "message": "Manager created"}

# Обновить руководителя
@router.put("/{manager_id}")
def update_manager(
    manager_id: int,
    manager: ManagerUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_manager = db.query(models.Manager).filter(models.Manager.id == manager_id).first()
    if not db_manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    for field, value in manager.dict(exclude_unset=True).items():
        setattr(db_manager, field, value)
    
    db_manager.updated_by = current_user.id
    db.commit()
    
    return {"message": "Manager updated"}

# Удалить руководителя
@router.delete("/{manager_id}")
def delete_manager(
    manager_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_manager = db.query(models.Manager).filter(models.Manager.id == manager_id).first()
    if not db_manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    db.delete(db_manager)
    db.commit()
    
    return {"message": "Manager deleted"}