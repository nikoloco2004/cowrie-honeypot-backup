import psycopg2
import boto3
import json
import os
from datetime import datetime

# AWS S3 config
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = "vegabase-prod-data"
S3_PREFIX = "incoming/"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "vegabase_prod")
DB_USER = os.getenv("DB_USER", "priyas")
DB_PASS = os.getenv("DB_PASS")

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name="us-west-2"
    )

def fetch_incoming_files():
    s3 = get_s3_client()
    response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    return response.get("Contents", [])

def ingest_file(s3_key):
    s3 = get_s3_client()
    obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    data = json.loads(obj["Body"].read().decode("utf-8"))

    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO jobs (customer_id, raw_data, status, created_at) VALUES (%s, %s, 'pending', %s)",
        (data["customer_id"], json.dumps(data), datetime.now())
    )
    conn.commit()
    conn.close()
    print(f"[{datetime.now()}] Ingested {s3_key}")

if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting ingest...")
    files = fetch_incoming_files()
    print(f"[{datetime.now()}] Found {len(files)} files in S3")
    for f in files:
        try:
            ingest_file(f["Key"])
        except Exception as e:
            print(f"[{datetime.now()}] Failed to ingest {f['Key']}: {e}")
    print(f"[{datetime.now()}] Ingest complete")
