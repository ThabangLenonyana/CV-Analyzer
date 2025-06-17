# Rename from parsed_cv.py to database.py - clearly indicates these are database models
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json
from typing import Dict, Any

Base = declarative_base()

class FileUpload(Base):
    """Database model for file uploads (generic, not just CVs)"""
    __tablename__ = "file_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)
    file_type = Column(String(50), default="cv")  # cv, job_description, etc.
    status = Column(String(50), default="pending")  # pending, processed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CVRecord(Base):
    """Database model for CV records"""
    __tablename__ = "cv_records"
    
    id = Column(Integer, primary_key=True, index=True)
    file_upload_id = Column(Integer, index=True)
    
    # Store structured data as JSON
    contact_info = Column(JSON)
    summary = Column(Text)
    skills = Column(JSON)
    technical_skills = Column(JSON)
    experiences = Column(JSON)
    education = Column(JSON)
    projects = Column(JSON)
    certifications = Column(JSON)
    languages = Column(JSON)
    achievements = Column(JSON)
    publications = Column(JSON)
    
    # Store the raw parsed JSON from Gemini for future use
    raw_parsed_json = Column(JSON)  # Changed from raw_text to store the full parsed JSON
    
    parsed_date = Column(DateTime, default=datetime.utcnow)
    parser_version = Column(String(50), default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert database model to dictionary"""
        return {
            "id": self.id,
            "file_upload_id": self.file_upload_id,
            "contact_info": self.contact_info or {},
            "summary": self.summary,
            "skills": self.skills or [],
            "technical_skills": self.technical_skills or {},
            "experiences": self.experiences or [],
            "education": self.education or [],
            "projects": self.projects or [],
            "certifications": self.certifications or [],
            "languages": self.languages or [],
            "achievements": self.achievements or [],
            "publications": self.publications or [],
            "raw_parsed_json": self.raw_parsed_json or {}
        }
    
    def to_structured_cv_dict(self) -> Dict[str, Any]:
        """Convert to StructuredCV compatible dictionary"""
        # If we have the raw parsed JSON, use it as the base
        if self.raw_parsed_json:
            return self.raw_parsed_json
        
        # Otherwise, reconstruct from individual fields
        return {
            "contact_info": self.contact_info or {},
            "summary": self.summary,
            "skills": self.skills or [],
            "technical_skills": self.technical_skills or {},
            "experiences": self.experiences or [],
            "education": self.education or [],
            "projects": self.projects or [],
            "certifications": self.certifications or [],
            "languages": self.languages or [],
            "achievements": self.achievements or [],
            "publications": self.publications or []
        }

class JobDescriptionRecord(Base):
    """Database model for job descriptions"""
    __tablename__ = "job_descriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), index=True)
    location = Column(String(255))
    job_type = Column(String(50))  # Full-time, Part-time, Contract, etc.
    experience_level = Column(String(50))  # Entry, Mid, Senior, etc.
    
    # Store structured data as JSON
    summary = Column(Text)
    responsibilities = Column(JSON)  # List of responsibilities
    required_skills = Column(JSON)  # List of required skills
    preferred_skills = Column(JSON)  # List of preferred skills
    requirements = Column(JSON)  # List of JobRequirement objects
    education_requirements = Column(JSON)  # List of education requirements
    certifications_required = Column(JSON)  # List of required certifications
    benefits = Column(JSON)  # List of benefits
    salary_range = Column(String(100))
    
    # Store the original job description text and structured JSON
    raw_text = Column(Text)
    structured_data = Column(JSON)  # Full StructuredJobDescription as JSON
    
    # Metadata
    source = Column(String(100))  # e.g., "manual", "scraped", "uploaded"
    industry = Column(String(100))
    department = Column(String(100))
    is_active = Column(Integer, default=1)  # 1 for active, 0 for inactive
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("AnalysisResult", back_populates="job_description")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert database model to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "summary": self.summary,
            "responsibilities": self.responsibilities or [],
            "required_skills": self.required_skills or [],
            "preferred_skills": self.preferred_skills or [],
            "requirements": self.requirements or [],
            "education_requirements": self.education_requirements or [],
            "certifications_required": self.certifications_required or [],
            "benefits": self.benefits or [],
            "salary_range": self.salary_range,
            "raw_text": self.raw_text or "",
            "structured_data": self.structured_data or {},
            "source": self.source,
            "industry": self.industry,
            "department": self.department,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_structured_job_dict(self) -> Dict[str, Any]:
        """Convert to StructuredJobDescription compatible dictionary"""
        # If we have the structured data, use it as the base
        if self.structured_data:
            return self.structured_data
        
        # Otherwise, reconstruct from individual fields
        return {
            "job_title": self.title,
            "company": self.company,
            "location": self.location,
            "job_type": self.job_type,
            "experience_level": self.experience_level,
            "summary": self.summary,
            "responsibilities": self.responsibilities or [],
            "required_skills": self.required_skills or [],
            "preferred_skills": self.preferred_skills or [],
            "requirements": self.requirements or [],
            "education_requirements": self.education_requirements or [],
            "certifications_required": self.certifications_required or [],
            "benefits": self.benefits or [],
            "salary_range": self.salary_range,
            "raw_text": self.raw_text or ""
        }

class AnalysisResult(Base):
    """Database model for analysis results"""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    cv_record_id = Column(Integer, ForeignKey("cv_records.id"), nullable=False, index=True)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False, index=True)
    
    # Overall scores
    overall_suitability_score = Column(Integer, nullable=False)  # 0-100
    technical_score = Column(Integer, nullable=False)  # 0-100
    experience_score = Column(Integer, nullable=False)  # 0-100
    education_score = Column(Integer, nullable=False)  # 0-100
    
    # Analysis details stored as JSON
    scoring_rationale = Column(Text)
    matching_skills = Column(JSON)  # List of matching skills
    missing_skills = Column(JSON)  # List of missing skills
    recommendations = Column(JSON)  # List of recommendations
    red_flags = Column(JSON)  # List of red flags
    
    # Detailed analysis breakdown
    skill_match_details = Column(JSON)  # List of SkillMatch objects
    experience_match_details = Column(JSON)  # List of ExperienceMatch objects
    education_match_details = Column(JSON)  # List of EducationMatch objects
    
    # Store the complete AnalysisResponse as JSON for future reference
    full_analysis_data = Column(JSON)
    
    # Metadata
    analysis_date = Column(DateTime, default=datetime.utcnow)
    analyzer_version = Column(String(50), default="1.0")
    analysis_duration_seconds = Column(Float)  # How long the analysis took
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cv_record = relationship("CVRecord")
    job_description = relationship("JobDescriptionRecord", back_populates="analyses")
    history_entries = relationship("AnalysisHistory", back_populates="analysis")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert database model to dictionary"""
        return {
            "id": self.id,
            "cv_record_id": self.cv_record_id,
            "job_description_id": self.job_description_id,
            "overall_suitability_score": self.overall_suitability_score,
            "technical_score": self.technical_score,
            "experience_score": self.experience_score,
            "education_score": self.education_score,
            "scoring_rationale": self.scoring_rationale,
            "matching_skills": self.matching_skills or [],
            "missing_skills": self.missing_skills or [],
            "recommendations": self.recommendations or [],
            "red_flags": self.red_flags or [],
            "skill_match_details": self.skill_match_details or [],
            "experience_match_details": self.experience_match_details or [],
            "education_match_details": self.education_match_details or [],
            "full_analysis_data": self.full_analysis_data or {},
            "analysis_date": self.analysis_date.isoformat() if self.analysis_date else None,
            "analyzer_version": self.analyzer_version,
            "analysis_duration_seconds": self.analysis_duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class AnalysisHistory(Base):
    """Database model for tracking analysis history and user interactions"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_result_id = Column(Integer, ForeignKey("analysis_results.id"), nullable=False, index=True)
    
    # Tracking information
    viewed_date = Column(DateTime, default=datetime.utcnow)
    view_type = Column(String(50))  # "full", "summary", "api", "download"
    user_agent = Column(String(500))  # Browser/client information
    ip_address = Column(String(45))  # Support both IPv4 and IPv6
    
    # User feedback
    user_feedback_rating = Column(Integer)  # 1-5 stars
    user_feedback_comment = Column(Text)
    feedback_date = Column(DateTime)
    
    # Actions taken
    action_type = Column(String(50))  # "viewed", "downloaded", "shared", "feedback"
    action_details = Column(JSON)  # Additional action metadata
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analysis = relationship("AnalysisResult", back_populates="history_entries")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert database model to dictionary"""
        return {
            "id": self.id,
            "analysis_result_id": self.analysis_result_id,
            "viewed_date": self.viewed_date.isoformat() if self.viewed_date else None,
            "view_type": self.view_type,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "user_feedback_rating": self.user_feedback_rating,
            "user_feedback_comment": self.user_feedback_comment,
            "feedback_date": self.feedback_date.isoformat() if self.feedback_date else None,
            "action_type": self.action_type,
            "action_details": self.action_details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }