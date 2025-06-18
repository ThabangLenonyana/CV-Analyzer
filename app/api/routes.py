import traceback
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
import logging
from pathlib import Path

from app.config import config
from app.services.cv_processor import cv_processor
from app.services.job_description_service import job_description_service
from app.services.analysis_service import analysis_service

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ===== CORE API ENDPOINTS =====
# API routes should be defined BEFORE the catch-all route

# Health Check
@router.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": config.APP_VERSION}

# Component Routes
@router.get("/api/components/{component_name}")
async def get_component(component_name: str):
    """Serve component templates"""
    component_path = Path(f"templates/components/{component_name}.html")
    
    if not component_path.exists():
        raise HTTPException(status_code=404, detail=f"Component {component_name} not found")
    
    with open(component_path, "r") as f:
        content = f.read()
    
    return Response(content=content, media_type="text/html")

# CV Management
@router.post("/api/cv/upload")
async def upload_cv(file: UploadFile = File(...)):
    """Upload and parse CV"""
    result = await cv_processor.process_cv_upload(file)
    return {"success": True, "data": result}

@router.get("/api/cv/recent")
async def get_recent_cvs(limit: int = 10):
    """Get recent CVs"""
    cvs = cv_processor.get_recent_cvs(limit)
    return {"success": True, "data": cvs}

@router.get("/api/cv/{cv_id}")
async def get_cv(cv_id: int):
    """Get specific CV"""
    cv = cv_processor.get_cv_by_id(cv_id)
    if not cv:
        raise HTTPException(404, "CV not found")
    return {"success": True, "data": cv}

# Job Description Management
@router.post("/api/jobs")
async def create_job(request: Request):
    """Create job description"""
    data = await request.json()
    job = job_description_service.create_job(data)
    return {"success": True, "data": job}

@router.get("/api/jobs")
async def list_jobs(limit: int = 20, company: str = None):
    """List job descriptions"""
    jobs = job_description_service.list_jobs(limit, company)
    return {"success": True, "data": jobs}

@router.get("/api/jobs/{job_id}")
async def get_job(job_id: int):
    """Get specific job"""
    job = job_description_service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"success": True, "data": job}

@router.delete("/api/jobs/{job_id}")
async def delete_job(job_id: int):
    """Delete job (soft delete)"""
    job_description_service.delete_job(job_id)
    return {"success": True}

# Analysis
@router.post("/api/analyze")
async def analyze_cv(request: Request):
    """Analyze CV against job"""
    try:
        data = await request.json()
        cv_id = data.get("cv_id")
        job_id = data.get("job_id")
        
        if not cv_id or not job_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "cv_id and job_id required"}
            )
        
        result = await analysis_service.analyze(cv_id, job_id)
        return {"success": True, "data": result}
    except HTTPException as e:
        # Return a proper JSON response for HTTP exceptions
        return JSONResponse(
            status_code=e.status_code,
            content={"success": False, "error": e.detail}
        )
    except Exception as e:
        # Handle other exceptions
        logger.error(f"Error in analyze_cv: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"}
        )

@router.get("/api/analyses/recent")
async def get_recent_analyses(limit: int = 20):
    """Get recent analyses with full related data"""
    try:
        analyses = analysis_service.get_recent_analyses(limit)
        
        # Convert to list if it's not already
        if not isinstance(analyses, list):
            analyses = []
        
        # Process each analysis
        analyses_data = []
        for analysis in analyses:
            # Handle both dict and object types
            if isinstance(analysis, dict):
                analysis_dict = analysis
            else:
                # Assume it has a to_dict method
                try:
                    analysis_dict = analysis.to_dict()
                except:
                    # Skip if we can't convert
                    continue
            
            analyses_data.append(analysis_dict)
        
        return {"success": True, "data": analyses_data}
    except Exception as e:
        logger.error(f"Error in get_recent_analyses: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to load recent analyses", "detail": str(e)}
        )

@router.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: int):
    """Get specific analysis with full related data"""
    try:
        analysis = analysis_service.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(404, "Analysis not found")
        
        # Convert to dict and include related data
        analysis_dict = analysis.to_dict()
        
        # Include the full cv_record if available
        if analysis.cv_record:
            analysis_dict['cv_record'] = analysis.cv_record.to_dict()
            # Include file info if available
            if analysis.cv_record.file_upload:
                analysis_dict['cv_record']['file_upload'] = analysis.cv_record.file_upload.to_dict()
        
        # Include the full job_description if available
        if analysis.job_description:
            analysis_dict['job_description'] = analysis.job_description.to_dict()
        
        return {"success": True, "data": analysis_dict}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_analysis: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to load analysis", "detail": str(e)}
        )

# Statistics
@router.get("/api/stats")
async def get_stats():
    """Get application statistics"""
    stats = analysis_service.get_statistics()
    return {"success": True, "data": stats}

# Add this temporary debug endpoint
@router.get("/api/debug/test-analyses")
async def debug_test_analyses():
    """Debug endpoint to test analysis fetching"""
    from app.repositories.analysis_repository import AnalysisRepository
    from app.models.database import Analysis
    
    repo = AnalysisRepository()
    
    try:
        # Test 1: Direct query
        with repo.get_db() as db:
            count = db.query(Analysis).count()
            first_few = db.query(Analysis).limit(3).all()
            
        # Test 2: Repository method
        recent = repo.get_recent_analyses(3)
        
        return {
            "success": True,
            "total_count": count,
            "direct_query_count": len(first_few),
            "repository_method_count": len(recent),
            "repository_data": recent
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# ===== SPA ROUTES (Must be last!) =====
@router.get("/", response_class=HTMLResponse)
async def serve_root(request: Request):
    """Serve the main SPA root"""
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request,
            "app_name": config.APP_NAME,
            "app_version": config.APP_VERSION,
            "allowed_extensions": list(config.ALLOWED_EXTENSIONS),
            "max_file_size_mb": config.MAX_FILE_SIZE_MB
        }
    )

@router.get("/{path:path}", response_class=HTMLResponse)
async def serve_spa(request: Request, path: str):
    """Serve the main SPA for all other page routes"""
    # Only serve HTML for non-API routes
    if not path.startswith(("api/", "static/")):
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "app_name": config.APP_NAME,
                "app_version": config.APP_VERSION,
                "allowed_extensions": list(config.ALLOWED_EXTENSIONS),
                "max_file_size_mb": config.MAX_FILE_SIZE_MB
            }
        )
    # For anything else, return 404
    raise HTTPException(status_code=404, detail="Not found")
