# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
import json
from database import get_db
import models
import schemas
from dependencies import verify_password, get_password_hash
from auth_utils import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Проверка существования пользователя
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Создание пользователя
    hashed = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed,
        full_name=user.full_name,
        role="admin"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "Admin created successfully"}

@router.post("/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not db_user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")
    
    # Создаем токен
    access_token = create_access_token(data={"sub": db_user.email, "email": db_user.email})
    
    # Возвращаем токен и информацию о пользователе
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "full_name": db_user.full_name,
            "role": db_user.role,
            "page_permissions": json.loads(db_user.page_permissions) if db_user.page_permissions else {"pages": [], "can_edit": False}
        }
    }