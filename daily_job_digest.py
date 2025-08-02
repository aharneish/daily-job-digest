import requests
import smtplib
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
import os
import re
import json
import time
import shutil
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# LangChain and Groq imports
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate

load_dotenv()

# 🛠 CONFIG
SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "Machine Learning Engineer")
LOCATION = os.getenv("LOCATION", "India")
MAX_AGE_HOURS = 24
GMAIL_USER = os.getenv("GMAIL_USER", "YOUR_EMAIL")
GMAIL_PASS = os.getenv("GMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL", GMAIL_USER)
LINKEDIN_COOKIE = os.getenv("LINKEDIN_SESSION_COOKIE")

# 🤖 GROQ AI CONFIG
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
ENABLE_RESUME_CUSTOMIZATION = os.getenv("ENABLE_RESUME_CUSTOMIZATION", "false").lower() == "true"
RESUME_FOLDER = os.getenv("RESUME_FOLDER", "resume")
OUTPUT_RESUME_FOLDER = os.getenv("OUTPUT_RESUME_FOLDER", "customized_resumes")
MAX_RESUMES_TO_CUSTOMIZE = int(os.getenv("MAX_RESUMES_TO_CUSTOMIZE", "5"))

# 🌐 WEB SEARCH CONFIG
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
WEB_SEARCH_QUERIES = [
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:naukri.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:shine.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:monster.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:glassdoor.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:freshersworld.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:timesjobs.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:instahyre.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:weworkremotely.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:remotely.works",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} site:remotive.com",
    f"{SEARCH_KEYWORDS} jobs {LOCATION} remote",
    f'"{SEARCH_KEYWORDS}" jobs posted today {LOCATION}',
    f'"{SEARCH_KEYWORDS}" hiring {LOCATION} latest'
]
MAX_SEARCH_RESULTS_PER_QUERY = int(os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "20"))

# 🎯 ENHANCED FILTERING CONFIG
REQUIRED_SKILLS = os.getenv("REQUIRED_SKILLS", "").split(",") if os.getenv("REQUIRED_SKILLS") else []
PREFERRED_SKILLS = os.getenv("PREFERRED_SKILLS", "python,tensorflow,pytorch,scikit-learn,machine learning,deep learning,AI,artificial intelligence").split(",")
EXCLUDE_KEYWORDS = os.getenv("EXCLUDE_KEYWORDS", "intern,internship,junior,entry level").split(",") if os.getenv("EXCLUDE_KEYWORDS") else []
MIN_SKILL_MATCH_SCORE = int(os.getenv("MIN_SKILL_MATCH_SCORE", "1"))
TIME_RANGE_HOURS = int(os.getenv("TIME_RANGE_HOURS", str(MAX_AGE_HOURS)))

# 🆕 EXPERIENCE FILTERING CONFIG
MIN_EXPERIENCE_YEARS = int(os.getenv("MIN_EXPERIENCE_YEARS", "0"))
MAX_EXPERIENCE_YEARS = int(os.getenv("MAX_EXPERIENCE_YEARS", "20"))
EXCLUDE_EXPERIENCE_KEYWORDS = os.getenv("EXCLUDE_EXPERIENCE_KEYWORDS", "").split(",") if os.getenv("EXCLUDE_EXPERIENCE_KEYWORDS") else []
INCLUDE_UNKNOWN_EXPERIENCE = os.getenv("INCLUDE_UNKNOWN_EXPERIENCE", "true").lower() == "true"

@dataclass
class JobListing:
    """Enhanced job listing data structure with experience tracking"""
    source: str
    title: str
    company: str
    location: str
    posted: str
    link: str
    description: str = ""
    skills_found: List[str] = None
    skill_score: int = 0
    posting_time: Optional[datetime] = None
    search_query: str = ""  # Track which search found this job
    experience_required: str = ""  # Raw experience text
    experience_years_min: Optional[int] = None  # Minimum years required
    experience_years_max: Optional[int] = None  # Maximum years required
    experience_match_score: int = 0  # How well it matches experience criteria
    resume_customized: bool = False  # Whether resume was customized for this job
    customized_resume_path: str = ""  # Path to customized resume
    
    def __post_init__(self):
        if self.skills_found is None:
            self.skills_found = []

