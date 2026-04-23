import anthropic
import psycopg2
import json
import os
from datetime import datetime

# Load config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "vegabase_prod")
DB_USER = os.getenv("DB_USER", "priyas")
DB_PASS = os.getenv("DB_PASS")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def get_pending_jobs():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()
    cur.execute("SELECT id, customer_id, raw_data FROM jobs WHERE status = 'pending' LIMIT 10")
    jobs = cur.fetchall()
    conn.close()
    return jobs

def analyze_data(raw_data):
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"Analyze the following customer data and return key insights as JSON:\n\n{raw_data}"
            }
        ]
    )
    return message.content[0].text

def update_job_status(job_id, status, result=None):
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()
    cur.execute(
        "UPDATE jobs SET status = %s, result = %s, updated_at = %s WHERE id = %s",
        (status, json.dumps(result), datetime.now(), job_id)
    )
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting pipeline run...")
    jobs = get_pending_jobs()
    print(f"[{datetime.now()}] Found {len(jobs)} pending jobs")

    for job in jobs:
        job_id, customer_id, raw_data = job
        try:
            print(f"[{datetime.now()}] Processing job {job_id} for customer {customer_id}")
            result = analyze_data(raw_data)
            update_job_status(job_id, "complete", result)
            print(f"[{datetime.now()}] Job {job_id} complete")
        except Exception as e:
            print(f"[{datetime.now()}] Job {job_id} failed: {e}")
            update_job_status(job_id, "failed")

    print(f"[{datetime.now()}] Pipeline run complete")
