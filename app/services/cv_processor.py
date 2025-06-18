import logging
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException

from app.services.file_handler import FileHandler
from app.services.cv_parser import parse_cv
from app.repositories.cv_repository import CVRepository, FileUploadRepository
from app.models.schemas import StructuredCV

logger = logging.getLogger(__name__)

class CVProcessor:
    """Service for processing CV uploads (orchestrator)"""
    
    def __init__(self):
        self.file_handler = FileHandler()
        self.cv_repository = CVRepository()
        self.file_repository = FileUploadRepository()
    
    async def process_cv_upload(self, file: UploadFile) -> Dict[str, Any]:
        """Process a CV file upload - orchestrates the entire workflow"""
        upload_record_id = None
        cv_record_id = None
        
        try:
            # Step 1: Save file
            filename, _, file_size = await self.file_handler.save_uploaded_file(file)
            logger.info(f"File saved: {filename}")
            
            # Step 2: Create upload record and get ID directly (session-safe)
            upload_record_id = self.file_repository.create_upload_record_and_get_id(
                filename=filename,
                original_filename=file.filename,
                file_size=file_size,
                file_type="cv"
            )
            logger.info(f"Upload record created with ID: {upload_record_id}")
            
            # Step 3: Parse CV (now returns tuple)
            file_path = self.file_handler.get_file_path(filename)
            logger.info(f"Parsing CV from: {file_path}")
            structured_cv, raw_parsed_json = await parse_cv(str(file_path))
            logger.info("CV parsed successfully")
            
            # Step 4: Save parsed CV with raw JSON and get ID immediately
            cv_record_id = self.cv_repository.save_cv_and_get_id(
                upload_record_id,
                structured_cv, 
                raw_parsed_json
            )
            logger.info(f"CV record saved with ID: {cv_record_id}")
            
            # Step 5: Update upload status
            self.file_repository.update_status(upload_record_id, "processed")
            
            # Step 6: Prepare response
            response = structured_cv.dict()
            response.update({
                "id": cv_record_id,  # Use the stored ID
                "upload_id": upload_record_id,
                "filename": filename,
                "original_filename": file.filename
            })
            
            logger.info(f"CV processed successfully. ID: {cv_record_id}")
            return response
            
        except Exception as e:
            # Update status to failed if we have an upload record ID
            if upload_record_id:
                try:
                    self.file_repository.update_status(upload_record_id, "failed")
                    logger.info(f"Updated upload {upload_record_id} status to failed")
                except Exception as update_error:
                    logger.error(f"Failed to update status to failed: {update_error}")
            
            logger.error(f"Error processing CV: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")
    
    def get_cv_by_id(self, cv_id: int) -> Dict[str, Any]:
        """Get CV by ID with file information"""
        cv_data = self.cv_repository.get_cv_with_file_info(cv_id)
        if not cv_data:
            raise HTTPException(status_code=404, detail="CV not found")
        return cv_data
    
    def get_structured_cv(self, cv_id: int) -> StructuredCV:
        """Get StructuredCV object from stored data without re-parsing"""
        structured_cv = self.cv_repository.get_structured_cv_by_id(cv_id)
        if not structured_cv:
            raise HTTPException(status_code=404, detail="CV not found")
        return structured_cv
    
    def get_recent_cvs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent CVs"""
        return self.cv_repository.get_recent_cvs(limit=limit)

# Create singleton instance
cv_processor = CVProcessor()