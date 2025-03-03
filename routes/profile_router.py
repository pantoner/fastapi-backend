from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from db import get_user_profile, save_user_profile, get_user_by_email
from main import ChatRequest

# Import authentication functions from auth_router
from .auth import get_current_user

class ChatRequest(BaseModel):
    message: str

profile_router = APIRouter()

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    weekly_mileage: Optional[int] = None
    race_type: Optional[str] = None
    best_time: Optional[str] = None
    best_time_date: Optional[date] = None
    last_time: Optional[str] = None
    last_time_date: Optional[date] = None
    target_race: Optional[str] = None
    target_time: Optional[str] = None
    injury_history: Optional[List[str]] = None
    nutrition: Optional[List[str]] = None
    last_check_in: Optional[date] = None

@profile_router.get("/profile")
def get_profile(current_user: str = Depends(get_current_user)):
    """Get the current user's profile."""
    # Get user ID from email
    user = get_user_by_email(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the user's profile
    profile = get_user_profile(user['id'])
    if not profile:
        # Return a basic profile if none exists
        return {
            "email": current_user,
            "name": user.get('name', ''),
            "injury_history": [],
            "nutrition": []
        }
    
    return profile

@profile_router.put("/profile")
def update_profile(profile_data: UserProfileUpdate, current_user: str = Depends(get_current_user)):
    """Update the current user's profile."""
    # Get user ID from email
    user = get_user_by_email(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert model to dict, excluding None values
    profile_dict = {k: v for k, v in profile_data.dict().items() if v is not None}
    
    # Save the profile
    success = save_user_profile(user['id'], profile_dict)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    # Get the updated profile
    updated_profile = get_user_profile(user['id'])
    return updated_profile

@profile_router.post("/profile-chat")
async def profile_chat(request: ChatRequest, current_user: str = Depends(get_current_user)):
    """
    Dedicated route for guiding the user through profile completion.
    The model is strictly limited to the known profile fields and asked to confirm or update them.
    """
    # Get user ID from email
    user = get_user_by_email(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the user's profile from the database
    profile_data = get_user_profile(user['id'])
    if not profile_data:
        profile_data = {
            "email": current_user,
            "name": user.get('name', ''),
            "injury_history": [],
            "nutrition": []
        }
    
    # Enumerate the valid fields in the user profile
    system_prompt = """
    You have access to a user profile with these fields only:
    - name
    - age
    - weekly_mileage
    - race_type
    - best_time
    - best_time_date
    - last_time
    - last_time_date
    - target_race
    - target_time
    - injury_history (list)
    - nutrition (list)
    - last_check_in

    Your goal is to confirm or update these fields by asking the user if the values in the profile are still accurate.
    If a field is missing or changed, ask the user for the correct information.
    Do not introduce new fields or topics outside this profile.
    Always keep your responses under 50 words and end with a follow-up question.
    """

    # Construct the final prompt, embedding the system prompt plus user profile and message
    full_prompt = f"""
    {system_prompt}

    **USER PROFILE DETAILS:**
    {json.dumps(profile_data, indent=2)}

    **USER MESSAGE:**
    {request.message}

    **TASK:**
    1. Identify missing or outdated fields in the user's profile.
    2. Ask short questions to confirm or update them.
    3. If the profile is complete, ask about training goals.
    """

    # You'll need to import the query_openai_model function or define it here
    response = query_openai_model(full_prompt)

    return {
        "assistant_response": response,
        "profile_data": profile_data
    }