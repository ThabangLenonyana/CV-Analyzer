from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.repositories.base_repository import BaseRepository
from app.models.database import JobDescriptionRecord
from app.models.schemas import StructuredJobDescription

logger = logging.getLogger(__name__)

class JobDescriptionRepository(BaseRepository[JobDescriptionRecord]):
    """Repository for job description database operations"""
    
    def __init__(self):
        super().__init__(JobDescriptionRecord)
    
    def save_job_description(self, structured_job: StructuredJobDescription, 
                           source: str = "manual", industry: str = None, 
                           department: str = None) -> JobDescriptionRecord:
        """Save a structured job description"""
        job_dict = structured_job.dict()
        
        job_record = self.create(
            title=structured_job.job_title,
            company=structured_job.company,
            location=structured_job.location,
            job_type=structured_job.job_type,
            experience_level=structured_job.experience_level,
            summary=structured_job.summary,
            responsibilities=structured_job.responsibilities,
            required_skills=structured_job.required_skills,
            preferred_skills=structured_job.preferred_skills,
            requirements=[req.dict() for req in structured_job.requirements],
            education_requirements=structured_job.education_requirements,
            certifications_required=structured_job.certifications_required,
            benefits=structured_job.benefits,
            salary_range=structured_job.salary_range,
            raw_text=structured_job.raw_text,
            structured_data=job_dict,
            source=source,
            industry=industry,
            department=department,
            is_active=1
        )
        
        logger.info(f"Saved job description with ID: {job_record.id}")
        return job_record
    
    def get_structured_job_by_id(self, job_id: int) -> Optional[StructuredJobDescription]:
        """Get StructuredJobDescription from stored data"""
        job_record = self.get_by_id(job_id)
        if not job_record:
            return None
        
        # Use the structured data to reconstruct StructuredJobDescription
        job_data = job_record.to_structured_job_dict()
        
        # Reconstruct JobRequirement objects
        from app.models.schemas import JobRequirement
        requirements = []
        for req_data in job_data.get("requirements", []):
            if isinstance(req_data, dict):
                requirements.append(JobRequirement(**req_data))
        
        job_data["requirements"] = requirements
        
        return StructuredJobDescription(**job_data)
    
    def get_active_jobs(self, limit: int = 20, company: str = None, 
                       job_type: str = None) -> List[Dict[str, Any]]:
        """Get active job descriptions with optional filters"""
        with self.get_session() as session:
            query = session.query(JobDescriptionRecord).filter(
                JobDescriptionRecord.is_active == 1
            )
            
            if company:
                query = query.filter(JobDescriptionRecord.company.ilike(f"%{company}%"))
            
            if job_type:
                query = query.filter(JobDescriptionRecord.job_type == job_type)
            
            results = query.order_by(JobDescriptionRecord.created_at.desc()).limit(limit).all()
            
            return [job.to_dict() for job in results]
    
    def search_jobs(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search job descriptions by title, company, or skills"""
        with self.get_session() as session:
            search_pattern = f"%{search_term}%"
            
            results = session.query(JobDescriptionRecord).filter(
                (JobDescriptionRecord.is_active == 1) &
                (
                    JobDescriptionRecord.title.ilike(search_pattern) |
                    JobDescriptionRecord.company.ilike(search_pattern) |
                    JobDescriptionRecord.summary.ilike(search_pattern)
                )
            ).order_by(JobDescriptionRecord.created_at.desc()).limit(limit).all()
            
            return [job.to_dict() for job in results]
    
    def get_similar_jobs(self, job_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar job descriptions based on skills and title"""
        job_record = self.get_by_id(job_id)
        if not job_record:
            return []
        
        # This is a simple implementation - in production, you might want
        # to use more sophisticated similarity algorithms
        with self.get_session() as session:
            similar_jobs = session.query(JobDescriptionRecord).filter(
                (JobDescriptionRecord.id != job_id) &
                (JobDescriptionRecord.is_active == 1) &
                (
                    JobDescriptionRecord.company == job_record.company |
                    JobDescriptionRecord.job_type == job_record.job_type |
                    JobDescriptionRecord.experience_level == job_record.experience_level
                )
            ).limit(limit).all()
            
            return [job.to_dict() for job in similar_jobs]
    
    def deactivate_job(self, job_id: int) -> Optional[JobDescriptionRecord]:
        """Soft delete by setting is_active to 0"""
        return self.update(job_id, is_active=0)
    
    def get_jobs_by_company(self, company: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all jobs for a specific company"""
        with self.get_session() as session:
            results = session.query(JobDescriptionRecord).filter(
                (JobDescriptionRecord.company.ilike(f"%{company}%")) &
                (JobDescriptionRecord.is_active == 1)
            ).order_by(JobDescriptionRecord.created_at.desc()).limit(limit).all()
            
            return [job.to_dict() for job in results]