############################
# profile_main.py
############################

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import requests
import json

from dotenv import load_dotenv

# DB functions from your db.py
from db import (
    get_user_by_email,
    create_user,
    get_user_profile,
    save_user_profile,
    create_default_profile
)

#############################################
# 1) Load Environment for OpenAI
#############################################
if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing!")
openai.api_key = OPENAI_API_KEY

#############################################
# 2) Conversation Manager Microservice
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
# 4) Pydantic Model
#############################################
class ProfileChatRequest(BaseModel):
    message: str
    email: str

#############################################
# 5) The LLM Parser: extract_run_info
#############################################
# We'll replicate the function inlined here. 
# This version uses openai.OpenAI(...) style if you prefer,
# or we can just do openai.ChatCompletion. We'll do the latter for simplicity:

def extract_run_info(text_input: str) -> dict:
    """
    Sends text_input to an LLM and attempts to parse:
      - number  => The first numeric value
      - racetype => {5k, 10k, half marathon, marathon}
      - dates   => any date
    Returns { "number": "", "racetype": "", "dates": "" }
    """

    system_prompt = (
        "You are a text parser. Find:\n"
        "1) The first numeric value => 'number'\n"
        "2) Race type => 'racetype'\n"
        "3) Date => 'dates'\n"
        "Return valid JSON EXACTLY {\"number\":\"\",\"racetype\":\"\",\"dates\":\"\"}\n"
        "No extra keys or explanation. If not found, keep them empty."
    )

    user_prompt = f"Extract from this text:\n{text_input}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,
            temperature=0
        )
        parsed_text = response["choices"][0]["message"]["content"].strip()

        try:
            result = json.loads(parsed_text)
        except json.JSONDecodeError:
            result = {"number": "", "racetype": "", "dates": ""}

        for k in ["number", "racetype", "dates"]:
            if k not in result:
                result[k] = ""
        return result

    except Exception as e:
        print(f"❌ LLM parse error: {e}")
        return {"number": "", "racetype": "", "dates": ""}


#############################################
# 6) query_openai_model for final prompt
#############################################
def query_openai_model(prompt: str) -> str:
    """
    If the conversation manager returns a 'final_prompt',
    we call this to produce a short response for the user.
    """
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4",  # or "gpt-3.5-turbo"
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
# 7) /profile-chat Endpoint
#############################################
from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

# You should already have these in your code:
#   - get_user_by_email(email) -> returns user dict or None
#   - get_user_profile(user_id) -> returns profile dict
#   - update_profile_field(user_id, field_name, field_value) -> updates either user_profiles or arrays
#   - extract_run_info(message) -> returns something like {"number": "10", "racetype": "5k", "dates": "2024-01-01"}
#   - query_openai_model(prompt) -> returns short assistant response
#   - CONVERSATION_MANAGER_URL -> your microservice endpoint

# The order in which the system needs fields:
FIELD_ORDER = [
    ("age", "ask_age"),
    ("weekly_mileage", "ask_weekly_mileage"),
    ("race_type", "ask_race_type"),
    ("best_time", "ask_best_time"),
    ("best_time_date", "ask_best_time_date"),
    ("last_time", "ask_last_time"),
    ("last_time_date", "ask_last_time_date"),
    ("target_race", "ask_target_race"),
    ("target_time", "ask_target_time"),
    ("injury_history", "ask_injury_history"),
    ("nutrition", "ask_nutrition")
]


def get_next_field_to_ask(profile: dict) -> str:
    """
    Returns the next field name from FIELD_ORDER that has not been set 
    (i.e., is None or empty in the profile). If all are filled, returns None.
    """
    for field_name, _prompt_key in FIELD_ORDER:
        value = profile.get(field_name, None)
        # Handle lists (injury_history, nutrition) as well as normal fields
        if isinstance(value, list):
            if not value:  # empty list => field not filled
                return field_name
        elif value is None or str(value).strip() == "":
            return field_name
    return None

