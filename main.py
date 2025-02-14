from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
GEMINI_API_KEY = "AIzaSyAOdIo9PawJQ_XbiRn6BvS1HXJnVogVpl0"  # Replace with your actual API key

# ✅ API Route: List Existing Projects
@app.get("/list-projects")
def get_projects():
    return list_projects()

# ✅ API Route: Create a New Project (Automatically Uses Default Workflow)
@app.post("/create-project")
def new_project(data: dict):
    project_name = data.get("project_name")
    return create_project(project_name)

# ✅ API Route: Delete a Project
@app.delete("/delete-project")
def remove_project(data: dict):
    project_name = data.get("project_name")
    return delete_project(project_name)


@app.post("/chat")
async def chat_with_gpt(chat_request: dict):
    """Send user input to Google Gemini API and return response."""
    prompt = chat_request.get("message", "")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Error communicating with Google Gemini API")

    response_data = response.json()
    
    # Extract AI response
    gpt_response = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")

    return {"response": gpt_response}    
