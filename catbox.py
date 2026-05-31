import aiohttp
from fastapi import UploadFile, HTTPException

async def upload_to_catbox(file: UploadFile) -> str:
    """
    Загружает файл на catbox.moe и возвращает прямую ссылку
    
    Как использовать:
        url = await upload_to_catbox(file)
    
    Аргументы:
        file: файл из формы UploadFile (FastAPI)
    
    Возвращает:
        str: прямая ссылка на файл (https://files.catbox.moe/abc123.jpg)
    """
    
    # API адрес Catbox
    CATBOX_API_URL = "https://catbox.moe/user/api.php"
    
    # Подготавливаем данные для отправки
    form_data = aiohttp.FormData()
    form_data.add_field('reqtype', 'fileupload')
    form_data.add_field('fileToUpload', file.file, filename=file.filename)
    
    # Отправляем запрос
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(CATBOX_API_URL, data=form_data) as response:
                result = await response.text()
                
                # Если загрузка успешна, Catbox возвращает прямую ссылку
                if response.status == 200 and result.startswith('https://'):
                    return result.strip()
                else:
                    # Если ошибка
                    raise HTTPException(
                        status_code=500,
                        detail=f"Catbox error: {result}"
                    )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Connection error: {str(e)}"
            )