from daily_job_digest import send_email  # Only if send_email is in another file

if __name__ == "__main__":
    jobs = fetch_jobs()
    if not jobs:
        jobs = [{
            "title": "No fresh jobs found",
            "company": "JobBot",
            "location": "Internet",
            "posted": "Now"
        }]
    send_email(jobs)
