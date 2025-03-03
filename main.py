from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from routes.artifact import router as artifact_router
from routes.contextual_chat import router as contextual_chat_router  # ✅ Import new route
# from routes.flan_t5_inference import run_flan_t5_model  # ✅ Import Flan-T5 processing
from ai_helpers import correct_spelling, detect_user_mood, get_llm_response, load_chat_history, save_chat_history
from faiss_helper import search_faiss
from routes.tts import router as tts_router
from routes.auth import auth_router
from routes.profile_router import profile_router
from db import init_db, seed_db
import openai  # ✅ Import OpenAI
import json
import os
from dotenv import load_dotenv
import requests

app = FastAPI()

# ✅ Enable CORS for frontend communication (restrict to frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fastapi-frontend.onrender.com"],  # ✅ Allow frontend requests ONLY
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # ✅ Allow all headers
)

# ✅ Load environment variables
if not os.getenv("RENDER_EXTERNAL_HOSTNAME"):  # ✅ Only load .env in local development
    load_dotenv()

# ✅ Load OpenAI API Key from Environment Variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENAI_API_KEY = ""


if not OPENAI_API_KEY:
    raise RuntimeError("OpenAI API key is missing!")
openai.api_key = OPENAI_API_KEY

# ✅ Paths to JSON files

CHAT_HISTORY_FILE = "chat_history.json"

class ChatRequest(BaseModel):
    message: str


USER_PROFILE_FILE = "user_profile.json"

def load_user_profile():
    """Load user profile from JSON file."""
    if not os.path.exists(USER_PROFILE_FILE):
        raise HTTPException(status_code=404, detail="User profile not found.")
    with open(USER_PROFILE_FILE, "r") as f:
        return json.load(f)


# ✅ API Route: Retrieve Chat History
@app.get("/chat-history")
async def get_chat_history():
    """Returns the stored chat history."""
    return load_chat_history()

# ✅ Query OpenAI GPT-4-turbo
import openai
import json

# ✅ Load OpenAI API Key

openai.api_key = OPENAI_API_KEY

def categorize_message(message: str):
    """Ask GPT to classify the user’s message into a predefined category."""
    prompt = f"""
    Classify the following user message into one of these categories:
    - Running
    - Nutrition
    - Mindset
    Respond with ONLY the category name, nothing else.

    User message: {message}
    """
    response = query_openai_model(prompt)
    return response.strip()  # Remove extra spaces/newlines

def query_openai_model(prompt):
    """Send the formatted prompt to OpenAI GPT-4-turbo and return the response."""
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are a short, collaborative running coach. "
                                              "Your responses must be under 50 words and always end with a follow-up question"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50
        }

        print("📨 Sending request to OpenAI:", json.dumps(payload, indent=2))  # ✅ Debugging request

        response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)

        print(f"🔍 OpenAI API Response Code: {response.status_code}")  # ✅ Debugging response status
        print(f"🔍 OpenAI API Response: {response.text}")  # ✅ Debugging response content

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"❌ OpenAI API Error: {response.status_code} - {response.text}")
            return "Error: Unable to get response."

    except Exception as e:
        print(f"❌ Exception in OpenAI API call: {str(e)}")
        return "Error: Unable to get response."


# Make sure you have a startup event to initialize the database
@app.on_event("startup")
async def app_startup():
    """Initialize the database on application startup."""
    print("🚀 Starting FastAPI Server")
    init_db()
    seed_db()


# ✅ API Route: Chat with OpenAI GPT-4
@app.post("/chat")
async def chat_with_gpt(chat_request: ChatRequest):
    # Load user profile
    user = get_user_by_email(current_user)
    user_profile = get_user_profile(user['id']) if user else {}
    profile_text = json.dumps(user_profile, indent=2)

    # Load chat history
    chat_history = load_chat_history()
    corrected_message = correct_spelling(chat_request.message)
    mood = detect_user_mood(corrected_message)

    # Retrieve relevant knowledge from FAISS
    retrieved_contexts = search_faiss(corrected_message, top_k=3)
    retrieved_text = "\n".join(retrieved_contexts) if retrieved_contexts else "No relevant data found."

    # Format chat history for LLM
    formatted_history = "\n".join(
        [f"You: {entry['user']}\nGPT: {entry['bot']}" for entry in chat_history]
    )

    # Construct full chat prompt
    full_prompt = f"""
    **ROLE & OBJECTIVE:**
    You are a collaborative running coach who provides brief, engaging responses. Keep answers under 50 words and always end with a follow-up question. Do not provide lists or detailed breakdowns; instead, engage the user about their preferences.

    **USER PROFILE:**
    {profile_text}

    **PREVIOUS CONVERSATION (Context):**
    {formatted_history}

    **RETRIEVED KNOWLEDGE:**
    {retrieved_text}

    **CURRENT USER MESSAGE:**
    {corrected_message}

    **TASK:**
    1. Determine the category of the user's message: Running, Nutrition, or Mindset.
    2. Based on the identified category and the provided context, generate a response that aligns with the user's journey.

    **RESPONSE FORMAT:**
    Category: [Identified Category]
    [Your response here]
    """

    # Call OpenAI GPT-4 API
    response = query_openai_model(full_prompt)

    # Parse the response to extract category and message
    try:
        category_line, bot_response = response.split('\n', 1)
        category = category_line.replace('Category:', '').strip()
    except ValueError:
        category = "Unknown"
        bot_response = response

    # Save chat history
    chat_history.append({"user": chat_request.message, "bot": bot_response})
    save_chat_history(chat_history)

    return {"category": category, "response": bot_response, "history": chat_history}



# ✅ Include artifact and contextual chat routers
app.include_router(artifact_router)
app.include_router(contextual_chat_router)  # ✅ Register contextual chat endpoint
app.include_router(tts_router)  # ✅ Register TTS streaming endpoint
app.include_router(auth_router, prefix="/auth")  # ✅ Register auth_router with prefix
app.include_router(profile_router, prefix="/profile", tags=["Profile"])


# ✅ Start the FastAPI server when running the script directly
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI Server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)