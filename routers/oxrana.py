import os
import boto3
import uuid
from botocore.exceptions import ClientError
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user

router = APIRouter(prefix="/oxrana", tags=["oxrana"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

# Схемы
class OxranaDocumentCreate(BaseModel):
    title_ru: str
    title_en: str
    file_path: str
    file_name: str = ""
    order: int = 0

class OxranaDocumentUpdate(BaseModel):
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

# ========== Загрузка PDF в облако ==========
@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    # Проверка расширения
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
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
        unique_filename = f"{uuid.uuid4()}.pdf"
        folder = "docs"
        key = f"{folder}/{unique_filename}"
        
        # Читаем файл
        content = await file.read()
        
        # Загружаем в бакет
        s3.put_object(
            Bucket=YC_BUCKET,
            Key=key,
            Body=content,
            ContentType='application/pdf',
            ACL='public-read'
        )
        
        # Формируем публичную ссылку
        public_url = f"https://storage.yandexcloud.net/{YC_BUCKET}/{key}"
        
        return {
            "file_path": public_url,
            "file_name": file.filename,
            "file_size": len(content)
        }
        
    except ClientError as e:
        print(f"Yandex Cloud upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")
    except Exception as e:
        print(f"Upload exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# ========== Остальные эндпоинты ==========

# Получить все документы
@router.get("/documents")
def get_documents(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    docs = db.query(models.OxranaDocument).filter(
        models.OxranaDocument.is_active == True
    ).order_by(models.OxranaDocument.order).all()
    
    result = []
    for doc in docs:
        result.append({
            "id": doc.id,
            "title": doc.title_ru if lang == "ru" else doc.title_en,
            "title_ru": doc.title_ru,
            "title_en": doc.title_en,
            "file_path": doc.file_path,
            "file_name": doc.file_name,
            "order": doc.order
        })
    return result

# Создать документ
@router.post("/documents")
def create_document(
    doc: OxranaDocumentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    new_doc = models.OxranaDocument(
        title_ru=doc.title_ru,
        title_en=doc.title_en,
        file_path=doc.file_path,
        file_name=doc.file_name,
        order=doc.order,
        updated_by=current_user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return {"id": new_doc.id, "message": "Document created"}

# Обновить документ
@router.put("/documents/{doc_id}")
def update_document(
    doc_id: int,
    doc: OxranaDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_doc = db.query(models.OxranaDocument).filter(models.OxranaDocument.id == doc_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    for field, value in doc.dict(exclude_unset=True).items():
        setattr(db_doc, field, value)
    
    db_doc.updated_by = current_user.id
    db.commit()
    
    return {"message": "Document updated"}

# Удалить документ
@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_doc = db.query(models.OxranaDocument).filter(models.OxranaDocument.id == doc_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(db_doc)
    db.commit()
    
    return {"message": "Document deleted"}