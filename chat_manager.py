import json
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from routes.auth import get_current_user_id
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response

router = APIRouter()

# Use user-specific chat history files
CHAT_HISTORY_DIR = "chat_histories"
USER_PROFILE_DATA_FILE = "user_profile.json"

# Create chat history directory if it doesn't exist
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

class ChatInput(BaseModel):
    message: str

class UserNameInput(BaseModel):
    name: str

class ProfileUpdateInput(BaseModel):
    field_name: str
    field_value: Optional[str] = None
    field_value_int: Optional[int] = None
    field_value_list: Optional[List[str]] = None

def get_chat_history_path(user_id: str):
    """Get user-specific chat history file path."""
    return os.path.join(CHAT_HISTORY_DIR, f"{user_id}_history.json")

def load_chat_history(user_id: str):
    """Load chat history for a specific user."""
    file_path = get_chat_history_path(user_id)
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)
        return []
    
    try:
        with open(file_path, "r") as f:
            history = json.load(f)
    except json.JSONDecodeError:
        history = []
        save_chat_history(user_id, history)
    
    return history[-10:]

def save_chat_history(user_id: str, history):
    """Save chat history for a specific user."""
    file_path = get_chat_history_path(user_id)
    with open(file_path, "w") as f:
        json.dump(history, f, indent=4)

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

def load_user_profile(user_id: str):
    """Load user profile data."""
    try:
        if not os.path.exists(USER_PROFILE_DATA_FILE):
            # No profiles file exists yet
            empty_profile = create_empty_profile(user_id)
            
            # Create the file with this user
            profiles = {user_id: empty_profile}
            with open(USER_PROFILE_DATA_FILE, "w") as file:
                json.dump(profiles, file, indent=4)
                
            return empty_profile
        
        with open(USER_PROFILE_DATA_FILE, "r") as file:
            profiles = json.load(file)
        
        if user_id not in profiles:
            # User doesn't exist in profiles yet
            empty_profile = create_empty_profile(user_id)
            
            # Add this user to profiles
            profiles[user_id] = empty_profile
            with open(USER_PROFILE_DATA_FILE, "w") as file:
                json.dump(profiles, file, indent=4)
                
            return empty_profile
        
        # User exists in profiles
        return profiles[user_id]
        
    except Exception as e:
        print(f"Error loading user profile: {str(e)}")
        return create_empty_profile(user_id)

def save_user_profile(user_id: str, updated_profile: dict):
    """Save user profile data."""
    try:
        if not os.path.exists(USER_PROFILE_DATA_FILE):
            profiles = {}
        else:
            with open(USER_PROFILE_DATA_FILE, "r") as file:
                profiles = json.load(file)
        
        # Ensure all required fields exist
        if user_id not in profiles:
            base_profile = create_empty_profile(user_id)
            for key, value in updated_profile.items():
                if key in base_profile:
                    base_profile[key] = value
            profiles[user_id] = base_profile
        else:
            # Update existing profile
            for key, value in updated_profile.items():
                profiles[user_id][key] = value
        
        with open(USER_PROFILE_DATA_FILE, "w") as file:
            json.dump(profiles, file, indent=4)
            
    except Exception as e:
        print(f"Error saving user profile: {str(e)}")

def is_profile_complete(profile: dict):
    """Check if all required fields in the profile are filled."""
    # String fields
    string_fields = ["name", "race_type", "best_time", "best_time_date", 
                    "last_time", "last_time_date", "target_race", "target_time"]
    for field in string_fields:
        if not profile.get(field, "").strip():
            return False
    
    # Numeric fields
    numeric_fields = ["age", "weekly_mileage"]
    for field in numeric_fields:
        if profile.get(field, 0) == 0:
            return False
    
    # List fields
    list_fields = ["injury_history", "nutrition"]
    for field in list_fields:
        if not profile.get(field, []):
            return False
    
    return True

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
        # String fields
        if field in ["name", "race_type", "best_time", "best_time_date", "last_time", 
                   "last_time_date", "target_race", "target_time"] and not profile.get(field, "").strip():
            return field, prompt
        
        # Numeric fields
        if field in ["age", "weekly_mileage"] and profile.get(field, 0) == 0:
            return field, prompt
        
        # List fields
        if field in ["injury_history", "nutrition"] and not profile.get(field, []):
            return field, prompt
    
    return None, None

