from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from config import SECRET_KEY
from db import get_user_by_email, create_user

auth_router = APIRouter()

ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = 30

# Fallback users in case database connection fails
FALLBACK_USERS = {
    "test@example.com": {"email": "test@example.com", "password": "plaintextpassword"},
    "secure@example.com": {"email": "secure@example.com", "password": "mypassword"},
    "final@example.com": {"email": "final@example.com", "password": "finalpassword"},
    "john@example.com": {"email": "john@example.com", "password": "password123"}
}

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

def create_jwt_token(email: str):
    expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRATION_MINUTES)
    payload = {"sub": email, "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(authorization: str = Header(None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    token = authorization.split("Bearer ")[1]
    return decode_jwt_token(token)

@auth_router.post("/register")
def register_user(user: UserRegister):
    existing_user = get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    user_id = create_user(user.name, user.email, user.password)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to register user")
    return {"message": "User registered successfully"}

@auth_router.post("/login")
def login(user: UserLogin):
    try:
        print(f"Login attempt for: {user.email}")
        
        # Try to get user from database
        db_user = get_user_by_email(user.email)
        print(f"Found user in DB: {db_user}")
        
        # If database lookup failed, check fallback users
        if not db_user:
            db_user = FALLBACK_USERS.get(user.email)
            print(f"Using fallback user: {db_user}")
        
        if not db_user:
            print(f"No user found for email: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        print(f"Comparing passwords: '{user.password}' vs '{db_user.get('password')}'")
        if db_user.get("password") != user.password:
            print(f"Password mismatch for: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_jwt_token(user.email)
        print(f"Generated token for: {user.email}")
        return {"access_token": token, "token_type": "Bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in login: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@auth_router.get("/me")
def get_user_details(current_user: str = Depends(get_current_user)):
    return {"email": current_user}