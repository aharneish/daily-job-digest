# Daily Job Digest

This project automates the collection of job listings and sends a daily digest email. It is designed to run as a scheduled workflow using GitHub Actions.

## Features

- Fetches job listings from `job_listings.csv`
- Sends a daily email digest using Gmail credentials
- Can be triggered manually or scheduled via GitHub Actions
- Containerization support via Docker

## File Structure

```
.
├── daily_job_digest.py         # Main script for generating and sending the job digest
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

3. **Configure environment variables**
   - `GMAIL_USER`: Your Gmail address used to send emails.
   - `GMAIL_PASS`: Gmail App Password. To create:
     1. Go to your Google Account > Security.
     2. Enable 2-Step Verification.
     3. Under 'Signing in to Google', select 'App Passwords'.
     4. Generate a password for 'Mail' and 'Other' (give a name, e.g., 'Job Digest').
     5. Use the generated password as `GMAIL_PASS`.
   - `LINKEDIN_SESSION_COOKIE`: Your LinkedIn session cookie (if scraping LinkedIn jobs). To get it:
     1. Log in to LinkedIn in your browser.
     2. Open Developer Tools (F12), go to the 'Application' tab.
     3. Under 'Cookies', find the value for `li_at`.
     4. Use this value as `LINKEDIN_SESSION_COOKIE`.

4. **Run the script**
   ```bash
   python daily_job_digest.py
   ```

## Automation

The workflow `.github/workflows/daily-job.yml` runs the job daily at 06:30 UTC and can be triggered manually. It sets up Python, installs dependencies, and runs the main script.

## Docker

To build and run the project in a container:
```bash
docker build -f Dockerfile.dockerfile -t job-digest .
docker run --env GMAIL_USER=... --env GMAIL_PASS=... --env LINKEDIN_SESSION_COOKIE=... job-digest
```

## Contributing

Feel free to open issues or submit pull requests for improvements.
