from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import requests

chat_router = APIRouter()

# Google Gemini API Key
GEMINI_API_KEY = "AIzaSyAOdIo9PawJQ_XbiRn6BvS1HXJnVogVpl0"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

class ChatRequest(BaseModel):
    message: str

@chat_router.post("/chat")
def chat_with_gpt(chat_request: ChatRequest):
    """Send user input to Google Gemini and return response."""
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
    
    # Extracting the AI response from the API response
    gpt_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    return {"response": gpt_response}
