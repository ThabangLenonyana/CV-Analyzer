from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.repositories.base_repository import BaseRepository
from app.models.database import CVRecord, FileUpload
from app.models.schemas import StructuredCV

logger = logging.getLogger(__name__)

class CVRepository(BaseRepository[CVRecord]):
    """Simplified CV repository"""
    
    def __init__(self):
        super().__init__(CVRecord)
    
    def save_cv(self, file_upload_id: int, structured_cv: StructuredCV,
                raw_parsed_json: Dict[str, Any]) -> CVRecord:
        """Save parsed CV data"""
        contact_info = structured_cv.contact_info
        
        return self.create(
            file_upload_id=file_upload_id,
            parsed_data=structured_cv.dict(),
            contact_name=contact_info.name,
            contact_email=contact_info.email
        )
    
    def save_cv_and_get_id(self, file_upload_id: int, structured_cv: StructuredCV,
                           raw_parsed_json: Dict[str, Any]) -> int:
        """Save parsed CV data and return ID immediately using proper session management"""
        try:
            with self.get_db() as db:
                contact_info = structured_cv.contact_info
                
                cv_record = CVRecord(
                    file_upload_id=file_upload_id,
                    parsed_data=structured_cv.dict(),
                    contact_name=contact_info.name if contact_info else None,
                    contact_email=contact_info.email if contact_info else None,
                    parsed_date=datetime.utcnow()
                )
                
                db.add(cv_record)
                db.flush()  # Flush to get the ID without committing
                record_id = cv_record.id  # Get the ID while still in session
                db.commit()  # Now commit the transaction
                
                return record_id
                
        except Exception as e:
            logger.error(f"Error saving CV record: {str(e)}")
            raise
    
    def get_structured_cv_by_id(self, cv_id: int) -> Optional[StructuredCV]:
        """Get StructuredCV object from stored data without re-parsing"""
        with self.get_db() as db:
            cv_record = db.query(CVRecord).filter(CVRecord.id == cv_id).first()
            
            if not cv_record:
                return None
            
            try:
                # Access all needed attributes while session is still active
                parsed_data = cv_record.parsed_data
                contact_name = cv_record.contact_name
                contact_email = cv_record.contact_email
                
                # Reconstruct from stored parsed data
                if parsed_data:
                    # Create StructuredCV from the stored JSON data
                    return StructuredCV(**parsed_data)
                else:
                    # Fallback: create basic StructuredCV from database fields
                    return StructuredCV(
                        personal_info={
                            "name": contact_name or "Unknown",
                            "email": contact_email or "",
                        },
                        summary="",
                        experience=[],
                        education=[],
                        skills=[],
                        certifications=[],
                        languages=[]
                    )
                    
            except Exception as e:
                logger.error(f"Error reconstructing CV: {str(e)}")
                return None
    
    def get_cv_with_file_info(self, cv_id: int) -> Optional[Dict[str, Any]]:
        """Get CV with file information"""
        with self.get_db() as db:
            result = db.query(CVRecord, FileUpload)\
                .join(FileUpload)\
                .filter(CVRecord.id == cv_id)\
                .first()
            
            if not result:
                return None
            
            cv, file = result
            return {
                "id": cv.id,
                "filename": file.original_filename,
                "file_size": file.file_size,
                "upload_date": file.upload_date,
                "contact_name": cv.contact_name,
                "contact_email": cv.contact_email,
                "parsed_data": cv.parsed_data,
                "parsed_date": cv.parsed_date
            }
    
    def get_recent_cvs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent CVs"""
        with self.get_db() as db:
            results = db.query(CVRecord, FileUpload)\
                .join(FileUpload)\
                .order_by(CVRecord.parsed_date.desc())\
                .limit(limit)\
                .all()
            
            return [{
                "id": cv.id,
                "filename": file.original_filename,
                "contact_name": cv.contact_name,
                "contact_email": cv.contact_email,
                "parsed_date": cv.parsed_date,
                "upload_date": file.upload_date
            } for cv, file in results]

class FileUploadRepository(BaseRepository[FileUpload]):
    """Simple file upload repository"""
    
    def __init__(self):
        super().__init__(FileUpload)
    
    def create_upload_record(self, filename: str, original_filename: str,
                           file_size: int, file_type: str) -> FileUpload:
        """Create file upload record"""
        return self.create(
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            file_type=file_type
        )
    
    def update_status(self, upload_id: int, status: str) -> Optional[FileUpload]:
        """Update upload status (add status field if needed)"""
        # For now, just log it since we don't have status field
        logger.info(f"Upload {upload_id} status: {status}")
        return self.get(upload_id)
    
    def create_upload_record_and_get_id(self, filename: str, original_filename: str, 
                                       file_size: int, file_type: str) -> int:
        """Create upload record and return ID immediately using proper session management"""
        try:
            with self.get_db() as db:
                upload_record = FileUpload(
                    filename=filename,
                    original_filename=original_filename,
                    file_size=file_size,
                    file_type=file_type,
                    upload_date=datetime.utcnow()
                )
                
                db.add(upload_record)
                db.flush()  # Flush to get the ID without committing
                record_id = upload_record.id  # Get the ID while still in session
                db.commit()  # Now commit the transaction
                
                return record_id
                
        except Exception as e:
            logger.error(f"Error creating upload record: {str(e)}")
            raise