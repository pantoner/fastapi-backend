import os
import json
import hashlib
import datetime

# ✅ Define Local Storage Path
LOCAL_STORAGE_DIR = "logs"

# ✅ Ensure the local storage directory exists
if not os.path.exists(LOCAL_STORAGE_DIR):
    os.makedirs(LOCAL_STORAGE_DIR)

def generate_hash(user_input, timestamp):
    """Generate a SHA-256 hash filename based on user input + timestamp."""
    if not user_input or not timestamp:
        raise ValueError("❌ ERROR: 'user_input' and 'timestamp' must not be empty.")

    hash_object = hashlib.sha256(f"{user_input}{timestamp}".encode())
    return hash_object.hexdigest()[:16]  # Use the first 16 characters for compactness

def save_to_local(filename, data):
    """Save JSON data locally instead of AWS S3."""
    if not filename:
        raise ValueError("❌ ERROR: Filename cannot be empty.")
    if not isinstance(data, dict):
        raise TypeError("❌ ERROR: Data must be a dictionary.")

    json_data = json.dumps(data, indent=4)
    local_file_path = os.path.join(LOCAL_STORAGE_DIR, f"{filename}.json")

    try:
        # ✅ Save JSON file locally
        with open(local_file_path, "w", encoding="utf-8") as file:
            file.write(json_data)

        print(f"✅ Log saved locally: {local_file_path}")
        return local_file_path  # ✅ Return local file path for tracking

    except Exception as e:
        raise RuntimeError(f"❌ ERROR: Failed to save log locally: {e}")

# ✅ Example Usage
if __name__ == "__main__":
    test_input = "Hello, Local Storage!"
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()

    filename = generate_hash(test_input, timestamp)
    log_data = {
        "timestamp": timestamp,
        "message": test_input
    }

    save_to_local(filename, log_data)