def parse_value_for_field(field_name: str, parsed_data: dict) -> object:
    """
    Given the field_name we need, return the appropriate value 
    from parsed_data or None if we can't find it.
    
    For normal numeric fields, we might look at parsed_data["number"].
    For race_type, we might look at parsed_data["racetype"].
    For date fields, we might look at parsed_data["dates"].
    For injury_history/nutrition, we'd handle it if we had them in the parsed input.
    
    Adjust this logic as needed for your parsing approach.
    """
    if field_name == "age":
        # Expect parsed_data["number"]
        num_str = parsed_data.get("number")
        if num_str is None:
            return None
        try:
            return int(num_str)
        except ValueError:
            return None

    if field_name == "weekly_mileage":
        # Also from parsed_data["number"]
        num_str = parsed_data.get("number")
        if num_str is None:
            return None
        try:
            return int(num_str)
        except ValueError:
            return None

    if field_name == "race_type":
        # Expect parsed_data["racetype"]
        return parsed_data.get("racetype")

    if field_name in ["best_time_date", "last_time_date"]:
        # Expect parsed_data["dates"]
        return parsed_data.get("dates")

    if field_name in ["best_time", "last_time", "target_time"]:
        # This might be more complicated in real usage (HH:MM:SS parse).
        # For now, if "number" is present, store that, or any string if you'd prefer:
        return parsed_data.get("number")

    if field_name == "target_race":
        # This could come from parsed_data["racetype"] in some contexts, 
        # or from another field in the user's message.
        return parsed_data.get("racetype")

    if field_name in ["injury_history", "nutrition"]:
        # In real usage, you'd parse these from user message if available.
        # If not found, return None so we keep prompting.
        # If found, return a list of items:
        # Example placeholder: an array from "parsed_data.get('injuries')" or similar
        return None

    # If no match, return None
    return None


class ProfileChatRequest(BaseModel):
    message: str
    email: str


import requests

# Define the URL for the profile update service
PROFILE_UPDATE_URL = os.getenv("PROFILE_UPDATE_URL", "https://your-profile-update-service.onrender.com/profile-update")

@app.post("/profile-chat")
import requests

# Define the URL for the profile update service
PROFILE_UPDATE_URL = os.getenv("PROFILE_UPDATE_URL", "https://your-profile-update-service.onrender.com/profile-update")

# FIRST_CALL_DONE = False

# @app.post("/profile-chat")
# def profile_chat(req: ProfileChatRequest):
#     global FIRST_CALL_DONE

#     """
#     1) Retrieve user by email. If not found, return an error (no user creation).
#     2) Fetch user profile from DB.
#     3) Force-update weekly_mileage=70 for user_id=1 on first call (just to confirm logs).
#     4) Determine which field we need next by checking the user's profile 
#        in the order of FIELD_ORDER.
#     5) Parse the user's message with extract_run_info.
#     6) If the needed field can be extracted, call the microservice.
#     7) Re-check, then call conversation manager, etc.
#     """

#     # 1) Retrieve user
#     user = get_user_by_email(req.email)
#     if not user:
#         return {
#             "assistant_response": "❌ No user found. Please register first.",
#             "profile_data": {}
#         }

#     user_id = user["id"]

#     # 2) Fetch profile
#     db_profile = get_user_profile(user_id)
#     if not db_profile:
#         return {
#             "assistant_response": "❌ No user profile found. Please ensure the user has a profile.",
#             "profile_data": {}
#         }

#     # 3) Force an update to see if the microservice logs show up
#     if not FIRST_CALL_DONE:
#         print("🚀 Forcing an update to weekly_mileage=70 for user_id=1, to test the microservice call.")
#         try:
#             force_resp = requests.post(
#                 f"{PROFILE_UPDATE_URL}/update-field",
#                 json={
#                     "user_id": 1,
#                     "field_name": "weekly_mileage",
#                     "field_value": 70
#                 }
#             )
#             if force_resp.ok:
#                 print("✅ Force update succeeded!")
#             else:
#                 print(f"❌ Force update failed: {force_resp.text}")
#         except Exception as e:
#             print(f"❌ Exception during forced update: {str(e)}")

