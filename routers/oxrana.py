import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models
from pydantic import BaseModel
from typing import Optional
from dependencies import get_current_user

router = APIRouter(prefix="/oxrana", tags=["oxrana"])

UPLOAD_DIR = "uploads/docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

# Загрузить PDF файл
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
    
    # Генерируем уникальное имя
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    
    return {
        "file_path": f"/uploads/docs/{filename}",
        "file_name": file.filename,
        "file_size": file_size
    }

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
    
    # Удаляем файл с диска
    if db_doc.file_path:
        file_path = db_doc.file_path.lstrip('/')
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.delete(db_doc)
    db.commit()
    
    return {"message": "Document deleted"}