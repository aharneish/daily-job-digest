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
from urllib.parse import quote, urljoin, urlparse
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

# 🛠 CONFIG
SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "Machine Learning Engineer")
LOCATION = os.getenv("LOCATION", "India")
MAX_AGE_HOURS = 24
GMAIL_USER = os.getenv("GMAIL_USER", "YOUR_EMAIL")
GMAIL_PASS = os.getenv("GMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL", GMAIL_USER)
LINKEDIN_COOKIE = os.getenv("LINKEDIN_SESSION_COOKIE")

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

@dataclass
class JobListing:
    """Enhanced job listing data structure"""
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
    
    def __post_init__(self):
        if self.skills_found is None:
            self.skills_found = []

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

class WebSearchScraper:
    """Web search-based job scraper for multiple job portals"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.processed_urls: Set[str] = set()
        
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
                search_query=query
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
            'indeed.com': 'Indeed'
        }
        
        for key, value in source_mapping.items():
            if key in domain:
                return value
                
        return f"Web ({domain})"

class JobFilter:
    """Enhanced job filtering class"""
    
    def __init__(self, 
                 required_skills: List[str] = None,
                 preferred_skills: List[str] = None,
                 exclude_keywords: List[str] = None,
                 time_range_hours: int = 24,
                 min_skill_score: int = 1):
        
        self.required_skills = [skill.strip().lower() for skill in (required_skills or []) if skill.strip()]
        self.preferred_skills = [skill.strip().lower() for skill in (preferred_skills or []) if skill.strip()]
        self.exclude_keywords = [kw.strip().lower() for kw in (exclude_keywords or []) if kw.strip()]
        self.time_range_hours = time_range_hours
        self.min_skill_score = min_skill_score
        self.cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
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
    
    def matches_requirements(self, job: dict) -> bool:
        job_text = f"{job.title or ''} {job.description or ''}".lower()
        job_title = (job.title or '').lower()

        # Required skills check is skipped (empty)

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
        """Filter jobs and add skill scoring"""
        filtered_jobs = []
        
        for job in jobs:
            # Parse posting time
            job.posting_time = self.parse_posting_time(job.posted)
            
            # Extract skills and calculate score
            job.skills_found, job.skill_score = self.extract_skills(job)
            
            # Check if job matches requirements
            if self.matches_requirements(job):
                filtered_jobs.append(job)
        
        # Sort by skill score (descending) and then by posting time (newest first)
        filtered_jobs.sort(key=lambda x: (-x.skill_score, x.posting_time or datetime.min), reverse=False)
        
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

            job = JobListing(
                source="Indeed",
                title=title_el.text.strip(),
                company=company_el.text.strip(),
                location=location_el.text.strip(),
                posted=date_el.text.strip(),
                link=job_url,
                description=description
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

            job = JobListing(
                source="LinkedIn",
                title=title_el.text.strip(),
                company=company_el.text.strip(),
                location=location_el.text.strip(),
                posted=date_el.text.strip(),
                link=job_url,
                description=description
            )
            jobs.append(job)

        print(f"✅ Found {len(jobs)} jobs from LinkedIn")
        return jobs
        
    except Exception as e:
        print(f"❌ Error scraping LinkedIn: {e}")
        return []

def save_to_csv(jobs: List[JobListing], filename="job_listings.csv"):
    """Save jobs to CSV with enhanced data"""
    print(f"📁 Writing {len(jobs)} jobs to CSV...")
    
    if not jobs:
        # Create empty CSV with headers
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source", "title", "company", "location", "posted", "link", 
                           "skill_score", "skills_found", "posting_time", "search_query"])
        return
    
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source", "title", "company", "location", "posted", "link", 
            "skill_score", "skills_found", "posting_time", "search_query"
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
                "search_query": job.search_query
            }
            writer.writerow(row)

def generate_email_content(jobs: List[JobListing], filter_stats: Dict) -> str:
    """Generate enhanced email content with filtering statistics"""
    
    if not jobs:
        return f"""
Hi there,

No Machine Learning Engineer jobs found matching your criteria in the last {TIME_RANGE_HOURS} hours.

Filter Settings:
• Time Range: {TIME_RANGE_HOURS} hours
• Required Skills: {', '.join(REQUIRED_SKILLS) if REQUIRED_SKILLS else 'None'}
• Preferred Skills: {', '.join(PREFERRED_SKILLS[:5])}{'...' if len(PREFERRED_SKILLS) > 5 else ''}
• Minimum Skill Score: {MIN_SKILL_MATCH_SCORE}
• Excluded Keywords: {', '.join(EXCLUDE_KEYWORDS) if EXCLUDE_KEYWORDS else 'None'}
• Web Search: {'Enabled' if ENABLE_WEB_SEARCH else 'Disabled'}

Try adjusting your filter criteria or check back later.

