import json
import os

# Define the JSON file path
USER_DATA_FILE = "users.json"

# Sample user data
test_user = {
    "name": "testuser",
    "email": "test@example.com",
    "password": "plaintextpassword"  # Stored as plain text for now
}

def load_users():
    """Load user data from JSON file."""
    if not os.path.exists(USER_DATA_FILE):
        return []
    
    with open(USER_DATA_FILE, "r") as file:
        return json.load(file)

def save_users(users):
    """Save user data to JSON file."""
    with open(USER_DATA_FILE, "w") as file:
        json.dump(users, file, indent=4)

def seed_user():
    users = load_users()
    
    # Check if the user already exists
    for user in users:
        if user["name"] == test_user["name"]:
            print("Test user already exists.")
            return
    
    # Add new user
    users.append(test_user)
    save_users(users)
    print("Test user added successfully.")

if __name__ == "__main__":
    seed_user()
