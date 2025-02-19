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

# ✅ Enable CORS for frontend communication (restrict to frontend domain)
router.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fastapi-frontend.onrender.com"],  # ✅ Allow frontend requests ONLY
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ✅ Allow all headers
)

# ✅ Load Gemini API URL (Ensure it is correctly set)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ Warning: GEMINI_API_KEY environment variable is missing!")
else:
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

CHAT_HISTORY_FILE = "chat_history.json"

class ChatRequest(BaseModel):
    message: str

# ✅ API Route: Retrieve Chat History
@router.get("/chat-history")
async def get_chat_history():
    """Returns the stored chat history."""
    return load_chat_history()

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
    #sent_to_gemini = f"{formatted_history}\nYou: {corrected_message}\nGPT:"
    full_prompt = f"{formatted_history}\nYou: {corrected_message}\nGPT:"

    # ✅ Send request to Gemini API (RESTORED working code logic)
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }
    
    headers = {"Content-Type": "application/json"}

    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error communicating with Google Gemini API")

    response_data = response.json()
    gpt_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    # ✅ Save chat history
    chat_history.append({"user": chat_request.message, "bot": gpt_response})
    save_chat_history(chat_history)

    # ✅ Create structured log entry (New feature added **without breaking** working functionality)
    log_entry = create_log_entry(original_input, corrected_message, full_prompt, gpt_response)

    # ✅ Save log to S3 (New feature added **without breaking** working functionality)
    s3_key = save_to_s3(hash_filename, log_entry)

    return {"response": gpt_response, "history": chat_history}
    