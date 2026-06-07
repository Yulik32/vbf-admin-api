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

# Секции автокаталога для отображения
CARCATALOG_SECTIONS = {
    "passenger": {"name_ru": "Легковые автомобили", "name_en": "Passenger cars"},
    "up_to_3t": {"name_ru": "Автомобили грузоподъемностью до 3т", "name_en": "Trucks up to 3t"},
    "truck": {"name_ru": "Грузовые автомобили", "name_en": "Trucks"}
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
            func.lower(models.Vacancy.description_en).like(search_term)
        )
    ).all()

    for vacancy in vacancies:
        title_vacancy = vacancy.title_ru if lang == "ru" else vacancy.title_en
        description_vacancy = vacancy.description_ru if lang == "ru" else vacancy.description_en
        
        fragment = ""
        if q.lower() in title_vacancy.lower():
            fragment = get_fragment(title_vacancy, q)
        elif description_vacancy and q.lower() in description_vacancy.lower():
            fragment = get_fragment(description_vacancy, q)
        
        results.append({
            "page": "job",
            "title": "Вакансии" if lang == "ru" else "Vacancies",
            "subtitle": title_vacancy,
            "route": "/job",
            "fragments": [fragment] if fragment else [title_vacancy]
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
            "title": "Руководители" if lang == "ru" else "Managers",
            "subtitle": f"{name} - {position}",
            "route": "/managers",
            "fragments": [f"{name} - {position}"]
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
        description = card.description_ru if lang == "ru" else card.description_en
        
        fragment = ""
        if q.lower() in title.lower():
            fragment = get_fragment(title, q)
        elif description and q.lower() in description.lower():
            fragment = get_fragment(description, q)
        
        results.append({
            "page": "license",
            "title": "Лицензии и качество" if lang == "ru" else "Licenses and Quality",
            "subtitle": title,
            "route": "/license",
            "fragments": [fragment] if fragment else [title[:100] + "..."]
        })
    
    # 6. ПОИСК ПО АВТОКАТАЛОГУ
    # Поиск по таблицам (моделям автомобилей)
    car_tables = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.is_active == True
    ).filter(
        or_(
            func.lower(models.CarCatalogTable.car_name_ru).like(search_term),
            func.lower(models.CarCatalogTable.car_name_en).like(search_term)
        )
    ).all()
    
    for table in car_tables:
        car_name = table.car_name_ru if lang == "ru" else table.car_name_en
        section_name = CARCATALOG_SECTIONS.get(table.section, {}).get(f"name_{lang}", table.section)
        
        # Находим фрагмент с искомым словом
        fragment = get_fragment(car_name, q) if q.lower() in car_name.lower() else car_name[:100]
        
        results.append({
            "page": "carcatalog",
            "title": "Автокаталог" if lang == "ru" else "Auto Catalog",
            "subtitle": f"{car_name}",
            "section": section_name,
            "type": "model",
            "table_id": table.id,
            "route": f"/carcatalog?model={table.id}",
            "fragments": [fragment]
        })
    
    # Поиск по записям автокаталога (детали, подшипники)
    car_items = db.query(models.CarCatalogItem).join(
        models.CarCatalogTable
    ).filter(
        models.CarCatalogTable.is_active == True
    ).filter(
        or_(
            func.lower(models.CarCatalogItem.installation_location_ru).like(search_term),
            func.lower(models.CarCatalogItem.installation_location_en).like(search_term),
            func.lower(models.CarCatalogItem.symbol).like(search_term),
            func.lower(models.CarCatalogItem.vpz_designation).like(search_term)
        )
    ).all()
    
    # Группируем результаты по таблицам
    items_by_table = {}
    for item in car_items:
        table = item.table
        car_name = table.car_name_ru if lang == "ru" else table.car_name_en
        section_name = CARCATALOG_SECTIONS.get(table.section, {}).get(f"name_{lang}", table.section)
        
        location = item.installation_location_ru if lang == "ru" else item.installation_location_en
        
        # Формируем фрагмент с найденным словом
        fragment = ""
        if q.lower() in location.lower():
            fragment = get_fragment(location, q)
        elif q.lower() in item.symbol.lower():
            fragment = f"Symbol: {item.symbol}"
        elif item.vpz_designation and q.lower() in item.vpz_designation.lower():
            fragment = f"VPZ: {item.vpz_designation}"
        else:
            fragment = f"{location} | Symbol: {item.symbol}"
        
        key = f"carcatalog_{table.id}"
        if key not in items_by_table:
            items_by_table[key] = {
                "page": "carcatalog",
                "title": "Автокаталог" if lang == "ru" else "Auto Catalog",
                "subtitle": car_name,
                "section": section_name,
                "type": "parts",
                "table_id": table.id,
                "route": f"/carcatalog?model={table.id}",
                "fragments": [],
                "items_count": 0
            }
        
        # Добавляем фрагмент, если его еще нет
        if fragment not in items_by_table[key]["fragments"]:
            items_by_table[key]["fragments"].append(fragment)
        items_by_table[key]["items_count"] += 1
    
    # Добавляем результаты из автокаталога
    for item_result in items_by_table.values():
        # Ограничиваем количество фрагментов до 3
        if len(item_result["fragments"]) > 3:
            item_result["fragments"] = item_result["fragments"][:3]
            item_result["fragments"].append(f"... и еще {item_result['items_count'] - 3} совпадений")
        
        results.append(item_result)
    
    # Удаляем дубликаты страниц
    unique_results = {}
    for result in results:
        # Для автокаталога используем уникальный ключ с table_id
        if result["page"] == "carcatalog" and "table_id" in result:
            key = f"{result['page']}_{result['table_id']}"
        else:
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
    
    # Подсвечиваем найденное слово (опционально)
    # fragment = fragment.replace(query, f"<mark>{query}</mark>")
    
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
    
    # Поиск по моделям автомобилей
    car_models = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.is_active == True,
        or_(
            func.lower(models.CarCatalogTable.car_name_ru).like(search_term),
            func.lower(models.CarCatalogTable.car_name_en).like(search_term)
        )
    ).limit(5).all()
    
    for model in car_models:
        suggestions.append({
            "title": model.car_name_ru if lang == "ru" else model.car_name_en,
            "route": f"/carcatalog?model={model.id}",
            "type": "car_model",
            "section": CARCATALOG_SECTIONS.get(model.section, {}).get(f"name_{lang}", model.section)
        })
    
    # Поиск по деталям (символам и обозначениям)
    car_parts = db.query(models.CarCatalogItem).join(
        models.CarCatalogTable
    ).filter(
        models.CarCatalogTable.is_active == True,
        or_(
            func.lower(models.CarCatalogItem.symbol).like(search_term),
            func.lower(models.CarCatalogItem.vpz_designation).like(search_term),
            func.lower(models.CarCatalogItem.installation_location_ru).like(search_term)
        )
    ).limit(10).all()
    
    for part in car_parts:
        car_name = part.table.car_name_ru if lang == "ru" else part.table.car_name_en
        location = part.installation_location_ru if lang == "ru" else part.installation_location_en
        
        suggestions.append({
            "title": f"{part.symbol} | {location[:50]}",
            "subtitle": car_name,
            "route": f"/carcatalog?model={part.table.id}",
            "type": "car_part",
            "symbol": part.symbol,
            "vpz": part.vpz_designation
        })
    
    # Убираем дубликаты
    unique = []
    seen = set()
    for s in suggestions:
        key = f"{s['type']}_{s['title']}"
        if key not in seen:
            seen.add(key)
            unique.append(s)
    
    return {"suggestions": unique[:15]}


