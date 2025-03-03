from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import jwt
from datetime import datetime, timedelta
from config import USER_DB_FILE, SECRET_KEY

auth_router = APIRouter()

ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = 30

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

def get_user_by_email(email: str):
    try:
        # Use read_only=True for queries to avoid locking issues
        conn = duckdb.connect(USER_DB_FILE, read_only=True)
        result = conn.execute("SELECT email, password FROM users WHERE email = ?", [email]).fetchone()
        conn.close()
        return {"email": result[0], "password": result[1]} if result else None
    except Exception as e:
        print(f"Database error in get_user_by_email: {str(e)}")
        return None

def create_user(name: str, email: str, password: str):
    conn = duckdb.connect(USER_DB_FILE)
    conn.execute(
        "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
        [name, email, password],
    )
    conn.close()

@auth_router.post("/register")
def register_user(user: UserRegister):
    existing_user = get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    create_user(user.name, user.email, user.password)
    return {"message": "User registered successfully"}

@auth_router.post("/login")
def login(user: UserLogin):
    try:
        print(f"Login attempt for: {user.email}")
        
        # Try to get user from database
        db_user = get_user_by_email(user.email)
        print(f"Found user in DB: {db_user}")
        
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

@auth_router.on_event("startup")
async def startup_event():
    import requests
    import os
    from config import USER_DB_FILE
    
    # Remove any existing WAL files
    if os.path.exists(f"{USER_DB_FILE}.wal"):
        os.remove(f"{USER_DB_FILE}.wal")
    
    # Only download if file doesn't exist or is empty
    if not os.path.exists(USER_DB_FILE) or os.path.getsize(USER_DB_FILE) == 0:
        url = "https://www.dropbox.com/scl/fi/pteg2bowzw4hm4yallflu/user_db.duckdb?rlkey=ih8a1p3eax714amnwkxazuczk&st=rym6vbdi&dl=1"
        
        try:
            response = requests.get(url)
            with open(USER_DB_FILE, 'wb') as f:
                f.write(response.content)
            print("✅ user_db.duckdb successfully downloaded.")
        except Exception as e:
            print(f"❌ Database download error: {str(e)}")
    
    # Verify database integrity
    try:
        conn = duckdb.connect(USER_DB_FILE, read_only=True)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        print("✅ Database connection verified.")
    except Exception as e:
        print(f"❌ Database verification error: {str(e)}")
        # Create new database if verification failed
        try:
            if os.path.exists(USER_DB_FILE):
                os.remove(USER_DB_FILE)
            conn = duckdb.connect(USER_DB_FILE)
            conn.execute("CREATE TABLE IF NOT EXISTS users (name VARCHAR, email VARCHAR PRIMARY KEY, password VARCHAR)")
            conn.execute("INSERT INTO users VALUES ('test@example.com', 'plaintextpassword')")
            conn.close()
            print("✅ Created new users database with test user.")
        except Exception as e2:
            print(f"❌ Failed to create new database: {str(e2)}")
