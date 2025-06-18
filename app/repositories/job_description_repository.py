from typing import List, Dict, Any, Optional
import logging

from app.repositories.base_repository import BaseRepository
from app.models.database import JobDescription
from app.models.schemas import StructuredJobDescription

logger = logging.getLogger(__name__)

class JobDescriptionRepository(BaseRepository[JobDescription]):
    """Simplified job description repository"""
    
    def __init__(self):
        super().__init__(JobDescription)
    
    def save_job_description(self, structured_job: StructuredJobDescription,
                           source: str = "manual", **kwargs) -> JobDescription:
        """Save a structured job description"""
        job_data = structured_job.dict()
        job_data.update(kwargs)  # Add any extra fields
        
        return self.create(
            job_title=structured_job.job_title,
            company=structured_job.company or "Unknown",
            job_data=job_data,
            is_active=True
        )
    
    def get_structured_job_by_id(self, job_id: int) -> Optional[StructuredJobDescription]:
        """Get StructuredJobDescription from stored data"""
        with self.get_db() as db:
            job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
            
            if not job:
                return None
            
            try:
                # Access all needed attributes while session is still active
                is_active = job.is_active
                job_data = job.job_data
                job_title = job.job_title
                company = job.company
                
                # Check if job is active
                if not is_active:
                    return None
                
                # Reconstruct from stored job_data
                if job_data:
                    return StructuredJobDescription(**job_data)
                else:
                    # Fallback: create basic StructuredJobDescription
                    return StructuredJobDescription(
                        job_title=job_title or "Unknown",
                        company=company or "Unknown",
                        description="",
                        responsibilities=[],
                        requirements=[],
                        nice_to_have=[],
                        skills_required=[]
                    )
                    
            except Exception as e:
                logger.error(f"Error reconstructing job description: {str(e)}")
                return None
    
    def get_active_jobs(self, limit: int = 20, company: str = None,
                       job_type: str = None) -> List[Dict[str, Any]]:
        """Get active job descriptions"""
        with self.get_db() as db:
            query = db.query(JobDescription).filter(JobDescription.is_active == True)
            
            if company:
                query = query.filter(JobDescription.company.ilike(f"%{company}%"))
            
            jobs = query.order_by(JobDescription.created_at.desc()).limit(limit).all()
            return [self._format_job(job) for job in jobs]
    
    def search_jobs(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search jobs by title or company"""
        with self.get_db() as db:
            pattern = f"%{search_term}%"
            jobs = db.query(JobDescription).filter(
                JobDescription.is_active == True,
                (JobDescription.job_title.ilike(pattern) | 
                 JobDescription.company.ilike(pattern))
            ).limit(limit).all()
            
            return [self._format_job(job) for job in jobs]
    
    def get_jobs_by_company(self, company: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all jobs for a company"""
        return self.get_active_jobs(limit=limit, company=company)
    
    def get_similar_jobs(self, job_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar jobs (simplified - just same company for now)"""
        job = self.get(job_id)
        if not job:
            return []
        
        return self.get_jobs_by_company(job.company, limit=limit)
    
    def deactivate_job(self, job_id: int) -> Optional[JobDescription]:
        """Soft delete a job"""
        return self.update(job_id, is_active=False)
    
    def _format_job(self, job: JobDescription) -> Dict[str, Any]:
        """Format job record for API response"""
        job_data = job.job_data.copy() if job.job_data else {}
        job_data.update({
            "id": job.id,
            "job_title": job.job_title,
            "company": job.company,
            "is_active": job.is_active,
            "created_at": job.created_at
        })
        return job_data