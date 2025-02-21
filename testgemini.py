import requests

GEMINI_API_KEY = "AIzaSyAOdIo9PawJQ_XbiRn6BvS1HXJnVogVpl0"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

test_prompt = "How should I structure my speed workouts?"

payload = {"contents": [{"parts": [{"text": test_prompt}]}]}
headers = {"Content-Type": "application/json"}

response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", json=payload, headers=headers)

print("🔍 Gemini API Response:")
print(response.json())
