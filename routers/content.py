from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from dependencies import get_current_user

router = APIRouter(prefix="/content", tags=["content"])

# Получить весь контент для страницы (публичный)
@router.get("/{page}")
def get_page_content(
    page: str,
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    contents = db.query(models.PageContent).filter(
        models.PageContent.page == page,
        models.PageContent.language == lang
    ).all()
    
    result = {}
    for item in contents:
        result[item.section] = item.content
    
    # Также получаем галерею для страницы
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

# Обновить контент страницы (только админ)
@router.put("/{page}/{section}")
def update_content(
    page: str,
    section: str,
    content_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Проверяем, что пользователь админ
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
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

# Управление галереей
@router.post("/{page}/gallery")
def add_gallery_image(
    page: str,
    image_data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
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
def delete_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin rights required")
    
    image = db.query(models.GalleryImage).filter(models.GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    db.delete(image)
    db.commit()
    return {"message": "Image deleted"}