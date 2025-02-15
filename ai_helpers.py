import json
import os
import requests
from textblob import TextBlob

# Load environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

# File paths
CHAT_HISTORY_FILE = "chat_history.json"

# ✅ Correct spelling & grammar before processing
def correct_spelling(user_input):
    corrected_text = str(TextBlob(user_input).correct())
    return corrected_text

# ✅ Detect frustration in user input
def detect_user_mood(user_input):
    frustration_keywords = ["rude", "annoying", "not helpful", "off-track", "what are you talking about"]
    
    for keyword in frustration_keywords:
        if keyword in user_input.lower():
            return "frustrated"
    return "neutral"

# ✅ Load chat history (keep last 10)
def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_FILE):
        return []
    with open(CHAT_HISTORY_FILE, "r") as f:
        history = json.load(f)
    return history[-10:]

# ✅ Save chat history
def save_chat_history(history):
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# ✅ AI Response Refinement
def get_llm_response(user_input):
    """Send user message to Google Gemini API and return AI response."""
    payload = {
        "contents": [{"parts": [{"text": f"Ensure a friendly and professional tone while answering: {user_input}"}]}]
    }
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        return response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    return "Error retrieving response from AI"

# ✅ Guide user back on track if they go off-topic
def enforce_focus(user_input, current_step):
    """Reaffirm the user's goal in the workflow."""
    focus_prompts = {
        "Define Business Problem": "Let's make sure we define the core business problem clearly.",
        "Set Project Direction": "Are you ready to set the project direction with a vision statement or OKRs?",
    }
    return focus_prompts.get(current_step, "Let's keep moving forward with your project.")
