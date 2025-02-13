from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import auth_router  # ✅ Import authentication routes
import requests
from pydantic import BaseModel

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change later for security)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ✅ Include authentication routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# ✅ Google Gemini API Configuration
GEMINI_API_KEY = "AIzaSyAOdIo9PawJQ_XbiRn6BvS1HXJnVogVpl0"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# ✅ Define Pydantic Model for Chat Request
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_with_gpt(chat_request: ChatRequest):
    """Send user input to Google Gemini API and return response."""
    payload = {
        "contents": [{
            "parts": [{"text": chat_request.message}]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error communicating with Google Gemini API")

    response_data = response.json()
    
    # Extracting AI response from the API response
    gpt_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    return {"response": gpt_response}

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
