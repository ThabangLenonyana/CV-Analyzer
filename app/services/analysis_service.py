import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException, Request

from app.repositories.analysis_repository import AnalysisRepository, AnalysisHistoryRepository
from app.services.cv_processor import cv_processor
from app.services.job_description_service import job_description_service
from app.services.analyzer import analyze_cv_job_match
from app.models.schemas import AnalysisResponse

logger = logging.getLogger(__name__)

class AnalysisService:
    """Enhanced service for managing CV-job analyses with persistence"""
    
    def __init__(self):
        self.analysis_repository = AnalysisRepository()
        self.history_repository = AnalysisHistoryRepository()
    
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
                analysis_record = self.analysis_repository.save_analysis_result(
                    cv_record_id=cv_id,
                    job_description_id=job_id,
                    analysis_response=analysis_result,
                    analysis_duration=analysis_duration
                )
                
                # Prepare response with database ID
                response = analysis_result.dict()
                response.update({
                    "analysis_id": analysis_record.id,
                    "cv_id": cv_id,
                    "job_id": job_id,
                    "analysis_duration_seconds": analysis_duration,
                    "saved_at": analysis_record.created_at.isoformat()
                })
                
                logger.info(f"Analysis completed and saved. ID: {analysis_record.id}")
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
            
        except Exception as e:
            logger.error(f"Error performing analysis: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error performing analysis: {str(e)}")
    
    def get_analysis_result(self, analysis_id: int, 
                          request: Request = None) -> Dict[str, Any]:
        """Get analysis result by ID and track the view"""
        analysis_data = self.analysis_repository.get_analysis_with_details(analysis_id)
        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        # Track the view
        if request:
            user_agent = request.headers.get("user-agent")
            # In a real app, you'd extract the real IP address
            ip_address = request.client.host if request.client else None
            
            self.history_repository.track_view(
                analysis_result_id=analysis_id,
                view_type="full",
                user_agent=user_agent,
                ip_address=ip_address
            )
        
        return analysis_data
    
    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent analysis results"""
        return self.analysis_repository.get_recent_analyses(limit=limit)
    
    def get_cv_analyses(self, cv_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a specific CV"""
        return self.analysis_repository.get_analyses_by_cv(cv_id)
    
    def get_job_analyses(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a specific job"""
        return self.analysis_repository.get_analyses_by_job(job_id)
    
    def get_top_matches(self, job_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top CV matches for a job"""
        return self.analysis_repository.get_top_matches_for_job(job_id, limit=limit)
    
    def add_user_feedback(self, analysis_id: int, rating: int, 
                         comment: str = None) -> Dict[str, Any]:
        """Add user feedback to an analysis"""
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Verify analysis exists
        analysis_data = self.analysis_repository.get_by_id(analysis_id)
        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        feedback_record = self.history_repository.add_user_feedback(
            analysis_result_id=analysis_id,
            rating=rating,
            comment=comment
        )
        
        return feedback_record.to_dict()
    
    def get_analysis_history(self, analysis_id: int) -> List[Dict[str, Any]]:
        """Get history for an analysis"""
        return self.history_repository.get_analysis_history(analysis_id)
    
    def get_feedback_summary(self, analysis_id: int) -> Dict[str, Any]:
        """Get feedback summary for an analysis"""
        return self.history_repository.get_user_feedback_summary(analysis_id)
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get overall analysis statistics"""
        return self.analysis_repository.get_analysis_statistics()
    
    def track_analysis_action(self, analysis_id: int, action_type: str, 
                            action_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Track a specific action on an analysis"""
        # Verify analysis exists
        analysis_data = self.analysis_repository.get_by_id(analysis_id)
        if not analysis_data:
            raise HTTPException(status_code=404, detail="Analysis result not found")
        
        history_record = self.history_repository.track_action(
            analysis_result_id=analysis_id,
            action_type=action_type,
            action_details=action_details
        )
        
        return history_record.to_dict()

# Create singleton instance
analysis_service = AnalysisService()