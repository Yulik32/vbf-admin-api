from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, users, cards, settings, content, upload, realty, managers, service, oxrana, license, catalog
from fastapi.staticfiles import StaticFiles
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
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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


# Создаём папку для загруженных файлов
uploads_path = "uploads"
if not os.path.exists(uploads_path):
    os.makedirs(uploads_path)

# Монтируем папку для статики
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

@app.get("/")
def root():
    return {"message": "Admin API is running", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}