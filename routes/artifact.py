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
    if not os.path.exists(WORKFLOW_INDEX_FILE):
        raise HTTPException(status_code=500, detail="Workflow index file not found.")
    
    with open(WORKFLOW_INDEX_FILE, "r") as f:
        return yaml.safe_load(f)["workflow"]["steps"]

def load_step_config(step_filename):
    """Load an individual step YAML file from the workflow/ folder."""
    step_path = os.path.join(WORKFLOW_FOLDER, step_filename)  # ✅ Ensure path includes `workflow/`
    if not os.path.exists(step_path):
        raise HTTPException(status_code=500, detail=f"Step file {step_path} not found.")
    
    with open(step_path, "r") as f:
        return yaml.safe_load(f)

def load_artifact():
    """Load artifact JSON file or create a new one if missing."""
    workflow_steps = load_workflow_index()
    first_step = f"workflow/{workflow_steps[0]}"  # ✅ Ensure first step includes `workflow/`

    if not os.path.exists(ARTIFACT_FILE):
        with open(ARTIFACT_FILE, "w") as f:
            json.dump({"current_step": first_step, "data": {}}, f, indent=4)

    try:
        with open(ARTIFACT_FILE, "r") as f:
            artifact = json.load(f)
    except json.JSONDecodeError:
        artifact = {"current_step": first_step, "data": {}}
        save_artifact(artifact)  # ✅ Reset `artifact.json` if it's empty or corrupted

    return artifact

@router.post("/artifact/start")
async def start_new_artifact():
    """Initialize a new artifact workflow and set the first step dynamically."""
    workflow_steps = load_workflow_index()
    first_step = f"workflow/{workflow_steps[0]}" if workflow_steps else None  # ✅ Ensure `workflow/` is included

    if not first_step:
        raise HTTPException(status_code=500, detail="Workflow steps not found in workflowIndex.yaml.")

    artifact = {"current_step": first_step, "data": {}}
    save_artifact(artifact)

    return {"message": "Artifact workflow started", "next_step": first_step}

@router.get("/artifact/current_step")
async def get_current_step():
    """Retrieve the current step from artifact.json."""
    artifact = load_artifact()
    return {"current_step": artifact.get("current_step", None)}

@router.get("/artifact/step/{step_filename}")
async def get_step(step_filename: str):
    """Retrieve step details from YAML and check if step exists."""
    workflow_steps = load_workflow_index()

    decoded_step_filename = requests.utils.unquote(step_filename)  # ✅ Decode filename for accuracy

    # ✅ Ensure requested step is in workflow index
    if decoded_step_filename not in workflow_steps:
        raise HTTPException(status_code=404, detail=f"Step '{decoded_step_filename}' not found in workflow index.")

    # ✅ Ensure step file exists
    try:
        step_config = load_step_config(decoded_step_filename)
    except HTTPException:
        return {"error": f"Step configuration file '{decoded_step_filename}' is missing."}

    artifact = load_artifact()
    chat_history = load_chat_history()

    return {
        "step": step_config["step"],
        "description": step_config.get("description", "No description available."),
        "input_type": step_config.get("input", ["text"]),
        "choices": step_config.get("options", []),
        "rules": step_config.get("rules", []),
        "next_step": step_config.get("next_step", "complete"),
        "artifact_data": artifact["data"].get(step_config["step"], ""),
        "chat_history": chat_history  # ✅ Return last 10 chat messages
    }

@router.post("/artifact/next_step")
async def next_step():
    """Move to the next step in the workflow."""
    artifact = load_artifact()
    workflow_steps = load_workflow_index()

    current_step = artifact.get("current_step")
    next_step = get_next_step(current_step, workflow_steps)

    if next_step == "complete":
        artifact["current_step"] = "complete"
        save_artifact(artifact)
        return {"message": "Workflow complete!", "next_step": "complete"}

    artifact["current_step"] = next_step
    save_artifact(artifact)

    return {"message": "Proceeding to next step.", "next_step": next_step}

def get_next_step(current_step, workflow_steps):
    """Determine the next step based on workflow index."""
    try:
        current_index = workflow_steps.index(current_step)
        return workflow_steps[current_index + 1] if current_index + 1 < len(workflow_steps) else "complete"
    except ValueError:
        return "complete"  # Step not found in index

def save_artifact(artifact):
    """Save artifact data to artifact.json."""
    with open(ARTIFACT_FILE, "w") as f:
        json.dump(artifact, f, indent=4)

def load_chat_history():
    """Load the last 10 chat messages from chat_history.json, or create an empty file if missing."""
    if not os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "w") as f:
            json.dump([], f)
        return []
    
    try:
        with open(CHAT_HISTORY_FILE, "r") as f:
            history = json.load(f)
    except json.JSONDecodeError:
        history = []
        save_chat_history(history)  # ✅ Reset chat history if it's empty or corrupted

    return history[-10:]  # ✅ Keep only the last 10 messages

def save_chat_history(history):
    """Save chat history to chat_history.json."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)
