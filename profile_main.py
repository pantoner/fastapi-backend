from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import json
import os
from dotenv import load_dotenv
import requests

# --------------------------------------------------
# ✅ ENVIRONMENT & APP SETUP
# --------------------------------------------------
app = FastAPI()

if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OpenAI API key is missing!")

openai.api_key = OPENAI_API_KEY

# --------------------------------------------------
# ✅ PATHS & MODELS
# --------------------------------------------------
USER_PROFILE_FILE = "user_profile.json"

class ProfileChatRequest(BaseModel):
    message: str
    email: str

# --------------------------------------------------
# ✅ HELPER FUNCTIONS
# --------------------------------------------------

def load_user_profile(email: str):
    """
    Load or create a user's profile based on their email.
    If the user doesn't exist in user_profile.json, create a blank profile.
    """
    if not os.path.exists(USER_PROFILE_FILE):
        # Create a blank JSON structure if file doesn't exist
        with open(USER_PROFILE_FILE, "w") as f:
            json.dump({}, f)

    with open(USER_PROFILE_FILE, "r") as f:
        profiles = json.load(f)

    # If user doesn't have a profile yet, create an empty one
    if email not in profiles:
        profiles[email] = {
            "email": email,
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
            "injury_history": [""],
            "nutrition": [""],
            "last_check_in": ""
        }
        save_user_profile(profiles)

    return profiles[email]

def save_user_profile(profiles):
    """Save updated profiles to user_profile.json."""
    with open(USER_PROFILE_FILE, "w") as f:
        json.dump(profiles, f, indent=2)

def query_openai_model_system(role_prompt: str, user_message: str):
    """
    Helper for specialized system instructions that differ from your main chat logic.
    """
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": role_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 150
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"❌ OpenAI API Error: {response.status_code} - {response.text}")
            return "Error: Unable to get response."
    except Exception as e:
        print(f"❌ Exception in OpenAI API call: {str(e)}")
        return "Error: Unable to get response."

# --------------------------------------------------
# ✅ ROUTES
# --------------------------------------------------

@app.post("/profile-chat")
def profile_chat(request: ProfileChatRequest):
    """
    A specialized endpoint for guiding the user to fill out their profile.
    Uses a distinct system role prompt to ask about user details (e.g. name, age).
    """

    # 1. Load or create the user's existing profile
    profile_data = load_user_profile(request.email)

    # 2. Define a specialized system prompt for collecting user profile data
    system_prompt = (
        "You are a friendly assistant dedicated to gathering user profile details for a running coach. "
        "Your job is to ask targeted questions to fill out the user's profile: name, age, weekly mileage, "
        "target race, best times, injury history, etc. Keep responses short (under 50 words) and always end "
        "with a follow-up question about the user's info. Avoid giving coaching advice; only gather data."
    )

    # 3. Call OpenAI with the user’s message
    openai_response = query_openai_model_system(system_prompt, request.message)

    # 4. Return the assistant's response
    return {
        "assistant_response": openai_response,
        "profile_data": profile_data
    }

# --------------------------------------------------
# ✅ RUN THE SERVER
# --------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Profile Setup Server on http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
