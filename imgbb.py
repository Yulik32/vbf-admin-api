import aiohttp
import base64
import os
from fastapi import UploadFile, HTTPException

async def upload_to_imgbb(file: UploadFile) -> str:
    # Берём API ключ из переменной окружения (безопасно!)
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")
    
    if not IMGBB_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="IMG BB API key not configured. Please add IMGBB_API_KEY to environment variables."
        )
    
    IMGBB_API_URL = "https://api.imgbb.com/1/upload"
    
    content = await file.read()
    encoded_image = base64.b64encode(content).decode('utf-8')
    
    data = {
        'key': IMGBB_API_KEY,
        'image': encoded_image,
        'name': file.filename,
        'expiration': 0
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(IMGBB_API_URL, data=data) as response:
                result = await response.json()
                
                if result.get('success'):
                    return result['data']['url']
                else:
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    raise HTTPException(
                        status_code=500,
                        detail=f"ImgBB error: {error_msg}"
                    )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Connection error: {str(e)}"
            )