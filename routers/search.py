# routers/search.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database import get_db
import models
from typing import List, Optional

router = APIRouter(prefix="/search", tags=["search"])

# Список страниц для поиска с их отображаемыми названиями
PAGES_CONFIG = {
    "main": {"name_ru": "Главная страница", "name_en": "Home page", "route": "/"},
    "history": {"name_ru": "История", "name_en": "History", "route": "/history"},
    "managers": {"name_ru": "Руководители", "name_en": "Managers", "route": "/managers"},
    "license": {"name_ru": "Лицензии и качество", "name_en": "Licenses and quality", "route": "/license"},
    "rent": {"name_ru": "Аренда", "name_en": "Rent", "route": "/rent"},
    "realty": {"name_ru": "Недвижимость", "name_en": "Realty", "route": "/realty"},
    "service": {"name_ru": "Служба продаж", "name_en": "Sales service", "route": "/service"},
    "catalog": {"name_ru": "Каталог", "name_en": "Catalog", "route": "/catalog"},
    "carcatalog": {"name_ru": "Автокаталог", "name_en": "Auto catalog", "route": "/carcatalog"},
    "other_products": {"name_ru": "Прочая продукция", "name_en": "Other products", "route": "/otherproducts"},
    "individual_packaging": {"name_ru": "Подшипники в упаковке", "name_en": "Packaged bearings", "route": "/individualpackaging"},
    "repairkits": {"name_ru": "Ремкомплекты", "name_en": "Repair kits", "route": "/repairkits"},
    "oxrana": {"name_ru": "Охрана труда", "name_en": "Labor protection", "route": "/oxrana"},
    "job": {"name_ru": "Вакансии", "name_en": "Vacancies", "route": "/job"},
    "news": {"name_ru": "Новости", "name_en": "News", "route": "/news"},
    "counterfeit": {"name_ru": "Контрафакт", "name_en": "Counterfeit", "route": "/counterfeit"},
    "yp": {"name_ru": "Управление персоналом", "name_en": "HR management", "route": "/yp"},
}

