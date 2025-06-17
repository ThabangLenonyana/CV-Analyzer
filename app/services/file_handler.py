import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple
from fastapi import UploadFile, HTTPException

from app.config import config

logger = logging.getLogger(__name__)

class FileHandler:
    """Service for handling file operations"""
    
    def __init__(self, upload_folder: str = None):
        self.upload_folder = Path(upload_folder or config.UPLOAD_FOLDER)
        self.upload_folder.mkdir(exist_ok=True)
    
    async def save_uploaded_file(self, file: UploadFile) -> Tuple[str, bytes, int]:
        """
        Save uploaded file and return filename, content, and size
        
        Returns:
            Tuple of (saved_filename, file_content, file_size)
        """
        # Validate file extension
        if not config.is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > config.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB"
            )
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = self.upload_folder / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"File saved: {filename}")
        return filename, content, file_size
    
    def delete_file(self, filename: str) -> bool:
        """Delete a file from the upload folder"""
        try:
            file_path = self.upload_folder / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False
    
    def get_file_path(self, filename: str) -> Path:
        """Get full path for a filename"""
        return self.upload_folder / filename