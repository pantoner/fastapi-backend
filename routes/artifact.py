import yaml
import json
import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helpers import correct_spelling, detect_user_mood, enforce_focus, get_llm_response  # ✅ Keep existing AI functionality

router = APIRouter()

WORKFLOW_INDEX_FILE = "workflowIndex.yaml"
WORKFLOW_FOLDER = "workflow/"
ARTIFACT_FILE = "artifact.json"
CHAT_HISTORY_FILE = "chat_history.json"

# ✅ Load API Key for LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

class StepInput(BaseModel):
    response: str

def load_workflow_index():
    """Load the workflow index file."""
    with open(WORKFLOW_INDEX_FILE, "r") as f:
        return yaml.safe_load(f)["workflow"]["steps"]

def load_step_config(step_filename):
    """Load an individual step YAML file from the workflow/ folder."""
    step_path = os.path.join(WORKFLOW_FOLDER, step_filename)  # ✅ Ensure path includes `workflow/`
    if not os.path.exists(step_path):
        raise HTTPException(status_code=404, detail=f"Step file {step_path} not found.")
    
    with open(step_path, "r") as f:
        return yaml.safe_load(f)

def load_artifact():
    """Load artifact JSON file or create a new one if missing."""
    workflow_steps = load_workflow_index()
    first_step = workflow_steps[0]  # ✅ Get the first step dynamically

    if not os.path.exists(ARTIFACT_FILE):
        with open(ARTIFACT_FILE, "w") as f:
            json.dump({"current_step": first_step, "data": {}}, f, indent=4)
    
    with open(ARTIFACT_FILE, "r") as f:
        return json.load(f)

@router.post("/artifact/confirm/{step_filename}")
async def confirm_step(step_filename: str, input_data: StepInput):
    """When the user confirms the statement, save it and proceed to the next step."""
    workflow_steps = load_workflow_index()
    step_config = load_step_config(step_filename)

    artifact = load_artifact()
    chat_history = load_chat_history()

    last_bot_message = next((msg["text"] for msg in reversed(chat_history) if msg["role"] == "bot"), None)
    
    if last_bot_message:
        artifact["data"][step_config["step"]] = last_bot_message  # ✅ Save the confirmed problem statement
        save_artifact(artifact)

    next_step = step_config.get("next_step")
    artifact["current_step"] = next_step if next_step else "complete"
    save_artifact(artifact)

    # ✅ Tell the LLM that the user has confirmed and to instruct the system to move forward
    move_to_next_instruction = step_config["llm_prompts"].get("move_to_next_step", "The user has confirmed their problem statement. Proceeding to the next step.")
    llm_response = get_llm_response(move_to_next_instruction)

    chat_history.append({"role": "bot", "text": llm_response})
    save_chat_history(chat_history)

    return {
        "message": step_config["system_messages"]["final_confirmation"].replace("{next_step}", artifact["current_step"]),
        "next_step": step_config["system_messages"]["move_to_next"].replace("{next_step}", artifact["current_step"]),
        "chat_history": chat_history
    }
