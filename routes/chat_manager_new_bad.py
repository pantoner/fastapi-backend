from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
import json
import sys
import os
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response
from faiss_helper import search_faiss
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from routes.openai_helpers import query_openai_model
from routes.auth import get_current_user_id


router = APIRouter()

CHAT_HISTORY_FILE = "chat_history.json"
USER_PROFILE_FILE = "user_profile.json"

class ChatInput(BaseModel):
    message: str

def get_welcome_message():
    """Get a simple welcome message for users."""
    return "Hi there! I'm your running coach. How can I help you today?"

@router.get("/chat/start")
async def start_chat():
    """Start a new chat session with a welcome message."""
    return {
        "message": get_welcome_message(),
        "profile_complete": True
    }

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
        save_chat_history(history)
    return history[-10:]

def save_chat_history(history):
    """Save chat history to chat_history.json."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def load_user_profile(user_id):
    """Load a specific user's profile from JSON file."""
    if not os.path.exists(USER_PROFILE_FILE):
        raise HTTPException(status_code=404, detail="User profile not found.")
    with open(USER_PROFILE_FILE, "r") as f:
        profiles = json.load(f)
    user_profile = profiles.get(user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="User profile not found.")
    return user_profile

# Import the OpenAI query function from main.py - this is a reference
# This should actually be imported from wherever it's defined
# def query_openai_model(prompt):
#     """Reference to the function that should be imported from main.py."""
#     # This function should be imported from main.py or defined here
#     # For now, we'll use get_llm_response as a placeholder
#     return get_llm_response(prompt)

@router.post("/chat")
async def chat_with_ai(chat_input: ChatInput, current_user_id: str = Depends(get_current_user_id)):
    """
    Process user input with comprehensive prompt including user profile.
    """
    user_message = chat_input.message.strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Load user profile for current user only
    user_profile = load_user_profile(current_user_id)
    profile_text = json.dumps(user_profile, indent=2)
    
    # Process message
    corrected_message = correct_spelling(user_message)
    mood = detect_user_mood(corrected_message)
    
    # Format chat history
    chat_history = load_chat_history()
    formatted_history = "\n".join(
        [f"You: {entry['user']}\nGPT: {entry['bot']}" for entry in chat_history]
    )
    
    # Retrieve relevant knowledge from FAISS
    retrieved_contexts = search_faiss(corrected_message, top_k=3)
    retrieved_text = "\n".join(retrieved_contexts) if retrieved_contexts else "No relevant data found."
    
    # Construct comprehensive prompt
    full_prompt = (
        "**ROLE & OBJECTIVE:**\n"
        "You are a **collaborative running coach** who provides **brief, engaging responses**. "
        "You **MUST keep answers under 50 words** and **ALWAYS end with a follow-up question**. "
        "DO NOT give lists or detailed breakdowns. Instead, ask the user about their preferences.\n\n"
        
        f"**USER PROFILE:**\n{profile_text}\n\n"
        
        "**EXAMPLES FROM TRAINING DATA:**\n"
        f"{retrieved_text}\n\n"
        
        f"**CURRENT USER MESSAGE:**\n{corrected_message}\n\n"
        
        "**COACH RESPONSE:**\n"
        "You MUST keep your response **under 50 words** and **always ask a follow-up question to ask if the runner feels good with the recommendation**."
    )
    
    # Generate AI response using the comprehensive prompt
    ai_response = query_openai_model(full_prompt)
    
    # Save chat history
    chat_history.append({"user": user_message, "bot": ai_response})
    save_chat_history(chat_history)
    
    return {"response": ai_response, "history": chat_history}