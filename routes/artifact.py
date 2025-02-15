import yaml
import json
import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

WORKFLOW_FILE = "workflow.yaml"
ARTIFACT_FILE = "artifact.json"
CHAT_HISTORY_FILE = "chat_history.json"

# ✅ Load API Key for LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

class StepInput(BaseModel):
    response: str

def load_workflow():
    """Load the YAML workflow file."""
    with open(WORKFLOW_FILE, "r") as f:
        return yaml.safe_load(f)["workflow"]

def load_artifact():
    """Load artifact JSON file or create a new one if missing."""
    if not os.path.exists(ARTIFACT_FILE):
        with open(ARTIFACT_FILE, "w") as f:
            json.dump({"current_step": "Define Business Problem", "data": {}}, f, indent=4)
    
    with open(ARTIFACT_FILE, "r") as f:
        return json.load(f)

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
    
    with open(CHAT_HISTORY_FILE, "r") as f:
        history = json.load(f)

    return history[-10:]  # ✅ Keep only the last 10 messages

def save_chat_history(history):
    """Save chat history to chat_history.json."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def find_step(step_name, workflow):
    """Find a step in the workflow by name."""
    return next((s for s in workflow if s["step"] == step_name), None)

@router.get("/artifact/step/{step_name}")
async def get_step(step_name: str):
    """Retrieve the prompt, details for the requested step, and previous chat messages."""
    workflow = load_workflow()
    step = find_step(step_name, workflow)

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    artifact = load_artifact()
    chat_history = load_chat_history()  # ✅ Load past messages

    return {
        "step": step["step"],
        "description": step["description"],
        "input_type": step["input"][0] if step.get("input") else "text",
        "choices": step.get("options", []),
        "rules": step.get("rules", []),
        "next_step": get_next_step(step["step"], workflow),
        "artifact_data": artifact["data"].get(step["step"], ""),
        "chat_history": chat_history  # ✅ Return last 10 chat messages
    }

@router.post("/artifact/step/{step_name}")
async def submit_step(step_name: str, input_data: StepInput):
    """Process user input, save conversation history, generate LLM response, and store final agreed artifact."""
    workflow = load_workflow()
    step = find_step(step_name, workflow)

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    artifact = load_artifact()
    chat_history = load_chat_history()

    # ✅ Save user response to chat history
    chat_history.append({"role": "user", "text": input_data.response})
    save_chat_history(chat_history)

    # ✅ Call LLM API to refine the artifact
    refined_response = get_llm_response(input_data.response)

    # ✅ Save LLM response to chat history
    chat_history.append({"role": "bot", "text": refined_response})
    save_chat_history(chat_history)

    # ✅ Check if the user has confirmed the final artifact
    if input_data.response.lower() in ["yes", "i like that", "approved"]:
        # ✅ Store the final artifact
        last_llm_message = next((msg["text"] for msg in reversed(chat_history) if msg["role"] == "bot"), None)
        if last_llm_message:
            artifact["data"][step["step"]] = last_llm_message  # ✅ Save final artifact
            save_artifact(artifact)

    next_step = get_next_step(step["step"], workflow)
    if next_step:
        artifact["current_step"] = next_step
    else:
        artifact["current_step"] = "complete"  # ✅ Mark workflow as complete

    save_artifact(artifact)

    return {"message": "Step saved", "next_step": artifact["current_step"], "chat_history": chat_history}

def get_next_step(current_step, workflow):
    """Determine the next step based on the current step."""
    for i, step in enumerate(workflow):
        if step["step"] == current_step and i + 1 < len(workflow):
            return workflow[i + 1]["step"]
    return None  # No next step (workflow complete)

def get_llm_response(user_input):
    """Call Google Gemini API to generate refined artifact responses."""
    payload = {
        "contents": [{"parts": [{"text": f"Refine this artifact statement: {user_input}"}]}]
    }

    headers = {"Content-Type": "application/json"}
    
    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        return response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")
    
    return "Error retrieving response from LLM"
