from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.repositories.base_repository import BaseRepository
from app.models.database import CVRecord, FileUpload
from app.models.schemas import StructuredCV

logger = logging.getLogger(__name__)

class CVRepository(BaseRepository[CVRecord]):
    """Repository for CV database operations"""
    
    def __init__(self):
        super().__init__(CVRecord)
    
    def save_cv(self, file_upload_id: int, structured_cv: StructuredCV, raw_parsed_json: Dict[str, Any]) -> CVRecord:
        """Save parsed CV data with raw JSON"""
        cv_dict = structured_cv.dict()
        
        cv_record = self.create(
            file_upload_id=file_upload_id,
            contact_info=cv_dict.get("contact_info"),
            summary=cv_dict.get("summary"),
            skills=cv_dict.get("skills"),
            technical_skills=cv_dict.get("technical_skills"),
            experiences=cv_dict.get("experiences"),
            education=cv_dict.get("education"),
            projects=cv_dict.get("projects"),
            certifications=cv_dict.get("certifications"),
            languages=cv_dict.get("languages"),
            achievements=cv_dict.get("achievements"),
            publications=cv_dict.get("publications"),
            raw_parsed_json=raw_parsed_json  # Store the raw parsed JSON
        )
        
        logger.info(f"Saved CV record with ID: {cv_record.id}")
        return cv_record
    
    def get_structured_cv_by_id(self, cv_id: int) -> Optional[StructuredCV]:
        """Get StructuredCV from stored data without re-parsing"""
        cv_record = self.get_by_id(cv_id)
        if not cv_record:
            return None
        
        # Use the raw parsed JSON to reconstruct StructuredCV
        cv_data = cv_record.to_structured_cv_dict()
        
        # Import here to avoid circular imports
        from app.services.cv_parser import GeminiCVParser
        parser = GeminiCVParser()
        
        # Use the parser's validation method to create StructuredCV from stored JSON
        return parser._validate_and_structure(cv_data)
    
    def get_recent_cvs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent CV records with file information"""
        with self.get_session() as session:
            results = session.query(CVRecord, FileUpload)\
                .join(FileUpload, CVRecord.file_upload_id == FileUpload.id)\
                .order_by(CVRecord.created_at.desc())\
                .limit(limit)\
                .all()
            
            cv_list = []
            for cv_record, file_upload in results:
                cv_data = cv_record.to_dict()
                cv_data["filename"] = file_upload.original_filename
                cv_data["upload_date"] = file_upload.upload_date.isoformat()
                cv_list.append(cv_data)
            
            return cv_list
    
    def get_cv_with_file_info(self, cv_id: int) -> Optional[Dict[str, Any]]:
        """Get CV with associated file information"""
        with self.get_session() as session:
            result = session.query(CVRecord, FileUpload)\
                .join(FileUpload, CVRecord.file_upload_id == FileUpload.id)\
                .filter(CVRecord.id == cv_id)\
                .first()
            
            if result:
                cv_record, file_upload = result
                cv_data = cv_record.to_dict()
                cv_data["filename"] = file_upload.original_filename
                cv_data["upload_date"] = file_upload.upload_date.isoformat()
                return cv_data
            
            return None

class FileUploadRepository(BaseRepository[FileUpload]):
    """Repository for file upload operations"""
    
    def __init__(self):
        super().__init__(FileUpload)
    
    def create_upload_record(self, filename: str, original_filename: str, 
                           file_size: int, file_type: str = "cv") -> FileUpload:
        """Create a new file upload record"""
        upload = self.create(
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            file_type=file_type,
            status="pending"
        )
        logger.info(f"Created file upload record with ID: {upload.id}")
        return upload
    
    def update_status(self, upload_id: int, status: str) -> Optional[FileUpload]:
        """Update upload status"""
        return self.update(upload_id, status=status)