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
        upload_record = None
        
        try:
            # Step 1: Save file
            filename, _, file_size = await self.file_handler.save_uploaded_file(file)
            
            # Step 2: Create upload record
            upload_record = self.file_repository.create_upload_record(
                filename=filename,
                original_filename=file.filename,
                file_size=file_size,
                file_type="cv"
            )
            
            # Step 3: Parse CV (now returns tuple)
            file_path = self.file_handler.get_file_path(filename)
            structured_cv, raw_parsed_json = await parse_cv(str(file_path))
            
            # Step 4: Save parsed CV with raw JSON
            cv_record = self.cv_repository.save_cv(
                upload_record.id, 
                structured_cv, 
                raw_parsed_json
            )
            
            # Step 5: Update upload status
            self.file_repository.update_status(upload_record.id, "processed")
            
            # Step 6: Prepare response
            response = structured_cv.dict()
            response.update({
                "id": cv_record.id,
                "upload_id": upload_record.id,
                "filename": filename,
                "original_filename": file.filename
            })
            
            logger.info(f"CV processed successfully. ID: {cv_record.id}")
            return response
            
        except Exception as e:
            # Update status to failed if we have an upload record
            if upload_record:
                self.file_repository.update_status(upload_record.id, "failed")
            
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