import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException

from app.repositories.analysis_repository import AnalysisRepository
from app.services.cv_processor import cv_processor
from app.services.job_description_service import job_description_service
from app.services.analyzer import analyze_cv_job_match
from app.models.schemas import AnalysisResponse

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for managing CV-job analyses"""
    
    def __init__(self):
        self.analysis_repository = AnalysisRepository()
    
    async def perform_analysis(self, cv_id: int, job_id: int, 
                         detailed: bool = True, 
                         save_result: bool = True) -> Dict[str, Any]:
        """Perform CV-job analysis and optionally save the result"""
        start_time = datetime.now()
        
        try:
            # Get CV and job description data
            structured_cv = cv_processor.get_structured_cv(cv_id)
            structured_job = job_description_service.get_structured_job(job_id)
            
            logger.info(f"Starting analysis: CV {cv_id} vs Job {job_id}")
            
            # Perform the analysis
            analysis_result = await analyze_cv_job_match(
                structured_cv=structured_cv,
                structured_job=structured_job,
                detailed=detailed
            )
            
            end_time = datetime.now()
            analysis_duration = (end_time - start_time).total_seconds()
            
            # Save the result if requested
            if save_result:
                analysis_record_data = self.analysis_repository.save_analysis_result(
                    cv_record_id=cv_id,
                    job_description_id=job_id,
                    analysis_response=analysis_result,
                    analysis_duration=analysis_duration
                )
                
                # Prepare response with database ID
                response = analysis_result.dict()
                response.update({
                    "id": analysis_record_data["id"],
                    "cv_id": cv_id,
                    "job_id": job_id,
                    "analysis_duration_seconds": analysis_duration,
                    "analysis_date": analysis_record_data["analysis_date"].isoformat()
                })
                
                logger.info(f"Analysis completed and saved. ID: {analysis_record_data['id']}")
                return response
            else:
                # Return analysis without saving
                response = analysis_result.dict()
                response.update({
                    "cv_id": cv_id,
                    "job_id": job_id,
                    "analysis_duration_seconds": analysis_duration
                })
                return response
            
        except HTTPException:
            # Re-raise HTTPException as-is
            raise
        except Exception as e:
            logger.error(f"Error performing analysis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error performing analysis: {str(e)}")
    
    async def analyze(self, cv_id: int, job_id: int) -> Dict[str, Any]:
        """Simple wrapper for perform_analysis"""
        return await self.perform_analysis(cv_id, job_id)
    
    def get_analysis_result(self, analysis_id: int) -> Dict[str, Any]:
        """Get analysis result by ID"""
        analysis_data = self.analysis_repository.get_analysis_with_details(analysis_id)
        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        return analysis_data
    
    def get_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Get specific analysis by ID with full details"""
        try:
            # Use the repository method that already exists
            analysis_data = self.analysis_repository.get_analysis_with_details(analysis_id)
            return analysis_data
        except Exception as e:
            logger.error(f"Error getting analysis {analysis_id}: {str(e)}")
            return None
    
    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent analyses with related data"""
        try:
            # Use the repository to get recent analyses
            analyses = self.analysis_repository.get_recent_analyses(limit)
            return analyses
        except Exception as e:
            logger.error(f"Error getting recent analyses: {str(e)}")
            return []
    
    def get_cv_analyses(self, cv_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a specific CV"""
        return self.analysis_repository.get_analyses_by_cv(cv_id)
    
    def get_job_analyses(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a specific job"""
        return self.analysis_repository.get_analyses_by_job(job_id)
    
    def get_top_matches(self, job_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top CV matches for a job"""
        return self.analysis_repository.get_top_matches_for_job(job_id, limit=limit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall analysis statistics"""
        return self.analysis_repository.get_analysis_statistics()

# Create singleton instance
analysis_service = AnalysisService()