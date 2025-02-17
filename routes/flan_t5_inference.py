import os
import json
import tensorflow as tf
import boto3  # ✅ Required for S3 download
from fastapi import APIRouter
from pydantic import BaseModel
from transformers import T5Tokenizer, T5ForConditionalGeneration
import datetime

router = APIRouter()

# ✅ S3 Configuration (Uses Render Environment Variables)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_MODEL_KEY = os.getenv("S3_MODEL_KEY")
LOCAL_MODEL_PATH = "fine_tuned_flant5_weights.h5"  # Where the model is stored locally

# ✅ Define JSON file for Flan-T5 logs
FLAN_T5_HISTORY_FILE = "flan_t5_history.json"
FLAN_T5_ERROR_LOG = "flan_t5_errors.log"  # ✅ Error log file

# ✅ Download model from S3 if not already present
def download_model_from_s3():
    if not os.path.exists(LOCAL_MODEL_PATH):
        print(f"📥 [INFO] Downloading model from S3: {S3_BUCKET_NAME}/{S3_MODEL_KEY}")
        s3 = boto3.client("s3")
        try:
            s3.download_file(S3_BUCKET_NAME, S3_MODEL_KEY, LOCAL_MODEL_PATH)
            print("✅ [SUCCESS] Model downloaded successfully!")
        except Exception as e:
            print(f"❌ [ERROR] Failed to download model: {e}")
            raise
    else:
        print("🔄 [INFO] Model already exists locally, skipping download.")

# ✅ Load tokenizer & model
tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-base")
download_model_from_s3()  # ✅ Ensure the model is downloaded before loading

# ✅ Load fine-tuned weights
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")
model.load_weights(LOCAL_MODEL_PATH)

class ChatRequest(BaseModel):
    message: str

def run_flan_t5_model(prompt: str) -> str:
    """Run the user input through the fine-tuned Flan-T5 model with error handling."""
    try:
        input_ids = tokenizer(prompt, return_tensors="tf").input_ids
        output_ids = model.generate(input_ids)
        output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return output_text
    except Exception as e:
        # ✅ Log error details
        error_message = f"[{datetime.datetime.now()}] ERROR: {str(e)} | Input: {prompt}\n"
        with open(FLAN_T5_ERROR_LOG, "a") as log_file:
            log_file.write(error_message)

        # ✅ Print error so it appears in Render logs
        print(error_message)

        # ✅ Return original input so chat continues as expected
        return prompt

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
    """Process user input through Flan-T5 and return the result."""
    
    # ✅ Run Flan-T5 Model with Error Handling
    flan_output = run_flan_t5_model(chat_request.message)

    # ✅ Save Flan-T5 log separately
    save_flan_t5_history({
        "user": chat_request.message,
        "flan_t5": flan_output
    })

    return {"flan_t5_response": flan_output}
