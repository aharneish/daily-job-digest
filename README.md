# Enhanced Daily Job Digest with Web Search

This project automates the collection of job listings from multiple sources including web search across various job portals, and sends a comprehensive daily digest email with advanced filtering capabilities.

## 🚀 New Features

### 🌐 **Web Search Integration**
- Automatically searches across **10+ job portals** including Naukri, Shine, Monster, Glassdoor, FreshersWorld, TimesJobs, Instahyre, and more
- Uses intelligent web scraping to find the latest job postings
- Supports time-based searches (past 24 hours, past hour)
- Configurable search queries and result limits

### 🎯 **Advanced Filtering**
- **Time Range Filtering**: Filter jobs by posting time (hours/days)
- **Skills-Based Filtering**: Required skills, preferred skills with scoring
- **Keyword Exclusion**: Filter out unwanted job types
- **Relevance Scoring**: Jobs ranked by skill matches
- **Duplicate Removal**: Intelligent deduplication across sources

### 📊 **Enhanced Analytics**
- Source breakdown (Indeed, LinkedIn, Web Search)
- Job quality metrics (high/medium/low relevance)
- Skill trend analysis
- Filtering statistics

## Features

- Fetches job listings from multiple sources:
  - **Indeed** (direct scraping)
  - **LinkedIn** (with session cookie)
  - **Web Search** across 10+ job portals
- Advanced filtering with time range and skills matching
- Intelligent job relevance scoring
- Sends detailed email digest with analytics
- Can be triggered manually or scheduled via GitHub Actions
- Containerization support via Docker

## File Structure

```
.
├── daily_job_digest.py         # Enhanced main script with web search
├── main.py                    # Entry point or utility script
├── job_listings.csv           # Source data for job listings
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Project metadata/configuration
├── Dockerfile.dockerfile      # Dockerfile for containerization
├── render.yaml                # Additional configuration
├── uv.lock                    # Dependency lock file
├── __pycache__/               # Python bytecode cache
├── Job-bot/                   # (Folder, contents not listed)
└── .github/
    └── workflows/
        └── daily-job.yml      # GitHub Actions workflow for automation
```

## Setup

1. **Clone the repository**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (create `.env` file)
   ```bash
   # Basic Configuration
   GMAIL_USER=your_email@gmail.com
   GMAIL_PASS=your_gmail_app_password
   TO_EMAIL=recipient@gmail.com
   
   # Job Search Config
   SEARCH_KEYWORDS=Machine Learning Engineer
   LOCATION=India
   
   # Web Search (NEW)
   ENABLE_WEB_SEARCH=true
   MAX_SEARCH_RESULTS_PER_QUERY=20
   
   # Advanced Filtering
   TIME_RANGE_HOURS=24
   REQUIRED_SKILLS=
   PREFERRED_SKILLS=python,tensorflow,pytorch,machine learning,AI
   MIN_SKILL_MATCH_SCORE=1
   EXCLUDE_KEYWORDS=intern,internship
   
   # LinkedIn (optional)
   LINKEDIN_SESSION_COOKIE=your_linkedin_li_at_cookie
   ```

4. **Gmail App Password Setup**:
   1. Go to your Google Account > Security
   2. Enable 2-Step Verification
   3. Under 'Signing in to Google', select 'App Passwords'
   4. Generate a password for 'Mail' and 'Other' (give a name, e.g., 'Job Digest')
   5. Use the generated password as `GMAIL_PASS`

5. **LinkedIn Session Cookie** (optional for LinkedIn scraping):
   1. Log in to LinkedIn in your browser
   2. Open Developer Tools (F12), go to the 'Application' tab
   3. Under 'Cookies', find the value for `li_at`
   4. Use this value as `LINKEDIN_SESSION_COOKIE`

6. **Run the script**
   ```bash
   python daily_job_digest.py
   ```

## 🌐 Web Search Sources

The enhanced script searches across these job portals:
- **Naukri.com** - India's largest job portal
- **Shine.com** - Career platform
- **Monster.com** - Global job board
- **Glassdoor.com** - Company reviews and jobs
- **FreshersWorld.com** - Entry-level jobs
- **TimesJobs.com** - Times Group job portal
- **Instahyre.com** - Tech jobs platform
- **General web search** for recent postings
- **Remote job search** across platforms

## 🎯 Advanced Configuration Examples

### For Senior ML Engineers
```bash
SEARCH_KEYWORDS=Senior Machine Learning Engineer
REQUIRED_SKILLS=senior,machine learning
PREFERRED_SKILLS=python,tensorflow,pytorch,kubernetes,docker,aws,gcp,azure
MIN_SKILL_MATCH_SCORE=3
EXCLUDE_KEYWORDS=intern,junior,entry level
TIME_RANGE_HOURS=24
```

### For Computer Vision Specialists
```bash
SEARCH_KEYWORDS=Computer Vision Engineer
REQUIRED_SKILLS=computer vision
PREFERRED_SKILLS=opencv,pytorch,tensorflow,python,deep learning,CNN,image processing
MIN_SKILL_MATCH_SCORE=2
TIME_RANGE_HOURS=12
```

### For Recent Jobs (Past Hour)
```bash
SEARCH_KEYWORDS=Machine Learning Engineer latest jobs
TIME_RANGE_HOURS=1
ENABLE_WEB_SEARCH=true
MAX_SEARCH_RESULTS_PER_QUERY=30
```

### For Remote Work
```bash
SEARCH_KEYWORDS=Remote Machine Learning Engineer
LOCATION=Remote
PREFERRED_SKILLS=python,tensorflow,pytorch,remote work,distributed systems
```

## 📧 Enhanced Email Features

The digest email now includes:
- **Filter Summary**: Applied criteria and statistics
- **Source Breakdown**: Jobs from each platform
- **Job Quality Metrics**: High/medium/low relevance breakdown
- **Top Skills Analysis**: Most demanded skills
- **Top Matches**: Best 5 jobs with detailed info
- **Complete CSV Export**: All jobs with metadata

## Automation

The workflow `.github/workflows/daily-job.yml` runs the job daily at 06:30 UTC and can be triggered manually. It sets up Python, installs dependencies, and runs the enhanced script with web search.

## Docker

To build and run the project in a container:
```bash
docker build -f Dockerfile.dockerfile -t enhanced-job-digest .
docker run --env-file .env enhanced-job-digest
```

## 🔧 Performance & Rate Limiting

- Built-in rate limiting to respect website policies
- Duplicate detection across all sources
- Efficient caching to avoid re-processing same URLs
- Configurable result limits per search query
- Error handling for failed requests

## 📊 Output Formats

- **Email Digest**: Rich HTML email with analytics
- **CSV Export**: Detailed spreadsheet with all job data
- **Console Logs**: Real-time progress and statistics

## Troubleshooting

### Web Search Issues
- If web search fails, the script continues with Indeed/LinkedIn
- Rate limiting may cause delays - this is normal
- Some job portals may block automated access - the script handles this gracefully

### Email Issues
- Ensure Gmail App Password is correctly set
- Check spam folder for digest emails
- Verify `GMAIL_USER` and `TO_EMAIL` are correct

### LinkedIn Issues
- LinkedIn cookie may expire - refresh it periodically
- LinkedIn scraping is optional and can be disabled

## Contributing

Feel free to open issues or submit pull requests for improvements. The enhanced script is designed to be modular and extensible.

## Legal & Ethical Considerations

- Respects robots.txt and rate limiting
- Uses public job posting data only
- Implements delays to avoid overwhelming servers
- Follows web scraping best practices

---

**Enhanced Job Bot** - Now with 10x more job sources! 🚀