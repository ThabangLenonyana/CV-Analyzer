from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging

from app.config import config

# Setup logger
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

# Setup templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION,
            "max_file_size_mb": config.MAX_FILE_SIZE_MB,
            "allowed_extensions": ", ".join(config.ALLOWED_EXTENSIONS)
        }
    )

@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint - returns HTML or JSON based on Accept header"""
    health_data = {
        "status": "healthy",
        "version": config.APP_VERSION,
        "gemini_configured": bool(config.GEMINI_API_KEY),
        "allowed_extensions": config.ALLOWED_EXTENSIONS,
        "max_file_size_mb": config.MAX_FILE_SIZE_MB
    }
    
    # Check if the request accepts JSON (API call)
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header:
        return JSONResponse(health_data)
    
    # Otherwise return HTML page
    health_data["request"] = request
    health_data["app_name"] = config.APP_NAME
    return templates.TemplateResponse("health.html", health_data)

@router.get("/api/config")
async def get_config():
    """Get public configuration for frontend"""
    return {
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
        "allowed_extensions": config.ALLOWED_EXTENSIONS,
        "app_version": config.APP_VERSION
    }
