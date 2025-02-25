import json
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from routes.auth import get_current_user_id  # Import from correct module path
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response

router = APIRouter()

CHAT_HISTORY_FILE = "chat_history.json"
USER_PROFILE_DATA_FILE = "user_profile.json"

class ChatInput(BaseModel):
    message: str

class UserNameInput(BaseModel):
    name: str

class ProfileUpdateInput(BaseModel):
    field_name: str
    field_value: Optional[str] = None
    field_value_int: Optional[int] = None
    field_value_list: Optional[List[str]] = None

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
        save_chat_history(history)  # Reset chat history if it's corrupted
    
    return history[-10:]  # Keep only the last 10 messages

def save_chat_history(history):
    """Save chat history to chat_history.json."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def load_user_profile(user_id: str):
    """Load user profile data with error handling."""
    try:
        if not os.path.exists(USER_PROFILE_DATA_FILE):
            return create_empty_profile(user_id)
        
        with open(USER_PROFILE_DATA_FILE, "r") as file:
            profiles = json.load(file)
        
        # If user profile doesn't exist, create a new one with default values
        if user_id not in profiles:
            return create_empty_profile(user_id)
        
        return profiles[user_id]
    except Exception as e:
        print(f"Error loading user profile: {str(e)}")
        return create_empty_profile(user_id)

def create_empty_profile(user_id: str):
    """Create an empty profile structure with default values."""
    return {
        "user_id": user_id,
        "name": "",
        "age": 0,
        "weekly_mileage": 0,
        "race_type": "",
        "best_time": "",
        "best_time_date": "",
        "last_time": "",
        "last_time_date": "",
        "target_race": "",
        "target_time": "",
        "injury_history": [],
        "nutrition": [],
        "last_check_in": ""
    }

def save_user_profile(user_id: str, updated_profile: dict):
    """Save user profile data."""
    try:
        if not os.path.exists(USER_PROFILE_DATA_FILE):
            profiles = {}
        else:
            with open(USER_PROFILE_DATA_FILE, "r") as file:
                profiles = json.load(file)
        
        # If this is a completely new profile being saved
        if user_id not in profiles:
            # Ensure all fields are present
            empty_profile = create_empty_profile(user_id)
            
            # Update with provided values
            for key, value in updated_profile.items():
                if key in empty_profile:
                    empty_profile[key] = value
            
            profiles[user_id] = empty_profile
        else:
            # If the profile exists, update with new values
            for key, value in updated_profile.items():
                profiles[user_id][key] = value
        
        with open(USER_PROFILE_DATA_FILE, "w") as file:
            json.dump(profiles, file, indent=4)
    except Exception as e:
        print(f"Error saving user profile: {str(e)}")

def get_next_empty_profile_field(profile: dict):
    """
    Determine the next empty field in the user profile.
    Returns tuple (field_name, prompt_message) or (None, None) if all fields are filled.
    """
    field_prompts = {
        "name": "What's your name?",
        "age": "How old are you?",
        "weekly_mileage": "How many miles do you run per week?",
        "race_type": "What type of races do you usually run (e.g., marathon, 5K)?",
        "best_time": "What's your best race time?",
        "best_time_date": "When did you achieve your best time (YYYY-MM-DD)?",
        "last_time": "What was your most recent race time?",
        "last_time_date": "When was your most recent race (YYYY-MM-DD)?",
        "target_race": "Do you have a target race coming up?",
        "target_time": "What's your target time for your next race?",
        "injury_history": "Do you have any injury history? (Respond with 'none' if not)",
        "nutrition": "Any specific nutrition practices or diet? (Respond with 'none' if not)"
    }
    
    for field, prompt in field_prompts.items():
        # For string fields
        if field in ["name", "race_type", "best_time", "best_time_date", "last_time", 
                   "last_time_date", "target_race", "target_time"] and not profile[field]:
            return field, prompt
        
        # For numeric fields
        if field in ["age", "weekly_mileage"] and profile[field] == 0:
            return field, prompt
        
        # For list fields
        if field in ["injury_history", "nutrition"] and not profile[field]:
            return field, prompt
    
    return None, None

@router.get("/chat/start")
def start_chat(current_user_id: str = Depends(get_current_user_id)):
    """
    Start a new chat session and check if the user profile is populated.
    """
    user_profile = load_user_profile(current_user_id)
    
    # Check if name is already set
    if user_profile["name"]:
        # Check if there are other empty fields to fill
        next_field, prompt = get_next_empty_profile_field(user_profile)
        
        if next_field:
            return {
                "message": f"Hello {user_profile['name']}, I see we still need some information for your profile. {prompt}",
                "next_field": next_field
            }
        else:
            return {
                "message": f"Hello {user_profile['name']}, how are you today? How can I help you with your running?",
                "profile_complete": True
            }
    else:
        # No name set yet
        return {
            "message": "Hello, thanks for logging in. Let me get to know you so that I can provide better help. What's your name?",
            "next_field": "name"
        }

@router.post("/chat/set_name")
def set_user_name(user_input: UserNameInput, current_user_id: str = Depends(get_current_user_id)):
    """
    Store the user's name and confirm it.
    """
    user_profile = load_user_profile(current_user_id)
    
    name = user_input.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid name provided.")
    
    user_profile["name"] = name
    save_user_profile(current_user_id, user_profile)
    
    # Get next empty field
    next_field, prompt = get_next_empty_profile_field(user_profile)
    
    if next_field:
        return {
            "message": f"Nice to meet you, {name}! Let's fill out your profile. {prompt}",
            "next_field": next_field
        }
    else:
        return {
            "message": f"Nice to meet you, {name}! Your profile is complete. How can I help you with your running?",
            "profile_complete": True
        }

@router.post("/chat/update_profile")
def update_profile_field(
    update: ProfileUpdateInput, 
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Update a specific field in the user profile.
    """
    user_profile = load_user_profile(current_user_id)
    field_name = update.field_name
    
    # Handle different field types appropriately
    if field_name in ["age", "weekly_mileage"] and update.field_value_int is not None:
        user_profile[field_name] = update.field_value_int
    elif field_name in ["injury_history", "nutrition"] and update.field_value_list is not None:
        user_profile[field_name] = update.field_value_list
    elif update.field_value is not None:
        # For string fields
        user_profile[field_name] = update.field_value.strip()
    else:
        raise HTTPException(status_code=400, detail="Invalid field value provided.")
    
    save_user_profile(current_user_id, user_profile)
    
    # Get next empty field
    next_field, prompt = get_next_empty_profile_field(user_profile)
    
    if next_field:
        return {
            "message": f"Thanks! {prompt}",
            "next_field": next_field
        }
    else:
        return {
            "message": "Great! Your profile is now complete. How can I help you with your running?",
            "profile_complete": True
        }

@router.post("/chat")
async def chat_with_ai(chat_input: ChatInput, current_user_id: str = Depends(get_current_user_id)):
    """
    Process user input, apply AI corrections, and return an AI-generated response.
    """
    user_message = chat_input.message.strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Load user profile to personalize responses
    user_profile = load_user_profile(current_user_id)
    
    # Apply AI functions
    corrected_message = correct_spelling(user_message)
    mood = detect_user_mood(corrected_message)
    
    # Generate AI response
    ai_response = get_llm_response(corrected_message)
    
    # Add personalization if name is available
    if user_profile["name"] and "Hello" in ai_response:
        ai_response = ai_response.replace("Hello", f"Hello {user_profile['name']}")
    
    # Load and update chat history
    chat_history = load_chat_history()
    chat_history.append({"user": user_message, "bot": ai_response})
    save_chat_history(chat_history)
    
    return {"response": ai_response, "history": chat_history}

@router.get("/profile")
def get_profile(current_user_id: str = Depends(get_current_user_id)):
    """
    Get the user's complete profile.
    """
    user_profile = load_user_profile(current_user_id)
    return user_profile