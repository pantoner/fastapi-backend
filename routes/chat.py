from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import datetime
import requests  # ✅ Revert to requests.post()
from ai_helpers import correct_spelling, detect_user_mood, load_chat_history, save_chat_history
from routes.flan_t5_inference import run_flan_t5_model  # ✅ Import Flan-T5 processing
from s3_utils import generate_hash, save_to_s3
from log_utils import create_log_entry
import os

router = APIRouter()

# ✅ Load Gemini API URL (Ensure it is correctly set)
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("❌ ERROR: GEMINI_API_KEY is missing!")

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_gpt(chat_request: ChatRequest):
    """Send user input to Google Gemini API, log conversation, and save to S3."""

    # ✅ Load chat history
    chat_history = load_chat_history()

    # ✅ Process input
    original_input = chat_request.message
    timestamp = datetime.datetime.utcnow().isoformat()
    hash_filename = generate_hash(original_input, timestamp)

    # ✅ Apply AI preprocessing (RESTORED to working code structure)
    corrected_message = correct_spelling(original_input)
    mood = detect_user_mood(corrected_message)

    # ✅ Run through Flan-T5 model (RESTORED to working code)
    corrected_message = run_flan_t5_model(corrected_message)

    # ✅ Format chat history for LLM (Matches working code)
    formatted_history = "\n".join(
        [f"You: {entry['user']}\nGPT: {entry['bot']}" for entry in chat_history]
    )

    # ✅ Construct prompt for Gemini API (RESTORED to working code)
    sent_to_gemini = f"{formatted_history}\nYou: {corrected_message}\nGPT:"

    # ✅ Send request to Gemini API (RESTORED working code logic)
    payload = {"contents": [{"parts": [{"text": sent_to_gemini}]}]}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GEMINI_API_KEY}"  # ✅ Use correct authentication
    }

    response = requests.post(GEMINI_API_URL, json=payload, headers=headers)

    # ✅ Print response for debugging
    print(f"🔍 RAW RESPONSE STATUS: {response.status_code}")
    print(f"🔍 RAW RESPONSE TEXT: {response.text}")

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Gemini API Error: {response.status_code} - {response.text}")

    response_data = response.json()

    # ✅ Reverted to working response extraction
    try:
        final_gemini_output = response_data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        final_gemini_output = "No response received"

    # ✅ Save chat history (Preserved from working code)
    chat_history.append({"user": original_input, "bot": final_gemini_output})
    save_chat_history(chat_history)

    # ✅ Create structured log entry (New feature added **without breaking** working functionality)
    log_entry = create_log_entry(original_input, corrected_message, corrected_message, sent_to_gemini, final_gemini_output)

    # ✅ Save log to S3 (New feature added **without breaking** working functionality)
    s3_key = save_to_s3(hash_filename, log_entry)

    return {
        "response": final_gemini_output,
        "log_filename": f"{hash_filename}.json",
        "s3_path": s3_key,
        "history": chat_history
    }
