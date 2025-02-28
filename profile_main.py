from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import json
import os
from dotenv import load_dotenv
import requests

# ✅ Initialize FastAPI App
app = FastAPI()

# ✅ Enable CORS for frontend communication (same as `main.py`)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load environment variables
if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OpenAI API key is missing!")

openai.api_key = OPENAI_API_KEY

# ✅ Paths to JSON Files
USER_PROFILE_FILE = "user_profile.json"

# ✅ Pydantic Models
class ProfileChatRequest(BaseModel):
    message: str
    email: str

# ✅ Function to Load or Create User Profile
def load_user_profile(email: str):
    """Load or create a user's profile in `user_profile.json`."""
    if not os.path.exists(USER_PROFILE_FILE):
        with open(USER_PROFILE_FILE, "w") as f:
            json.dump({}, f)

    with open(USER_PROFILE_FILE, "r") as f:
        profiles = json.load(f)

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
    """Save updated profiles to `user_profile.json`."""
    with open(USER_PROFILE_FILE, "w") as f:
        json.dump(profiles, f, indent=2)

# ✅ Query OpenAI API for Profile Setup
def query_openai_model(prompt):
    """Send a user message to OpenAI for profile setup assistance."""
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are an AI assistant designed to help users complete their running profile. "
                                              "Ask for missing information, confirm existing details, and guide them step by step. "
                                              "Your responses must be under 50 words and always end with a follow-up question."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50
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

# ✅ API Route: Profile Chat
@app.post("/profile-chat")
async def profile_chat(request: ProfileChatRequest):
    """Dedicated route for guiding the user through profile completion."""
    profile_data = load_user_profile(request.email)

    # ✅ Construct profile-based prompt
    full_prompt = f"""
    **USER PROFILE DETAILS:**
    {json.dumps(profile_data, indent=2)}

    **USER MESSAGE:**
    {request.message}

    **TASK:**
    1. Identify missing fields in the user's profile.
    2. Ask a relevant question to collect missing data.
    3. If the profile is complete, ask about training goals.
    """

    response = query_openai_model(full_prompt)

    return {
        "assistant_response": response,
        "profile_data": profile_data
    }

# ✅ Start FastAPI Server
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Profile Setup Server on http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
