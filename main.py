from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from routes.artifact import router as artifact_router
from routes.contextual_chat import router as contextual_chat_router  # ✅ Import new route
from routes.flan_t5_inference import run_flan_t5_model  # ✅ Import Flan-T5 processing
# from routes.chat import router as chat_router  # ✅ Import chat router
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response, load_chat_history, save_chat_history
import requests
import json
import os
from dotenv import load_dotenv

app = FastAPI()

# ✅ Enable CORS for frontend communication (restrict to frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fastapi-frontend.onrender.com"],  # ✅ Allow frontend requests ONLY
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ✅ Allow all headers
)

# ✅ Load .env file ONLY in local development
if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):  # This variable exists only on Render
    load_dotenv()

# ✅ Load GEMINI API Key from Environment Variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ Warning: GEMINI_API_KEY environment variable is missing!")
else:
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

# ✅ Paths to JSON files
USERS_FILE = "users.json"
CHAT_HISTORY_FILE = "chat_history.json"

# ✅ Pydantic Models
class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str

# ✅ Function to Load Users from JSON File
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)


# ✅ API Route: Login Endpoint
@app.post("/auth/login")
async def login(request: LoginRequest):
    users = load_users()

    # ✅ Check if the email and password match
    for user in users:
        if user["email"] == request.email and user["password"] == request.password:
            return {"access_token": "mock-jwt-token", "token_type": "bearer"}

    raise HTTPException(status_code=401, detail="Invalid email or password")

# ✅ API Route: Retrieve Chat History
@app.get("/chat-history")
async def get_chat_history():
    """Returns the stored chat history."""
    return load_chat_history()

# ✅ API Route: Chat with Google Gemini API
@app.post("/chat")
async def chat_with_gpt(chat_request: ChatRequest):
    """Send user input to Google Gemini API along with chat history for context."""
    chat_history = load_chat_history()  # ✅ Load past chats
    corrected_message = correct_spelling(chat_request.message)
    mood = detect_user_mood(corrected_message)

    # ✅ Process through Flan-T5 model
    corrected_message = run_flan_t5_model(corrected_message)

    # ✅ Format chat history for LLM
    formatted_history = "\n".join(
        [f"You: {entry['user']}\nGPT: {entry['bot']}" for entry in chat_history]
    )

    # ✅ Add the latest user message
    full_prompt = f"{formatted_history}\nYou: {corrected_message}\nGPT:"


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

    return {"response": gpt_response, "history": chat_history}

# ✅ Include artifact and contextual chat routers
app.include_router(artifact_router)
app.include_router(contextual_chat_router)  # ✅ Register contextual chat endpoint
# app.include_router(chat_router)  # ✅ Register chat API

# ✅ Start the FastAPI server when running the script directly
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