@router.get("/chat/start")
def start_chat(current_user_id: str = Depends(get_current_user_id)):
    """
    Start a new chat session and check if the user profile is populated.
    Handles all three scenarios appropriately.
    """
    user_profile = load_user_profile(current_user_id)
    
    # Check if profile is complete
    if is_profile_complete(user_profile):
        # Scenario 1: Complete profile
        return {
            "message": f"Hello {user_profile['name']}, how are you today? How can I help you with your running?",
            "profile_complete": True
        }
    
    # Scenario 2 & 3: Either empty existing profile or new profile
    # In both cases, we want to prompt for missing information
    next_field, prompt = get_next_empty_profile_field(user_profile)
    
    # Check if at least name is set
    if user_profile.get("name", "").strip():
        return {
            "message": f"Hello {user_profile['name']}, I see your profile isn't complete. {prompt}",
            "next_field": next_field
        }
    else:
        # Name is not set (first question)
        return {
            "message": "Hello, thanks for logging in. Let me get to know you so I can provide better help. What's your name?",
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
            "message": f"Nice to meet you, {name}! Let's complete your profile. {prompt}",
            "next_field": next_field
        }
    else:
        return {
            "message": f"Nice to meet you, {name}! Your profile is now complete. How can I help you with your running?",
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
        if field_name == "name" and not update.field_value.strip():
            raise HTTPException(status_code=400, detail="Name cannot be empty.")
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
    
    # Check if profile is incomplete - if so, route to profile completion
    if not is_profile_complete(user_profile):
        next_field, prompt = get_next_empty_profile_field(user_profile)
        
        # If no name set, interpret this message as the name
        if next_field == "name":
            user_profile["name"] = user_message
            save_user_profile(current_user_id, user_profile)
            
            next_field, prompt = get_next_empty_profile_field(user_profile)
            return {
                "response": f"Nice to meet you, {user_message}! Let's complete your profile. {prompt}",
                "next_field": next_field
            }
        else:
            # For other profile fields, remind user to complete profile first
            return {
                "response": f"Before we chat, let's complete your profile. {prompt}",
                "next_field": next_field
            }
    
    # Apply AI functions
    corrected_message = correct_spelling(user_message)
    mood = detect_user_mood(corrected_message)
    
    # Generate AI response
    ai_response = get_llm_response(corrected_message)
    
    # Add personalization if name is available
    if user_profile.get("name", "") and "Hello" in ai_response:
        ai_response = ai_response.replace("Hello", f"Hello {user_profile['name']}")
    
    # Load and update chat history - user specific
    chat_history = load_chat_history(current_user_id)
    chat_history.append({"user": user_message, "bot": ai_response})
    save_chat_history(current_user_id, chat_history)
    
    return {"response": ai_response, "history": chat_history}

@router.get("/profile")
def get_profile(current_user_id: str = Depends(get_current_user_id)):
    """
    Get the user's complete profile.
    """
    user_profile = load_user_profile(current_user_id)
    return user_profile

@router.get("/debug/profile_status")
def check_profile_status(current_user_id: str = Depends(get_current_user_id)):
    """
    Debugging endpoint to check profile status.
    """
    user_profile = load_user_profile(current_user_id)
    next_field, prompt = get_next_empty_profile_field(user_profile)
    
    return {
        "user_id": current_user_id,
        "profile": user_profile,
        "is_complete": is_profile_complete(user_profile),
        "next_empty_field": next_field,
        "next_prompt": prompt
    }