class ResumeCustomizer:
    """AI-powered resume customization using Groq API with improved formatting"""
    
    def __init__(self, groq_api_key: str, model: str = "llama-3.1-70b-versatile"):
        if not groq_api_key:
            raise ValueError("Groq API key is required for resume customization")
        
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name=model,
            temperature=0.2,  # Lower temperature for more consistent formatting
            max_tokens=6000   # Increased token limit
        )
        
        self.resume_customization_prompt = PromptTemplate(
            input_variables=["original_resume", "job_title", "company_name", "job_description", "required_skills"],
            template="""You are an expert resume writer and career consultant. Your task is to customize a resume for a specific job application while maintaining excellent formatting and readability.

ORIGINAL RESUME:
{original_resume}

JOB DETAILS:
- Job Title: {job_title}
- Company: {company_name}
- Required Skills: {required_skills}

JOB DESCRIPTION:
{job_description}

INSTRUCTIONS:
1. Analyze the job description and identify key requirements, skills, and qualifications
2. Customize the resume to better match the job requirements while keeping it truthful
3. Maintain or improve the original formatting structure (headings, sections, bullet points)
4. Use clear section headers (e.g., PROFESSIONAL SUMMARY, EXPERIENCE, SKILLS, EDUCATION)
5. Keep consistent formatting throughout (proper spacing, indentation, bullet points)
6. Prioritize relevant experience and skills that match the job
7. Adjust the professional summary/objective to align with the role
8. Use keywords from the job description naturally throughout the resume
9. Keep all information factual - do not add fake experience or skills
10. Ensure the output is clean, well-formatted, and easily readable

FORMATTING REQUIREMENTS:
- Use clear section headers in ALL CAPS or bold
- Maintain consistent spacing between sections
- Use bullet points (•) for lists and achievements
- Keep contact information at the top
- Use proper date formats (MM/YYYY or Month YYYY)
- Maintain professional formatting throughout

IMPORTANT GUIDELINES:
- Do NOT add any experience, skills, or qualifications that don't exist in the original resume
- Do NOT fabricate any information
- Only reorganize, reword, and emphasize existing content
- Maintain professional tone and clean formatting
- Keep the resume length similar to the original
- Ensure the output is immediately readable and well-formatted

OUTPUT FORMAT:
Please provide the customized resume with proper formatting, clear sections, and professional layout. The resume should be ready to save and use immediately without additional formatting needed."""
        )
        
        self.cover_letter_prompt = PromptTemplate(
            input_variables=["resume_content", "job_title", "company_name", "job_description"],
            template="""You are an expert cover letter writer. Create a compelling cover letter based on the resume and job details provided.

RESUME CONTENT:
{resume_content}

JOB DETAILS:
- Job Title: {job_title}
- Company: {company_name}

JOB DESCRIPTION:
{job_description}

INSTRUCTIONS:
1. Write a professional cover letter that complements the resume
2. Use proper business letter format with clear paragraph structure
3. Include proper spacing and formatting
4. Highlight the most relevant experience and skills for this specific role
5. Show enthusiasm for the company and position
6. Demonstrate understanding of the job requirements
7. Keep it concise (3-4 paragraphs)
8. Use a professional but engaging tone
9. Include a strong opening and closing

FORMAT:
- Include date and proper salutation
- Use clear paragraph breaks
- Professional closing
- Proper spacing throughout

Please write a well-formatted, compelling cover letter for this job application:"""
        )
    
    def customize_resume(self, original_resume: str, job: JobListing) -> str:
        """Customize resume for a specific job using Groq AI with improved formatting"""
        try:
            # Clean and prepare the original resume
            cleaned_resume = self._clean_resume_text(original_resume)
            
            # Prepare skills string
            required_skills = ", ".join(job.skills_found) if job.skills_found else "Not specified"
            
            # Limit job description length to avoid token limits
            job_description = job.description[:2500] if job.description else "No description available"
            
            # Create the prompt
            prompt = self.resume_customization_prompt.format(
                original_resume=cleaned_resume,
                job_title=job.title,
                company_name=job.company,
                job_description=job_description,
                required_skills=required_skills
            )
            
            # Generate customized resume
            messages = [
                SystemMessage(content="You are an expert resume writer focused on creating well-formatted, targeted, and truthful resume customizations. Always maintain professional formatting and readability."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm(messages)
            customized_resume = response.content
            
            # Post-process to ensure good formatting
            formatted_resume = self._post_process_resume(customized_resume)
            
            return formatted_resume
            
        except Exception as e:
            print(f"❌ Error customizing resume: {e}")
            return original_resume  # Return original if customization fails
    
    def _clean_resume_text(self, resume_text: str) -> str:
        """Clean and prepare resume text for processing"""
        # Remove excessive whitespace while preserving structure
        lines = resume_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:  # Keep non-empty lines
                cleaned_lines.append(cleaned_line)
            elif cleaned_lines and cleaned_lines[-1]:  # Add single empty line for spacing
                cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines)
    
    def _post_process_resume(self, resume_text: str) -> str:
        """Post-process resume to ensure good formatting"""
        lines = resume_text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Clean up the line
            cleaned_line = line.strip()
            
            # Skip completely empty lines at the beginning
            if not processed_lines and not cleaned_line:
                continue
                
            # Add proper spacing for section headers (all caps or containing key terms)
            if cleaned_line and (
                cleaned_line.isupper() or 
                any(header in cleaned_line.upper() for header in 
                    ['EXPERIENCE', 'EDUCATION', 'SKILLS', 'SUMMARY', 'OBJECTIVE', 'PROJECTS', 'CERTIFICATIONS'])
            ):
                # Add space before section headers (except for the first one)
                if processed_lines and processed_lines[-1]:
                    processed_lines.append('')
                processed_lines.append(cleaned_line)
                continue
            
            # Add the line
            if cleaned_line:
                processed_lines.append(cleaned_line)
            else:
                # Only add empty line if the previous line wasn't empty
                if processed_lines and processed_lines[-1]:
                    processed_lines.append('')
        
        # Join and clean up multiple consecutive empty lines
        result = '\n'.join(processed_lines)
        
        # Replace multiple consecutive newlines with max 2
        import re
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result
    
    def _convert_to_markdown(self, content: str) -> str:
        """Convert plain text resume to markdown for better formatting"""
        lines = content.split('\n')
        markdown_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                markdown_lines.append('')
                continue
            
            # Convert section headers to markdown headers
            if (stripped.isupper() and len(stripped) > 3) or any(
                header in stripped.upper() for header in 
                ['PROFESSIONAL SUMMARY', 'EXPERIENCE', 'EDUCATION', 'SKILLS', 
                 'PROJECTS', 'CERTIFICATIONS', 'OBJECTIVE', 'SUMMARY']
            ):
                markdown_lines.append(f"## {stripped}")
                markdown_lines.append('')
            # Convert job titles and company names (lines with | or @)
            elif '|' in stripped or '@' in stripped or any(
                keyword in stripped.lower() for keyword in ['engineer', 'developer', 'analyst', 'manager', 'specialist']
            ):
                markdown_lines.append(f"### {stripped}")
            # Convert bullet points
            elif stripped.startswith('•') or stripped.startswith('-') or stripped.startswith('*'):
                markdown_lines.append(f"- {stripped[1:].strip()}")
            # Regular lines
            else:
                markdown_lines.append(stripped)
        
        # Add title and metadata
        title = "# AI-Customized Resume\n\n"
        timestamp = f"*Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n\n"
        
        result = title + timestamp + '\n'.join(markdown_lines)
        return result.strip() + '\n'
    
    def create_pdf_resume(self, content: str, job_folder: Path, base_filename: str) -> Optional[Path]:
        """Create a PDF version of the customized resume (optional)"""
        try:
            # Try to create PDF using reportlab if available
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                
                pdf_filename = f"{Path(base_filename).stem}_customized.pdf"
                pdf_path = job_folder / pdf_filename
                
                # Create PDF document
                doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
                styles = getSampleStyleSheet()
                story = []
                
                # Custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    spaceAfter=12,
                    textColor='black'
                )
                
                header_style = ParagraphStyle(
                    'CustomHeader',
                    parent=styles['Heading2'],
                    fontSize=14,
                    spaceAfter=8,
                    textColor='black'
                )
                
                normal_style = ParagraphStyle(
                    'CustomNormal',
                    parent=styles['Normal'],
                    fontSize=11,
                    spaceAfter=6
                )
                
                # Process content
                lines = content.split('\n')
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        story.append(Spacer(1, 6))
                        continue
                    
                    # Determine style based on content
                    if stripped.isupper() and len(stripped) > 3:
                        story.append(Paragraph(stripped, header_style))
                    elif any(header in stripped.upper() for header in 
                           ['EXPERIENCE', 'EDUCATION', 'SKILLS', 'SUMMARY']):
                        story.append(Paragraph(stripped, header_style))
                    else:
                        # Escape HTML characters
                        escaped = stripped.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        story.append(Paragraph(escaped, normal_style))
                
                # Build PDF
                doc.build(story)
                print(f"✅ PDF version created: {pdf_path}")
                return pdf_path
                
            except ImportError:
                print("⚠️ reportlab not installed. Cannot create PDF. Install with: pip install reportlab")
                return None
                
        except Exception as e:
            print(f"⚠️ Could not create PDF version: {e}")
            return None.strip()
    
    def generate_cover_letter(self, resume_content: str, job: JobListing) -> str:
        """Generate a well-formatted cover letter for the job application"""
        try:
            # Limit content length to avoid token issues
            limited_resume = resume_content[:1500] if resume_content else ""
            limited_description = job.description[:1500] if job.description else ""
            
            prompt = self.cover_letter_prompt.format(
                resume_content=limited_resume,
                job_title=job.title,
                company_name=job.company,
                job_description=limited_description
            )
            
            messages = [
                SystemMessage(content="You are an expert cover letter writer who creates compelling, well-formatted, personalized cover letters with proper business formatting."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm(messages)
            cover_letter = response.content
            
            # Post-process cover letter for better formatting
            formatted_cover_letter = self._format_cover_letter(cover_letter)
            
            return formatted_cover_letter
            
        except Exception as e:
            print(f"❌ Error generating cover letter: {e}")
            return ""
    
    def _format_cover_letter(self, cover_letter_text: str) -> str:
        """Format cover letter for better readability"""
        from datetime import datetime
        
        # Add date if not present
        if not any(datetime.now().strftime("%Y") in line for line in cover_letter_text.split('\n')[:5]):
            current_date = datetime.now().strftime("%B %d, %Y")
            cover_letter_text = f"{current_date}\n\n{cover_letter_text}"
        
        # Clean up formatting
        lines = cover_letter_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:
                formatted_lines.append(cleaned_line)
            else:
                # Add single empty line for paragraph breaks
                if formatted_lines and formatted_lines[-1]:
                    formatted_lines.append('')
        
        result = '\n'.join(formatted_lines)
        
        # Clean up multiple consecutive newlines
        import re
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()


class ResumeManager:
    """Enhanced Resume Manager with better file handling and formatting"""
    
    def __init__(self, resume_folder: str, output_folder: str):
        self.resume_folder = Path(resume_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
        
        # Initialize Groq customizer if enabled
        if ENABLE_RESUME_CUSTOMIZATION and GROQ_API_KEY:
            self.customizer = ResumeCustomizer(GROQ_API_KEY, GROQ_MODEL)
        else:
            self.customizer = None
    
    def save_customized_resume(self, content: str, job_folder: Path, original_filename: str) -> Path:
        """Save customized resume with better formatting and encoding"""
        # Create customized filename
        name_without_ext = Path(original_filename).stem
        original_extension = Path(original_filename).suffix.lower()
        
        # Always save AI-generated content as .txt for maximum compatibility
        # Even if original was .pdf, .docx, etc., AI generates text content
        customized_filename = f"{name_without_ext}_customized.txt"
        customized_path = job_folder / customized_filename
        
        try:
            # Ensure content is properly formatted
            formatted_content = self._ensure_proper_formatting(content)
            
            # Save with UTF-8 encoding and proper line endings
            with open(customized_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(formatted_content)
            
            print(f"✅ Customized resume saved as text: {customized_path}")
            
            # Also create a markdown version for better formatting
            markdown_filename = f"{name_without_ext}_customized.md"
            markdown_path = job_folder / markdown_filename
            
            try:
                markdown_content = self._convert_to_markdown(formatted_content)
                with open(markdown_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(markdown_content)
                print(f"✅ Markdown version saved: {markdown_path}")
            except Exception as e:
                print(f"⚠️ Could not save markdown version: {e}")
            
            return customized_path
            
        except Exception as e:
            print(f"❌ Error saving customized resume: {e}")
            return None
    
    def _ensure_proper_formatting(self, content: str) -> str:
        """Ensure the content has proper formatting for readability"""
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Add a header comment for clarity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"# AI-Customized Resume - Generated on {timestamp}\n# This resume has been tailored for the specific job application\n\n"
        
        # Don't add header if content already looks like it has one
        if not content.strip().startswith('#') and not content.strip().startswith('RESUME') and not any(
            line.strip().upper().startswith(('NAME:', 'EMAIL:', 'PHONE:')) 
            for line in content.split('\n')[:5]
        ):
            content = header + content
        
        # Ensure proper spacing and formatting
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # Keep the line as is, but ensure consistent formatting
            if line.strip():
                formatted_lines.append(line)
            else:
                # Only add empty line if previous line wasn't empty
                if formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append('')
        
        # Join lines and clean up excessive whitespace
        result = '\n'.join(formatted_lines)
        
        # Ensure the file ends with a single newline
        result = result.rstrip() + '\n'
        
        return result
    
    def save_cover_letter(self, content: str, job_folder: Path) -> Path:
        """Save cover letter with proper formatting"""
        cover_letter_path = job_folder / "cover_letter.txt"
        
        try:
            # Add header for clarity
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f"# AI-Generated Cover Letter - Created on {timestamp}\n# This cover letter has been tailored for the specific job application\n\n"
            
            formatted_content = header + content.strip() + '\n'
            
            with open(cover_letter_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(formatted_content)
            
            print(f"✅ Cover letter saved: {cover_letter_path}")
            return cover_letter_path
            
        except Exception as e:
            print(f"❌ Error saving cover letter: {e}")
            return None
    
    def read_resume_content(self, file_path: Path) -> str:
        """Read resume content with better error handling and encoding detection"""
        try:
            # Try UTF-8 first
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Fallback to other encodings
                try:
                    with open(file_path, 'r', encoding='latin1') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_path, 'r', encoding='cp1252') as f:
                        content = f.read()
            
            if file_path.suffix.lower() == '.txt' or file_path.suffix.lower() == '.md':
                return content
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                try:
                    import docx
                    doc = docx.Document(file_path)
                    paragraphs = []
                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            paragraphs.append(paragraph.text)
                    return '\n'.join(paragraphs)
                except ImportError:
                    print("⚠️ python-docx not installed. Cannot read .docx files. Install with: pip install python-docx")
                    return ""
            elif file_path.suffix.lower() == '.pdf':
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text_parts = []
                        for page in reader.pages:
                            text_parts.append(page.extract_text())
                        return '\n'.join(text_parts)
                except ImportError:
                    print("⚠️ PyPDF2 not installed. Cannot read .pdf files. Install with: pip install PyPDF2")
                    return ""
            else:
                print(f"⚠️ Unsupported file format: {file_path.suffix}")
                return ""
                
        except Exception as e:
            print(f"❌ Error reading resume file {file_path}: {e}")
            return ""
    
    def create_job_folder(self, job: JobListing) -> Path:
        """Create a well-organized folder for the job application"""
        # Clean job title and company name for folder name
        job_title_clean = re.sub(r'[<>:"/\\|?*]', '-', job.title)[:50].strip('-')
        company_clean = re.sub(r'[<>:"/\\|?*]', '-', job.company)[:30].strip('-')
        
        # Create timestamp for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        folder_name = f"{timestamp}_{job_title_clean}_{company_clean}".strip('_')
        job_folder = self.output_folder / folder_name
        
        # Create unique folder if it already exists
        counter = 1
        original_folder = job_folder
        while job_folder.exists():
            job_folder = Path(f"{original_folder}_{counter:02d}")
            counter += 1
        
        job_folder.mkdir(exist_ok=True)
        print(f"📁 Created job folder: {job_folder}")
        return job_folder
    
    def get_original_resume_files(self) -> List[Path]:
        """Get all resume files from the resume folder"""
        if not self.resume_folder.exists():
            print(f"⚠️ Resume folder '{self.resume_folder}' not found")
            return []
        
        # Support common resume file formats
        extensions = ['.txt', '.md', '.docx', '.pdf', '.doc']
        resume_files = []
        
        for ext in extensions:
            resume_files.extend(self.resume_folder.glob(f'*{ext}'))
        
        return resume_files
    
    def save_job_info(self, job: JobListing, job_folder: Path):
        """Save job information to the folder"""
        job_info = {
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "posted": job.posted,
            "link": job.link,
            "source": job.source,
            "skills_found": job.skills_found,
            "skill_score": job.skill_score,
            "experience_required": job.experience_required,
            "experience_match_score": job.experience_match_score,
            "description": job.description
        }
        
        job_info_path = job_folder / "job_info.json"
        
        try:
            with open(job_info_path, 'w', encoding='utf-8') as f:
                json.dump(job_info, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Error saving job info: {e}")
    
    def customize_resumes_for_jobs(self, jobs: List[JobListing], max_jobs: int = 5) -> List[JobListing]:
        """Customize resumes for top matching jobs with improved formatting"""
        if not self.customizer:
            print("⚠️ Resume customization disabled or Groq API key not provided")
            return jobs
        
        resume_files = self.get_original_resume_files()
        if not resume_files:
            print("⚠️ No resume files found for customization")
            return jobs
        
        # Use the first resume file found
        original_resume_path = resume_files[0]
        print(f"📄 Using resume file: {original_resume_path.name}")
        
        original_resume_content = self.read_resume_content(original_resume_path)
        if not original_resume_content:
            print("❌ Could not read resume content")
            return jobs
        
        print(f"📄 Original resume length: {len(original_resume_content)} characters")
        
        # Customize resumes for top jobs
        customized_jobs = []
        successful_customizations = 0
        
        for i, job in enumerate(jobs[:max_jobs]):
            print(f"\n🤖 Customizing resume for: {job.title} at {job.company} ({i+1}/{max_jobs})")
            
            try:
                # Create job folder with better organization
                job_folder = self.create_job_folder(job)
                
                # Customize resume using improved AI
                print("   🔄 Generating customized resume...")
                customized_resume = self.customizer.customize_resume(original_resume_content, job)
                
                if not customized_resume or len(customized_resume.strip()) < 100:
                    print("   ⚠️ Generated resume seems too short, using original")
                    customized_resume = original_resume_content
                
                # Save customized resume with better formatting
                customized_resume_path = self.save_customized_resume(
                    customized_resume, job_folder, original_resume_path.name
                )
                
                if customized_resume_path:
                    print(f"   ✅ Resume customized: {len(customized_resume)} characters")
                    
                    # Optionally create PDF version if reportlab is available
                    try:
                        pdf_path = self.create_pdf_resume(customized_resume, job_folder, original_resume_path.name)
                        if pdf_path:
                            print(f"   📄 PDF version created: {pdf_path.name}")
                    except Exception as e:
                        print(f"   ⚠️ PDF creation skipped: {e}")
                    
                    # Generate and save cover letter
                    print("   🔄 Generating cover letter...")
                    cover_letter = self.customizer.generate_cover_letter(customized_resume, job)
                    if cover_letter:
                        self.save_cover_letter(cover_letter, job_folder)
                        print("   ✅ Cover letter generated")
                    else:
                        print("   ⚠️ Cover letter generation failed")
                    
                    # Copy original resume for reference
                    original_copy_path = job_folder / f"original_{original_resume_path.name}"
                    try:
                        import shutil
                        shutil.copy2(original_resume_path, original_copy_path)
                        print("   📋 Original resume copied for reference")
                    except Exception as e:
                        print(f"   ⚠️ Could not copy original resume: {e}")
                    
                    # Save job information
                    self.save_job_info(job, job_folder)
                    
                    # Update job with customization info
                    job.resume_customized = True
                    job.customized_resume_path = str(customized_resume_path)
                    successful_customizations += 1
                    
                    print(f"   🎉 Complete! Files saved to: {job_folder.name}")
                    
                else:
                    print("   ❌ Failed to save customized resume")
                    job.resume_customized = False
                    job.customized_resume_path = ""
                
                # Rate limiting for API calls
                print("   ⏱️ Waiting 3 seconds before next customization...")
                time.sleep(3)
                
            except Exception as e:
                print(f"   ❌ Error customizing resume for {job.company}: {e}")
                job.resume_customized = False
                job.customized_resume_path = ""
                continue
            
            customized_jobs.append(job)
        
        # Add remaining jobs without customization
        for job in jobs[max_jobs:]:
            job.resume_customized = False
            job.customized_resume_path = ""
            customized_jobs.append(job)
        
        print(f"\n🎉 Resume customization completed!")
        print(f"   📊 Successfully customized: {successful_customizations}/{min(len(jobs), max_jobs)} resumes")
        if successful_customizations > 0:
            print(f"   📁 All customized resumes saved in: {self.output_folder}")
        
        return customized_jobs# ... (keeping all the existing code for brevity)

def fetch_job_description(job_url: str) -> str:
    """Fetch detailed job description from job URL"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(job_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "lxml")
        
        # Try to find job description in common selectors
        description_selectors = [
            "div.jobsearch-jobDescriptionText",
            "div[data-testid='job-description']",
            ".job-description",
            "#jobDescriptionText",
            ".description"
        ]
        
        for selector in description_selectors:
            desc_element = soup.select_one(selector)
            if desc_element:
                return desc_element.get_text(strip=True)
                
        return ""
    except Exception as e:
        print(f"⚠️ Could not fetch description for {job_url}: {e}")
        return ""

class ExperienceParser:
    """Class to parse and analyze experience requirements from job text"""
    
    def __init__(self):
        # Common experience patterns
        self.experience_patterns = [
            # "2-5 years", "3-7 years", "5-10 years"
            r'(\d+)[-–]\s*(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)',
            # "2+ years", "5+ years", "3+ years experience"
            r'(\d+)\+\s*years?\s*(?:of\s*)?(?:experience|exp)',
            # "minimum 3 years", "min 5 years", "at least 2 years"
            r'(?:minimum|min|at\s*least)\s*(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)',
            # "3 years experience", "5 years of experience"
            r'(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)',
            # "2 to 5 years", "3 to 7 years"
            r'(\d+)\s*to\s*(\d+)\s*years?\s*(?:of\s*)?(?:experience|exp)',
            # Experience levels
            r'(entry\s*level|junior|fresher|graduate)',
            r'(mid\s*level|intermediate|senior|lead|principal)',
        ]
        
        # Experience level mappings
        self.level_mappings = {
            'fresher': (0, 1),
            'graduate': (0, 2),
            'entry level': (0, 2),
            'junior': (0, 3),
            'mid level': (2, 8),
            'intermediate': (3, 8),
            'senior': (5, 15),
            'lead': (7, 20),
            'principal': (8, 20),
        }
    
    def parse_experience_requirements(self, job_text: str) -> Tuple[str, Optional[int], Optional[int]]:
        """
        Parse experience requirements from job text.
        Returns: (raw_text, min_years, max_years)
        """
        job_text_lower = job_text.lower()
        
        # Look for explicit year ranges first
        for pattern in self.experience_patterns[:5]:  # Numeric patterns
            matches = re.findall(pattern, job_text_lower, re.IGNORECASE)
            if matches:
                match = matches[0]
                if isinstance(match, tuple) and len(match) == 2:
                    try:
                        min_years = int(match[0])
                        max_years = int(match[1])
                        raw_text = f"{min_years}-{max_years} years"
                        return raw_text, min_years, max_years
                    except ValueError:
                        continue
                elif isinstance(match, str) and match.isdigit():
                    try:
                        years = int(match)
                        raw_text = f"{years}+ years"
                        return raw_text, years, None
                    except ValueError:
                        continue
        
        # Look for experience levels
        for level, (min_years, max_years) in self.level_mappings.items():
            if level in job_text_lower:
                return level.title(), min_years, max_years
        
        # Check for specific patterns that indicate no experience required
        no_exp_indicators = ['no experience', 'fresher', '0 years', 'entry level']
        for indicator in no_exp_indicators:
            if indicator in job_text_lower:
                return indicator.title(), 0, 2
        
        return "", None, None
    
    def calculate_experience_match_score(self, job_min: Optional[int], job_max: Optional[int], 
                                       filter_min: int, filter_max: int) -> int:
        """
        Calculate how well the job experience requirements match the filter criteria.
        Returns score from 0-10 (10 being perfect match)
        """
        # If job requirements are unknown, return neutral score
        if job_min is None and job_max is None:
            return 5 if INCLUDE_UNKNOWN_EXPERIENCE else 0
        
        # Convert job requirements to range
        if job_min is None:
            job_min = 0
        if job_max is None:
            job_max = job_min + 5  # Assume 5-year range if not specified
        
        # Check for overlap between job requirements and filter range
        overlap_start = max(job_min, filter_min)
        overlap_end = min(job_max, filter_max)
        
        if overlap_start <= overlap_end:
            # Calculate overlap percentage
            job_range = job_max - job_min + 1
            filter_range = filter_max - filter_min + 1
            overlap_range = overlap_end - overlap_start + 1
            
            # Score based on overlap quality
            overlap_ratio = overlap_range / min(job_range, filter_range)
            return int(overlap_ratio * 10)
        else:
            # No overlap
            # Check if we're close (within 2 years)
            distance = min(abs(job_min - filter_max), abs(filter_min - job_max))
            if distance <= 2:
                return 3  # Close but not matching
            else:
                return 0  # No match

class WebSearchScraper:
    """Web search-based job scraper for multiple job portals"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.processed_urls: Set[str] = set()
        self.experience_parser = ExperienceParser()
        
    def search_jobs_via_web(self, queries: List[str]) -> List[JobListing]:
        """Search for jobs using web search and scrape results"""
        all_jobs = []
        
        for query in queries:
            print(f"🔍 Searching: {query}")
            try:
                search_results = self._perform_web_search(query)
                jobs_from_query = self._extract_jobs_from_search_results(search_results, query)
                all_jobs.extend(jobs_from_query)
                time.sleep(2)  # Rate limiting
            except Exception as e:
                print(f"⚠️ Error searching '{query}': {e}")
                continue
                
        # Remove duplicates based on URL
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job.link not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job.link)
                
        print(f"✅ Found {len(unique_jobs)} unique jobs from web search")
        return unique_jobs
    
    def _perform_web_search(self, query: str) -> List[Dict]:
        """Perform web search using DuckDuckGo (free alternative)"""
        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        
        try:
            response = self.session.get(search_url, timeout=15)
            soup = BeautifulSoup(response.text, 'lxml')
            
            results = []
            for result in soup.select('.result'):
                title_elem = result.select_one('.result__title a')
                snippet_elem = result.select_one('.result__snippet')
                
                if title_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'snippet': snippet_elem.get_text(strip=True) if snippet_elem else ''
                    })
                    
                if len(results) >= MAX_SEARCH_RESULTS_PER_QUERY:
                    break
                    
            return results
            
        except Exception as e:
            print(f"⚠️ Web search failed: {e}")
            return []
    
    def _extract_jobs_from_search_results(self, search_results: List[Dict], query: str) -> List[JobListing]:
        """Extract job listings from search results"""
        jobs = []
        
        for result in search_results:
            url = result['url']
            title = result['title']
            snippet = result['snippet']
            
            # Skip if already processed
            if url in self.processed_urls:
                continue
                
            # Filter for job-related results
            if not self._is_job_related(title, snippet):
                continue
                
            try:
                job = self._scrape_job_details(url, title, snippet, query)
                if job:
                    jobs.append(job)
                    self.processed_urls.add(url)
                    time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"⚠️ Error scraping {url}: {e}")
                continue
                
        return jobs
    
    def _is_job_related(self, title: str, snippet: str) -> bool:
        """Check if search result is job-related"""
        job_indicators = [
            'job', 'career', 'hiring', 'vacancy', 'position', 'opening',
            'recruitment', 'apply', 'opportunity', 'employment'
        ]
        
        text = f"{title} {snippet}".lower()
        return any(indicator in text for indicator in job_indicators)
    
    def _scrape_job_details(self, url: str, title: str, snippet: str, query: str) -> Optional[JobListing]:
        """Scrape detailed job information from job posting URL"""
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract job details based on common patterns
            job_title = self._extract_job_title(soup, title)
            company = self._extract_company(soup)
            location = self._extract_location(soup)
            posted_date = self._extract_posted_date(soup)
            description = self._extract_description(soup)
            
            # Extract experience requirements
            full_text = f"{job_title} {description} {snippet}"
            exp_text, exp_min, exp_max = self.experience_parser.parse_experience_requirements(full_text)
            
            # Determine source from URL
            source = self._get_source_from_url(url)
            
            return JobListing(
                source=source,
                title=job_title,
                company=company,
                location=location,
                posted=posted_date,
                link=url,
                description=description,
                search_query=query,
                experience_required=exp_text,
                experience_years_min=exp_min,
                experience_years_max=exp_max
            )
            
        except Exception as e:
            print(f"⚠️ Could not scrape {url}: {e}")
            return None
    
    def _extract_job_title(self, soup: BeautifulSoup, fallback_title: str) -> str:
        """Extract job title from various job portal patterns"""
        selectors = [
            'h1.job-title', 'h1[data-testid="job-title"]', '.job-header h1',
            'h1.jobTitle', '.jobtitle h1', 'h1.title', '.job-title',
            'h1', 'title'  # Fallback selectors
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem and elem.get_text(strip=True):
                return elem.get_text(strip=True)
                
        return fallback_title
    
    def _extract_company(self, soup: BeautifulSoup) -> str:
        """Extract company name from various patterns"""
        selectors = [
            '.company-name', '.companyName', '[data-testid="company-name"]',
            '.employer', '.company', '.hiring-company', '.job-company',
            'span.company', 'div.company'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem and elem.get_text(strip=True):
                return elem.get_text(strip=True)
                
        return "Unknown Company"
    
    def _extract_location(self, soup: BeautifulSoup) -> str:
        """Extract job location from various patterns"""
        selectors = [
            '.location', '.job-location', '[data-testid="location"]',
            '.companyLocation', '.work-location', '.job-loc'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem and elem.get_text(strip=True):
                return elem.get_text(strip=True)
                
        return LOCATION  # Fallback to search location
    
    def _extract_posted_date(self, soup: BeautifulSoup) -> str:
        """Extract posting date from various patterns"""
        selectors = [
            '.posted-date', '.job-posted', '[data-testid="posted-date"]',
            '.date-posted', 'time', '.posting-date', '.job-date'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem and elem.get_text(strip=True):
                return elem.get_text(strip=True)
                
        return "Recently"  # Fallback
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract job description from various patterns"""
        selectors = [
            '.job-description', '[data-testid="job-description"]',
            '.jobDescription', '.description', '.job-details',
            '.job-content', '.posting-details'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
                
        # Fallback: get main content
        main_content = soup.select_one('main') or soup.select_one('body')
        if main_content:
            return main_content.get_text(strip=True)[:2000]  # Limit length
            
        return ""
    
    def _get_source_from_url(self, url: str) -> str:
        """Determine job portal source from URL"""
        domain = urlparse(url).netloc.lower()
        
        source_mapping = {
            'naukri.com': 'Naukri',
            'shine.com': 'Shine',
            'monster.com': 'Monster',
            'glassdoor.com': 'Glassdoor',
            'freshersworld.com': 'FreshersWorld',
            'timesjobs.com': 'TimesJobs',
            'instahyre.com': 'Instahyre',
            'linkedin.com': 'LinkedIn',
            'indeed.com': 'Indeed',
            'weworkremotely.com': 'weworkremotely',
            'remotely.works':'remotely.works',
            'remotive.com':'remotive',
        }
        
        for key, value in source_mapping.items():
            if key in domain:
                return value
                
        return f"Web ({domain})"

class JobFilter:
    """Enhanced job filtering class with experience filtering"""
    
    def __init__(self, 
                 required_skills: List[str] = None,
                 preferred_skills: List[str] = None,
                 exclude_keywords: List[str] = None,
                 time_range_hours: int = 24,
                 min_skill_score: int = 1,
                 min_experience_years: int = 0,
                 max_experience_years: int = 20,
                 exclude_experience_keywords: List[str] = None,
                 include_unknown_experience: bool = True):
        
        self.required_skills = [skill.strip().lower() for skill in (required_skills or []) if skill.strip()]
        self.preferred_skills = [skill.strip().lower() for skill in (preferred_skills or []) if skill.strip()]
        self.exclude_keywords = [kw.strip().lower() for kw in (exclude_keywords or []) if kw.strip()]
        self.time_range_hours = time_range_hours
        self.min_skill_score = min_skill_score
        self.cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        # Experience filtering
        self.min_experience_years = min_experience_years
        self.max_experience_years = max_experience_years
        self.exclude_experience_keywords = [kw.strip().lower() for kw in (exclude_experience_keywords or []) if kw.strip()]
        self.include_unknown_experience = include_unknown_experience
        self.experience_parser = ExperienceParser()
        
    def parse_posting_time(self, posted_text: str) -> Optional[datetime]:
        """Parse posting time from various formats"""
        posted_lower = posted_text.lower().strip()
        now = datetime.now()
        
        try:
            # Handle "just posted", "1 hour ago", "2 days ago", etc.
            if "just" in posted_lower or "now" in posted_lower:
                return now
            elif "hour" in posted_lower:
                hours_match = re.search(r'(\d+)\s*hour', posted_lower)
                if hours_match:
                    hours = int(hours_match.group(1))
                    return now - timedelta(hours=hours)
            elif "day" in posted_lower:
                days_match = re.search(r'(\d+)\s*day', posted_lower)
                if days_match:
                    days = int(days_match.group(1))
                    return now - timedelta(days=days)
            elif "week" in posted_lower:
                weeks_match = re.search(r'(\d+)\s*week', posted_lower)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    return now - timedelta(weeks=weeks)
            elif "month" in posted_lower:
                months_match = re.search(r'(\d+)\s*month', posted_lower)
                if months_match:
                    months = int(months_match.group(1))
                    return now - timedelta(days=months * 30)
        except:
            pass
            
        return now  # Default to now if parsing fails
    
    def extract_skills(self, job: JobListing) -> tuple[List[str], int]:
        """Extract and score skills from job content"""
        job_text = f"{job.title} {job.description}".lower()
        found_skills = []
        skill_score = 0
        
        # Check preferred skills
        for skill in self.preferred_skills:
            if skill in job_text:
                found_skills.append(skill)
                skill_score += 1
                
        return found_skills, skill_score
    
    def check_experience_requirements(self, job: JobListing) -> bool:
        """Check if job meets experience requirements"""
        # If no experience requirements are parsed, check if we should include unknown
        if job.experience_years_min is None and job.experience_years_max is None:
            return self.include_unknown_experience
        
        # Check for excluded experience keywords
        job_text = f"{job.title} {job.description} {job.experience_required}".lower()
        for exclude_keyword in self.exclude_experience_keywords:
            if exclude_keyword in job_text:
                print(f"❌ Job filtered out: Contains excluded experience keyword '{exclude_keyword}'")
                return False
        
        # Calculate experience match score
        job.experience_match_score = self.experience_parser.calculate_experience_match_score(
            job.experience_years_min, job.experience_years_max,
            self.min_experience_years, self.max_experience_years
        )
        
        # Accept jobs with score > 0 (some overlap) or unknown experience if allowed
        return job.experience_match_score > 0 or (
            job.experience_years_min is None and job.experience_years_max is None and self.include_unknown_experience
        )
    
    def matches_requirements(self, job: JobListing) -> bool:
        """Check if job matches all filter requirements"""
        job_text = f"{job.title or ''} {job.description or ''}".lower()
        job_title = (job.title or '').lower()

        # Required skills check (skipped if empty)
        
        # Experience requirements check
        if not self.check_experience_requirements(job):
            print(f"❌ Job filtered out: Experience requirements don't match")
            return False

        # Preferred skill score
        skill_score = sum(skill in job_text for skill in self.preferred_skills)

        if skill_score < self.min_skill_score:
            print(f"❌ Job filtered out: Skill score {skill_score} < Min {self.min_skill_score}")
            passes_filter = False
        else:
            passes_filter = True

        # Fallback on job title match
        if not passes_filter and any(keyword in job_title for keyword in ["ml", "machine learning", "ai"]):
            print("🔁 Fallback: Title matches basic ML/AI pattern, forcing pass")
            passes_filter = True

        return passes_filter
    
    def filter_and_score_jobs(self, jobs: List[JobListing]) -> List[JobListing]:
        """Filter jobs and add skill scoring with experience analysis"""
        filtered_jobs = []
        
        for job in jobs:
            # Parse posting time
            job.posting_time = self.parse_posting_time(job.posted)
            
            # Extract skills and calculate score
            job.skills_found, job.skill_score = self.extract_skills(job)
            
            # Parse experience if not already done
            if not job.experience_required and not job.experience_years_min:
                full_text = f"{job.title} {job.description}"
                job.experience_required, job.experience_years_min, job.experience_years_max = \
                    self.experience_parser.parse_experience_requirements(full_text)
            
            # Check if job matches requirements
            if self.matches_requirements(job):
                filtered_jobs.append(job)
        
        # Sort by experience match score, then skill score, then posting time
        filtered_jobs.sort(key=lambda x: (
            -x.experience_match_score,
            -x.skill_score, 
            x.posting_time or datetime.min
        ), reverse=False)
        
        return filtered_jobs

def fetch_web_search_jobs():
    """Fetch jobs using web search across multiple job portals"""
    print("🌐 Starting web search for jobs...")
    
    if not ENABLE_WEB_SEARCH:
        print("⚠️ Web search disabled in config")
        return []
    
    scraper = WebSearchScraper()
    jobs = scraper.search_jobs_via_web(WEB_SEARCH_QUERIES)
    
    print(f"✅ Found {len(jobs)} jobs from web search")
    return jobs

def fetch_indeed_jobs():
    print("🔍 Scraping Indeed...")
    url = f"https://in.indeed.com/jobs?q={SEARCH_KEYWORDS}&l={LOCATION}&sort=date"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        jobs = []
        experience_parser = ExperienceParser()

        for card in soup.select("div.job_seen_beacon"):
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span.companyName")
            location_el = card.select_one("div.companyLocation")
            date_el = card.select_one("span.date")
            link_el = card.select_one("a")

            if not all([title_el, company_el, location_el, date_el, link_el]):
                continue

            job_url = f"https://in.indeed.com{link_el['href']}"
            description = fetch_job_description(job_url)
            
            # Parse experience requirements
            full_text = f"{title_el.text.strip()} {description}"
            exp_text, exp_min, exp_max = experience_parser.parse_experience_requirements(full_text)

            job = JobListing(
                source="Indeed",
                title=title_el.text.strip(),
                company=company_el.text.strip(),
                location=location_el.text.strip(),
                posted=date_el.text.strip(),
                link=job_url,
                description=description,
                experience_required=exp_text,
                experience_years_min=exp_min,
                experience_years_max=exp_max
            )
            jobs.append(job)
            
        print(f"✅ Found {len(jobs)} jobs from Indeed")
        return jobs
        
    except Exception as e:
        print(f"❌ Error scraping Indeed: {e}")
        return []

def fetch_linkedin_jobs():
    print("🔍 Scraping LinkedIn...")
    
    if not LINKEDIN_COOKIE:
        print("⚠️ LinkedIn cookie not provided, skipping LinkedIn scraping")
        return []
    
    url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={SEARCH_KEYWORDS}&location={LOCATION}&f_TPR=r{TIME_RANGE_HOURS}h&sortBy=DD"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": f"li_at={LINKEDIN_COOKIE}"
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        jobs = []
        experience_parser = ExperienceParser()

        for job in soup.select("li"):
            title_el = job.select_one("h3")
            company_el = job.select_one("h4")
            location_el = job.select_one(".job-search-card__location")
            date_el = job.select_one("time")
            link_el = job.select_one("a")

            if not all([title_el, company_el, location_el, date_el, link_el]):
                continue

            job_url = link_el["href"].strip()
            description = fetch_job_description(job_url)
            
            # Parse experience requirements
            full_text = f"{title_el.text.strip()} {description}"
            exp_text, exp_min, exp_max = experience_parser.parse_experience_requirements(full_text)

            job = JobListing(
                source="LinkedIn",
                title=title_el.text.strip(),
                company=company_el.text.strip(),
                location=location_el.text.strip(),
                posted=date_el.text.strip(),
                link=job_url,
                description=description,
                experience_required=exp_text,
                experience_years_min=exp_min,
                experience_years_max=exp_max
            )
            jobs.append(job)

        print(f"✅ Found {len(jobs)} jobs from LinkedIn")
        return jobs
        
    except Exception as e:
        print(f"❌ Error scraping LinkedIn: {e}")
        return []

def save_to_csv(jobs: List[JobListing], filename="job_listings.csv"):
    """Save jobs to CSV with enhanced data including experience and resume customization info"""
    print(f"📁 Writing {len(jobs)} jobs to CSV...")
    
    if not jobs:
        # Create empty CSV with headers
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "source", "title", "company", "location", "posted", "link", 
                "skill_score", "skills_found", "posting_time", "search_query",
                "experience_required", "experience_years_min", "experience_years_max", 
                "experience_match_score", "resume_customized", "customized_resume_path"
            ])
        return
    
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source", "title", "company", "location", "posted", "link", 
            "skill_score", "skills_found", "posting_time", "search_query",
            "experience_required", "experience_years_min", "experience_years_max", 
            "experience_match_score", "resume_customized", "customized_resume_path"
        ])
        writer.writeheader()
        
        for job in jobs:
            row = {
                "source": job.source,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "posted": job.posted,
                "link": job.link,
                "skill_score": job.skill_score,
                "skills_found": ", ".join(job.skills_found),
                "posting_time": job.posting_time.strftime("%Y-%m-%d %H:%M:%S") if job.posting_time else "",
                "search_query": job.search_query,
                "experience_required": job.experience_required,
                "experience_years_min": job.experience_years_min or "",
                "experience_years_max": job.experience_years_max or "",
                "experience_match_score": job.experience_match_score,
                "resume_customized": job.resume_customized,
                "customized_resume_path": job.customized_resume_path
            }
            writer.writerow(row)

def generate_email_content(jobs: List[JobListing], filter_stats: Dict) -> str:
    """Generate enhanced email content with experience filtering and resume customization statistics"""
    
    customized_jobs = [j for j in jobs if j.resume_customized]
    
    if not jobs:
        return f"""
Hi there,

No {SEARCH_KEYWORDS} jobs found matching your criteria in the last {TIME_RANGE_HOURS} hours.

Filter Settings:
• Time Range: {TIME_RANGE_HOURS} hours
• Required Skills: {', '.join(REQUIRED_SKILLS) if REQUIRED_SKILLS else 'None'}
• Preferred Skills: {', '.join(PREFERRED_SKILLS[:5])}{'...' if len(PREFERRED_SKILLS) > 5 else ''}
• Minimum Skill Score: {MIN_SKILL_MATCH_SCORE}
• Experience Range: {MIN_EXPERIENCE_YEARS}-{MAX_EXPERIENCE_YEARS} years
• Include Unknown Experience: {'Yes' if INCLUDE_UNKNOWN_EXPERIENCE else 'No'}
• Resume Customization: {'Enabled' if ENABLE_RESUME_CUSTOMIZATION else 'Disabled'}
• Max Resumes to Customize: {MAX_RESUMES_TO_CUSTOMIZE}
• Web Search: {'Enabled' if ENABLE_WEB_SEARCH else 'Disabled'}

Try adjusting your filter criteria or check back later.

Regards,
Your AI-Powered Job Bot with Resume Customization 🤖🎯
"""

    # Create summary by experience level
    entry_level_jobs = [j for j in jobs if j.experience_years_max and j.experience_years_max <= 2]
    mid_level_jobs = [j for j in jobs if j.experience_years_min and 3 <= j.experience_years_min <= 7]
    senior_level_jobs = [j for j in jobs if j.experience_years_min and j.experience_years_min >= 8]
    unknown_exp_jobs = [j for j in jobs if not j.experience_years_min and not j.experience_years_max]
    
    # Experience breakdown
    experience_stats = {
        "Entry Level (0-2 years)": len(entry_level_jobs),
        "Mid Level (3-7 years)": len(mid_level_jobs),
        "Senior Level (8+ years)": len(senior_level_jobs),
        "Unknown Experience": len(unknown_exp_jobs)
    }
    
    # Source breakdown
    source_stats = {}
    for job in jobs:
        source_stats[job.source] = source_stats.get(job.source, 0) + 1
    
    top_skills = {}
    for job in jobs:
        for skill in job.skills_found:
            top_skills[skill] = top_skills.get(skill, 0) + 1
    
    top_skills_sorted = sorted(top_skills.items(), key=lambda x: x[1], reverse=True)[:10]
    
    content = f"""
Hi there,

🎯 Found {len(jobs)} {SEARCH_KEYWORDS} jobs matching your criteria!
🤖 AI Resume Customization: {len(customized_jobs)} resumes tailored for top matches!

📊 FILTER SUMMARY:
• Total jobs scraped: {filter_stats.get('total_scraped', 0)}
• Jobs after filtering: {len(jobs)}
• Time range: {TIME_RANGE_HOURS} hours
• Experience range: {MIN_EXPERIENCE_YEARS}-{MAX_EXPERIENCE_YEARS} years
• Required skills: {', '.join(REQUIRED_SKILLS) if REQUIRED_SKILLS else 'None'}
• Min skill score: {MIN_SKILL_MATCH_SCORE}
• Web search: {'Enabled' if ENABLE_WEB_SEARCH else 'Disabled'}

🤖 AI RESUME CUSTOMIZATION:
• Resume customization: {'Enabled' if ENABLE_RESUME_CUSTOMIZATION else 'Disabled'}
• Resumes customized: {len(customized_jobs)}/{min(len(jobs), MAX_RESUMES_TO_CUSTOMIZE)}
• Groq model: {GROQ_MODEL}
• Output folder: {OUTPUT_RESUME_FOLDER}

📈 SOURCE BREAKDOWN:
{chr(10).join([f'• {source}: {count} jobs' for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True)])}

👔 EXPERIENCE LEVEL BREAKDOWN:
{chr(10).join([f'• {level}: {count} jobs' for level, count in experience_stats.items() if count > 0])}

🏆 JOB QUALITY BREAKDOWN:
• High skill match (3+ skills): {len([j for j in jobs if j.skill_score >= 3])} jobs
• Medium skill match (1-2 skills): {len([j for j in jobs if 1 <= j.skill_score < 3])} jobs
• High experience match (8+ score): {len([j for j in jobs if j.experience_match_score >= 8])} jobs

🔥 TOP MATCHING SKILLS:
{chr(10).join([f'• {skill}: {count} jobs' for skill, count in top_skills_sorted[:5]])}

🎯 TOP MATCHES WITH AI-CUSTOMIZED RESUMES:
"""
    
    # Add top jobs with customization info
    for i, job in enumerate(jobs[:MAX_RESUMES_TO_CUSTOMIZE], 1):
        skills_str = ', '.join(job.skills_found[:3])
        if len(job.skills_found) > 3:
            skills_str += f" (+{len(job.skills_found)-3} more)"
            
        exp_str = job.experience_required if job.experience_required else "Experience not specified"
        customization_status = "✅ Resume Customized" if job.resume_customized else "📄 Standard Resume"
        
        content += f"""
{i}. {job.title} at {job.company} {customization_status}
   📍 {job.location} | 🕒 {job.posted} | ⭐ Skill Score: {job.skill_score} | 🎯 Exp Score: {job.experience_match_score}/10
   👔 Experience: {exp_str} | 🌐 {job.source}
   🔧 Skills: {skills_str}
   🔗 {job.link}
"""
        if job.resume_customized and job.customized_resume_path:
            content += f"   📁 Customized resume saved to: {job.customized_resume_path}\n"

    # Add remaining jobs without detailed customization info
    if len(jobs) > MAX_RESUMES_TO_CUSTOMIZE:
        content += f"\n📋 ADDITIONAL MATCHES ({len(jobs) - MAX_RESUMES_TO_CUSTOMIZE} more jobs):\n"
        for i, job in enumerate(jobs[MAX_RESUMES_TO_CUSTOMIZE:], MAX_RESUMES_TO_CUSTOMIZE + 1):
            content += f"{i}. {job.title} at {job.company} (Score: {job.skill_score}/{job.experience_match_score})\n"

    content += f"""

📎 Complete list with all {len(jobs)} jobs is attached as CSV.

🤖 AI RESUME CUSTOMIZATION DETAILS:
{f"• {len(customized_jobs)} resumes have been customized using Groq AI" if customized_jobs else "• No resumes were customized (feature may be disabled)"}
• Each customized resume includes:
  - Tailored professional summary
  - Emphasized relevant skills and experience
  - Job-specific keyword optimization
  - Custom cover letter generated
  - Original resume preserved for reference
• All customized resumes saved in: {OUTPUT_RESUME_FOLDER}/

Regards,
Your AI-Powered Job Bot with Resume Customization 🤖🎯

---
🛠 Experience Filter Settings:
• Experience Range: {MIN_EXPERIENCE_YEARS}-{MAX_EXPERIENCE_YEARS} years
• Include Unknown Experience: {'Yes' if INCLUDE_UNKNOWN_EXPERIENCE else 'No'}
• Excluded Experience Keywords: {', '.join(EXCLUDE_EXPERIENCE_KEYWORDS) if EXCLUDE_EXPERIENCE_KEYWORDS else 'None'}

🤖 AI Resume Settings:
• Resume Customization: {'Enabled' if ENABLE_RESUME_CUSTOMIZATION else 'Disabled'}
• Groq Model: {GROQ_MODEL}
• Max Resumes to Customize: {MAX_RESUMES_TO_CUSTOMIZE}
• Resume Folder: {RESUME_FOLDER}
• Output Folder: {OUTPUT_RESUME_FOLDER}

🛠 Other Filter Settings:
• Required Skills: {', '.join(REQUIRED_SKILLS) if REQUIRED_SKILLS else 'None'}
• Preferred Skills: {', '.join(PREFERRED_SKILLS)}
• Excluded Keywords: {', '.join(EXCLUDE_KEYWORDS) if EXCLUDE_KEYWORDS else 'None'}
• Time Range: {TIME_RANGE_HOURS} hours
• Web Search Queries: {len(WEB_SEARCH_QUERIES)} active
"""
    
    return content

def send_email(jobs: List[JobListing], filter_stats: Dict):
    """Send enhanced email with experience filtering and resume customization statistics"""
    
    customized_count = len([j for j in jobs if j.resume_customized])
    subject_suffix = f"no matches" if not jobs else f"{len(jobs)} matches, {customized_count} customized"
    
    print("📧 Sending email...")

    msg = EmailMessage()
    msg["Subject"] = f"🧠🤖 AI-Powered ML Job Digest (Resume Customization) — {subject_suffix}"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL

    email_content = generate_email_content(jobs, filter_stats)
    msg.set_content(email_content)

    # Save CSV even if no jobs (for tracking)
    save_to_csv(jobs)
    
    # Attach CSV
    try:
        with open("job_listings.csv", "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="csv", 
                             filename=f"job_listings_ai_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    except Exception as e:
        print(f"⚠️ Could not attach CSV: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def main():
    print("🚀 Starting AI-Powered Job Digest with Resume Customization...")
    print(f"📋 Filter Config:")
    print(f"   • Time Range: {TIME_RANGE_HOURS} hours")
    print(f"   • Experience Range: {MIN_EXPERIENCE_YEARS}-{MAX_EXPERIENCE_YEARS} years")
    print(f"   • Include Unknown Experience: {'Yes' if INCLUDE_UNKNOWN_EXPERIENCE else 'No'}")
    print(f"   • Required Skills: {REQUIRED_SKILLS if REQUIRED_SKILLS else 'None'}")
    print(f"   • Preferred Skills: {len(PREFERRED_SKILLS)} skills configured")
    print(f"   • Min Skill Score: {MIN_SKILL_MATCH_SCORE}")
    print(f"   • Excluded Keywords: {EXCLUDE_KEYWORDS if EXCLUDE_KEYWORDS else 'None'}")
    print(f"   • Excluded Experience Keywords: {EXCLUDE_EXPERIENCE_KEYWORDS if EXCLUDE_EXPERIENCE_KEYWORDS else 'None'}")
    print(f"   • Web Search: {'Enabled' if ENABLE_WEB_SEARCH else 'Disabled'}")
    print(f"   • Resume Customization: {'Enabled' if ENABLE_RESUME_CUSTOMIZATION else 'Disabled'}")
    print(f"   • Max Resumes to Customize: {MAX_RESUMES_TO_CUSTOMIZE}")
    print(f"   • Groq Model: {GROQ_MODEL}")
    
    all_jobs = []
    
    # Fetch jobs from traditional sources
    indeed_jobs = fetch_indeed_jobs()
    linkedin_jobs = fetch_linkedin_jobs()
    all_jobs.extend(indeed_jobs)
    all_jobs.extend(linkedin_jobs)
    
    # Fetch jobs from web search
    web_search_jobs = fetch_web_search_jobs()
    all_jobs.extend(web_search_jobs)
    
    print(f"📊 Total jobs scraped: {len(all_jobs)}")
    
    # Initialize filter with experience parameters
    job_filter = JobFilter(
        required_skills=REQUIRED_SKILLS,
        preferred_skills=PREFERRED_SKILLS,
        exclude_keywords=EXCLUDE_KEYWORDS,
        time_range_hours=TIME_RANGE_HOURS,
        min_skill_score=MIN_SKILL_MATCH_SCORE,
        min_experience_years=MIN_EXPERIENCE_YEARS,
        max_experience_years=MAX_EXPERIENCE_YEARS,
        exclude_experience_keywords=EXCLUDE_EXPERIENCE_KEYWORDS,
        include_unknown_experience=INCLUDE_UNKNOWN_EXPERIENCE
    )
    
    # Filter and score jobs
    filtered_jobs = job_filter.filter_and_score_jobs(all_jobs)
    
    print(f"✅ Jobs after filtering: {len(filtered_jobs)}")
    
    # Initialize resume manager and customize resumes for top jobs
    if ENABLE_RESUME_CUSTOMIZATION and GROQ_API_KEY:
        print("🤖 Starting AI resume customization...")
        resume_manager = ResumeManager(RESUME_FOLDER, OUTPUT_RESUME_FOLDER)
        filtered_jobs = resume_manager.customize_resumes_for_jobs(filtered_jobs, MAX_RESUMES_TO_CUSTOMIZE)
        
        customized_count = len([j for j in filtered_jobs if j.resume_customized])
        print(f"✅ Resume customization completed: {customized_count} resumes customized")
    else:
        print("⚠️ Resume customization disabled (ENABLE_RESUME_CUSTOMIZATION=false or missing GROQ_API_KEY)")
    
    # Experience analysis
    exp_analysis = {}
    for job in filtered_jobs:
        if job.experience_required:
            exp_analysis[job.experience_required] = exp_analysis.get(job.experience_required, 0) + 1
    
    if exp_analysis:
        print("📊 Experience breakdown of filtered jobs:")
        for exp, count in sorted(exp_analysis.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   • {exp}: {count} jobs")
    
    # Prepare stats for email
    filter_stats = {
        "total_scraped": len(all_jobs),
        "indeed_count": len(indeed_jobs),
        "linkedin_count": len(linkedin_jobs),
        "web_search_count": len(web_search_jobs),
        "filtered_count": len(filtered_jobs),
        "customized_count": len([j for j in filtered_jobs if j.resume_customized])
    }
    
    # Send email with results
    send_email(filtered_jobs, filter_stats)
    
    print("🎉 AI-Powered job digest with resume customization completed!")
    print(f"📈 Final stats:")
    print(f"   • Indeed: {len(indeed_jobs)} jobs")
    print(f"   • LinkedIn: {len(linkedin_jobs)} jobs")
    print(f"   • Web Search: {len(web_search_jobs)} jobs")  
    print(f"   • After filtering: {len(filtered_jobs)} jobs")
    print(f"   • Experience filter range: {MIN_EXPERIENCE_YEARS}-{MAX_EXPERIENCE_YEARS} years")
    print(f"   • Resumes customized: {len([j for j in filtered_jobs if j.resume_customized])}")
    
    if ENABLE_RESUME_CUSTOMIZATION and filtered_jobs:
        print(f"📁 Customized resumes saved in: {OUTPUT_RESUME_FOLDER}")

if __name__ == "__main__":
    main()