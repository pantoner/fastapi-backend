from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Google Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
GEMINI_API_KEY = "YOUR_API_KEY"  # Replace with your actual API key

# ✅ Chat Endpoint
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
