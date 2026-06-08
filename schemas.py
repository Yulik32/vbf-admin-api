# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# ----- User schemas -----
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "user"  # super_admin, admin, editor, viewer

class UserCreate(UserBase):
    password: str
    page_permissions: Optional[Dict[str, Any]] = None  # {"pages": ["vacancies", "carcatalog"], "can_edit": True}

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    page_permissions: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    page_permissions: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----- Auth schemas -----
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# ----- Page permissions schemas -----
class AvailablePage(BaseModel):
    key: str
    name_ru: str
    name_en: str

class UserPagePermissions(BaseModel):
    pages: List[str] = []
    can_edit: bool = False
    can_view: bool = True

# ----- Card schemas -----
class CardBase(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    order: int = 0

class CardCreate(CardBase):
    pass

class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None

class CardOut(CardBase):
    id: int
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ----- Setting schemas -----
class SettingCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

class SettingOut(BaseModel):
    id: int
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True