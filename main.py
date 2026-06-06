from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from routers import auth, users, cards, settings, content, upload, realty, managers, service, oxrana, license, catalog, vacancies, search
import os

# Создаём таблицы в БД
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Admin Panel API",
    description="API для React админ-панели",
    version="1.0.0"
)

# CORS для React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://yulyafjo.beget.tech",
        "https://yulyafjo.beget.tech"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cards.router)
app.include_router(settings.router)
app.include_router(content.router)
app.include_router(upload.router)
app.include_router(realty.router)
app.include_router(managers.router)
app.include_router(service.router)
app.include_router(oxrana.router)
app.include_router(license.router)
app.include_router(catalog.router)
app.include_router(vacancies.router)
app.include_router(search.router)

# ========== МОНТИРУЕМ ВСЕ СТАТИЧЕСКИЕ ПАПКИ ==========

# Папка для загруженных файлов
uploads_path = "uploads"
if not os.path.exists(uploads_path):
    os.makedirs(uploads_path)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

# Папка gallery (если есть)
if os.path.exists("gallery"):
    app.mount("/gallery", StaticFiles(directory="gallery"), name="gallery")

# Папка license (если есть)
if os.path.exists("license"):
    app.mount("/license", StaticFiles(directory="license"), name="license")

# Папка docs (если есть)
if os.path.exists("docs"):
    app.mount("/docs", StaticFiles(directory="docs"), name="docs")

# Папка catalog (если есть)
if os.path.exists("catalog"):
    app.mount("/catalog", StaticFiles(directory="catalog"), name="catalog")

# Папка quality (если есть)
if os.path.exists("quality"):
    app.mount("/quality", StaticFiles(directory="quality"), name="quality")

@app.get("/")
def root():
    return {"message": "Admin API is running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}