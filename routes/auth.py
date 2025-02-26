from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import json
import os
import jwt  # JWT for authentication
from datetime import datetime, timedelta

auth_router = APIRouter()

USER_DATA_FILE = "users.json"
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

def create_jwt_token(email: str):
    """Generate a JWT token for authentication."""
    expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
    payload = {"sub": email, "exp": expiration}
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

def get_current_user(authorization: str = Header(None)):
    """Extract user from JWT token in Authorization header."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
    token = authorization.split("Bearer ")[1]
    return decode_jwt_token(token)

@auth_router.post("/register")
def register_user(user: UserRegister):
    users = load_users()

    for u in users:
        if u["email"] == user.email:
            raise HTTPException(status_code=400, detail="User already exists")

    new_user = user.dict()
    users.append(new_user)
    save_users(users)

    return {"message": "User registered successfully"}

@auth_router.post("/login")
def login(user: UserLogin):
    users = load_users()

    for u in users:
        if u["email"] == user.email and u["password"] == user.password:
            token = create_jwt_token(user.email)
            return {"access_token": token, "token_type": "Bearer"}

    raise HTTPException(status_code=401, detail="Invalid credentials")

@auth_router.get("/me")
def get_user_details(current_user: str = Depends(get_current_user)):
    return {"email": current_user}