# routers/upload.py
import os
import boto3
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from dependencies import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}

# ========== Загрузка файла в облако ==========
@router.post("/{page}/{section}")
async def upload_file(
    page: str,
    section: str,
    file: UploadFile = File(...),
    alt_ru: str = Form(None),
    alt_en: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    # Проверка расширения
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}")
    
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
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        folder = f"uploads/{page}/{section}"
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
        
        # Сохраняем в БД
        media = models.UploadedMedia(
            page=page,
            section=section,
            filename=unique_filename,
            original_name=file.filename,
            file_path=public_url,
            file_size=len(content),
            mime_type=file.content_type,
            alt_ru=alt_ru or "",
            alt_en=alt_en or "",
            updated_by=current_user.id
        )
        db.add(media)
        db.commit()
        db.refresh(media)
        
        return {
            "id": media.id,
            "url": media.file_path,
            "filename": unique_filename,
            "original_name": file.filename,
            "alt_ru": media.alt_ru,
            "alt_en": media.alt_en
        }
        
    except Exception as e:
        print(f"Upload exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# ========== Остальные эндпоинты ==========

# Получить все изображения для страницы/секции
@router.get("/{page}/{section}")
def get_media(
    page: str,
    section: str,
    db: Session = Depends(get_db)
):
    media = db.query(models.UploadedMedia).filter(
        models.UploadedMedia.page == page,
        models.UploadedMedia.section == section,
        models.UploadedMedia.is_active == True
    ).order_by(models.UploadedMedia.order).all()
    
    return [{
        "id": m.id,
        "url": m.file_path,
        "alt_ru": m.alt_ru,
        "alt_en": m.alt_en,
        "order": m.order
    } for m in media]

# Удалить изображение
@router.delete("/{media_id}")
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    media = db.query(models.UploadedMedia).filter(models.UploadedMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    db.delete(media)
    db.commit()
    
    return {"message": "Media deleted"}

# Обновить порядок и alt-тексты
@router.put("/{media_id}")
def update_media(
    media_id: int,
    alt_ru: str = None,
    alt_en: str = None,
    order: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ['admin', 'super_admin']:
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    media = db.query(models.UploadedMedia).filter(models.UploadedMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    if alt_ru is not None:
        media.alt_ru = alt_ru
    if alt_en is not None:
        media.alt_en = alt_en
    if order is not None:
        media.order = order
    
    db.commit()
    
    return {"message": "Media updated"}