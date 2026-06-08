# routers/settings.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from dependencies import get_current_user, check_page_permission

router = APIRouter(prefix="/settings", tags=["settings"])

# ========== Вспомогательная функция для проверки прав на настройки ==========
def require_settings_access(action: str = "view"):
    """Проверяет права доступа к настройкам"""
    def checker(current_user: models.User = Depends(get_current_user)):
        # admin и super_admin имеют полный доступ
        if current_user.role in ["admin", "super_admin"]:
            return current_user
        
        # Настройки обычно доступны только админам
        # Но если нужно дать доступ редакторам - можно добавить
        page_key = "settings"
        if not check_page_permission(current_user, page_key, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No {action} rights for settings"
            )
        return current_user
    return checker

# ========== ОБРАБОТКА OPTIONS ЗАПРОСОВ ДЛЯ CORS ==========
@router.options("/")
async def options_settings():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/{key}")
async def options_setting():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# ========== Публичные эндпоинты (без авторизации) ==========

# GET /settings/{key} — публичный, читаем настройки сайта
@router.get("/{key}", response_model=schemas.SettingOut)
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

# GET /settings/ — все настройки, публично
@router.get("/", response_model=list[schemas.SettingOut])
def get_all_settings(db: Session = Depends(get_db)):
    return db.query(models.SiteSetting).all()

# ========== Админские эндпоинты (с проверкой прав) ==========

# POST /settings/ — создать настройку
@router.post("/", response_model=schemas.SettingOut)
def create_setting(
    setting: schemas.SettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_settings_access("edit"))
):
    existing = db.query(models.SiteSetting).filter(models.SiteSetting.key == setting.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setting key already exists")
    
    db_setting = models.SiteSetting(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        updated_by=current_user.id
    )
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

# PUT /settings/{key} — обновить настройку
@router.put("/{key}", response_model=schemas.SettingOut)
def update_setting(
    key: str,
    setting_update: schemas.SettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_settings_access("edit"))
):
    db_setting = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    update_data = setting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_setting, field, value)
    
    db_setting.updated_by = current_user.id
    db.commit()
    db.refresh(db_setting)
    return db_setting

# DELETE /settings/{key} — удалить настройку
@router.delete("/{key}")
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_settings_access("edit"))
):
    db_setting = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    db.delete(db_setting)
    db.commit()
    return {"message": "Setting deleted successfully"}

# GET /settings/admin/all — получить все настройки для админки (включая неактивные)
@router.get("/admin/all")
def get_all_settings_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_settings_access("view"))
):
    """Получить все настройки для админки"""
    settings = db.query(models.SiteSetting).order_by(models.SiteSetting.key).all()
    return [{
        "id": s.id,
        "key": s.key,
        "value": s.value,
        "description": s.description,
        "updated_at": s.updated_at
    } for s in settings]