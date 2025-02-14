from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import os

app = FastAPI()

# ✅ Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change for security)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load GEMINI API Key from Environment Variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is missing!")

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

# ✅ Path to users.json file
USERS_FILE = "users.json"

# ✅ Pydantic Model for Login Request
class LoginRequest(BaseModel):
    email: str
    password: str

# ✅ Function to Load Users from JSON File
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

# ✅ API Route: Login Endpoint
@app.post("/auth/login")
async def login(request: LoginRequest):
    users = load_users()

    # ✅ Check if the email and password match
    for user in users:
        if user["email"] == request.email and user["password"] == request.password:
            return {"access_token": "mock-jwt-token", "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid email or password")

# ✅ API Route: Chat with Google Gemini API
@app.post("/chat")
async def chat_with_gpt(chat_request: dict):
    """Send user input to Google Gemini API and return response."""
    prompt = chat_request.get("message", "")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error communicating with Google Gemini API")

    response_data = response.json()

    # Extract AI response
    gpt_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    return {"response": gpt_response}
