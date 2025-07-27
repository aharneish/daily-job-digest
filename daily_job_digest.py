import requests
import smtplib
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid
import os
from dotenv import load_dotenv
load_dotenv()

# 🛠 CONFIG
SEARCH_KEYWORDS = "Machine Learning Engineer"
LOCATION = "India"
MAX_AGE_HOURS = 24
GMAIL_USER = "YOUR_EMAIL"       # your Gmail address
GMAIL_PASS = os.getenv("GMAIL_PASS")       # app password (not your Gmail password)
TO_EMAIL = "YOUR_EMAIL"
LINKEDIN_COOKIE = os.getenv("LINKEDIN_SESSION_COOKIE")  # set as secret

def fetch_indeed_jobs():
    print("🔍 Scraping Indeed...")
    url = f"https://in.indeed.com/jobs?q={SEARCH_KEYWORDS}&l={LOCATION}&sort=date"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
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

        posted = date_el.text.lower()
        if "hour" in posted or "just" in posted:
            jobs.append({
                "source": "Indeed",
                "title": title_el.text.strip(),
                "company": company_el.text.strip(),
                "location": location_el.text.strip(),
                "posted": posted.strip(),
                "link": f"https://in.indeed.com{link_el['href']}"
            })
    return jobs

def fetch_linkedin_jobs():
    print("🔍 Scraping LinkedIn...")
    now = datetime.utcnow()
    start = now - timedelta(hours=MAX_AGE_HOURS)
    start_ts = int(start.timestamp())

    url = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={SEARCH_KEYWORDS}&location={LOCATION}&f_TPR=r{MAX_AGE_HOURS}h&sortBy=DD"
    )
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": f"li_at={LINKEDIN_COOKIE}"
    }

    r = requests.get(url, headers=headers)
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

        jobs.append({
            "source": "LinkedIn",
            "title": title_el.text.strip(),
            "company": company_el.text.strip(),
            "location": location_el.text.strip(),
            "posted": date_el.text.strip(),
            "link": link_el["href"].strip()
        })

    return jobs

def save_to_csv(jobs, filename="job_listings.csv"):
    print(f"📁 Writing {len(jobs)} jobs to CSV...")
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
        writer.writeheader()
        writer.writerows(jobs)

def send_email(jobs):
    if not jobs:
        print("📭 No jobs found in the last 12 hours. Skipping email.")
        return

    save_to_csv(jobs)
    print("📧 Sending email...")

    msg = EmailMessage()
    msg["Subject"] = f"🧠 ML Job Digest — {len(jobs)} new listings"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL

    msg.set_content(f"""
Hi there,

Here are the top Machine Learning Engineer jobs posted in the last {MAX_AGE_HOURS} hours.

Attached is the CSV with job titles, companies, locations, and links.

Regards,
Your Job Bot 🤖
""")

    with open("job_listings.csv", "rb") as f:
        msg.add_attachment(f.read(), maintype="text", subtype="csv", filename="job_listings.csv")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)

    print("✅ Email sent!")

def main():
    indeed = fetch_indeed_jobs()
    linkedin = fetch_linkedin_jobs()
    all_jobs = indeed + linkedin
    send_email(all_jobs)

if __name__ == "__main__":
    main()
