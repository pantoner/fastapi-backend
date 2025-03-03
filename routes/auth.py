from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import jwt
import duckdb
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
    conn = duckdb.connect(USER_DB_FILE)
    conn.execute("PRAGMA disable_checkpoint_on_shutdown;")  # Place it here
    result = conn.execute("SELECT email, password FROM users WHERE email = ?", [email]).fetchone()
    conn.close()
    return {"email": result[0], "password": result[1]} if result else None

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
    db_user = get_user_by_email(user.email)
    if not db_user or db_user["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt_token(user.email)
    return {"access_token": token, "token_type": "Bearer"}

@auth_router.get("/me")
def get_user_details(current_user: str = Depends(get_current_user)):
    return {"email": current_user}

@auth_router.on_event("startup")
async def startup_event():
    import requests
    from config import USER_DB_FILE

    url = "https://www.dropbox.com/scl/fi/pteg2bowzw4hm4yallflu/user_db.duckdb?rlkey=ih8a1p3eax714amnwkxazuczk&st=rym6vbdi&dl=1"
    
    response = requests.get(url)

    with open(USER_DB_FILE, 'wb') as f:
        f.write(response.content)

    print("✅ user_db.duckdb successfully downloaded and ready.")
