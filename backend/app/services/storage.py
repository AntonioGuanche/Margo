"""File storage service — local for dev, R2 later."""

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


async def save_upload(file: UploadFile, subfolder: str = "menus") -> str:
    """Save an uploaded file to local storage.

    Returns the relative path to the saved file.
    """
    folder = UPLOAD_DIR / subfolder
    folder.mkdir(exist_ok=True)

    # Sanitize filename
    original_name = file.filename or "upload"
    filename = f"{uuid4().hex}_{original_name}"
    path = folder / filename

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return str(path)
