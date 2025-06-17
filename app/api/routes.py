from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, List

from app.config import config
from app.services.cv_processor import cv_processor
from app.services.job_description_service import job_description_service
from app.services.analysis_service import analysis_service
from app.models.schemas import StructuredCV, StructuredJobDescription, AnalysisResponse, JobRequirement

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

@router.get("/job-descriptions/new", response_class=HTMLResponse)
async def new_job_description_page(request: Request):
    """Serve the new job description form page"""
    return templates.TemplateResponse(
        "new_job.html",
        {
            "request": request,
            "app_name": config.APP_NAME
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

# CV Routes
@router.post("/api/cv/upload")
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload and parse a CV file
    
    Returns parsed CV data with database ID
    """
    result = await cv_processor.process_cv_upload(file)
    
    return {
        "success": True,
        "message": "CV uploaded and parsed successfully",
        "cv_id": result["id"],
        "upload_id": result["upload_id"],
        "filename": result["filename"],
        "cv_data": result
    }

@router.get("/api/cv/history")
async def get_cv_history(limit: int = 10):
    """Get recent CV upload history"""
    cvs = cv_processor.get_recent_cvs(limit=limit)
    return {
        "success": True,
        "cvs": cvs,
        "count": len(cvs)
    }

@router.get("/api/cv/{cv_id}")
async def get_cv_by_id(cv_id: int):
    """Get a specific parsed CV by ID"""
    cv_data = cv_processor.get_cv_by_id(cv_id)
    return {
        "success": True,
        "cv_id": cv_id,
        "cv_data": cv_data
    }

@router.delete("/api/cv/{cv_id}")
async def delete_cv(cv_id: int):
    """Delete a CV from the database (soft delete by updating status)"""
    try:
        # For now, just update the status to 'deleted'
        # You might want to implement a proper soft delete in the database service
        cv_data = cv_processor.get_cv_by_id(cv_id)
        if not cv_data:
            raise HTTPException(status_code=404, detail="CV not found")
        
        # TODO: Implement delete functionality in database service
        # cv_processor.delete_cv(cv_id)
        
        return {
            "success": True,
            "message": f"CV {cv_id} marked for deletion"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting CV {cv_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete CV")

# Job Description Routes
@router.post("/api/job-descriptions")
async def create_job_description(request: Request):
    """
    Create a new job description from structured data
    
    Takes job description data from the form submission
    """
    try:
        job_data = await request.json()
        
        # Check if job already exists to prevent duplicates
        existing_jobs = job_description_service.list_jobs(
            company=job_data.get('company'),
            limit=100
        )
        
        # Check for exact match
        for job in existing_jobs:
            if job['job_title'] == job_data.get('job_title'):
                logger.warning(f"Job '{job_data.get('job_title')}' at '{job_data.get('company')}' already exists")
                # Return the existing job instead of creating a duplicate
                return {
                    "success": True,
                    "message": "Job description already exists",
                    "job_id": job['id'],
                    "job_data": job,
                    "existing": True
                }
        
        result = job_description_service.create_job_description(job_data)
        
        return {
            "success": True,
            "message": "Job description created successfully",
            "job_id": result["id"],
            "job_data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job description: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating job description: {str(e)}")

@router.get("/api/job-descriptions")
async def list_job_descriptions(limit: int = 20, company: str = None, job_type: str = None):
    """List job descriptions with optional filters"""
    jobs = job_description_service.list_jobs(limit=limit, company=company, job_type=job_type)
    
    # Format jobs for frontend compatibility
    formatted_jobs = []
    for job in jobs:
        formatted_job = {
            "id": job.get("id"),
            "title": job.get("job_title"),  # Add 'title' for backward compatibility
            "job_title": job.get("job_title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "job_type": job.get("job_type"),
            "experience_level": job.get("experience_level"),
            "summary": job.get("summary"),
            "required_skills": job.get("required_skills", []),
            "preferred_skills": job.get("preferred_skills", []),
            "created_at": job.get("created_at"),
            "is_active": job.get("is_active", True)
        }
        formatted_jobs.append(formatted_job)
    
    return {
        "success": True,
        "jobs": formatted_jobs,
        "count": len(formatted_jobs)
    }

@router.get("/api/job-descriptions/{job_id}")
async def get_job_description(job_id: int):
    """Get a specific job description"""
    job_data = job_description_service.get_job_description(job_id)
    return {
        "success": True,
        "job_id": job_id,
        "job_data": job_data
    }

@router.put("/api/job-descriptions/{job_id}")
async def update_job_description(job_id: int, request: Request):
    """Update a job description"""
    try:
        updates = await request.json()
        result = job_description_service.update_job_description(job_id, updates)
        return {
            "success": True,
            "message": "Job description updated successfully",
            "job_id": job_id,
            "job_data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job description {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating job description: {str(e)}")

@router.delete("/api/job-descriptions/{job_id}")
async def deactivate_job_description(job_id: int):
    """Deactivate (soft delete) a job description"""
    try:
        result = job_description_service.deactivate_job(job_id)
        return {
            "success": True,
            "message": "Job description deactivated successfully",
            "job_id": job_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating job description {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deactivating job description: {str(e)}")

@router.get("/api/job-descriptions/search")
async def search_job_descriptions(q: str, limit: int = 10):
    """Search job descriptions"""
    jobs = job_description_service.search_jobs(q, limit=limit)
    return {
        "success": True,
        "search_term": q,
        "jobs": jobs,
        "count": len(jobs)
    }

@router.get("/api/job-descriptions/{job_id}/similar")
async def get_similar_jobs(job_id: int, limit: int = 5):
    """Get similar job descriptions"""
    similar_jobs = job_description_service.get_similar_jobs(job_id, limit=limit)
    return {
        "success": True,
        "job_id": job_id,
        "similar_jobs": similar_jobs,
        "count": len(similar_jobs)
    }

@router.get("/api/companies/{company}/jobs")
async def get_company_jobs(company: str, limit: int = 10):
    """Get all jobs for a company"""
    jobs = job_description_service.get_jobs_by_company(company, limit=limit)
    return {
        "success": True,
        "company": company,
        "jobs": jobs,
        "count": len(jobs)
    }

# Analysis Routes
@router.post("/api/analyses")
async def create_analysis(request: Request):
    """
    Perform CV-job analysis with persistence
    
    Expects JSON body with:
    - cv_id: Database ID of the CV
    - job_id: Database ID of the job description  
    - detailed: Include detailed analysis (optional, default True)
    - save_result: Save to database (optional, default True)
    """
    try:
        body = await request.json()
        
        cv_id = body.get("cv_id")
        job_id = body.get("job_id")
        detailed = body.get("detailed", True)
        save_result = body.get("save_result", True)
        
        if not cv_id or not job_id:
            raise HTTPException(status_code=400, detail="Both cv_id and job_id are required")
        
        # Perform analysis
        analysis_result = await analysis_service.perform_analysis(
            cv_id=cv_id,
            job_id=job_id,
            detailed=detailed,
            save_result=save_result
        )
        
        return {
            "success": True,
            "message": "Analysis completed successfully",
            "analysis": analysis_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error performing analysis: {str(e)}")

@router.get("/api/analyses")
async def list_analyses(limit: int = 20):
    """Get recent analysis results"""
    analyses = analysis_service.get_recent_analyses(limit=limit)
    return {
        "success": True,
        "analyses": analyses,
        "count": len(analyses)
    }

@router.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: int, request: Request):
    """Get analysis result by ID"""
    analysis_data = analysis_service.get_analysis_result(analysis_id, request)
    return {
        "success": True,
        "analysis_id": analysis_id,
        "analysis": analysis_data
    }

@router.get("/api/cv/{cv_id}/analyses")
async def get_cv_analyses(cv_id: int):
    """Get all analyses for a CV"""
    analyses = analysis_service.get_cv_analyses(cv_id)
    return {
        "success": True,
        "cv_id": cv_id,
        "analyses": analyses,
        "count": len(analyses)
    }

@router.get("/api/job-descriptions/{job_id}/analyses")
async def get_job_analyses(job_id: int):
    """Get all analyses for a job description"""
    analyses = analysis_service.get_job_analyses(job_id)
    return {
        "success": True,
        "job_id": job_id,
        "analyses": analyses,
        "count": len(analyses)
    }

@router.get("/api/job-descriptions/{job_id}/top-matches")
async def get_top_matches(job_id: int, limit: int = 10):
    """Get top CV matches for a job"""
    matches = analysis_service.get_top_matches(job_id, limit=limit)
    return {
        "success": True,
        "job_id": job_id,
        "top_matches": matches,
        "count": len(matches)
    }

@router.post("/api/analyses/{analysis_id}/feedback")
async def add_analysis_feedback(analysis_id: int, request: Request):
    """Add user feedback to an analysis"""
    try:
        body = await request.json()
        rating = body.get("rating")
        comment = body.get("comment")
        
        if not rating:
            raise HTTPException(status_code=400, detail="Rating is required")
        
        feedback = analysis_service.add_user_feedback(
            analysis_id=analysis_id,
            rating=rating,
            comment=comment
        )
        
        return {
            "success": True,
            "message": "Feedback added successfully",
            "feedback": feedback
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding feedback: {str(e)}")

@router.get("/api/analyses/{analysis_id}/history")
async def get_analysis_history(analysis_id: int):
    """Get history for an analysis"""
    history = analysis_service.get_analysis_history(analysis_id)
    return {
        "success": True,
        "analysis_id": analysis_id,
        "history": history
    }

@router.get("/api/statistics/analyses")
async def get_analysis_statistics():
    """Get overall analysis statistics"""
    stats = analysis_service.get_analysis_statistics()
    return {
        "success": True,
        "statistics": stats
    }

@router.post("/api/analyses/{analysis_id}/actions/{action_type}")
async def track_analysis_action(analysis_id: int, action_type: str, request: Request):
    """
    Track a specific action on an analysis
    
    Action types: "viewed", "downloaded", "shared", etc.
    """
    try:
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        
        result = analysis_service.track_analysis_action(
            analysis_id=analysis_id,
            action_type=action_type,
            action_details=body
        )
        
        return {
            "success": True,
            "message": f"Action '{action_type}' tracked successfully",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error tracking action: {str(e)}")

# Utility routes for job descriptions
@router.post("/api/validate/job-description")
async def validate_job_description(request: Request):
    """
    Validate if the provided JSON matches the StructuredJobDescription schema
    
    Useful for testing job description JSON before saving
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
        logger.error(f"Error validating job description: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating: {str(e)}")

# Add these routes to support SPA navigation

@router.get("/job-descriptions/{job_id}", response_class=HTMLResponse)
async def job_detail_page(request: Request, job_id: int):
    """Serve the main SPA template for job detail"""
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

@router.get("/job-descriptions/{job_id}/edit", response_class=HTMLResponse)
async def edit_job_page(request: Request, job_id: int):
    """Serve the main SPA template for job editing"""
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

@router.get("/analyses/{analysis_id}", response_class=HTMLResponse)
async def analysis_detail_page(request: Request, analysis_id: int):
    """Serve the main SPA template for analysis detail"""
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

@router.get("/jobs", response_class=HTMLResponse)
@router.get("/history", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def spa_views(request: Request):
    """Serve the main SPA template for other views"""
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
