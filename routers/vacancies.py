# routers/vacancies.py
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
from dependencies import get_current_user

router = APIRouter(prefix="/vacancies", tags=["vacancies"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

# ========== Схемы ==========
class VacancyCreate(BaseModel):
    title_ru: str
    title_en: str
    experience_ru: str
    experience_en: str
    salary_ru: str
    salary_en: str
    description_ru: str
    description_en: str
    category: str
    type: str
    image_url: str = ""
    order: int = 0

class VacancyUpdate(BaseModel):
    title_ru: Optional[str] = None
    title_en: Optional[str] = None
    experience_ru: Optional[str] = None
    experience_en: Optional[str] = None
    salary_ru: Optional[str] = None
    salary_en: Optional[str] = None
    description_ru: Optional[str] = None
    description_en: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    image_url: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

# ========== ОБРАБОТКА OPTIONS ЗАПРОСОВ ДЛЯ CORS ==========
@router.options("/")
async def options_vacancies():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/{vacancy_id}")
async def options_vacancy():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# ========== Загрузка изображения в Yandex Cloud ==========
@router.post("/upload-image")
async def upload_vacancy_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
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
        key = f"vacancies/{unique_filename}"
        
        content = await file.read()
        
        s3.put_object(
            Bucket=YC_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type,
            ACL='public-read'
        )
        
        public_url = f"https://storage.yandexcloud.net/{YC_BUCKET}/{key}"
        return {"url": public_url}
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# ========== Получить все вакансии (публичный) ==========
@router.get("/")
def get_vacancies(
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    vacancies = db.query(models.Vacancy).filter(
        models.Vacancy.is_active == True
    ).order_by(models.Vacancy.order).all()
    
    result = []
    for v in vacancies:
        result.append({
            "id": v.id,
            "title_ru": v.title_ru,
            "title_en": v.title_en,
            "experience_ru": v.experience_ru,
            "experience_en": v.experience_en,
            "salary_ru": v.salary_ru,
            "salary_en": v.salary_en,
            "description_ru": v.description_ru,
            "description_en": v.description_en,
            "category": v.category,
            "type": v.type,
            "image_url": v.image_url,
            "order": v.order
        })
    return result

# ========== Создать вакансию ==========
@router.post("/")
def create_vacancy(
    vacancy: VacancyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    new_vacancy = models.Vacancy(
        title_ru=vacancy.title_ru,
        title_en=vacancy.title_en,
        experience_ru=vacancy.experience_ru,
        experience_en=vacancy.experience_en,
        salary_ru=vacancy.salary_ru,
        salary_en=vacancy.salary_en,
        description_ru=vacancy.description_ru,
        description_en=vacancy.description_en,
        category=vacancy.category,
        type=vacancy.type,
        image_url=vacancy.image_url,
        order=vacancy.order,
        updated_by=current_user.id
    )
    db.add(new_vacancy)
    db.commit()
    db.refresh(new_vacancy)
    return {"id": new_vacancy.id, "message": "Vacancy created"}

# ========== Обновить вакансию ==========
@router.put("/{vacancy_id}")
def update_vacancy(
    vacancy_id: int,
    vacancy: VacancyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not db_vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    
    for field, value in vacancy.dict(exclude_unset=True).items():
        setattr(db_vacancy, field, value)
    
    db_vacancy.updated_by = current_user.id
    db.commit()
    
    return {"message": "Vacancy updated"}

# ========== Удалить вакансию ==========
@router.delete("/{vacancy_id}")
def delete_vacancy(
    vacancy_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    db_vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not db_vacancy:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    
    db.delete(db_vacancy)
    db.commit()
    
    return {"message": "Vacancy deleted"}