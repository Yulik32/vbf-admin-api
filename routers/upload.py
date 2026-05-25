import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from dependencies import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Загрузка файла
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
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    # Проверка расширения
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Создаём подпапку если нужно
    folder_path = os.path.join(UPLOAD_DIR, section)
    os.makedirs(folder_path, exist_ok=True)
    
    # Генерируем уникальное имя
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(folder_path, safe_filename)
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения: {str(e)}")
    
    # Сохраняем в БД
    media = models.UploadedMedia(
        page=page,
        section=section,
        filename=safe_filename,
        original_name=file.filename,
        file_path=f"/uploads/{section}/{safe_filename}",
        file_size=os.path.getsize(file_path),
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
        "filename": safe_filename,
        "original_name": file.filename,
        "alt_ru": media.alt_ru,
        "alt_en": media.alt_en
    }

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
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    media = db.query(models.UploadedMedia).filter(models.UploadedMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    
    # Удаляем файл с диска
    file_path = media.file_path.lstrip('/')
    if os.path.exists(file_path):
        os.remove(file_path)
    
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
    if current_user.role != 'admin':
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