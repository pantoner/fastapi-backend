import yaml
import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

WORKFLOW_FILE = "workflow.yaml"
ARTIFACT_FILE = "artifact.json"

class StepInput(BaseModel):
    response: str

def load_workflow():
    """Load the YAML workflow file."""
    with open(WORKFLOW_FILE, "r") as f:
        return yaml.safe_load(f)["workflow"]

def load_artifact():
    """Load artifact JSON file or create a new one if missing (without overwriting existing data)."""
    if not os.path.exists(ARTIFACT_FILE):  # ✅ Only create if missing
        artifact = {"current_step": "Define Business Problem", "data": {}}
        with open(ARTIFACT_FILE, "w") as f:
            json.dump(artifact, f, indent=4)
        return artifact  # ✅ Return the new artifact structure

    with open(ARTIFACT_FILE, "r") as f:
        return json.load(f)  # ✅ Load existing data if file exists
        
def save_artifact(artifact):
    """Save artifact data to JSON file."""
    with open(ARTIFACT_FILE, "w") as f:
        json.dump(artifact, f, indent=4)

def find_step(step_name, workflow):
    """Find a step in the workflow by name."""
    return next((s for s in workflow if s["step"] == step_name), None)

@router.get("/artifact/step/{step_name}")
async def get_step(step_name: str):
    """Retrieve the prompt and details for the requested step."""
    workflow = load_workflow()
    step = find_step(step_name, workflow)

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    artifact = load_artifact()

    return {
        "step": step["step"],
        "description": step["description"],
        "input_type": step["input"][0] if step.get("input") else "text",
        "choices": step.get("options", []),
        "rules": step.get("rules", []),
        "next_step": get_next_step(step["step"], workflow),
        "artifact_data": artifact["data"].get(step["step"], "")
    }

@router.post("/artifact/step/{step_name}")
async def submit_step(step_name: str, input_data: StepInput):
    """Store the response for the current step and move to the next step."""
    workflow = load_workflow()
    step = find_step(step_name, workflow)

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    artifact = load_artifact()
    artifact["data"][step["step"]] = input_data.response  # Save response

    next_step = get_next_step(step["step"], workflow)
    
    if next_step:
        artifact["current_step"] = next_step
    else:
        artifact["current_step"] = "complete"  # Mark as complete if no next step

    save_artifact(artifact)

    return {"message": "Step saved", "next_step": artifact["current_step"]}

def get_next_step(current_step, workflow):
    """Determine the next step based on the current step."""
    for i, step in enumerate(workflow):
        if step["step"] == current_step and i + 1 < len(workflow):
            return workflow[i + 1]["step"]
    return None  # No next step (workflow complete)
