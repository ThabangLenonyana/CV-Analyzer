from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.repositories.base_repository import BaseRepository
from app.models.database import AnalysisResult, AnalysisHistory
from app.models.schemas import AnalysisResponse

logger = logging.getLogger(__name__)

class AnalysisRepository(BaseRepository[AnalysisResult]):
    """Repository for analysis result database operations"""
    
    def __init__(self):
        super().__init__(AnalysisResult)
    
    def save_analysis_result(self, cv_record_id: int, job_description_id: int,
                           analysis_response: AnalysisResponse,
                           analysis_duration: float = None) -> AnalysisResult:
        """Save an analysis result"""
        analysis_dict = analysis_response.dict()
        
        # Extract detailed analysis data
        detailed_analysis = analysis_dict.get("detailed_analysis")
        skill_matches = []
        experience_matches = []
        education_matches = []
        
        if detailed_analysis:
            skill_matches = [match for match in detailed_analysis.get("skill_matches", [])]
            experience_matches = [match for match in detailed_analysis.get("experience_matches", [])]
            education_matches = [match for match in detailed_analysis.get("education_matches", [])]
        
        analysis_record = self.create(
            cv_record_id=cv_record_id,
            job_description_id=job_description_id,
            overall_suitability_score=analysis_response.suitability_score,
            technical_score=analysis_response.technical_score,
            experience_score=analysis_response.experience_score,
            education_score=analysis_response.education_score,
            scoring_rationale=analysis_response.scoring_rationale,
            matching_skills=analysis_response.matching_skills,
            missing_skills=analysis_response.missing_skills,
            recommendations=analysis_response.recommendations,
            red_flags=analysis_response.red_flags,
            skill_match_details=skill_matches,
            experience_match_details=experience_matches,
            education_match_details=education_matches,
            full_analysis_data=analysis_dict,
            analysis_duration_seconds=analysis_duration,
            analyzer_version="1.0"
        )
        
        logger.info(f"Saved analysis result with ID: {analysis_record.id}")
        return analysis_record
    
    def get_analysis_with_details(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis result with CV and job description details"""
        with self.get_session() as session:
            from app.models.database import CVRecord, JobDescriptionRecord
            
            result = session.query(
                AnalysisResult, CVRecord, JobDescriptionRecord
            ).join(
                CVRecord, AnalysisResult.cv_record_id == CVRecord.id
            ).join(
                JobDescriptionRecord, AnalysisResult.job_description_id == JobDescriptionRecord.id
            ).filter(AnalysisResult.id == analysis_id).first()
            
            if result:
                analysis, cv_record, job_record = result
                analysis_data = analysis.to_dict()
                analysis_data["cv_details"] = cv_record.to_dict()
                analysis_data["job_details"] = job_record.to_dict()
                return analysis_data
            
            return None
    
    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent analysis results with basic details"""
        with self.get_session() as session:
            from app.models.database import CVRecord, JobDescriptionRecord, FileUpload
            
            results = session.query(
                AnalysisResult, CVRecord, JobDescriptionRecord, FileUpload
            ).join(
                CVRecord, AnalysisResult.cv_record_id == CVRecord.id
            ).join(
                JobDescriptionRecord, AnalysisResult.job_description_id == JobDescriptionRecord.id
            ).join(
                FileUpload, CVRecord.file_upload_id == FileUpload.id
            ).order_by(
                AnalysisResult.created_at.desc()
            ).limit(limit).all()
            
            analysis_list = []
            for analysis, cv_record, job_record, file_upload in results:
                analysis_data = analysis.to_dict()
                analysis_data.update({
                    "cv_name": cv_record.contact_info.get("name") if cv_record.contact_info else "Unknown",
                    "cv_filename": file_upload.original_filename,
                    "job_title": job_record.title,
                    "job_company": job_record.company
                })
                analysis_list.append(analysis_data)
            
            return analysis_list
    
    def get_analyses_by_cv(self, cv_record_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a specific CV"""
        with self.get_session() as session:
            from app.models.database import JobDescriptionRecord
            
            results = session.query(AnalysisResult, JobDescriptionRecord).join(
                JobDescriptionRecord, AnalysisResult.job_description_id == JobDescriptionRecord.id
            ).filter(
                AnalysisResult.cv_record_id == cv_record_id
            ).order_by(AnalysisResult.created_at.desc()).all()
            
            analyses = []
            for analysis, job_record in results:
                analysis_data = analysis.to_dict()
                analysis_data["job_details"] = job_record.to_dict()
                analyses.append(analysis_data)
            
            return analyses
    
    def get_analyses_by_job(self, job_description_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a specific job description"""
        with self.get_session() as session:
            from app.models.database import CVRecord, FileUpload
            
            results = session.query(AnalysisResult, CVRecord, FileUpload).join(
                CVRecord, AnalysisResult.cv_record_id == CVRecord.id
            ).join(
                FileUpload, CVRecord.file_upload_id == FileUpload.id
            ).filter(
                AnalysisResult.job_description_id == job_description_id
            ).order_by(AnalysisResult.overall_suitability_score.desc()).all()
            
            analyses = []
            for analysis, cv_record, file_upload in results:
                analysis_data = analysis.to_dict()
                analysis_data.update({
                    "cv_name": cv_record.contact_info.get("name") if cv_record.contact_info else "Unknown",
                    "cv_filename": file_upload.original_filename
                })
                analyses.append(analysis_data)
            
            return analyses
    
    def get_top_matches_for_job(self, job_description_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top matching CVs for a job description"""
        analyses = self.get_analyses_by_job(job_description_id)
        return sorted(analyses, key=lambda x: x["overall_suitability_score"], reverse=True)[:limit]
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get overall analysis statistics"""
        with self.get_session() as session:
            total_analyses = session.query(AnalysisResult).count()
            
            # Average scores
            avg_scores = session.query(
                session.query(AnalysisResult.overall_suitability_score).subquery().c.overall_suitability_score.label('avg_overall'),
                session.query(AnalysisResult.technical_score).subquery().c.technical_score.label('avg_technical'),
                session.query(AnalysisResult.experience_score).subquery().c.experience_score.label('avg_experience'),
                session.query(AnalysisResult.education_score).subquery().c.education_score.label('avg_education')
            ).first()
            
            # Recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_analyses = session.query(AnalysisResult).filter(
                AnalysisResult.created_at >= thirty_days_ago
            ).count()
            
            return {
                "total_analyses": total_analyses,
                "recent_analyses_30_days": recent_analyses,
                "average_scores": {
                    "overall": avg_scores[0] if avg_scores else 0,
                    "technical": avg_scores[1] if avg_scores else 0,
                    "experience": avg_scores[2] if avg_scores else 0,
                    "education": avg_scores[3] if avg_scores else 0
                }
            }

class AnalysisHistoryRepository(BaseRepository[AnalysisHistory]):
    """Repository for analysis history tracking"""
    
    def __init__(self):
        super().__init__(AnalysisHistory)
    
    def track_view(self, analysis_result_id: int, view_type: str = "full",
                   user_agent: str = None, ip_address: str = None) -> AnalysisHistory:
        """Track when an analysis is viewed"""
        history_record = self.create(
            analysis_result_id=analysis_result_id,
            viewed_date=datetime.utcnow(),
            view_type=view_type,
            user_agent=user_agent,
            ip_address=ip_address,
            action_type="viewed"
        )
        
        return history_record
    
    def add_user_feedback(self, analysis_result_id: int, rating: int,
                         comment: str = None) -> AnalysisHistory:
        """Add user feedback for an analysis"""
        history_record = self.create(
            analysis_result_id=analysis_result_id,
            viewed_date=datetime.utcnow(),
            action_type="feedback",
            user_feedback_rating=rating,
            user_feedback_comment=comment,
            feedback_date=datetime.utcnow()
        )
        
        return history_record
    
    def track_action(self, analysis_result_id: int, action_type: str,
                    action_details: Dict[str, Any] = None) -> AnalysisHistory:
        """Track a specific action on an analysis"""
        history_record = self.create(
            analysis_result_id=analysis_result_id,
            viewed_date=datetime.utcnow(),
            action_type=action_type,
            action_details=action_details or {}
        )
        
        return history_record
    
    def get_analysis_history(self, analysis_result_id: int) -> List[Dict[str, Any]]:
        """Get all history entries for an analysis"""
        with self.get_session() as session:
            results = session.query(AnalysisHistory).filter(
                AnalysisHistory.analysis_result_id == analysis_result_id
            ).order_by(AnalysisHistory.created_at.desc()).all()
            
            return [entry.to_dict() for entry in results]
    
    def get_user_feedback_summary(self, analysis_result_id: int) -> Dict[str, Any]:
        """Get summary of user feedback for an analysis"""
        with self.get_session() as session:
            feedback_entries = session.query(AnalysisHistory).filter(
                (AnalysisHistory.analysis_result_id == analysis_result_id) &
                (AnalysisHistory.action_type == "feedback") &
                (AnalysisHistory.user_feedback_rating.isnot(None))
            ).all()
            
            if not feedback_entries:
                return {"total_feedback": 0, "average_rating": 0, "comments": []}
            
            ratings = [entry.user_feedback_rating for entry in feedback_entries]
            comments = [entry.user_feedback_comment for entry in feedback_entries if entry.user_feedback_comment]
            
            return {
                "total_feedback": len(feedback_entries),
                "average_rating": sum(ratings) / len(ratings),
                "ratings_distribution": {i: ratings.count(i) for i in range(1, 6)},
                "comments": comments
            }