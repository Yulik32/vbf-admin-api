from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from dependencies import get_current_admin

router = APIRouter(prefix="/settings", tags=["settings"])

# GET /settings (публичный — читаем настройки сайта)
@router.get("/{key}", response_model=schemas.SettingOut)
def get_setting(key: str, db: Session = Depends(get_db)):
    setting = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

# GET /settings (все настройки, публично)
@router.get("/", response_model=list[schemas.SettingOut])
def get_all_settings(db: Session = Depends(get_db)):
    return db.query(models.SiteSetting).all()

# POST /settings (только админ)
@router.post("/", response_model=schemas.SettingOut)
def create_setting(
    setting: schemas.SettingCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    existing = db.query(models.SiteSetting).filter(models.SiteSetting.key == setting.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setting key already exists")
    
    db_setting = models.SiteSetting(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        updated_by=admin.id
    )
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

# PUT /settings/{key} (только админ)
@router.put("/{key}", response_model=schemas.SettingOut)
def update_setting(
    key: str,
    setting_update: schemas.SettingUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    db_setting = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    update_data = setting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_setting, field, value)
    
    db_setting.updated_by = admin.id
    db.commit()
    db.refresh(db_setting)
    return db_setting

# DELETE /settings/{key} (только админ)
@router.delete("/{key}")
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    db_setting = db.query(models.SiteSetting).filter(models.SiteSetting.key == key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    db.delete(db_setting)
    db.commit()
    return {"message": "Setting deleted successfully"}