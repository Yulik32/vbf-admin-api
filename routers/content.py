import os
import boto3
import uuid
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from dependencies import get_current_user

router = APIRouter(prefix="/content", tags=["content"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

# ========== Загрузка файлов в облако ==========
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    # Проверка типа файла
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
        folder = "content"
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

# Получить весь контент для страницы (публичный)
@router.get("/{page}")
def get_page_content(
    page: str,
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    contents = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.language == lang
    ).all()
    
    result = {}
    for item in contents:
        result[item.section] = item.content
    
    # Также получаем галерею для страницы
    gallery = db.query(models.GalleryImage).filter(
        models.GalleryImage.page == page,
        models.GalleryImage.is_active == True
    ).order_by(models.GalleryImage.image_order).all()
    
    result['gallery'] = [{
        'id': img.id,
        'url': img.image_url,
        'alt': img.alt_ru if lang == 'ru' else img.alt_en,
        'order': img.image_order
    } for img in gallery]
    
    return result

# Обновить контент страницы (только админ)
@router.put("/{page}/{section}")
def update_content(
    page: str,
    section: str,
    content_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Проверяем, что пользователь админ
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    content_item = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.section == section,
        models.PageContent.language == content_data.get('language', 'ru')
    ).first()
    
    if content_item:
        content_item.content = content_data.get('content', '')
        content_item.updated_by = current_user.id
    else:
        content_item = models.PageContent(
            page=page,
            section=section,
            language=content_data.get('language', 'ru'),
            content=content_data.get('content', ''),
            updated_by=current_user.id
        )
        db.add(content_item)
    
    db.commit()
    return {"message": "Content updated"}

# Управление галереей
@router.post("/{page}/gallery")
def add_gallery_image(
    page: str,
    image_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    image = models.GalleryImage(
        page=page,
        image_url=image_data.get('url'),
        alt_ru=image_data.get('alt_ru', ''),
        alt_en=image_data.get('alt_en', ''),
        image_order=image_data.get('order', 0)
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return {"id": image.id, "message": "Image added"}

@router.delete("/gallery/{image_id}")
def delete_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    image = db.query(models.GalleryImage).filter(models.GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db.delete(image)
    db.commit()
    return {"message": "Image deleted"}