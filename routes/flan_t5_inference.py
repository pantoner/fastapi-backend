import os
import json
import datetime
import requests  # ✅ Required for API calls to the inference endpoint
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# ✅ Inference API Endpoint
FLAN_T5_INFERENCE_URL = "https://wt9wi9fvpft43dmv.us-east4.gcp.endpoints.huggingface.cloud"

# ✅ Load API Key from Environment Variable
API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# ✅ Define JSON file for Flan-T5 logs
FLAN_T5_HISTORY_FILE = "flan_t5_history.json"
FLAN_T5_ERROR_LOG = "flan_t5_errors.log"  # ✅ Error log file

class ChatRequest(BaseModel):
    message: str

def run_flan_t5_model(prompt: str) -> str:
    """Send user input to the inference endpoint and return the result."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"  # ✅ Include the API Key
        }
        response = requests.post(
            FLAN_T5_INFERENCE_URL,
            headers=headers,
            json={"inputs": prompt},
        )
        response.raise_for_status()  # ✅ Raise an error for bad status codes
        return response.json()["generated_text"]  # ✅ Extract response
    except Exception as e:
        # ✅ Log error details
        error_message = f"[{datetime.datetime.now()}] ERROR: {str(e)} | Input: {prompt}\n"
        with open(FLAN_T5_ERROR_LOG, "a") as log_file:
            log_file.write(error_message)

        print(error_message)  # ✅ Print error for debugging

        return "[Error processing request]"

def save_flan_t5_history(entry):
    """Save the Flan-T5 processed prompt log separately."""
    if os.path.exists(FLAN_T5_HISTORY_FILE):
        with open(FLAN_T5_HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []

    history.append(entry)

    with open(FLAN_T5_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

@router.post("/chat/flan_t5")
async def chat_with_flan_t5(chat_request: ChatRequest):
    """Process user input through Flan-T5 inference endpoint and return the result."""
    
    # ✅ Run Flan-T5 Model with Error Handling
    flan_output = run_flan_t5_model(chat_request.message)

    # ✅ Save Flan-T5 log separately
    save_flan_t5_history({
        "user": chat_request.message,
        "flan_t5": flan_output
    })

    return {"flan_t5_response": flan_output}