#         FIRST_CALL_DONE = True

#     # 4) Determine the next needed field
#     needed_field = get_next_field_to_ask(db_profile)
#     print(f"🔍 Next needed field is: {needed_field}")

#     # 5) Parse the user's message
#     parsed = extract_run_info(req.message)
#     print(f"🔍 Parsed from user message: {parsed}")

#     # 6) If there's a needed field, see if we can fill it from parsed data
#     if needed_field is not None:
#         new_value = parse_value_for_field(needed_field, parsed)
#         print(f"🔍 parse_value_for_field returned: {new_value}")
#         if new_value is not None:
#             # Update the field using the web service
#             try:
#                 update_response = requests.post(
#                     f"{PROFILE_UPDATE_URL}/update-field",
#                     json={
#                         "user_id": user_id,
#                         "field_name": needed_field,
#                         "field_value": new_value
#                     }
#                 )
                
#                 if not update_response.ok:
#                     print(f"❌ Error updating {needed_field} via web service: {update_response.text}")
#                 else:
#                     print(f"✅ Successfully updated {needed_field} to {new_value} via web service")
#             except Exception as e:
#                 print(f"❌ Error calling profile update service: {str(e)}")

#     # 7) Re-check updated profile
#     db_profile = get_user_profile(user_id)
#     needed_field = get_next_field_to_ask(db_profile)

#     # 8) Call conversation manager
#     body = {
#         "user_message": req.message,
#         "profile_data": db_profile
#     }
#     try:
#         manager_resp = requests.post(CONVERSATION_MANAGER_URL, json=body)
#         if manager_resp.status_code != 200:
#             return {
#                 "assistant_response": f"Error from manager: {manager_resp.text}",
#                 "profile_data": db_profile
#             }
#         manager_data = manager_resp.json()
#     except Exception as e:
#         return {
#             "assistant_response": f"Could not contact manager: {str(e)}",
#             "profile_data": db_profile
#         }

#     if manager_data.get("profile_complete"):
#         return {
#             "assistant_response": "Profile is complete!",
#             "profile_data": db_profile
#         }

#     # 9) Prompt the user again via the LLM
#     final_prompt = manager_data.get("final_prompt", "")
#     openai_reply = query_openai_model(final_prompt)

#     return {
#         "assistant_response": openai_reply,
#         "profile_data": db_profile
#     }

from fastapi import APIRouter
import requests

router = APIRouter()

PROFILE_UPDATE_URL = "https://your-profile-update-service.onrender.com"  # Adjust as needed

@router.post("/profile-chat")
def profile_chat():
    """
    A minimal route that ONLY calls the update-field microservice,
    setting weekly_mileage=70 for user_id=1. Returns success/failure info.
    """
    print("🚀 Forcing an update to weekly_mileage=70 for user_id=1, to test the microservice call.")

    # Attempt the forced update
    try:
        force_resp = requests.post(
            f"{PROFILE_UPDATE_URL}/update-field",
            json={
                "user_id": 1,
                "field_name": "weekly_mileage",
                "field_value": 70
            }
        )
        if force_resp.ok:
            print("✅ Force update succeeded!")
            return {"status": "success", "details": "Updated weekly_mileage to 70 for user_id=1"}
        else:
            error_msg = f"❌ Force update failed: {force_resp.text}"
            print(error_msg)
            return {"status": "error", "details": error_msg}
    except Exception as e:
        error_msg = f"❌ Exception during forced update: {str(e)}"
        print(error_msg)
        return {"status": "error", "details": error_msg}





##################################################
# Run if local
##################################################
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting on 0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)