@router.get("/carcatalog")
def search_carcatalog(
    q: str,
    lang: str = "ru",
    db: Session = Depends(get_db)
):
    """
    Специализированный поиск только по автокаталогу
    """
    if not q or len(q.strip()) < 2:
        return {"results": [], "message": "Введите минимум 2 символа для поиска"}
    
    search_term = f"%{q.lower()}%"
    results = {
        "models": [],
        "parts": [],
        "total": 0
    }
    
    # Поиск по моделям автомобилей
    models = db.query(models.CarCatalogTable).filter(
        models.CarCatalogTable.is_active == True,
        or_(
            func.lower(models.CarCatalogTable.car_name_ru).like(search_term),
            func.lower(models.CarCatalogTable.car_name_en).like(search_term)
        )
    ).all()
    
    for model in models:
        results["models"].append({
            "id": model.id,
            "name": model.car_name_ru if lang == "ru" else model.car_name_en,
            "section": model.section,
            "section_name": CARCATALOG_SECTIONS.get(model.section, {}).get(f"name_{lang}", model.section),
            "items_count": db.query(models.CarCatalogItem).filter(
                models.CarCatalogItem.table_id == model.id
            ).count()
        })
    
    # Поиск по деталям
    parts = db.query(models.CarCatalogItem).join(
        models.CarCatalogTable
    ).filter(
        models.CarCatalogTable.is_active == True,
        or_(
            func.lower(models.CarCatalogItem.installation_location_ru).like(search_term),
            func.lower(models.CarCatalogItem.installation_location_en).like(search_term),
            func.lower(models.CarCatalogItem.symbol).like(search_term),
            func.lower(models.CarCatalogItem.vpz_designation).like(search_term)
        )
    ).all()
    
    for part in parts:
        results["parts"].append({
            "id": part.id,
            "table_id": part.table_id,
            "car_model": part.table.car_name_ru if lang == "ru" else part.table.car_name_en,
            "installation_location": part.installation_location_ru if lang == "ru" else part.installation_location_en,
            "symbol": part.symbol,
            "vpz_designation": part.vpz_designation
        })
    
    results["total"] = len(results["models"]) + len(results["parts"])
    
    return results