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

# ✅ Load Gemini API URL (was missing before)
GEMINI_API_URL = os.getenv("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_URL or not GEMINI_API_KEY:
    raise RuntimeError("❌ ERROR: GEMINI_API_URL or GEMINI_API_KEY is missing!")

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

    # ✅ Apply AI preprocessing
    corrected_input = correct_spelling(original_input)
    mood = detect_user_mood(corrected_input)

    # ✅ Process through Flan-T5 model
    flan_t5_output = run_flan_t5_model(corrected_input)

    # ✅ Format chat history for LLM
    formatted_history = "\n".join(
        [f"You: {entry['user']}\nGPT: {entry['bot']}" for entry in chat_history]
    )

    # ✅ Construct prompt for Gemini API
    sent_to_gemini = f"{formatted_history}\nYou: {flan_t5_output}\nGPT:"

    # ✅ Send request to Gemini API (Reverted to requests.post)
    payload = {"contents": [{"parts": [{"text": sent_to_gemini}]}]}
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code != 200:
        print(f"❌ Gemini API Error: {response.status_code} - {response.text}")  # 🔍 Debugging line
        raise HTTPException(status_code=500, detail="Error communicating with Google Gemini API")

    response_data = response.json()
    final_gemini_output = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    # ✅ Save chat history
    chat_history.append({"user": original_input, "bot": final_gemini_output})
    save_chat_history(chat_history)

    # ✅ Create structured log entry
    log_entry = create_log_entry(original_input, corrected_input, flan_t5_output, sent_to_gemini, final_gemini_output)

    # ✅ Save log to S3
    s3_key = save_to_s3(hash_filename, log_entry)

    return {
        "response": final_gemini_output,
        "log_filename": f"{hash_filename}.json",
        "s3_path": s3_key,
        "history": chat_history
    }
