from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.config import config
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    # Startup
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    # Clean up old uploads on startup (optional)
    if os.path.exists(config.UPLOAD_FOLDER):
        logger.info(f"Upload folder ready at: {config.UPLOAD_FOLDER}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")

# Create FastAPI app instance
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="AI-powered CV analysis application using Google Gemini",
    lifespan=lifespan,
    debug=config.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted")

# Include API routes
app.include_router(router)

# Error handlers
@app.exception_handler(413)
async def request_entity_too_large(request: Request, exc):
    """Handle file too large errors"""
    return {"error": f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return {"error": exc.detail, "status_code": exc.status_code}

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="debug" if config.DEBUG else "info"
    )