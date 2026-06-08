# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from database import get_db
import models
import schemas
from dependencies import get_current_user, get_password_hash, get_current_super_admin

router = APIRouter(prefix="/users", tags=["users"])

# Список всех доступных страниц
AVAILABLE_PAGES = [
    {"key": "dashboard", "name_ru": "Панель управления", "name_en": "Dashboard"},
    {"key": "main_page", "name_ru": "Главная страница", "name_en": "Main page"},
    {"key": "history", "name_ru": "История", "name_en": "History"},
    {"key": "managers", "name_ru": "Руководители", "name_en": "Managers"},
    {"key": "license", "name_ru": "Качество и лицензии", "name_en": "Licenses"},
    {"key": "rent", "name_ru": "Аренда", "name_en": "Rent"},
    {"key": "realty", "name_ru": "Недвижимость", "name_en": "Realty"},
    {"key": "service", "name_ru": "Сервис", "name_en": "Service"},
    {"key": "catalog", "name_ru": "Каталог продукции", "name_en": "Catalog"},
    {"key": "carcatalog", "name_ru": "Автокаталог", "name_en": "Auto catalog"},
    {"key": "other_products", "name_ru": "Прочая продукция", "name_en": "Other products"},
    {"key": "individual_packaging", "name_ru": "Подшипники в упаковке", "name_en": "Packaged bearings"},
    {"key": "repairkits", "name_ru": "Ремкомплекты", "name_en": "Repair kits"},
    {"key": "oxrana", "name_ru": "Охрана труда", "name_en": "Labor protection"},
    {"key": "job", "name_ru": "Вакансии", "name_en": "Vacancies"},
    {"key": "users", "name_ru": "Пользователи", "name_en": "Users"},
    {"key": "settings", "name_ru": "Настройки сайта", "name_en": "Settings"},
]

# ==================== ТОЛЬКО ДЛЯ SUPER_ADMIN ====================

# Получить всех пользователей (только super_admin)
@router.get("/", response_model=List[schemas.UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_super_admin)  # только super_admin
):
    users = db.query(models.User).filter(models.User.is_active == True).all()
    for user in users:
        if user.page_permissions:
            user.page_permissions = json.loads(user.page_permissions)
    return users

# Создать пользователя (только super_admin)
@router.post("/", response_model=schemas.UserResponse)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_super_admin)  # только super_admin
):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    page_perms_json = json.dumps(user.page_permissions) if user.page_permissions else None
    
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        page_permissions=page_perms_json
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    if new_user.page_permissions:
        new_user.page_permissions = json.loads(new_user.page_permissions)
    
    return new_user

# Обновить пользователя (только super_admin)
@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_super_admin)  # только super_admin
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Нельзя редактировать самого себя (super_admin не может изменить свои права)
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot edit your own user")
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "page_permissions" and value:
            value = json.dumps(value)
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    
    if db_user.page_permissions:
        db_user.page_permissions = json.loads(db_user.page_permissions)
    
    return db_user

# Удалить пользователя (только super_admin)
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_super_admin)  # только super_admin
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(db_user)
    db.commit()
    
    return {"message": "User deleted"}

# ==================== ПУБЛИЧНЫЕ ЭНДПОИНТЫ (для всех авторизованных) ====================

# Получить список доступных страниц для текущего пользователя
@router.get("/pages")
def get_available_pages(
    current_user: models.User = Depends(get_current_user)
):
    """Получить список страниц, доступных текущему пользователю"""
    if current_user.role == "super_admin":
        return AVAILABLE_PAGES
    
    if current_user.page_permissions:
        try:
            perms = json.loads(current_user.page_permissions) if isinstance(current_user.page_permissions, str) else current_user.page_permissions
            allowed_pages = perms.get("pages", [])
            
            pages = [p for p in AVAILABLE_PAGES if p["key"] in allowed_pages]
            return pages
        except:
            pass
    
    return []

# Получить информацию о текущем пользователе
@router.get("/me", response_model=schemas.UserResponse)
def get_me(
    current_user: models.User = Depends(get_current_user)
):
    if current_user.page_permissions:
        current_user.page_permissions = json.loads(current_user.page_permissions)
    return current_user