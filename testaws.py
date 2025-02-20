"""
test_s3_utils.py

A simple script to test generate_hash() and save_to_s3() functions.
Make sure your AWS credentials and S3 bucket name are set in the environment:
    - S3_BUCKET_NAME
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_REGION

Usage:
    python test_s3_utils.py
"""

import os
import json
import datetime
import boto3

# Import the functions you want to test
from s3_utils import generate_hash, save_to_s3

def main():
    # 1) Set AWS environment variables
    S3_BUCKET_NAME = "flan-t5-models"
    AWS_ACCESS_KEY_ID = "AKIAQOQKGIPU5QV62VVA"
    AWS_SECRET_ACCESS_KEY = "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"
    AWS_REGION = "us-east-1"

    # 2) Ensure no missing AWS credentials
    if not S3_BUCKET_NAME or not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not AWS_REGION:
        print("❌ ERROR: Missing one or more required AWS environment variables.")
        return

    # 3) Prepare test data
    test_input = "Hello, S3!"
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()  # ✅ Fixes deprecated utcnow()
    test_data = {
        "timestamp": timestamp,
        "message": test_input
    }

    # 4) Generate hash filename
    filename = generate_hash(user_input=test_input, timestamp=timestamp)
    print(f"🔍 Generated Filename: {filename}.json")
    print(f"🔍 S3_BUCKET_NAME: {S3_BUCKET_NAME}")
    print(f"🔍 AWS_ACCESS_KEY_ID: {AWS_ACCESS_KEY_ID}")
    print(f"🔍 AWS_SECRET_ACCESS_KEY: {'SET' if AWS_SECRET_ACCESS_KEY else 'MISSING'}")
    print(f"🔍 AWS_REGION: {AWS_REGION}")

    # 5) Upload test data to S3
    try:
        s3_key = save_to_s3(filename, test_data)
        print(f"✅ Successfully uploaded to: s3://{S3_BUCKET_NAME}/{s3_key}")
    except Exception as e:
        print(f"❌ Upload to S3 failed: {e}")
        return

    # 6) Download the object from S3 and verify contents
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        downloaded_data = json.loads(response["Body"].read())
    except Exception as e:
        print(f"❌ Error fetching file from S3: {e}")
        return

    # 7) Compare downloaded data with the original
    if downloaded_data == test_data:
        print("✅ File contents match the original data!")
    else:
        print("❌ File contents do NOT match the original data.")
        print("Original:", test_data)
        print("Downloaded:", downloaded_data)

if __name__ == "__main__":
    main()
