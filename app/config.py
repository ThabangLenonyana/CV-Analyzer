import os
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Google Gemini Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL")
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "pdf,docx").split(",")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    
    # Application Configuration
    APP_NAME = "CV Analyzer"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # API Rate Limiting (for future implementation)
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY environment variable is required")
        
        if cls.MAX_FILE_SIZE_MB <= 0:
            errors.append("MAX_FILE_SIZE_MB must be greater than 0")
        
        if not cls.ALLOWED_EXTENSIONS:
            errors.append("At least one file extension must be allowed")
        
        # Create upload folder if it doesn't exist
        if not os.path.exists(cls.UPLOAD_FOLDER):
            try:
                os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
            except Exception as e:
                errors.append(f"Failed to create upload folder: {str(e)}")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
        
        return True
    
    @classmethod
    def get_allowed_extensions_set(cls) -> set:
        """Get allowed extensions as a set for easy checking"""
        return set(ext.strip().lower() for ext in cls.ALLOWED_EXTENSIONS)
    
    @classmethod
    def is_allowed_file(cls, filename: str) -> bool:
        """Check if a filename has an allowed extension"""
        if "." not in filename:
            return False
        extension = filename.rsplit(".", 1)[1].lower()
        return extension in cls.get_allowed_extensions_set()

# Create a global config instance
config = Config()