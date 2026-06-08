# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from database import get_db
from dependencies import get_password_hash, verify_password, get_current_user
from auth import create_access_token
import models

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    """Вход в систему"""
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    access_token = create_access_token(data={"sub": user.email, "email": user.email})
    
    # Возвращаем информацию о пользователе вместе с токеном
    import json
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "page_permissions": json.loads(user.page_permissions) if user.page_permissions else {"pages": [], "can_edit": False}
        }
    }

@router.post("/register")
def register(email: str, password: str, full_name: str = None, db: Session = Depends(get_db)):
    """Регистрация нового пользователя (только для super_admin)"""
    # Проверка существующего пользователя
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(password)
    
    new_user = models.User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role="viewer",  # По умолчанию - только просмотр
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}