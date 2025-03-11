# profile_main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import requests
import re

from dotenv import load_dotenv

# Import DB functions
from db import (
    get_user_by_email,
    create_user,
    get_user_profile,
    save_user_profile,
    create_default_profile
)

#############################################
# 1) Environment & OpenAI Config
#############################################
if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing!")
openai.api_key = OPENAI_API_KEY

#############################################
# 2) Microservice Endpoint
#############################################
CONVERSATION_MANAGER_URL = "https://profileprompt.onrender.com/manager/conversation-manager"

#############################################
# 3) FastAPI App
#############################################
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#############################################
# 4) In-Memory Conversation State
#############################################
# Key: user_id
# Value: dict with "pending_field": str or None
# Example: USER_STATE[5] = { "pending_field": "weekly_mileage" }
USER_STATE = {}

#############################################
# 5) Pydantic Model
#############################################
class ProfileChatRequest(BaseModel):
    message: str
    email: str

#############################################
# 6) Query OpenAI
#############################################
def query_openai_model(prompt: str) -> str:
    """Send the final prompt to OpenAI GPT-4 and return the model's short response."""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant designed to help users complete their running profile. "
                        "Ask for missing information, confirm existing details, and guide them step by step. "
                        "Your responses must be under 50 words and always end with a follow-up question."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50
        }
        resp = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"❌ OpenAI Error: {resp.status_code} - {resp.text}")
            return "Error: Unable to get response."
    except Exception as e:
        print(f"❌ Exception calling OpenAI: {str(e)}")
        return "Error: Unable to get response."

#############################################
# 7) Naive Parsers
#############################################
def parse_mileage(msg: str):
    """Extract first integer from message as weekly_mileage."""
    match = re.search(r"\d+", msg)
    return int(match.group(0)) if match else None

def parse_age(msg: str):
    """Extract first integer from message as age."""
    match = re.search(r"\d+", msg)
    return int(match.group(0)) if match else None

#############################################
# 8) /profile-chat Endpoint
#############################################
@app.post("/profile-chat")
def profile_chat(req: ProfileChatRequest):
    """
    1) Find or create a user by email.
    2) Get their DB profile.
    3) If we have a pending_field (from last time), parse the current message to fill that field -> update DB.
    4) Call manager with updated DB profile to see if profile is complete or which field is next.
    5) If complete, return short-circuit.
    6) Else, manager returns final_prompt -> we call OpenAI -> return model reply to user.
    """

    # 1) Look up user
    user = get_user_by_email(req.email)
    if not user:
        new_user_id = create_user(name="NewUser", email=req.email, password="temp123")
        if not new_user_id:
            return {"assistant_response": "Error creating user in DB."}
        create_default_profile(new_user_id)
        user = get_user_by_email(req.email)
    user_id = user["id"]

    # 2) DB Profile
    db_profile = get_user_profile(user_id)
    if not db_profile:
        create_default_profile(user_id)
        db_profile = get_user_profile(user_id)

    # -- Retrieve or init user state
    if user_id not in USER_STATE:
        USER_STATE[user_id] = {"pending_field": None}
    state = USER_STATE[user_id]

    # 3) If we have a pending_field, parse from current message, update DB
    pf = state["pending_field"]
    if pf == "weekly_mileage":
        miles = parse_mileage(req.message)
        if miles is not None:
            db_profile["weekly_mileage"] = miles
            save_user_profile(user_id, db_profile)
            state["pending_field"] = None
    elif pf == "age":
        years = parse_age(req.message)
        if years is not None:
            db_profile["age"] = years
            save_user_profile(user_id, db_profile)
            state["pending_field"] = None

    USER_STATE[user_id] = state  # save updated state

    # 4) Call conversation manager with updated profile
    body = {
        "user_message": req.message,
        "profile_data": db_profile
    }
    try:
        manager_resp = requests.post(CONVERSATION_MANAGER_URL, json=body)
        if manager_resp.status_code != 200:
            return {
                "assistant_response": f"Error from manager: {manager_resp.text}",
                "profile_data": db_profile
            }
        manager_data = manager_resp.json()
    except Exception as e:
        return {
            "assistant_response": f"Could not contact manager: {str(e)}",
            "profile_data": db_profile
        }

    # 5) If profile is complete
    if manager_data.get("profile_complete"):
        return {
            "assistant_response": "Profile is complete!",
            "profile_data": db_profile
        }

    final_prompt = manager_data.get("final_prompt", "")
    updated_profile = manager_data.get("profile_data", db_profile)

    # The manager might indicate the next missing field in the final_prompt
    # We'll do naive detection:
    if "weekly mileage" in final_prompt.lower():
        state["pending_field"] = "weekly_mileage"
    elif "age" in final_prompt.lower():
        state["pending_field"] = "age"
    else:
        state["pending_field"] = None

    USER_STATE[user_id] = state

    # 6) Call OpenAI with final_prompt
    openai_reply = query_openai_model(final_prompt)

    return {
        "assistant_response": openai_reply,
        "profile_data": updated_profile
    }

#############################################
# Run Locally
#############################################
if __name__ == "__main__":
    import uvicorn
    print("Starting Profile Chat Server on 0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
