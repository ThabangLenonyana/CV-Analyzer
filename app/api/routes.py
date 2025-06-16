from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import json
from pathlib import Path
from datetime import datetime
import logging

from app.config import config
from app.services.cv_parser import parse_cv
from app.models.schemas import StructuredCV, StructuredJobDescription, AnalysisResponse
from app.services.analyzer import analyze_cv_job_match

# Setup logger
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Page Routes
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

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Serve the CV upload page"""
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "app_name": config.APP_NAME,
            "max_file_size_mb": config.MAX_FILE_SIZE_MB,
            "allowed_extensions": config.ALLOWED_EXTENSIONS
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

# API Routes
@router.get("/api/config")
async def get_config():
    """Get public configuration for frontend"""
    return {
        "max_file_size_mb": config.MAX_FILE_SIZE_MB,
        "allowed_extensions": config.ALLOWED_EXTENSIONS,
        "app_version": config.APP_VERSION
    }

@router.post("/api/cv/upload")
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload and parse a CV file
    
    Returns parsed CV data
    """
    try:
        # Validate file extension
        if not config.is_allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # Validate file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > config.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB"
            )
        
        # Save file temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = Path(config.UPLOAD_FOLDER) / filename
        
        # Ensure upload folder exists
        file_path.parent.mkdir(exist_ok=True)
        
        # Write file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"CV uploaded: {filename}")
        
        # Parse CV
        logger.info("Parsing CV...")
        structured_cv = await parse_cv(str(file_path))
        
        # Store parsed CV in session or temporary storage for later use
        # For now, we'll return it to the client
        
        return {
            "success": True,
            "message": "CV uploaded and parsed successfully",
            "filename": filename,
            "cv_data": structured_cv.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CV: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")

@router.post("/api/cv/analyze")
async def analyze_cv_job(request: Request):
    """
    Analyze CV against job description
    
    Expects JSON body with:
    - cv_data: Parsed CV data
    - job_description: Job description as JSON object (StructuredJobDescription)
    - detailed: Include detailed analysis (optional, default True)
    """
    try:
        body = await request.json()
        
        # Extract data from request
        cv_data = body.get("cv_data")
        job_data = body.get("job_description")
        detailed = body.get("detailed", True)
        
        if not cv_data:
            raise HTTPException(status_code=400, detail="CV data is required")
        if not job_data:
            raise HTTPException(status_code=400, detail="Job description is required")
        
        # Create structured objects
        try:
            structured_cv = StructuredCV(**cv_data)
            structured_job = StructuredJobDescription(**job_data)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=f"Invalid data format: {str(e)}")
        
        logger.info("Starting CV analysis...")
        logger.info(f"CV: {structured_cv.contact_info.name if structured_cv.contact_info else 'Unknown'}")
        logger.info(f"Job: {structured_job.job_title} at {structured_job.company}")
        
        # Perform analysis
        analysis_result = await analyze_cv_job_match(
            structured_cv=structured_cv,
            structured_job=structured_job,
            detailed=detailed
        )
        
        return {
            "success": True,
            "analysis": analysis_result.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing CV: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing CV: {str(e)}")

@router.get("/api/sample-job-descriptions")
async def get_sample_job_descriptions():
    """
    Get sample job descriptions for testing
    
    Returns a list of pre-defined job descriptions in JSON format
    """
    try:
        # Load sample job descriptions from files or define them here
        samples = []
        
        # Check if we have sample files in output directory
        output_dir = Path("output")
        if output_dir.exists():
            # Look for JSON files that might be job descriptions
            for file_path in output_dir.glob("*job*.json"):
                try:
                    with open(file_path, 'r') as f:
                        job_data = json.load(f)
                        # Validate it's a job description
                        if "job_title" in job_data and "required_skills" in job_data:
                            samples.append({
                                "name": file_path.stem,
                                "data": job_data
                            })
                except Exception as e:
                    logger.warning(f"Failed to load sample job from {file_path}: {e}")
        
        # Add a default sample if no files found
        if not samples:
            samples.append({
                "name": "Graduate Java Developer",
                "data": {
                    "job_title": "Graduate Java Developer",
                    "company": "TechCorp Solutions",
                    "location": "Cape Town, South Africa",
                    "job_type": "Full-time",
                    "experience_level": "Entry Level / Graduate",
                    "summary": "We are seeking a talented and motivated Graduate Java Developer to join our dynamic development team.",
                    "responsibilities": [
                        "Develop and maintain Java-based applications using Spring Boot",
                        "Write clean, efficient, and well-documented code",
                        "Participate in code reviews",
                        "Collaborate with senior developers"
                    ],
                    "required_skills": ["Java", "Object-Oriented Programming", "SQL", "Git"],
                    "preferred_skills": ["Spring Boot", "Docker", "AWS"],
                    "requirements": [],
                    "education_requirements": ["Bachelor's degree in Computer Science or related field"],
                    "certifications_required": [],
                    "benefits": ["Competitive salary", "Learning opportunities"],
                    "salary_range": "R15,000 - R25,000 per month",
                    "raw_text": ""
                }
            })
        
        return {
            "success": True,
            "samples": samples
        }
        
    except Exception as e:
        logger.error(f"Error loading sample job descriptions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error loading samples: {str(e)}")

@router.post("/api/cv/validate-job-json")
async def validate_job_json(request: Request):
    """
    Validate if the provided JSON matches the StructuredJobDescription schema
    
    Useful for testing job description JSON before analysis
    """
    try:
        body = await request.json()
        
        # Try to create a StructuredJobDescription object
        try:
            job = StructuredJobDescription(**body)
            return {
                "success": True,
                "valid": True,
                "message": "Valid job description format",
                "parsed_data": job.dict()
            }
        except ValidationError as e:
            return {
                "success": False,
                "valid": False,
                "message": "Invalid job description format",
                "errors": e.errors()
            }
            
    except Exception as e:
        logger.error(f"Error validating job JSON: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating JSON: {str(e)}")
