FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV TZ=Asia/Kolkata
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your job script
COPY daily_job_digest.py .

# Create cron job
RUN echo "30 6 * * * python /app/daily_job_digest.py >> /var/log/cron.log 2>&1" > /etc/cron.d/jobdigest

# Apply cron job
RUN chmod 0644 /etc/cron.d/jobdigest && crontab /etc/cron.d/jobdigest

# Create the log file
RUN touch /var/log/cron.log

# Start cron in foreground
CMD ["cron", "-f"]
