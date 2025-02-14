
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from app.config import (
    DOWNLOAD_DIR,
)


# Iniatialize router file
router = APIRouter()


@router.get('/get-file/{file_name}', name='get_file')
async def get_file(file_name: str):
    """
    Get a file by its name from the downloads directory.
    """
    import mimetypes
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'  # Fallback MIME type


    return FileResponse(
        file_path, 
        # media_type='application/octet-stream',
        # filename=file_name
        media_type=mime_type,  # Use the correct MIME type for your video
        headers={"Content-Disposition": f"inline; filename={file_name}"}
    )
