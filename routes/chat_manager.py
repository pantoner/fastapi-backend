import json
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response  # ✅ Keep AI functionality

router = APIRouter()

CHAT_HISTORY_FILE = "chat_history.json"

# Add this function
def get_welcome_message():
    """Get a simple welcome message for users."""
    return "Hi there! I'm your running coach. How can I help you today?"

# Change @app.get to @router.get
@router.get("/chat/start")
async def start_chat():
    """Start a new chat session with a welcome message."""
    return {
        "message": "Hi there! I'm your running coach. How can I help you today?",
        "profile_complete": True
    }

class ChatInput(BaseModel):
    message: str

def load_chat_history():
    """Load the last 10 chat messages or create an empty file if missing."""
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump([], f)
        return []
    
    try:
        with open(CHAT_HISTORY_FILE, "r") as f:
            history = json.load(f)
    except json.JSONDecodeError:
        history = []
        save_chat_history(history)  # ✅ Reset chat history if it's corrupted

    return history[-10:]  # ✅ Keep only the last 10 messages

def save_chat_history(history):
    """Save chat history to chat_history.json."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

@router.post("/chat")
async def chat_with_ai(chat_input: ChatInput):
    """
    Process user input, apply AI corrections, and return an AI-generated response.
    """
    user_message = chat_input.message.strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # ✅ Apply AI functions
    corrected_message = correct_spelling(user_message)
    mood = detect_user_mood(corrected_message)
    
    # ✅ Generate AI response
    ai_response = get_llm_response(corrected_message)

    # ✅ Load and update chat history
    chat_history = load_chat_history()
    chat_history.append({"user": user_message, "bot": ai_response})
    save_chat_history(chat_history)

    return {"response": ai_response, "history": chat_history}
