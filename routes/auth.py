from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import json
import os
import uuid
import jwt  # JWT for authentication
from datetime import datetime, timedelta
from typing import List
from pydantic import Field

auth_router = APIRouter()

# Ensure the paths are correctly referencing the root directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
USER_DATA_FILE = os.path.join(BASE_DIR, "users.json")
USER_PROFILE_DATA_FILE = os.path.join(BASE_DIR, "user_profile.json")

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = 30

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    user_id: str
    age: int = 0
    weekly_mileage: int = 0
    race_type: str = ""
    best_time: str = ""
    best_time_date: str = ""
    last_time: str = ""
    last_time_date: str = ""
    target_race: str = ""
    target_time: str = ""
    injury_history: List[str] = Field(default_factory=list)
    nutrition: List[str] = Field(default_factory=list)
    last_check_in: str = ""

def load_data(file_path):
    """Load data from a JSON file."""
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as file:
        return json.load(file)

def save_data(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def create_jwt_token(user_id: str):
    """Generate a JWT token for authentication."""
    expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
    payload = {"sub": user_id, "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str):
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_id(authorization: str = Header(None)):
    """Extract user ID from JWT token in Authorization header."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    token = authorization.split("Bearer ")[1]
    return decode_jwt_token(token)

@auth_router.post("/register")
def register_user(user: UserRegister):
    users = load_data(USER_DATA_FILE)

    # Check if the email already exists
    for existing_user in users.values():
        if existing_user["email"] == user.email:
            return {"message": "User already exists", "user_id": existing_user["id"]}

    user_id = str(uuid.uuid4())
    users[user_id] = {
        "id": user_id,
        "name": user.name,
        "email": user.email,
        "password": user.password,  # Note: Store hashed passwords in production
    }
    save_data(USER_DATA_FILE, users)

    # Create an associated user profile with default values
    user_profiles = load_data(USER_PROFILE_DATA_FILE)
    user_profiles[user_id] = UserProfile(user_id=user_id).dict()
    save_data(USER_PROFILE_DATA_FILE, user_profiles)

    return {"message": "User registered successfully", "user_id": user_id}

@auth_router.post("/login")
def login(user: UserLogin):
    users = load_data(USER_DATA_FILE)

    # Find user by email
    for user_id, user_data in users.items():
        if user_data["email"] == user.email and user_data["password"] == user.password:
            token = create_jwt_token(user_id)
            return {"access_token": token, "token_type": "Bearer"}

    raise HTTPException(status_code=401, detail="Invalid credentials")

@auth_router.get("/me")
def get_user_details(current_user_id: str = Depends(get_current_user_id)):
    users = load_data(USER_DATA_FILE)
    user = users.get(current_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": user["email"], "name": user["name"]}
