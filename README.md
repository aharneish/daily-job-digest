# 🤖 AI-Powered Job Scraper with Resume Customization

## 🚀 Quick Setup Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Your Groq API Key (Free!)
1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key for your `.env` file

### 3. Create Resume Folder Structure
```
your_project/
├── resume/
│   ├── my_resume.txt       # Your main resume (text format)
│   ├── my_resume.docx      # Optional: Word format
│   └── my_resume.pdf       # Optional: PDF format
├── customized_resumes/     # Will be created automatically
├── daily_job_digest.py
├── .env
└── requirements.txt
```

### 4. Configure Your .env File
```bash
# Required settings
GROQ_API_KEY=your_groq_api_key_here
GMAIL_USER=your_email@gmail.com
GMAIL_PASS=your_app_password

# Resume customization settings
ENABLE_RESUME_CUSTOMIZATION=true
RESUME_FOLDER=resume
OUTPUT_RESUME_FOLDER=customized_resumes
MAX_RESUMES_TO_CUSTOMIZE=5

# Job search settings
SEARCH_KEYWORDS=Machine Learning Engineer
LOCATION=India
MIN_EXPERIENCE_YEARS=2
MAX_EXPERIENCE_YEARS=8
```

### 5. Prepare Your Resume
Place your resume in the `resume/` folder in one of these formats:
- `.txt` - Plain text (recommended for best AI processing)
- `.docx` - Microsoft Word
- `.pdf` - PDF format
- `.md` - Markdown format

## 🤖 How AI Resume Customization Works

### For Each Top Job Match:
1. **Analyzes** the job description for key requirements
2. **Customizes** your resume to highlight relevant experience
3. **Optimizes** keywords for ATS systems
4. **Generates** a tailored cover letter
5. **Creates** a dedicated folder with:
   - Customized resume
   - Cover letter
   - Original resume (for reference)
   - Job details in JSON format

### Example Output Structure:
```
customized_resumes/
├── Machine Learning Engineer - Google/
│   ├── my_resume_customized.txt
│   ├── cover_letter.txt
│   ├── original_my_resume.txt
│   └── job_info.json
├── Data Scientist - Microsoft/
│   ├── my_resume_customized.txt
│   ├── cover_letter.txt
│   ├── original_my_resume.txt
│   └── job_info.json
└── AI Engineer - OpenAI/
    ├── my_resume_customized.txt
    ├── cover_letter.txt
    ├── original_my_resume.txt
    └── job_info.json
```

## 🎯 Key Features

### ✅ What the AI Does:
- Reorganizes experience to highlight relevant skills
- Adjusts professional summary for each role
- Emphasizes matching technical skills
- Uses job-specific keywords naturally
- Generates personalized cover letters
- Maintains factual accuracy (no fake information)

### ❌ What the AI Doesn't Do:
- Add fake experience or skills
- Change your actual work history
- Create unrealistic qualifications
- Modify core personal information

## 🛠 Configuration Options

### Resume Customization Intensity:
```bash
# Conservative (3 best matches, highest quality)
MAX_RESUMES_TO_CUSTOMIZE=3
GROQ_MODEL=llama-3.1-70b-versatile

# Balanced (5 matches, good quality)
MAX_RESUMES_TO_CUSTOMIZE=5
GROQ_MODEL=llama-3.1-70b-versatile

# Aggressive (10 matches, faster processing)
MAX_RESUMES_TO_CUSTOMIZE=10
GROQ_MODEL=llama-3.1-8b-instant
```

### Available Groq Models:
- `llama-3.1-70b-versatile` - Best quality, slower (Recommended)
- `llama-3.1-8b-instant` - Fast processing, good quality
- `mixtral-8x7b-32768` - Large context window
- `gemma2-9b-it` - Lightweight option

## 📊 Enhanced Email Reports

### New Email Features:
- Resume customization statistics
- AI processing summary
- Direct links to customized resume folders
- Cover letter generation status
- Model performance metrics

### Sample Email Subject:
```
🧠🤖 AI-Powered ML Job Digest (Resume Customization) — 12 matches, 5 customized
```

## 🔧 Advanced Usage Tips

### 1. Optimize Your Base Resume
- Use clear, structured formatting
- Include comprehensive skill lists
- Detail your achievements with metrics
- Use industry-standard terminology

### 2. Fine-tune Job Filtering
```bash
# For better AI customization results
MIN_SKILL_MATCH_SCORE=2  # Higher quality jobs
PREFERRED_SKILLS=python,machine learning,tensorflow,pytorch,aws,docker
```

### 3. Monitor API Usage
- Groq offers generous free tiers
- Each resume customization uses ~2-3 API calls
- Monitor your usage at [https://console.groq.com/](https://console.groq.com/)

### 4. Resume Format Recommendations
- **Best:** Plain text (.txt) - Easiest for AI to process
- **Good:** Markdown (.md) - Structured but readable
- **OK:** Word (.docx) - Requires python-docx
- **Limited:** PDF (.pdf) - May lose formatting

## 🚨 Troubleshooting

### Common Issues:

1. **"Groq API key is required"**
   - Check your `.env` file has `GROQ_API_KEY=your_actual_key`
   - Ensure no extra spaces around the key

2. **"No resume files found"**
   - Verify `resume/` folder exists
   - Check file formats are supported (.txt, .md, .docx, .pdf)
   - Ensure `RESUME_FOLDER=resume` in `.env`

3. **"Error customizing resume"**
   - Check your Groq API key is valid
   - Verify internet connection
   - Try a different model (e.g., `llama-3.1-8b-instant`)

4. **Poor customization quality**
   - Try `llama-3.1-70b-versatile` model
   - Improve your base resume structure
   - Reduce `MAX_RESUMES_TO_CUSTOMIZE` for higher quality

### Debug Mode:
```bash
# Add this to see detailed processing
export DEBUG=true
python daily_job_digest.py
```

## 🔄 Running the System

### Manual Run:
```bash
python daily_job_digest.py
```

### Scheduled Run (Cron):
```bash
# Run daily at 9 AM
0 9 * * * /usr/bin/python3 /path/to/daily_job_digest.py
```

### Test Configuration:
```bash
# Test with minimal settings first
MAX_RESUMES_TO_CUSTOMIZE=1
GROQ_MODEL=llama-3.1-8b-instant
```

## 💡 Best Practices

1. **Start Small:** Test with 1-2 resume customizations first
2. **Quality Base Resume:** Ensure your original resume is comprehensive
3. **Monitor Results:** Review customized resumes for quality
4. **Iterate Settings:** Adjust filters based on results
5. **Keep Backups:** Original resumes are preserved automatically
6. **Review Before Sending:** Always review AI-customized content

## 📈 Success Metrics

Track your improvements:
- Application response rates
- Interview call rates
- Time saved on resume customization
- Quality of job matches

The AI system learns from job descriptions to create increasingly targeted resumes for better application success rates!