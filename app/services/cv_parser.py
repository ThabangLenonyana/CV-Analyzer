import google.genai as genai
import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio
from datetime import datetime
import re

from app.models.schemas import StructuredCV, ContactInfo, Education, Experience, Project, Certification

# Configure logging
logger = logging.getLogger(__name__)

class CVParsingError(Exception):
    """Custom exception for CV parsing errors"""
    pass

class GeminiCVParser:
    """Service for parsing CVs using Google Gemini Vision API"""
    
    def __init__(self):
        self.model = None
        self.configure_gemini()
    
    def configure_gemini(self):
        """Configure the Gemini API with credentials"""
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            # Configure the client
            self.client = genai.Client(api_key=api_key)
            self.model = 'gemini-1.5-flash'  # Model name for the new API
            logger.info("Gemini API configured successfully")
        except Exception as e:
            logger.error(f"Error configuring Gemini API: {str(e)}")
            raise CVParsingError(f"Failed to configure Gemini API: {str(e)}")
    
    async def parse_cv_from_file(self, file_path: str) -> StructuredCV:
        """
        Parse CV from a file using Gemini Vision
        
        Args:
            file_path: Path to the CV file (PDF, DOCX, or image)
            
        Returns:
            StructuredCV object with extracted information
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"CV file not found: {file_path}")
            
            # Read file content
            logger.info(f"Reading CV file: {file_path}")
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Parse CV with retry logic
            result = await self._parse_with_retry(file_content, file_path)
            
            # Validate and structure the result
            structured_cv = self._validate_and_structure(result)
            
            # Extract raw text if not provided
            if not structured_cv.raw_text:
                structured_cv.raw_text = await self._extract_raw_text(file_content, file_path)
            
            return structured_cv
            
        except Exception as e:
            logger.error(f"Error parsing CV: {str(e)}")
            raise CVParsingError(f"Failed to parse CV: {str(e)}")
    
    async def _parse_with_retry(self, file_content: bytes, file_path: str, max_retries: int = 3) -> Dict[str, Any]:
        """Parse CV with retry logic for robustness"""
        prompt = self._create_extraction_prompt()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Parsing attempt {attempt + 1}/{max_retries}")
                
                # Create the request with file content
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=[
                        {
                            "parts": [
                                {"text": prompt},
                                {
                                    "inline_data": {
                                        "mime_type": self._get_mime_type(file_path),
                                        "data": file_content
                                    }
                                }
                            ]
                        }
                    ]
                )
                
                # Extract and clean JSON from response
                json_str = self._extract_json_from_response(response.text)
                return json.loads(json_str)
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise CVParsingError("Failed to parse JSON response after all retries")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type based on file extension"""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def _create_extraction_prompt(self) -> str:
        """Create detailed prompt for CV extraction"""
        return """
        You are an expert CV/Resume parser. Extract ALL information from the provided document 
        and return it as a valid JSON object following this exact schema. Be thorough and extract
        every detail you can find.

        **IMPORTANT INSTRUCTIONS:**
        1. Return ONLY valid JSON - no markdown, no explanations
        2. Use null for missing optional fields, empty arrays [] for missing lists
        3. Extract dates in YYYY-MM format when possible, or as found in the document
        4. Categorize technical skills appropriately (e.g., "Programming Languages", "Frameworks", "Databases", etc.)
        5. Differentiate between responsibilities and achievements in experiences
        6. Extract ALL skills mentioned throughout the document, not just from skills section
        7. For achievements array, use ONLY strings, not objects. If achievements have dates, include them in the string like "Achievement text (Date)"

        **JSON Schema:**
        {
            "contact_info": {
                "name": "string or null",
                "email": "string or null",
                "phone": "string or null",
                "linkedin": "string or null",
                "github": "string or null",
                "location": "string or null"
            },
            "summary": "string or null - professional summary/objective",
            "skills": ["array of skill strings"],
            "technical_skills": {
                "Programming Languages": ["Python", "Java", etc.],
                "Frameworks": ["Django", "React", etc.],
                "Databases": ["MySQL", "MongoDB", etc.],
                "Tools": ["Git", "Docker", etc.],
                "Cloud": ["AWS", "Azure", etc.]
            },
            "experiences": [{
                "company": "string - required",
                "position": "string - required",
                "start_date": "string or null - YYYY-MM format preferred",
                "end_date": "string or null - YYYY-MM or 'Present'",
                "location": "string or null",
                "responsibilities": ["array of responsibility strings"],
                "achievements": ["array of achievement strings"]
            }],
            "education": [{
                "institution": "string - required",
                "degree": "string - required",
                "field_of_study": "string or null",
                "start_date": "string or null",
                "end_date": "string or null",
                "gpa": "string or null",
                "achievements": ["array of achievement strings - honors, awards, etc."]
            }],
            "projects": [{
                "name": "string - required",
                "description": "string or null",
                "technologies": ["array of technology strings"],
                "role": "string or null",
                "highlights": ["array of highlight strings"]
            }],
            "certifications": [{
                "name": "string - required",
                "issuer": "string or null",
                "date": "string or null",
                "credential_id": "string or null"
            }],
            "languages": ["array of language strings"],
            "achievements": ["array of achievement strings - include dates in the string if applicable"],
            "publications": ["array of publication strings"]
        }

        REMEMBER: All array fields must contain strings only, not objects. If you need to include dates or other metadata, incorporate them into the string itself.

        Extract information from the CV and return ONLY the JSON object.
        """
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from model response, handling various formats"""
        # Remove markdown code blocks if present
        cleaned = response_text.strip()
        
        # Remove ```json and ``` markers
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
        
        # Find JSON object
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            return json_match.group(0)
        
        return cleaned
    
    async def _extract_raw_text(self, file_content: bytes, file_path: str) -> str:
        """Extract raw text from CV for reference"""
        try:
            prompt = "Extract and return all text content from this document as plain text."
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": self._get_mime_type(file_path),
                                    "data": file_content
                                }
                            }
                        ]
                    }
                ]
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Failed to extract raw text: {str(e)}")
            return ""

    def _validate_and_structure(self, parsed_data: Dict[str, Any]) -> StructuredCV:
        """Validate and convert parsed data to StructuredCV model"""
        try:
            # Handle contact info
            contact_data = parsed_data.get('contact_info', {})
            if contact_data is None:
                contact_data = {}
            
            # Pre-process achievements to handle different formats
            achievements = parsed_data.get('achievements', [])
            processed_achievements = []
            
            for achievement in achievements:
                if isinstance(achievement, str):
                    processed_achievements.append(achievement)
                elif isinstance(achievement, dict):
                    # Extract achievement text and optionally append date
                    achievement_text = achievement.get('achievement', str(achievement))
                    date = achievement.get('date', '')
                    if date:
                        processed_achievements.append(f"{achievement_text} ({date})")
                    else:
                        processed_achievements.append(achievement_text)
                else:
                    processed_achievements.append(str(achievement))
            
            # Create structured CV with processed data
            structured_cv = StructuredCV(
                contact_info=ContactInfo(**contact_data),
                summary=parsed_data.get('summary'),
                skills=parsed_data.get('skills', []),
                technical_skills=parsed_data.get('technical_skills', {}),
                languages=parsed_data.get('languages', []),
                achievements=processed_achievements,  # Use processed achievements
                publications=parsed_data.get('publications', [])
            )
            
            # Process experiences with error handling
            for exp in parsed_data.get('experiences', []):
                if exp and isinstance(exp, dict):
                    try:
                        structured_cv.experiences.append(Experience(**exp))
                    except Exception as e:
                        logger.warning(f"Skipping invalid experience entry: {e}")
            
            # Process education with error handling
            for edu in parsed_data.get('education', []):
                if edu and isinstance(edu, dict):
                    try:
                        structured_cv.education.append(Education(**edu))
                    except Exception as e:
                        logger.warning(f"Skipping invalid education entry: {e}")
            
            # Process projects with error handling
            for proj in parsed_data.get('projects', []):
                if proj and isinstance(proj, dict):
                    try:
                        structured_cv.projects.append(Project(**proj))
                    except Exception as e:
                        logger.warning(f"Skipping invalid project entry: {e}")
            
            # Process certifications with error handling
            for cert in parsed_data.get('certifications', []):
                if cert and isinstance(cert, dict):
                    try:
                        structured_cv.certifications.append(Certification(**cert))
                    except Exception as e:
                        logger.warning(f"Skipping invalid certification entry: {e}")
            
            return structured_cv
            
        except Exception as e:
            logger.error(f"Error structuring CV data: {str(e)}")
            # Log the problematic data for debugging
            logger.debug(f"Parsed data: {json.dumps(parsed_data, indent=2)}")
            raise CVParsingError(f"Failed to structure CV data: {str(e)}")
    
    def normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        """Normalize date strings to YYYY-MM format"""
        if not date_str:
            return None
        
        # Common date patterns
        patterns = [
            (r'(\d{4})-(\d{1,2})', r'\1-\2'),  # YYYY-MM
            (r'(\d{1,2})/(\d{4})', r'\2-\1'),  # MM/YYYY
            (r'([A-Za-z]+)\s+(\d{4})', self._month_year_to_yyyy_mm),  # Month YYYY
            (r'(\d{4})', r'\1-01'),  # Just year
        ]
        
        for pattern, replacement in patterns:
            match = re.match(pattern, date_str.strip())
            if match:
                if callable(replacement):
                    return replacement(match)
                else:
                    return match.expand(replacement)
        
        return date_str  # Return as-is if no pattern matches
    
    def _month_year_to_yyyy_mm(self, match) -> str:
        """Convert 'Month YYYY' to 'YYYY-MM'"""
        months = {
            'january': '01', 'jan': '01',
            'february': '02', 'feb': '02',
            'march': '03', 'mar': '03',
            'april': '04', 'apr': '04',
            'may': '05',
            'june': '06', 'jun': '06',
            'july': '07', 'jul': '07',
            'august': '08', 'aug': '08',
            'september': '09', 'sep': '09', 'sept': '09',
            'october': '10', 'oct': '10',
            'november': '11', 'nov': '11',
            'december': '12', 'dec': '12'
        }
        
        month_str = match.group(1).lower()
        year = match.group(2)
        
        month_num = months.get(month_str, '01')
        return f"{year}-{month_num}"

# Singleton instance
_parser_instance = None

def get_cv_parser() -> GeminiCVParser:
    """Get or create singleton CV parser instance"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = GeminiCVParser()
    return _parser_instance

# Convenience function for direct usage
async def parse_cv(file_path: str) -> StructuredCV:
    """
    Parse a CV file and return structured data
    
    Args:
        file_path: Path to CV file
        
    Returns:
        StructuredCV object with extracted information
    """
    parser = get_cv_parser()
    return await parser.parse_cv_from_file(file_path)