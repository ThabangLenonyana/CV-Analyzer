import os
from dotenv import load_dotenv
from typing import List
from pathlib import Path
import shutil

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Railway Detection
    IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT"))
    
    # Data Directory Configuration
    if IS_RAILWAY:
        # Use Railway's persistent volume
        DATA_DIR = "/data"
        os.makedirs(DATA_DIR, exist_ok=True)
    else:
        # Use local directory
        DATA_DIR = "."
    
    # Google Gemini Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "pdf,docx").split(",")
    
    # Set upload folder based on environment
    if IS_RAILWAY:
        UPLOAD_FOLDER = f"{DATA_DIR}/uploads"
    else:
        UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    
    # Application Configuration
    APP_NAME = "CV Analyzer"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8080"))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # API Rate Limiting (for future implementation)
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    
    # Database settings
    DATABASE_TYPE = os.getenv("DATABASE_TYPE", "sqlite")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "cv_analyzer.db")
    DATABASE_USER = os.getenv("DATABASE_USER", "")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    @classmethod
    def setup_railway_persistence(cls):
        """Set up persistent storage on Railway"""
        if not cls.IS_RAILWAY:
            return
        
        # Copy database to persistent volume if it doesn't exist there
        local_db = cls.DATABASE_NAME
        persistent_db = f"{cls.DATA_DIR}/{cls.DATABASE_NAME}"
        
        if os.path.exists(local_db) and not os.path.exists(persistent_db):
            print(f"Copying database to persistent volume: {persistent_db}")
            shutil.copy2(local_db, persistent_db)
        
        # Update database name to use persistent path
        cls.DATABASE_NAME = persistent_db
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        # Set up Railway persistence before validation
        cls.setup_railway_persistence()
        
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
    
    @property
    def DATABASE_URL(self) -> str:
        """Get database URL with proper configuration"""
        if self.DATABASE_TYPE == "sqlite":
            # Use absolute path for SQLite
            db_path = Path(self.DATABASE_NAME).absolute()
            return f"sqlite:///{db_path}?mode=wal"  # Enable WAL mode for better concurrency
        else:
            # For other databases (PostgreSQL, MySQL, etc.)
            return f"{self.DATABASE_TYPE}://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

# Create a global config instance
config = Config()