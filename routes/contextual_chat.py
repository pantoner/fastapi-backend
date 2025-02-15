from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response, load_chat_history, save_chat_history
import requests
import os

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

class ChatRequest(BaseModel):
    message: str

@router.post("/chat/contextual")
async def chat_with_context(chat_request: ChatRequest):
    """Chat with historical context included in the prompt."""
    chat_history = load_chat_history()
    corrected_message = correct_spelling(chat_request.message)

    # ✅ Format chat history for LLM
    formatted_history = "\n".join(
        [f"You: {entry['user']}\nGPT: {entry['bot']}" for entry in chat_history]
    )

    # ✅ Add the latest user message
    full_prompt = f"{formatted_history}\nYou: {chat_request.message}\nGPT:"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error communicating with Google Gemini API")

    response_data = response.json()
    gpt_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    # ✅ Save chat history
    chat_history.append({"user": chat_request.message, "bot": gpt_response})
    save_chat_history(chat_history)

    return {"response": gpt_response, "history": chat_history}
