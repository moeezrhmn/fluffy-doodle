
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from app.config import (
    DOWNLOAD_DIR,
)
import mimetypes


# Iniatialize router file
router = APIRouter()


@router.get("/get-file/{file_name}", name="get_file")
async def get_file(file_name: str):
    """
    Serve a file from the downloads directory.
    """

    # Ensure the file exists
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if not os.path.isfile(file_path):  # Use isfile to prevent directory traversal attacks
        raise HTTPException(status_code=404, detail="File not found")

    # Guess MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"  # Fallback MIME type

    # Return file response with correct headers
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_name,  # Ensures correct filename when downloading
        headers={"Content-Disposition": f"inline; filename={file_name}"}  # `inline` allows direct viewing in browser
    )