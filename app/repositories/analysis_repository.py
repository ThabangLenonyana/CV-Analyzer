from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.repositories.base_repository import BaseRepository
from app.models.database import Analysis, CVRecord, JobDescription, FileUpload
from app.models.schemas import AnalysisResponse
from sqlalchemy import func
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

class AnalysisRepository(BaseRepository[Analysis]):
    """Simplified analysis repository"""
    
    def __init__(self):
        super().__init__(Analysis)
    
    def save_analysis_result(self, cv_record_id: int, job_description_id: int,
                       analysis_response: AnalysisResponse,
                       analysis_duration: float = None) -> Dict[str, Any]:
        """Save analysis result and return essential data immediately"""
        analysis_data = analysis_response.dict()
        if analysis_duration:
            analysis_data['duration_seconds'] = analysis_duration
    
        try:
            with self.get_db() as db:
                analysis = Analysis(
                    cv_record_id=cv_record_id,
                    job_description_id=job_description_id,
                    suitability_score=analysis_response.suitability_score,
                    analysis_data=analysis_data,
                    analysis_date=datetime.utcnow()
                )
                
                db.add(analysis)
                db.flush()  # Flush to get the ID without committing
                
                # Get all needed data while session is active
                analysis_id = analysis.id
                analysis_date = analysis.analysis_date
                
                db.commit()  # Now commit the transaction
                
                # Return a dictionary with the essential data
                return {
                    "id": analysis_id,
                    "analysis_date": analysis_date,
                    "cv_record_id": cv_record_id,
                    "job_description_id": job_description_id,
                    "suitability_score": analysis_response.suitability_score
                }
                
        except Exception as e:
            logger.error(f"Error saving analysis result: {str(e)}")
            raise
    
    def get_analysis_with_details(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Get full analysis details"""
        with self.get_db() as db:
            result = db.query(
                Analysis, CVRecord, JobDescription, FileUpload
            ).join(
                CVRecord, Analysis.cv_record_id == CVRecord.id
            ).join(
                JobDescription, Analysis.job_description_id == JobDescription.id
            ).join(
                FileUpload, CVRecord.file_upload_id == FileUpload.id
            ).filter(Analysis.id == analysis_id).first()
            
            if not result:
                return None
            
            analysis, cv, job, file = result
            data = self._format_analysis(analysis)
            data.update({
                "cv_details": {
                    "id": cv.id,
                    "name": cv.contact_name,
                    "email": cv.contact_email,
                    "filename": file.original_filename,
                    "parsed_data": cv.parsed_data
                },
                "job_details": {
                    "id": job.id,
                    "title": job.job_title,
                    "company": job.company,
                    "job_data": job.job_data
                }
            })
            
            return data
    
    def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent analyses with full details"""
        try:
            with self.get_db() as db:  # Add context manager
                analyses = (
                    db.query(Analysis)
                    .options(
                        joinedload(Analysis.cv_record).joinedload(CVRecord.file_upload),
                        joinedload(Analysis.job_description)
                    )
                    .order_by(Analysis.analysis_date.desc())
                    .limit(limit)
                    .all()
                )
                
                logger.info(f"Found {len(analyses)} analyses in database")
                
                # Convert to dict with related data
                results = []
                for analysis in analyses:
                    try:
                        # Create the result dictionary
                        result = {
                            'id': analysis.id,
                            'cv_record_id': analysis.cv_record_id,
                            'job_description_id': analysis.job_description_id,
                            'suitability_score': analysis.suitability_score,
                            'analysis_date': analysis.analysis_date.isoformat() if analysis.analysis_date else None,
                            'analysis_data': analysis.analysis_data
                        }
                        
                        # Add CV record data if available
                        if analysis.cv_record:
                            result['cv_record'] = {
                                'id': analysis.cv_record.id,
                                'contact_name': analysis.cv_record.contact_name,
                                'contact_email': analysis.cv_record.contact_email,
                                'parsed_data': analysis.cv_record.parsed_data
                            }
                            
                            # Add file upload data if available
                            if analysis.cv_record.file_upload:
                                result['cv_record']['file_upload'] = {
                                    'id': analysis.cv_record.file_upload.id,
                                    'original_filename': analysis.cv_record.file_upload.original_filename,
                                    'filename': analysis.cv_record.file_upload.filename,
                                    'upload_date': analysis.cv_record.file_upload.upload_date.isoformat() if analysis.cv_record.file_upload.upload_date else None
                            }
                        
                        # Add job description data if available
                        if analysis.job_description:
                            result['job_description'] = {
                                'id': analysis.job_description.id,
                                'job_title': analysis.job_description.job_title,
                                'company': analysis.job_description.company,
                                'job_data': analysis.job_description.job_data
                            }
                        
                        results.append(result)
                        logger.debug(f"Processed analysis {analysis.id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing analysis {analysis.id}: {str(e)}")
                        continue
                
                logger.info(f"Returning {len(results)} formatted analyses")
                return results
                
        except Exception as e:
            logger.error(f"Error getting recent analyses: {str(e)}", exc_info=True)
            return []
    
    def get_analyses_by_cv(self, cv_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a CV"""
        with self.get_db() as db:
            results = db.query(Analysis, JobDescription).join(
                JobDescription, Analysis.job_description_id == JobDescription.id
            ).filter(
                Analysis.cv_record_id == cv_id
            ).order_by(Analysis.analysis_date.desc()).all()
            
            analyses = []
            for analysis, job in results:
                data = self._format_analysis(analysis)
                data.update({
                    "job_title": job.job_title,
                    "company": job.company
                })
                analyses.append(data)
            
            return analyses
    
    def get_analyses_by_job(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a job"""
        with self.get_db() as db:
            results = db.query(Analysis, CVRecord, FileUpload).join(
                CVRecord, Analysis.cv_record_id == CVRecord.id
            ).join(
                FileUpload, CVRecord.file_upload_id == FileUpload.id
            ).filter(
                Analysis.job_description_id == job_id
            ).order_by(Analysis.suitability_score.desc()).all()
            
            analyses = []
            for analysis, cv, file in results:
                data = self._format_analysis(analysis)
                data.update({
                    "cv_name": cv.contact_name,
                    "cv_filename": file.original_filename
                })
                analyses.append(data)
            
            return analyses
    
    def get_top_matches_for_job(self, job_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top CV matches for a job"""
        return self.get_analyses_by_job(job_id)[:limit]
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get basic statistics"""
        with self.get_db() as db:
            total_analyses = db.query(func.count(Analysis.id)).scalar()
            
            # Average score
            avg_score = db.query(func.avg(Analysis.suitability_score)).scalar() or 0
            
            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_count = db.query(func.count(Analysis.id)).filter(
                Analysis.analysis_date >= week_ago
            ).scalar()
            
            # Count by score range
            excellent = db.query(func.count(Analysis.id)).filter(
                Analysis.suitability_score >= 80
            ).scalar()
            good = db.query(func.count(Analysis.id)).filter(
                Analysis.suitability_score.between(60, 79)
            ).scalar()
            fair = db.query(func.count(Analysis.id)).filter(
                Analysis.suitability_score.between(40, 59)
            ).scalar()
            poor = db.query(func.count(Analysis.id)).filter(
                Analysis.suitability_score < 40
            ).scalar()
            
            return {
                "total_analyses": total_analyses,
                "average_score": round(avg_score, 2),
                "recent_analyses": recent_count,
                "score_distribution": {
                    "excellent": excellent,
                    "good": good,
                    "fair": fair,
                    "poor": poor
                }
            }
    
    def _format_analysis(self, analysis: Analysis) -> Dict[str, Any]:
        """Format analysis for API response"""
        return {
            "id": analysis.id,
            "cv_id": analysis.cv_record_id,
            "job_id": analysis.job_description_id,
            "suitability_score": analysis.suitability_score,
            "analysis": analysis.analysis_data,
            "analysis_date": analysis.analysis_date,
            "created_at": analysis.analysis_date  # For compatibility
        }

# Remove AnalysisHistoryRepository since we don't have that table