Regards,
Your Enhanced Job Bot 🤖
"""

    # Create summary by skill score
    high_score_jobs = [j for j in jobs if j.skill_score >= 3]
    medium_score_jobs = [j for j in jobs if 1 <= j.skill_score < 3]
    
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

🎯 Found {len(jobs)} Machine Learning Engineer jobs matching your criteria!

📊 FILTER SUMMARY:
• Total jobs scraped: {filter_stats.get('total_scraped', 0)}
• Jobs after filtering: {len(jobs)}
• Time range: {TIME_RANGE_HOURS} hours
• Required skills: {', '.join(REQUIRED_SKILLS) if REQUIRED_SKILLS else 'None'}
• Min skill score: {MIN_SKILL_MATCH_SCORE}
• Web search: {'Enabled' if ENABLE_WEB_SEARCH else 'Disabled'}

📈 SOURCE BREAKDOWN:
{chr(10).join([f'• {source}: {count} jobs' for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True)])}

🏆 JOB QUALITY BREAKDOWN:
• High relevance (3+ skills): {len(high_score_jobs)} jobs
• Medium relevance (1-2 skills): {len(medium_score_jobs)} jobs

🔥 TOP MATCHING SKILLS:
{chr(10).join([f'• {skill}: {count} jobs' for skill, count in top_skills_sorted[:5]])}

🎯 TOP MATCHES:
"""
    
    # Add top 5 jobs
    for i, job in enumerate(jobs[:5], 1):
        skills_str = ', '.join(job.skills_found[:3])
        if len(job.skills_found) > 3:
            skills_str += f" (+{len(job.skills_found)-3} more)"
            
        content += f"""
{i}. {job.title} at {job.company}
   📍 {job.location} | 🕒 {job.posted} | ⭐ Score: {job.skill_score} | 🌐 {job.source}
   🔧 Skills: {skills_str}
   🔗 {job.link}
"""

    content += f"""

📎 Complete list with all {len(jobs)} jobs is attached as CSV.

Regards,
Your Enhanced Job Bot 🤖

---
🛠 Filter Settings:
• Required Skills: {', '.join(REQUIRED_SKILLS) if REQUIRED_SKILLS else 'None'}
• Preferred Skills: {', '.join(PREFERRED_SKILLS)}
• Excluded Keywords: {', '.join(EXCLUDE_KEYWORDS) if EXCLUDE_KEYWORDS else 'None'}
• Time Range: {TIME_RANGE_HOURS} hours
• Web Search Queries: {len(WEB_SEARCH_QUERIES)} active
"""
    
    return content

def send_email(jobs: List[JobListing], filter_stats: Dict):
    """Send enhanced email with filtering statistics"""
    
    subject_suffix = "no matches" if not jobs else f"{len(jobs)} matches"
    
    print("📧 Sending email...")

    msg = EmailMessage()
    msg["Subject"] = f"🧠 Enhanced ML Job Digest — {subject_suffix}"
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
                             filename=f"job_listings_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
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
    print("🚀 Starting Enhanced Job Digest with Web Search...")
    print(f"📋 Filter Config:")
    print(f"   • Time Range: {TIME_RANGE_HOURS} hours")
    print(f"   • Required Skills: {REQUIRED_SKILLS if REQUIRED_SKILLS else 'None'}")
    print(f"   • Preferred Skills: {len(PREFERRED_SKILLS)} skills configured")
    print(f"   • Min Skill Score: {MIN_SKILL_MATCH_SCORE}")
    print(f"   • Excluded Keywords: {EXCLUDE_KEYWORDS if EXCLUDE_KEYWORDS else 'None'}")
    print(f"   • Web Search: {'Enabled' if ENABLE_WEB_SEARCH else 'Disabled'}")
    
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
    
    # Initialize filter
    job_filter = JobFilter(
        required_skills=REQUIRED_SKILLS,
        preferred_skills=PREFERRED_SKILLS,
        exclude_keywords=EXCLUDE_KEYWORDS,
        time_range_hours=TIME_RANGE_HOURS,
        min_skill_score=MIN_SKILL_MATCH_SCORE
    )
    
    # Filter and score jobs
    filtered_jobs = job_filter.filter_and_score_jobs(all_jobs)
    
    print(f"✅ Jobs after filtering: {len(filtered_jobs)}")
    
    # Prepare stats for email
    filter_stats = {
        "total_scraped": len(all_jobs),
        "indeed_count": len(indeed_jobs),
        "linkedin_count": len(linkedin_jobs),
        "web_search_count": len(web_search_jobs),
        "filtered_count": len(filtered_jobs)
    }
    
    # Send email with results
    send_email(filtered_jobs, filter_stats)
    
    print("🎉 Enhanced job digest with web search completed!")
    print(f"📈 Final stats:")
    print(f"   • Indeed: {len(indeed_jobs)} jobs")
    print(f"   • LinkedIn: {len(linkedin_jobs)} jobs")
    print(f"   • Web Search: {len(web_search_jobs)} jobs")
    print(f"   • After filtering: {len(filtered_jobs)} jobs")

if __name__ == "__main__":
    main()