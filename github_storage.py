import os
import base64
from github import Github
from github import GithubException
from fastapi import UploadFile, HTTPException

async def upload_to_github(file: UploadFile) -> str:
    """
    Загружает файл в репозиторий GitHub и возвращает прямую ссылку
    """
    # Получаем токен из переменной окружения
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN not configured. Please add it to environment variables."
        )
    
    # Настройки репозитория
    REPO_NAME = "Yulik32/vbf-admin-api"  # ЗАМЕНИТЕ на ваше имя репозитория!
    BRANCH = "main"
    UPLOAD_FOLDER = "uploads/license"   # Папка в репозитории
    
    try:
        # Подключаемся к GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Читаем содержимое файла
        content = await file.read()
        
        # Генерируем уникальное имя файла
        import uuid
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Путь к файлу в репозитории
        file_path = f"{UPLOAD_FOLDER}/{unique_filename}"
        
        # Кодируем содержимое в base64
        encoded_content = base64.b64encode(content).decode('utf-8')
        
        # Загружаем файл в репозиторий
        try:
            # Проверяем, существует ли уже файл
            existing_file = repo.get_contents(file_path, ref=BRANCH)
            # Если существует, обновляем
            repo.update_file(
                path=file_path,
                message=f"Update {unique_filename}",
                content=encoded_content,
                sha=existing_file.sha,
                branch=BRANCH
            )
        except GithubException:
            # Если файла нет, создаём новый
            repo.create_file(
                path=file_path,
                message=f"Upload {unique_filename}",
                content=encoded_content,
                branch=BRANCH
            )
        
        # Формируем прямую ссылку на raw-файл
        raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/{BRANCH}/{file_path}"
        
        return raw_url
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"GitHub upload error: {str(e)}"
        )