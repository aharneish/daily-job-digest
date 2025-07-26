import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import smtplib
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from dotenv import load_dotenv

load_dotenv()

# -------------------- CONFIG --------------------
GMAIL_USER = "aharneish@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_PASS")
RECIPIENT = "aharneish@gmail.com"
LINKEDIN_COOKIE = os.getenv("LINKEDIN_SESSION_COOKIE")

SEARCH_KEYWORDS = "Machine Learning Engineer"
LOCATION = "India"
MAX_AGE_HOURS = 12
CSV_FILENAME = "job_listings.csv"
# -------------------------------------------------

def is_recent(posted_str, max_age_hours=12):
    posted_str = posted_str.lower()
    if "just" in posted_str:
        return True
    if "hour" in posted_str:
        try:
            hours = int(posted_str.split()[0])
            return hours <= max_age_hours
        except:
            return False
    if "minute" in posted_str:
        return True
    if "day" in posted_str:
        try:
            days = int(posted_str.split()[0])
            return (days * 24) <= max_age_hours
        except:
            return False
    return False

def scrape_indeed_jobs(keyword, location, max_age_hours):
    print("🌐 Scraping Indeed...")
    url = f"https://in.indeed.com/jobs?q={keyword}&l={location}&sort=date"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")
    jobs = []

    for card in soup.select("div.job_seen_beacon"):
        title = card.select_one("h2.jobTitle span")
        company = card.select_one("span.companyName")
        loc = card.select_one("div.companyLocation")
        posted = card.select_one("span.date")
        link_el = card.select_one("a")
        if not all([title, company, loc, posted, link_el]):
            continue
        if not is_recent(posted.text, max_age_hours):
            continue
        job_url = "https://in.indeed.com" + link_el["href"]
        jobs.append({
            "title": title.text.strip(),
            "company": company.text.strip(),
            "location": loc.text.strip(),
            "posted": posted.text.strip(),
            "link": job_url
        })
    print(f"✅ Found {len(jobs)} jobs on Indeed")
    return jobs

def scrape_linkedin_jobs(keyword, max_age_hours):
    print("🌐 Scraping LinkedIn...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": f"li_at={LINKEDIN_COOKIE}"
    }

    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={keyword}&location=India&f_TPR=r{max_age_hours}h&sortBy=DD"
    )
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")

    jobs = []
    for job_card in soup.select("li"):
        title_el = job_card.select_one("h3")
        company_el = job_card.select_one("h4")
        location_el = job_card.select_one(".job-search-card__location")
        time_ago_el = job_card.select_one("time")
        link_el = job_card.select_one("a")

        if not all([title_el, company_el, location_el, time_ago_el, link_el]):
            continue
        if not is_recent(time_ago_el.text, max_age_hours):
            continue
        jobs.append({
            "title": title_el.text.strip(),
            "company": company_el.text.strip(),
            "location": location_el.text.strip(),
            "posted": time_ago_el.text.strip(),
            "link": "https://www.linkedin.com" + link_el['href'].split('?')[0]
        })
    print(f"✅ Found {len(jobs)} jobs on LinkedIn")
    return jobs

def save_jobs_to_csv(jobs, filename):
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["title", "company", "location", "posted", "link"])
        writer.writeheader()
        writer.writerows(jobs)

def send_email(jobs):
    print("📧 Sending email...")
    msg = MIMEMultipart()
    msg["Subject"] = f"🔥 {len(jobs)} New ML Jobs - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT

    # Plain text summary
    text = "\n".join(
        f"{j['title']} at {j['company']} ({j['location']}) - {j['posted']}\n{j['link']}"
        for j in jobs
    ) or "No jobs found in the last 12 hours."

    # HTML version
    html = "<h3>🔥 New Job Listings</h3><ul>"
    for j in jobs:
        html += f"<li><b>{j['title']}</b> at {j['company']} ({j['location']}) - {j['posted']}<br>"
        html += f"<a href='{j['link']}'>Apply Here</a></li><br>"
    html += "</ul>"

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    # Attach CSV
    with open(CSV_FILENAME, "rb") as f:
        part = MIMEApplication(f.read(), Name=CSV_FILENAME)
        part["Content-Disposition"] = f'attachment; filename="{CSV_FILENAME}"'
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

    print("✅ Email sent!")

def main():
    indeed_jobs = scrape_indeed_jobs(SEARCH_KEYWORDS, LOCATION, MAX_AGE_HOURS)
    linkedin_jobs = scrape_linkedin_jobs(SEARCH_KEYWORDS, MAX_AGE_HOURS)
    all_jobs = indeed_jobs + linkedin_jobs
    save_jobs_to_csv(all_jobs, CSV_FILENAME)
    send_email(all_jobs)

if __name__ == "__main__":
    main()
