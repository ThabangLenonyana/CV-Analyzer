import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

from app.repositories.job_description_repository import JobDescriptionRepository
from app.models.schemas import StructuredJobDescription, JobRequirement

logger = logging.getLogger(__name__)

class JobDescriptionService:
    """Service for managing job descriptions"""
    
    def __init__(self):
        self.repository = JobDescriptionRepository()
    
    def create_job_description(self, job_data: Dict[str, Any], 
                             source: str = "manual") -> Dict[str, Any]:
        """Create a new job description from structured data"""
        try:
            # Process requirements if provided as plain data
            if "requirements" in job_data and isinstance(job_data["requirements"], list):
                processed_requirements = []
                for req in job_data["requirements"]:
                    if isinstance(req, dict) and "category" in req and "requirements" in req:
                        # Already in correct format
                        processed_requirements.append(req)
                    elif isinstance(req, str):
                        # Simple string, assume it's a required skill
                        processed_requirements.append({
                            "category": "Required",
                            "requirements": [req]
                        })
                job_data["requirements"] = processed_requirements
            
            # Validate and create StructuredJobDescription
            structured_job = StructuredJobDescription(**job_data)
            
            # Save to database
            job_record = self.repository.save_job_description(
                structured_job, 
                source=source,
                industry=job_data.get("industry"),
                department=job_data.get("department")
            )
            
            return job_record.to_dict()
            
        except Exception as e:
            logger.error(f"Error creating job description: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating job description: {str(e)}")
    
    def get_job_description(self, job_id: int) -> Dict[str, Any]:
        """Get job description by ID"""
        job_data = self.repository.get(job_id)  # Changed from get_by_id to get
        if not job_data:
            raise HTTPException(status_code=404, detail="Job description not found")
        return job_data.to_dict()
    
    def get_structured_job(self, job_id: int) -> StructuredJobDescription:
        """Get StructuredJobDescription object"""
        structured_job = self.repository.get_structured_job_by_id(job_id)
        if not structured_job:
            raise HTTPException(status_code=404, detail="Job description not found")
        return structured_job
    
    def list_jobs(self, limit: int = 20, company: str = None, 
                  job_type: str = None) -> List[Dict[str, Any]]:
        """List active job descriptions with optional filters"""
        return self.repository.get_active_jobs(limit=limit, company=company, job_type=job_type)
    
    def search_jobs(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search job descriptions"""
        return self.repository.search_jobs(search_term, limit=limit)
    
    def get_similar_jobs(self, job_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar job descriptions"""
        return self.repository.get_similar_jobs(job_id, limit=limit)
    
    def update_job_description(self, job_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update job description"""
        job_record = self.repository.update(job_id, **updates)
        if not job_record:
            raise HTTPException(status_code=404, detail="Job description not found")
        return job_record.to_dict()
    
    def deactivate_job(self, job_id: int) -> Dict[str, Any]:
        """Deactivate a job description"""
        job_record = self.repository.deactivate_job(job_id)
        if not job_record:
            raise HTTPException(status_code=404, detail="Job description not found")
        return job_record.to_dict()
    
    def get_jobs_by_company(self, company: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all jobs for a company"""
        return self.repository.get_jobs_by_company(company, limit=limit)

# Create singleton instance
job_description_service = JobDescriptionService()