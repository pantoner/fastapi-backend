from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import json
import os
from dotenv import load_dotenv
import requests
from config import PROMPT_MICROSERVICE_URL

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

def find_missing_fields(profile):
    fields_order = [
        "name", "age", "weekly_mileage", "race_type",
        "best_time", "best_time_date", "last_time",
        "last_time_date", "target_race", "target_time",
        "injury_history", "nutrition", "last_check_in"
    ]
    missing = []
    for field in fields_order:
        val = profile.get(field)
        if not val or (isinstance(val, list) and not any(val)):
            missing.append(field)
    return missing

# ✅ API Route: Profile Chat
@app.post("/profile-chat")
async def profile_chat(request: ProfileChatRequest):
    # 1. Load or create user profile
    profile_data = load_user_profile(request.email)

    # 2. Check if profile is complete
    missing = find_missing_fields(profile_data)
    if not missing:
        # If no fields missing, maybe skip microservice or ask about goals
        return {
            "assistant_response": "Profile is complete! (demo).",
            "profile_data": profile_data
        }

    # For demonstration, pick first missing field
    next_field = missing[0]
    attempt = 0
    confirmation = False

    # 3. Build microservice body
    body_for_microservice = {
        "field": next_field,
        "attempt": attempt,
        "confirmation": confirmation,
        "last_message": request.message,
        "user_profile": json.dumps(profile_data),
        "chat_history": ""
    }

    # 4. Call the microservice
    try:
        mc_response = requests.post(
            PROMPT_MICROSERVICE_URL,
            json=body_for_microservice
        )
        if mc_response.status_code == 200:
            prompt_data = mc_response.json()
            final_prompt = prompt_data.get("prompt_text", "")
        else:
            final_prompt = f"[Microservice error: {mc_response.status_code} - {mc_response.text}]"
    except Exception as e:
        final_prompt = f"[Could not contact microservice: {str(e)}]"

    # 5. Send that prompt to OpenAI
    openai_response = query_openai_model(final_prompt)

    # 6. Return the LLM’s response
    return {
        "assistant_response": openai_response,
        "profile_data": profile_data
    }


# ✅ Start FastAPI Server
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Profile Setup Server on http://0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
