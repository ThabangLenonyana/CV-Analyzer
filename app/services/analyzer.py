import google.genai as genai
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import asyncio
from datetime import datetime
import re
from collections import defaultdict

from app.models.schemas import (
    StructuredCV, StructuredJobDescription, AnalysisResponse,
    DetailedAnalysis, SkillMatch, ExperienceMatch, EducationMatch,
    JobRequirement
)

# Configure logging
logger = logging.getLogger(__name__)

class AnalysisError(Exception):
    """Custom exception for analysis errors"""
    pass

class CVJobAnalyzer:
    """Service for analyzing CV compatibility with job descriptions using Gemini"""
    
    def __init__(self):
        self.client = None
        self.model = None
        self.configure_gemini()
    
    def configure_gemini(self):
        """Configure the Gemini API with credentials"""
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            self.client = genai.Client(api_key=api_key)
            self.model = 'gemini-2.0-flash'
            logger.info("Gemini API configured successfully for analyzer")
        except Exception as e:
            logger.error(f"Error configuring Gemini API: {str(e)}")
            raise AnalysisError(f"Failed to configure Gemini API: {str(e)}")
    
    async def analyze_cv_for_job(self, 
                                 structured_cv: StructuredCV, 
                                 structured_job: StructuredJobDescription,
                                 detailed: bool = True) -> AnalysisResponse:
        """
        Analyze CV against job description
        
        Args:
            structured_cv: Parsed CV data
            structured_job: Parsed job description data
            detailed: Whether to include detailed analysis
            
        Returns:
            AnalysisResponse with complete analysis
        """
        try:
            # Conduct multi-stage analysis
            # Stage 1: Skills analysis
            skills_analysis = await self._analyze_skills(structured_cv, structured_job)
            
            # Stage 2: Experience analysis
            experience_analysis = await self._analyze_experience(structured_cv, structured_job)
            
            # Stage 3: Education analysis
            education_analysis = await self._analyze_education(structured_cv, structured_job)
            
            # Stage 4: Overall suitability and recommendations
            # Stage 4: Overall suitability and recommendations
            overall_analysis = await self._analyze_overall_suitability(
                structured_cv, structured_job, 
                skills_analysis, experience_analysis, education_analysis
            )
            
            # Calculate scores
            scores = self._calculate_scores(
                skills_analysis, experience_analysis, 
                education_analysis, overall_analysis
            )
            
            # Build response
            response = AnalysisResponse(
                suitability_score=scores['overall'],
                technical_score=scores['technical'],
                experience_score=scores['experience'],
                education_score=scores['education'],
                scoring_rationale=overall_analysis.get('rationale', ''),
                matching_skills=skills_analysis.get('matching', []),
                missing_skills=skills_analysis.get('missing', []),
                recommendations=overall_analysis.get('recommendations', []),
                red_flags=overall_analysis.get('red_flags', [])
            )
            
            # Add detailed analysis if requested
            if detailed:
                response.detailed_analysis = await self._create_detailed_analysis(
                    structured_cv, structured_job,
                    skills_analysis, experience_analysis, education_analysis
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error analyzing CV: {str(e)}")
            raise AnalysisError(f"Failed to analyze CV: {str(e)}")
    
    async def _analyze_skills(self, cv: StructuredCV, job: StructuredJobDescription) -> Dict[str, Any]:
        """Analyze skills match between CV and job"""
        # Combine all CV skills
        cv_skills = set(cv.skills)
        for category, skills in cv.technical_skills.items():
            cv_skills.update(skills)
        
        # Extract skills from experiences and projects
        for exp in cv.experiences:
            # Look for skills in responsibilities and achievements
            text = ' '.join(exp.responsibilities + exp.achievements)
            cv_skills.update(self._extract_skills_from_text(text))
        
        for proj in cv.projects:
            cv_skills.update(proj.technologies)
        
        # Normalize skills for comparison
        cv_skills_normalized = {skill.lower().strip() for skill in cv_skills}
        required_skills_normalized = {skill.lower().strip() for skill in job.required_skills}
        preferred_skills_normalized = {skill.lower().strip() for skill in job.preferred_skills}
        
        # Find matches
        matching_required = []
        missing_required = []
        
        for skill in job.required_skills:
            if any(self._skills_match(skill, cv_skill) for cv_skill in cv_skills):
                matching_required.append(skill)
            else:
                missing_required.append(skill)
        
        matching_preferred = []
        for skill in job.preferred_skills:
            if any(self._skills_match(skill, cv_skill) for cv_skill in cv_skills):
                matching_preferred.append(skill)
        
        # Use Gemini for deeper skill analysis
        skill_analysis_prompt = f"""
        Analyze the skills match between this CV and job requirements.
        
        CV Skills: {json.dumps(list(cv_skills))}
        Required Skills: {json.dumps(job.required_skills)}
        Preferred Skills: {json.dumps(job.preferred_skills)}
        
        Identify:
        1. Direct skill matches
        2. Related/transferable skills that could apply
        3. Critical gaps
        4. Hidden strengths not explicitly listed
        
        Return a JSON object with:
        {{
            "strong_matches": ["skills that strongly match"],
            "partial_matches": ["skills that partially match or are related"],
            "critical_gaps": ["important missing skills"],
            "transferable_skills": ["CV skills that could transfer to job requirements"],
            "skill_strength_rating": "weak/moderate/strong"
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[{"parts": [{"text": skill_analysis_prompt}]}]
            )
            
            skill_insights = json.loads(self._extract_json_from_response(response.text))
        except:
            skill_insights = {}
        
        return {
            'matching': matching_required + matching_preferred,
            'missing': missing_required,
            'matching_required': matching_required,
            'matching_preferred': matching_preferred,
            'insights': skill_insights,
            'cv_skills': list(cv_skills)
        }
    
    async def _analyze_experience(self, cv: StructuredCV, job: StructuredJobDescription) -> Dict[str, Any]:
        """Analyze experience match"""
        # Extract years of experience
        cv_years = self._calculate_total_experience(cv)
        required_years = self._extract_required_years(job)
        
        # Analyze role relevance
        experience_prompt = f"""
        Analyze how well this candidate's experience matches the job requirements.
        
        Candidate Experience:
        {json.dumps([{
            'company': exp.company,
            'position': exp.position,
            'duration': f"{exp.start_date} to {exp.end_date}",
            'key_points': exp.responsibilities[:3] + exp.achievements[:2]
        } for exp in cv.experiences], indent=2)}
        
        Job Requirements:
        - Title: {job.job_title}
        - Level: {job.experience_level}
        - Key Responsibilities: {json.dumps(job.responsibilities[:5])}
        
        Analyze:
        1. Role similarity and progression
        2. Industry/domain relevance
        3. Responsibility overlap
        4. Achievement quality
        5. Career trajectory
        
        Return JSON:
        {{
            "relevance_score": "low/medium/high",
            "matching_experiences": ["relevant experience descriptions"],
            "experience_gaps": ["missing experience areas"],
            "career_progression": "positive/neutral/concerning",
            "years_match": "under/meets/exceeds requirements",
            "key_insights": ["important observations"]
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[{"parts": [{"text": experience_prompt}]}]
            )
            
            exp_analysis = json.loads(self._extract_json_from_response(response.text))
        except:
            exp_analysis = {'relevance_score': 'medium'}
        
        return {
            'total_years': cv_years,
            'required_years': required_years,
            'analysis': exp_analysis,
            'experiences': [{
                'company': exp.company,
                'position': exp.position,
                'duration': f"{exp.start_date or 'Unknown'} - {exp.end_date or 'Present'}"
            } for exp in cv.experiences]
        }
    
    async def _analyze_education(self, cv: StructuredCV, job: StructuredJobDescription) -> Dict[str, Any]:
        """Analyze education match"""
        education_data = {
            'degrees': [f"{edu.degree} in {edu.field_of_study or 'N/A'}" for edu in cv.education],
            'institutions': [edu.institution for edu in cv.education],
            'requirements': job.education_requirements,
            'certifications': [cert.name for cert in cv.certifications],
            'required_certs': job.certifications_required
        }
        
        # Check basic education requirements
        meets_requirements = any(
            self._education_meets_requirement(edu, req)
            for edu in cv.education
            for req in job.education_requirements
        ) if job.education_requirements else True
        
        # Check certifications
        has_required_certs = all(
            any(self._certification_matches(cert.name, req) for cert in cv.certifications)
            for req in job.certifications_required
        ) if job.certifications_required else True
        
        return {
            'meets_requirements': meets_requirements,
            'has_required_certifications': has_required_certs,
            'education_details': education_data,
            'missing_certifications': [
                req for req in job.certifications_required
                if not any(self._certification_matches(cert.name, req) for cert in cv.certifications)
            ]
        }
    
    async def _analyze_overall_suitability(self, cv: StructuredCV, job: StructuredJobDescription,
                                         skills_analysis: Dict, experience_analysis: Dict,
                                         education_analysis: Dict) -> Dict[str, Any]:
        """Generate overall suitability analysis and recommendations"""
        # Prepare context for Gemini
        context = f"""
        Analyze this candidate's overall suitability for the position.
        
        Job: {job.job_title} at {job.company or 'Unknown Company'}
        Level: {job.experience_level or 'Not specified'}
        
        Skills Match:
        - Matching required: {len(skills_analysis['matching_required'])}/{len(job.required_skills)}
        - Missing critical: {json.dumps(skills_analysis['missing'][:5])}
        
        Experience:
        - Years: {experience_analysis['total_years']} (required: {experience_analysis['required_years']})
        - Relevance: {experience_analysis['analysis'].get('relevance_score', 'unknown')}
        
        Education:
        - Meets requirements: {education_analysis['meets_requirements']}
        - Has required certs: {education_analysis['has_required_certifications']}
        
        Provide:
        1. Executive summary of fit (2-3 sentences)
        2. Top 3-5 specific recommendations for the candidate
        3. Any red flags or concerns
        4. Overall hire recommendation
        
        Return JSON:
        {{
            "rationale": "executive summary",
            "recommendations": ["specific actionable recommendations"],
            "red_flags": ["concerns or gaps"],
            "hire_recommendation": "strong yes/yes/maybe/no",
            "key_strengths": ["top strengths for this role"],
            "improvement_areas": ["areas to improve for better fit"]
        }}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[{"parts": [{"text": context}]}]
            )
            
            analysis = json.loads(self._extract_json_from_response(response.text))
            return analysis
        except:
            return {
                'rationale': 'Unable to generate detailed analysis',
                'recommendations': ['Review skills match', 'Consider experience relevance'],
                'red_flags': []
            }
    
    async def _create_detailed_analysis(self, cv: StructuredCV, job: StructuredJobDescription,
                                      skills_analysis: Dict, experience_analysis: Dict,
                                      education_analysis: Dict) -> DetailedAnalysis:
        """Create detailed analysis object"""
        detailed = DetailedAnalysis()
        
        # Skill matches with evidence
        for skill in skills_analysis['matching_required']:
            evidence = self._find_skill_evidence(skill, cv)
            detailed.skill_matches.append(SkillMatch(
                skill=skill,
                cv_evidence=evidence,
                strength="strong" if len(evidence) > 2 else "moderate"
            ))
        
        # Experience matches
        for i, req in enumerate(job.responsibilities[:5]):
            match = self._find_experience_match(req, cv)
            detailed.experience_matches.append(ExperienceMatch(
                requirement=req,
                cv_experience=match['experience'],
                match_quality=match['quality']
            ))
        
        # Education matches
        for req in job.education_requirements:
            match = self._find_education_match(req, cv)
            detailed.education_matches.append(EducationMatch(
                requirement=req,
                cv_education=match['education'],
                meets_requirement=match['meets']
            ))
        
        # Strengths and gaps
        insights = skills_analysis.get('insights', {})
        detailed.technical_strengths = insights.get('strong_matches', [])[:5]
        detailed.technical_gaps = insights.get('critical_gaps', [])[:5]
        
        exp_insights = experience_analysis['analysis']
        detailed.experience_strengths = exp_insights.get('matching_experiences', [])[:3]
        detailed.experience_gaps = exp_insights.get('experience_gaps', [])[:3]
        
        # Education alignment
        if education_analysis['meets_requirements'] and education_analysis['has_required_certifications']:
            detailed.education_alignment = "strong"
        elif education_analysis['meets_requirements']:
            detailed.education_alignment = "moderate"
        else:
            detailed.education_alignment = "weak"
        
        return detailed
    
    def _calculate_scores(self, skills_analysis: Dict, experience_analysis: Dict,
                         education_analysis: Dict, overall_analysis: Dict) -> Dict[str, int]:
        """Calculate numerical scores for each category"""
        # Technical score
        required_skills = len(skills_analysis.get('matching_required', []))
        total_required = len(skills_analysis.get('missing', [])) + required_skills
        technical_score = int((required_skills / total_required * 100) if total_required > 0 else 50)
        
        # Experience score
        exp_relevance = experience_analysis['analysis'].get('relevance_score', 'medium')
        exp_score_map = {'low': 30, 'medium': 60, 'high': 90}
        experience_score = exp_score_map.get(exp_relevance, 50)
        
        # Adjust for years of experience
        if experience_analysis['total_years'] >= experience_analysis['required_years']:
            experience_score = min(100, experience_score + 10)
        
        # Education score
        education_score = 100 if education_analysis['meets_requirements'] else 50
        if not education_analysis['has_required_certifications']:
            education_score -= 20
        
        # Overall score (weighted average)
        overall_score = int(
            technical_score * 0.4 +
            experience_score * 0.4 +
            education_score * 0.2
        )
        
        # Adjust based on hire recommendation
        hire_rec = overall_analysis.get('hire_recommendation', 'maybe')
        if hire_rec == 'strong yes':
            overall_score = max(85, overall_score)
        elif hire_rec == 'no':
            overall_score = min(40, overall_score)
        
        return {
            'technical': technical_score,
            'experience': experience_score,
            'education': education_score,
            'overall': overall_score
        }
    
    # Helper methods
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from model response"""
        cleaned = response_text.strip()
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
        
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            return json_match.group(0)
        return cleaned
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract potential skills from text"""
        # Common skill patterns
        skill_keywords = ['python', 'java', 'javascript', 'react', 'django', 'aws', 'docker',
                         'kubernetes', 'sql', 'mongodb', 'git', 'ci/cd', 'agile', 'scrum']
        
        found_skills = []
        text_lower = text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _skills_match(self, required: str, candidate: str) -> bool:
        """Check if two skills match (fuzzy matching)"""
        required_lower = required.lower().strip()
        candidate_lower = candidate.lower().strip()
        
        # Exact match
        if required_lower == candidate_lower:
            return True
        
        # Substring match
        if required_lower in candidate_lower or candidate_lower in required_lower:
            return True
        
        # Common variations
        variations = {
            'javascript': ['js', 'node.js', 'nodejs'],
            'python': ['py'],
            'kubernetes': ['k8s'],
            'amazon web services': ['aws'],
            'google cloud platform': ['gcp'],
            'continuous integration': ['ci', 'ci/cd']
        }
        
        for key, vals in variations.items():
            if required_lower in [key] + vals and candidate_lower in [key] + vals:
                return True
        
        return False
    
    def _calculate_total_experience(self, cv: StructuredCV) -> int:
        """Calculate total years of experience"""
        total_months = 0
        
        for exp in cv.experiences:
            if exp.start_date:
                try:
                    start = datetime.strptime(exp.start_date, '%Y-%m')
                    if exp.end_date and exp.end_date.lower() != 'present':
                        end = datetime.strptime(exp.end_date, '%Y-%m')
                    else:
                        end = datetime.now()
                    
                    months = (end.year - start.year) * 12 + end.month - start.month
                    total_months += max(0, months)
                except:
                    # If date parsing fails, estimate 2 years per position
                    total_months += 24
        
        return total_months // 12
    
    def _extract_required_years(self, job: StructuredJobDescription) -> int:
        """Extract required years of experience from job description"""
        # Look in experience level
        if job.experience_level:
            level_map = {
                'entry': 0, 'junior': 1, 'mid': 3,
                'senior': 5, 'lead': 7, 'principal': 10
            }
            for key, years in level_map.items():
                if key in job.experience_level.lower():
                    return years
        
        # Look in requirements
        for req_group in job.requirements:
            for req in req_group.requirements:
                match = re.search(r'(\d+)\+?\s*years?', req.lower())
                if match:
                    return int(match.group(1))
        
        return 0
    
    def _education_meets_requirement(self, education, requirement: str) -> bool:
        """Check if education meets requirement"""
        req_lower = requirement.lower()
        edu_text = f"{education.degree} {education.field_of_study or ''}".lower()
        
        # Check for degree level
        degree_levels = ['bachelor', 'master', 'phd', 'doctorate']
        for level in degree_levels:
            if level in req_lower and level in edu_text:
                return True
        
        # Check for field match
        if education.field_of_study:
            field_lower = education.field_of_study.lower()
            if any(field in req_lower for field in field_lower.split()):
                return True
        
        return False
    
    def _certification_matches(self, cert_name: str, requirement: str) -> bool:
        """Check if certification matches requirement"""
        cert_lower = cert_name.lower()
        req_lower = requirement.lower()
        
        # Direct match
        if req_lower in cert_lower or cert_lower in req_lower:
            return True
        
        # Common certification abbreviations
        cert_map = {
            'aws certified': ['aws', 'amazon web services'],
            'azure': ['az-', 'microsoft azure'],
            'google cloud': ['gcp', 'google certified'],
            'cisco': ['ccna', 'ccnp', 'ccie'],
            'comptia': ['a+', 'network+', 'security+']
        }
        
        for key, values in cert_map.items():
            if any(v in req_lower for v in [key] + values) and any(v in cert_lower for v in [key] + values):
                return True
        
        return False
    
    def _find_skill_evidence(self, skill: str, cv: StructuredCV) -> List[str]:
        """Find evidence of skill in CV"""
        evidence = []
        skill_lower = skill.lower()
        
        # Check in skills sections
        if skill in cv.skills or any(skill in s for s in cv.skills):
            evidence.append("Listed in skills section")
        
        # Check in technical skills
        for category, skills in cv.technical_skills.items():
            if any(skill_lower in s.lower() for s in skills):
                evidence.append(f"Listed under {category}")
        
        # Check in experiences
        for exp in cv.experiences:
            exp_text = ' '.join(exp.responsibilities + exp.achievements).lower()
            if skill_lower in exp_text:
                evidence.append(f"Used at {exp.company}")
        
        # Check in projects
        for proj in cv.projects:
            if any(skill_lower in tech.lower() for tech in proj.technologies):
                evidence.append(f"Used in project: {proj.name}")
        
        return evidence[:3]  # Return top 3 evidence
    
    def _find_experience_match(self, requirement: str, cv: StructuredCV) -> Dict[str, Any]:
        """Find matching experience for a requirement"""
        best_match = {'experience': None, 'quality': 'none'}
        
        for exp in cv.experiences:
            for resp in exp.responsibilities + exp.achievements:
                if self._text_similarity(requirement, resp) > 0.3:
                    best_match = {
                        'experience': f"{exp.position} at {exp.company}: {resp[:100]}...",
                        'quality': 'full' if self._text_similarity(requirement, resp) > 0.6 else 'partial'
                    }
                    break
            
            if best_match['quality'] == 'full':
                break
        
        return best_match
    
    def _find_education_match(self, requirement: str, cv: StructuredCV) -> Dict[str, Any]:
        """Find matching education for a requirement"""
        for edu in cv.education:
            if self._education_meets_requirement(edu, requirement):
                return {
                    'education': f"{edu.degree} in {edu.field_of_study or 'N/A'} from {edu.institution}",
                    'meets': True
                }
        
        return {'education': None, 'meets': False}
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

# Singleton instance
_analyzer_instance = None

def get_cv_analyzer() -> CVJobAnalyzer:
    """Get or create singleton analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = CVJobAnalyzer()
    return _analyzer_instance

# Convenience function
async def analyze_cv_job_match(structured_cv: StructuredCV, structured_job: StructuredJobDescription, detailed: bool = True) -> AnalysisResponse:
    """
    Analyze CV against job description
    
    Args:
        structured_cv: Parsed CV data
        structured_job: Parsed job description data
        detailed: Include detailed analysis
        
    Returns:
        AnalysisResponse with complete analysis
    """
    analyzer = get_cv_analyzer()
    return await analyzer.analyze_cv_for_job(structured_cv, structured_job, detailed)