# Simplified database models - remove redundant tables and fields

from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class FileUpload(Base):
    """Track uploaded CV files"""
    __tablename__ = 'file_uploads'
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))
    upload_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    cv_record = relationship("CVRecord", back_populates="file_upload", uselist=False)

    def to_dict(self):
        """Convert FileUpload object to dictionary"""
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None
        }

class CVRecord(Base):
    """Store parsed CV data"""
    __tablename__ = 'cv_records'
    
    id = Column(Integer, primary_key=True, index=True)
    file_upload_id = Column(Integer, ForeignKey('file_uploads.id'), unique=True)
    
    # Core CV data as JSON
    parsed_data = Column(JSON, nullable=False)  # Complete structured CV data
    contact_name = Column(String(255), index=True)  # For quick searching
    contact_email = Column(String(255))
    
    parsed_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    file_upload = relationship("FileUpload", back_populates="cv_record")
    analyses = relationship("Analysis", back_populates="cv_record")

    def to_dict(self):
        """Convert CVRecord object to dictionary"""
        return {
            'id': self.id,
            'file_upload_id': self.file_upload_id,
            'parsed_data': self.parsed_data,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'parsed_date': self.parsed_date.isoformat() if self.parsed_date else None
        }

class JobDescription(Base):
    """Store job descriptions"""
    __tablename__ = 'job_descriptions'
    
    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    
    # Complete job data as JSON
    job_data = Column(JSON, nullable=False)  # Complete structured job data
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="job_description")
    
    def to_dict(self):
        """Convert JobDescription object to dictionary"""
        return {
            'id': self.id,
            'job_title': self.job_title,
            'company': self.company,
            'job_data': self.job_data,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Analysis(Base):
    """Store CV-Job analysis results"""
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True, index=True)
    cv_record_id = Column(Integer, ForeignKey('cv_records.id'), index=True)
    job_description_id = Column(Integer, ForeignKey('job_descriptions.id'), index=True)
    
    # Core scores
    suitability_score = Column(Float, nullable=False)
    
    # Complete analysis data as JSON
    analysis_data = Column(JSON, nullable=False)  # Complete analysis response
    
    analysis_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cv_record = relationship("CVRecord", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")

    def to_dict(self):
        """Convert Analysis object to dictionary"""
        return {
            'id': self.id,
            'cv_record_id': self.cv_record_id,
            'job_description_id': self.job_description_id,
            'suitability_score': self.suitability_score,
            'analysis_data': self.analysis_data,
            'analysis_date': self.analysis_date.isoformat() if self.analysis_date else None
        }