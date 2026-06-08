# routers/car_catalog.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
from pydantic import BaseModel
from dependencies import get_current_user, check_page_permission
from datetime import datetime

router = APIRouter(prefix="/car-catalog", tags=["car-catalog"])

# ==================== СХЕМЫ ====================

class CarCatalogItemBase(BaseModel):
    installation_location_ru: str
    installation_location_en: str
    symbol: str
    vpz_designation: Optional[str] = ""
    display_order: int = 0

class CarCatalogItemCreate(CarCatalogItemBase):
    table_id: int

class CarCatalogItemUpdate(BaseModel):
    installation_location_ru: Optional[str] = None
    installation_location_en: Optional[str] = None
    symbol: Optional[str] = None
    vpz_designation: Optional[str] = None
    display_order: Optional[int] = None

class CarCatalogItemResponse(CarCatalogItemBase):
    id: int
    table_id: int
    
    class Config:
        from_attributes = True


class CarCatalogTableBase(BaseModel):
    table_key: str
    car_name_ru: str
    car_name_en: str
    section: str = "passenger"
    display_order: int = 0

class CarCatalogTableCreate(CarCatalogTableBase):
    pass

class CarCatalogTableUpdate(BaseModel):
    car_name_ru: Optional[str] = None
    car_name_en: Optional[str] = None
    section: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class CarCatalogTableResponse(CarCatalogTableBase):
    id: int
    section: str
    display_order: int
    is_active: bool
    items: List[CarCatalogItemResponse] = []
    
    class Config:
        from_attributes = True


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def require_carcatalog_edit(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на редактирование автокаталога"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "carcatalog", "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No edit rights for car catalog"
        )
    return current_user

def require_carcatalog_view(current_user: models.User = Depends(get_current_user)):
    """Проверяет права на просмотр автокаталога в админке"""
    if current_user.role in ["admin", "super_admin"]:
        return current_user
    
    if not check_page_permission(current_user, "carcatalog", "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No view rights for car catalog"
        )
    return current_user


# ==================== ОБРАБОТКА OPTIONS ЗАПРОСОВ ====================

@router.options("/tables")
async def options_tables():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/tables/{table_id}")
async def options_table(table_id: int):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/items")
async def options_items():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/items/{item_id}")
async def options_item(item_id: int):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@router.options("/import")
async def options_import():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Credentials": "true",
        }
    )


# ==================== ПУБЛИЧНЫЕ ЭНДПОИНТЫ (без авторизации) ====================

# Получить все таблицы с записями (публичный)
@router.get("/tables", response_model=List[CarCatalogTableResponse])
def get_tables(
    section: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.is_active == True
    )
    
    if section:
        query = query.filter(models.CarCatalogTable.section == section)
    
    tables = query.order_by(models.CarCatalogTable.display_order).all()
    
    for table in tables:
        table.items = db.query(models.CarCatalogItem).filter(
            models.CarCatalogItem.table_id == table.id
        ).order_by(models.CarCatalogItem.display_order).all()
    
    return tables


# Получить одну таблицу (публичный)
@router.get("/tables/{table_id}", response_model=CarCatalogTableResponse)
def get_table(
    table_id: int,
    db: Session = Depends(get_db)
):
    table = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.id == table_id,
        models.CarCatalogTable.is_active == True
    ).first()
    
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    table.items = db.query(models.CarCatalogItem).filter(
        models.CarCatalogItem.table_id == table.id
    ).order_by(models.CarCatalogItem.display_order).all()
    
    return table


# ==================== АДМИНСКИЕ ЭНДПОИНТЫ (с проверкой прав) ====================

# Получить все таблицы для админки (включая неактивные)
@router.get("/tables/admin/all")
def get_tables_admin(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_view)
):
    """Получить все таблицы для админки (включая неактивные)"""
    tables = db.query(models.CarCatalogTable).order_by(models.CarCatalogTable.display_order).all()
    
    for table in tables:
        table.items = db.query(models.CarCatalogItem).filter(
            models.CarCatalogItem.table_id == table.id
        ).order_by(models.CarCatalogItem.display_order).all()
    
    return tables


# Создать таблицу
@router.post("/tables", response_model=CarCatalogTableResponse)
def create_table(
    table: CarCatalogTableCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    existing = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.table_key == table.table_key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Table key already exists")
    
    new_table = models.CarCatalogTable(
        table_key=table.table_key,
        car_name_ru=table.car_name_ru,
        car_name_en=table.car_name_en,
        section=table.section,
        display_order=table.display_order,
        updated_by=current_user.id
    )
    db.add(new_table)
    db.commit()
    db.refresh(new_table)
    
    new_table.items = []
    return new_table


# Обновить таблицу
@router.put("/tables/{table_id}", response_model=CarCatalogTableResponse)
def update_table(
    table_id: int,
    table_update: CarCatalogTableUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    db_table = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.id == table_id
    ).first()
    
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    update_data = table_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_table, field, value)
    
    db_table.updated_by = current_user.id
    db_table.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_table)
    
    db_table.items = db.query(models.CarCatalogItem).filter(
        models.CarCatalogItem.table_id == db_table.id
    ).order_by(models.CarCatalogItem.display_order).all()
    
    return db_table


# Удалить таблицу (мягкое удаление)
@router.delete("/tables/{table_id}")
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    db_table = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.id == table_id
    ).first()
    
    if not db_table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    db_table.is_active = False
    db_table.updated_by = current_user.id
    db.commit()
    
    return {"message": "Table deleted successfully"}


# ==================== ЗАПИСИ ====================

# Создать запись
@router.post("/items", response_model=CarCatalogItemResponse)
def create_item(
    item: CarCatalogItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    table = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.id == item.table_id,
        models.CarCatalogTable.is_active == True
    ).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    new_item = models.CarCatalogItem(
        table_id=item.table_id,
        installation_location_ru=item.installation_location_ru,
        installation_location_en=item.installation_location_en,
        symbol=item.symbol,
        vpz_designation=item.vpz_designation,
        display_order=item.display_order
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return new_item


# Обновить запись
@router.put("/items/{item_id}", response_model=CarCatalogItemResponse)
def update_item(
    item_id: int,
    item_update: CarCatalogItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    db_item = db.query(models.CarCatalogItem).filter(
        models.CarCatalogItem.id == item_id
    ).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)
    
    db_item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_item)
    
    return db_item


# Удалить запись
@router.delete("/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    db_item = db.query(models.CarCatalogItem).filter(
        models.CarCatalogItem.id == item_id
    ).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    
    return {"message": "Item deleted successfully"}


# Массовое обновление порядка записей
@router.put("/items/reorder")
def reorder_items(
    items: List[dict],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    for item_data in items:
        db.query(models.CarCatalogItem).filter(
            models.CarCatalogItem.id == item_data['id']
        ).update({"display_order": item_data['display_order']})
    
    db.commit()
    return {"message": "Items reordered successfully"}


# ==================== ИМПОРТ ИЗ JSON ====================

@router.post("/import")
def import_from_json(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_carcatalog_edit)
):
    # Импортируем данные из вашего файла
    from data.carcatalogData import get_carcatalog_data
    
    data = get_carcatalog_data('ru')
    
    # Очищаем существующие данные
    db.query(models.CarCatalogItem).delete()
    db.query(models.CarCatalogTable).delete()
    
    for i, table_data in enumerate(data):
        if i < 14:
            section = "passenger"
        elif i < 16:
            section = "up_to_3t"
        else:
            section = "truck"
        
        table = models.CarCatalogTable(
            table_key=table_data['id'],
            car_name_ru=table_data['carName'],
            car_name_en=table_data['carName'],
            section=section,
            display_order=i,
            updated_by=current_user.id
        )
        db.add(table)
        db.flush()
        
        for j, item_data in enumerate(table_data['data']):
            item = models.CarCatalogItem(
                table_id=table.id,
                installation_location_ru=item_data['installationLocation'],
                installation_location_en=item_data['installationLocation'],
                symbol=item_data['symbol'],
                vpz_designation=item_data['vpzDesignation'],
                display_order=j
            )
            db.add(item)
    
    db.commit()
    return {"message": f"Imported {len(data)} tables successfully"}