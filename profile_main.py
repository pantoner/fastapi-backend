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
@app.post("/profile-chat")
def profile_chat(req: ProfileChatRequest):
    """
    1) Find/create user in DB by email
    2) Parse user's current message with 'extract_run_info' => store (weekly_mileage, race_type, last_time_date)
    3) Call the conversation manager => returns { profile_complete, final_prompt }
    4) If complete => short-circuit
    5) Otherwise => call query_openai_model(final_prompt) => return to user
    """

    # 1) Find user
    user = get_user_by_email(req.email)
    if not user:
        new_id = create_user("NewUser", req.email, "temp123")
        if not new_id:
            return {"assistant_response": "Error creating user in DB."}
        create_default_profile(new_id)
        user = get_user_by_email(req.email)
    user_id = user["id"]

    # 2) Get their DB profile
    db_profile = get_user_profile(user_id)
    if not db_profile:
        create_default_profile(user_id)
        db_profile = get_user_profile(user_id)

    # 2a) parse the user's message for fields
    parsed = extract_run_info(req.message)
    # If we find a 'number', let's store it as weekly_mileage (example approach)
    if parsed["number"]:
        try:
            miles = int(parsed["number"])
            db_profile["weekly_mileage"] = miles
        except ValueError:
            # if it's not an integer, skip
            pass
    # If we find a racetype, store it as 'race_type'
    if parsed["racetype"]:
        db_profile["race_type"] = parsed["racetype"]
    # If we find a date, store in last_time_date (or whichever field you prefer)
    if parsed["dates"]:
        db_profile["last_time_date"] = parsed["dates"]

    # 2b) Save updated profile in DB
    save_user_profile(user_id, db_profile)

    # 3) Call the conversation manager
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

    # 4) If profile_complete
    if manager_data.get("profile_complete"):
        return {
            "assistant_response": "Profile is complete!",
            "profile_data": db_profile
        }

    # 5) Otherwise, we get a final_prompt from the manager
    final_prompt = manager_data.get("final_prompt", "")
    updated_profile = manager_data.get("profile_data", db_profile)

    # We call openai to get a short response
    openai_reply = query_openai_model(final_prompt)

    return {
        "assistant_response": openai_reply,
        "profile_data": updated_profile
    }


##################################################
# Run if local
##################################################
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting on 0.0.0.0:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
