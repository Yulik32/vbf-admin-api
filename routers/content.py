# routers/content.py
import os
import boto3
import uuid
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response
from sqlalchemy.orm import Session
from database import get_db
import models
from dependencies import get_current_user, check_page_permission

router = APIRouter(prefix="/content", tags=["content"])

# ========== Настройки Yandex Cloud Object Storage ==========
YC_ACCESS_KEY = os.getenv("YC_ACCESS_KEY")
YC_SECRET_KEY = os.getenv("YC_SECRET_KEY")
YC_BUCKET = os.getenv("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

# ========== Вспомогательная функция для проверки прав ==========
def check_content_permission(page: str, current_user: models.User, action: str = "edit"):
    page_keys = {
        "main": "main_page",
        "history": "history",
        "managers": "managers",
        "license": "license",
        "rent": "rent",
        "realty": "realty",
        "service": "service",
        "catalog": "catalog",
        "carcatalog": "carcatalog",
        "other_products": "other_products",
        "individual_packaging": "individual_packaging",
        "repairkits": "repairkits",
        "oxrana": "oxrana",
        "job": "job",
    }
    page_key = page_keys.get(page, page)
    return check_page_permission(current_user, page_key, action)

# Функции для проверки прав - ВОЗВРАЩАЮТ ЗАВИСИМОСТЬ
def require_content_edit(page: str):
    async def dependency(current_user: models.User = Depends(get_current_user)):
        if current_user.role in ["admin", "super_admin"]:
            return current_user
        if not check_content_permission(page, current_user, "edit"):
            raise HTTPException(status_code=403, detail=f"No edit rights for {page} content")
        return current_user
    return dependency

def require_content_view(page: str):
    async def dependency(current_user: models.User = Depends(get_current_user)):
        if current_user.role in ["admin", "super_admin"]:
            return current_user
        if not check_content_permission(page, current_user, "view"):
            raise HTTPException(status_code=403, detail=f"No view rights for {page} content")
        return current_user
    return dependency

# ========== OPTIONS ==========
@router.options("/upload")
async def options_upload():
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
        "Access-Control-Allow-Credentials": "true",
    })

@router.options("/{page}")
async def options_page(page: str):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
        "Access-Control-Allow-Credentials": "true",
    })

@router.options("/{page}/gallery")
async def options_gallery(page: str):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
        "Access-Control-Allow-Credentials": "true",
    })

@router.options("/gallery/{image_id}")
async def options_gallery_image(image_id: int):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
        "Access-Control-Allow-Credentials": "true",
    })

# ========== ЗАГРУЗКА ФАЙЛОВ ==========
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "super_admin"]:
        page_keys = ["main_page", "history", "managers", "license", "rent", "realty", 
                     "service", "catalog", "carcatalog", "other_products", 
                     "individual_packaging", "repairkits", "oxrana", "job"]
        has_edit_rights = any(check_page_permission(current_user, key, "edit") for key in page_keys)
        if not has_edit_rights:
            raise HTTPException(status_code=403, detail="No edit rights for any content page")
    
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
        key = f"content/{unique_filename}"
        content = await file.read()
        s3.put_object(
            Bucket=YC_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type,
            ACL='public-read'
        )
        return {"url": f"https://storage.yandexcloud.net/{YC_BUCKET}/{key}"}
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

# ========== ПУБЛИЧНЫЙ ЭНДПОИНТ ==========
@router.get("/{page}")
def get_page_content(page: str, lang: str = "ru", db: Session = Depends(get_db)):
    contents = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.language == lang
    ).all()
    result = {}
    for item in contents:
        result[item.section] = item.content
    gallery = db.query(models.GalleryImage).filter(
        models.GalleryImage.page == page,
        models.GalleryImage.is_active == True
    ).order_by(models.GalleryImage.image_order).all()
    result['gallery'] = [{
        'id': img.id,
        'url': img.image_url,
        'alt': img.alt_ru if lang == 'ru' else img.alt_en,
        'order': img.image_order
    } for img in gallery]
    return result

# ========== АДМИНСКИЕ ЭНДПОИНТЫ ==========

@router.put("/{page}/{section}")
async def update_content(
    page: str,
    section: str,
    content_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_content_edit(page))  # page определен выше
):
    content_item = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.section == section,
        models.PageContent.language == content_data.get('language', 'ru')
    ).first()
    if content_item:
        content_item.content = content_data.get('content', '')
        content_item.updated_by = current_user.id
    else:
        content_item = models.PageContent(
            page=page,
            section=section,
            language=content_data.get('language', 'ru'),
            content=content_data.get('content', ''),
            updated_by=current_user.id
        )
        db.add(content_item)
    db.commit()
    return {"message": "Content updated"}

@router.get("/admin/{page}")
async def get_page_content_admin(
    page: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_content_view(page))  # page определен выше
):
    ru_contents = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.language == 'ru'
    ).all()
    en_contents = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.language == 'en'
    ).all()
    result = {}
    for item in ru_contents:
        result[f"{item.section}_ru"] = item.content
    for item in en_contents:
        result[f"{item.section}_en"] = item.content
    gallery = db.query(models.GalleryImage).filter(
        models.GalleryImage.page == page
    ).order_by(models.GalleryImage.image_order).all()
    result['gallery'] = [{
        'id': img.id,
        'url': img.image_url,
        'alt_ru': img.alt_ru,
        'alt_en': img.alt_en,
        'order': img.image_order,
        'is_active': img.is_active
    } for img in gallery]
    return result

@router.post("/{page}/gallery")
async def add_gallery_image(
    page: str,
    image_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_content_edit(page))  # page определен выше
):
    image = models.GalleryImage(
        page=page,
        image_url=image_data.get('url'),
        alt_ru=image_data.get('alt_ru', ''),
        alt_en=image_data.get('alt_en', ''),
        image_order=image_data.get('order', 0)
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return {"id": image.id, "message": "Image added"}

@router.delete("/gallery/{image_id}")
async def delete_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    image = db.query(models.GalleryImage).filter(models.GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    if not check_content_permission(image.page, current_user, "edit"):
        if current_user.role not in ["admin", "super_admin"]:
            raise HTTPException(status_code=403, detail=f"No edit rights for {image.page} gallery")
    db.delete(image)
    db.commit()
    return {"message": "Image deleted"}