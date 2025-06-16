from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Union

# CV Section Models
class ContactInfo(BaseModel):
    """Contact information extracted from CV"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None

class Education(BaseModel):
    """Education entry"""
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[str] = None
    achievements: List[str] = []

class Experience(BaseModel):
    """Work experience entry"""
    company: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    responsibilities: List[str] = []
    achievements: List[str] = []

class Project(BaseModel):
    """Project entry"""
    name: str
    description: Optional[str] = None
    technologies: List[str] = []
    role: Optional[str] = None
    highlights: List[str] = []

class Certification(BaseModel):
    """Certification entry"""
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    credential_id: Optional[str] = None

class Achievement(BaseModel):
    """Achievement entry with optional date"""
    achievement: str
    date: Optional[str] = None
    
    @validator('achievement', pre=True)
    def extract_achievement(cls, v):
        if isinstance(v, dict):
            return v.get('achievement', str(v))
        return str(v)

class StructuredCV(BaseModel):
    """Structured CV data"""
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    skills: List[str] = []
    technical_skills: Dict[str, List[str]] = {}  # e.g., {"Programming": ["Python", "Java"]}
    experiences: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    certifications: List[Certification] = []
    languages: List[str] = []
    achievements: List[Union[str, Achievement]] = []  # Can be either strings or Achievement objects
    publications: List[str] = []
    raw_text: str = ""  # Keep the raw text for reference
    
    @validator('achievements', pre=True)
    def normalize_achievements(cls, v):
        """Convert various achievement formats to a consistent structure"""
        if not v:
            return []
        
        normalized = []
        for item in v:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                # If it has 'achievement' key, extract it
                if 'achievement' in item:
                    achievement_text = item['achievement']
                    date = item.get('date', '')
                    if date:
                        normalized.append(f"{achievement_text} ({date})")
                    else:
                        normalized.append(achievement_text)
                else:
                    # Try to convert the dict to a meaningful string
                    normalized.append(str(item))
            else:
                normalized.append(str(item))
        
        return normalized

# Job Description Section Models
class JobRequirement(BaseModel):
    """Job requirement entry"""
    category: str  # e.g., "Required", "Preferred", "Nice to have"
    requirements: List[str]

class StructuredJobDescription(BaseModel):
    """Structured job description data"""
    job_title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Part-time, Contract, etc.
    experience_level: Optional[str] = None  # Entry, Mid, Senior, etc.
    summary: Optional[str] = None
    responsibilities: List[str] = []
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    requirements: List[JobRequirement] = []
    education_requirements: List[str] = []
    certifications_required: List[str] = []
    benefits: List[str] = []
    salary_range: Optional[str] = None
    raw_text: str = ""  # Keep the raw text for reference

# Analysis Models
class SkillMatch(BaseModel):
    """Skill matching detail"""
    skill: str
    cv_evidence: List[str] = []  # Where this skill appears in CV
    strength: str = "weak"  # weak, moderate, strong

class ExperienceMatch(BaseModel):
    """Experience matching detail"""
    requirement: str
    cv_experience: Optional[str] = None
    years_required: Optional[int] = None
    years_possessed: Optional[int] = None
    match_quality: str = "none"  # none, partial, full

class EducationMatch(BaseModel):
    """Education matching detail"""
    requirement: str
    cv_education: Optional[str] = None
    meets_requirement: bool = False

class DetailedAnalysis(BaseModel):
    """Detailed analysis breakdown"""
    skill_matches: List[SkillMatch] = []
    experience_matches: List[ExperienceMatch] = []
    education_matches: List[EducationMatch] = []
    certification_matches: List[str] = []
    
    # Strengths and weaknesses by category
    technical_strengths: List[str] = []
    technical_gaps: List[str] = []
    experience_strengths: List[str] = []
    experience_gaps: List[str] = []
    education_alignment: str = "weak"  # weak, moderate, strong

class AnalysisRequest(BaseModel):
    """Request model for CV analysis"""
    job_description: str = Field(..., min_length=50, description="Job description text")

class AnalysisResponse(BaseModel):
    """Enhanced response model for CV analysis"""
    suitability_score: int = Field(..., ge=0, le=100, description="Overall suitability score (0-100)")
    
    # Category scores
    technical_score: int = Field(..., ge=0, le=100, description="Technical skills match score")
    experience_score: int = Field(..., ge=0, le=100, description="Experience match score")
    education_score: int = Field(..., ge=0, le=100, description="Education match score")
    
    # Summary
    scoring_rationale: str = Field(..., description="Executive summary of the analysis")
    
    # Detailed breakdowns
    matching_skills: List[str] = Field(..., description="Skills matching the job description")
    missing_skills: List[str] = Field(..., description="Required skills missing from the CV")
    
    # Recommendations
    recommendations: List[str] = Field(default=[], description="Specific recommendations for the candidate")
    red_flags: List[str] = Field(default=[], description="Potential concerns or red flags")
    
    # Detailed analysis (optional, for premium features)
    detailed_analysis: Optional[DetailedAnalysis] = None

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Detailed error information")