@router.get("/")
def search(
    q: str,
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    """
    Поиск по всем страницам сайта
    """
    if not q or len(q.strip()) < 2:
        return {"results": [], "message": "Введите минимум 2 символа для поиска"}
    
    search_term = f"%{q.lower()}%"
    results = []
    
    # 1. Поиск по страницам контента (page_content)
    page_contents = db.query(models.PageContent).filter(
        or_(
            func.lower(models.PageContent.content).like(search_term),
            func.lower(models.PageContent.section).like(search_term)
        )
    ).all()
    
    for content in page_contents:
        page_config = PAGES_CONFIG.get(content.page)
        if page_config:
            existing = next((r for r in results if r["page"] == content.page), None)
            if existing:
                if content.content and q.lower() in content.content.lower():
                    fragment = get_fragment(content.content, q)
                    if fragment not in existing["fragments"]:
                        existing["fragments"].append(fragment)
            else:
                results.append({
                    "page": content.page,
                    "title": page_config[f"name_{lang}"],
                    "route": page_config["route"],
                    "fragments": [get_fragment(content.content, q)] if content.content and q.lower() in content.content.lower() else []
                })
    
    # 2. Поиск по вакансиям
    vacancies = db.query(models.Vacancy).filter(
        models.Vacancy.is_active == True
    ).filter(
        or_(
            func.lower(models.Vacancy.title_ru).like(search_term),
            func.lower(models.Vacancy.title_en).like(search_term),
            func.lower(models.Vacancy.description_ru).like(search_term),
            func.lower(models.Vacancy.description_en).like(search_term),
            func.lower(models.Vacancy.experience_ru).like(search_term),
            func.lower(models.Vacancy.experience_en).like(search_term),
            func.lower(models.Vacancy.salary_ru).like(search_term),
            func.lower(models.Vacancy.salary_en).like(search_term)
        )
    ).all()
    
    for vacancy in vacancies:
        title = vacancy.title_ru if lang == "ru" else vacancy.title_en
        # Название страницы - "Вакансии", а в title - конкретная вакансия
        results.append({
            "page": "job",
            "title": title,  # Название вакансии
            "page_name": "Вакансии" if lang == "ru" else "Vacancies",  # Название страницы
            "route": "/job",
            "fragments": [get_fragment(vacancy.description_ru if lang == "ru" else vacancy.description_en, q)] if vacancy.description_ru else []
        })
    
    # 3. Поиск по руководителям
    managers = db.query(models.Manager).filter(
        models.Manager.is_active == True
    ).filter(
        or_(
            func.lower(models.Manager.name_ru).like(search_term),
            func.lower(models.Manager.name_en).like(search_term),
            func.lower(models.Manager.position_ru).like(search_term),
            func.lower(models.Manager.position_en).like(search_term)
        )
    ).all()
    
    for manager in managers:
        name = manager.name_ru if lang == "ru" else manager.name_en
        position = manager.position_ru if lang == "ru" else manager.position_en
        results.append({
            "page": "managers",
            "title": f"{name} - {position}",
            "page_name": "Руководители" if lang == "ru" else "Managers",  # Название страницы
            "route": "/managers",
            "fragments": [f"{position}"]
        })
    
    # 4. Поиск по документам охраны труда
    oxrana_docs = db.query(models.OxranaDocument).filter(
        models.OxranaDocument.is_active == True
    ).filter(
        or_(
            func.lower(models.OxranaDocument.title_ru).like(search_term),
            func.lower(models.OxranaDocument.title_en).like(search_term)
        )
    ).all()
    
    for doc in oxrana_docs:
        title = doc.title_ru if lang == "ru" else doc.title_en
        results.append({
            "page": "oxrana",
            "title": title,
            "page_name": "Охрана труда" if lang == "ru" else "Labor Protection",
            "route": "/oxrana",
            "fragments": [f"Документ: {title}"]
        })
    
    # 5. Поиск по сертификатам качества
    quality_cards = db.query(models.QualityCard).filter(
        models.QualityCard.is_active == True
    ).filter(
        or_(
            func.lower(models.QualityCard.title_ru).like(search_term),
            func.lower(models.QualityCard.title_en).like(search_term),
            func.lower(models.QualityCard.description_ru).like(search_term),
            func.lower(models.QualityCard.description_en).like(search_term)
        )
    ).all()
    
    for card in quality_cards:
        title = card.title_ru if lang == "ru" else card.title_en
        results.append({
            "page": "license",
            "title": title,
            "page_name": "Лицензии и качество" if lang == "ru" else "Licenses and Quality",
            "route": "/license",
            "fragments": [card.description_ru[:150] + "..." if card.description_ru else ""]
        })
    
    # Удаляем дубликаты страниц
    unique_results = {}
    for result in results:
        key = result["page"]
        if key not in unique_results:
            unique_results[key] = result
        else:
            for frag in result.get("fragments", []):
                if frag and frag not in unique_results[key]["fragments"]:
                    unique_results[key]["fragments"].append(frag)
    
    return {"results": list(unique_results.values()), "count": len(unique_results)}


def get_fragment(text: str, query: str, length: int = 150) -> str:
    """
    Возвращает фрагмент текста вокруг найденного слова
    """
    if not text:
        return ""
    
    text_lower = text.lower()
    query_lower = query.lower()
    
    pos = text_lower.find(query_lower)
    if pos == -1:
        return text[:length] + "..." if len(text) > length else text
    
    start = max(0, pos - 50)
    end = min(len(text), pos + len(query) + 100)
    
    fragment = text[start:end]
    
    if start > 0:
        fragment = "..." + fragment
    if end < len(text):
        fragment = fragment + "..."
    
    return fragment


@router.get("/suggest")
def search_suggest(
    q: str,
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    """
    Быстрый поиск для подсказок (автокомплит)
    """
    if not q or len(q.strip()) < 2:
        return {"suggestions": []}
    
    search_term = f"%{q.lower()}%"
    suggestions = []
    
    # Поиск по страницам
    page_contents = db.query(models.PageContent).filter(
        func.lower(models.PageContent.content).like(search_term)
    ).limit(5).all()
    
    for content in page_contents:
        page_config = PAGES_CONFIG.get(content.page)
        if page_config:
            suggestions.append({
                "title": page_config[f"name_{lang}"],
                "route": page_config["route"],
                "type": "page"
            })
    
    # Поиск по вакансиям
    vacancies = db.query(models.Vacancy).filter(
        models.Vacancy.is_active == True,
        func.lower(models.Vacancy.title_ru).like(search_term)
    ).limit(5).all()
    
    for vacancy in vacancies:
        suggestions.append({
            "title": vacancy.title_ru if lang == "ru" else vacancy.title_en,
            "route": "/job",
            "type": "vacancy"
        })
    
    # Убираем дубликаты
    unique = []
    for s in suggestions:
        if s not in unique:
            unique.append(s)
    
    return {"suggestions": unique[:10]}