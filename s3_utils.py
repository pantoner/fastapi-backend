import os
import json
import hashlib
import boto3

# ✅ Load AWS Credentials from Environment Variables
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# ✅ Initialize S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def generate_hash(user_input, timestamp):
    """Generate a SHA-256 hash filename based on user input + timestamp."""
    hash_object = hashlib.sha256(f"{user_input}{timestamp}".encode())
    return hash_object.hexdigest()[:16]  # Use the first 16 characters for compactness

def save_to_s3(filename, data):
    """Save JSON data to AWS S3."""
    json_data = json.dumps(data, indent=4)
    s3_key = f"conversations/{filename}.json"

    # ✅ Upload JSON string to S3
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=json_data,
        ContentType="application/json"
    )

    print(f"✅ Log saved to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
    return s3_key  # ✅ Return S3 path for tracking
