import json
import os
import requests
import openai

# Get API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def query_openai_model(prompt):
    """Send the formatted prompt to OpenAI GPT-4-turbo and return the response."""
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are a short, collaborative running coach. "
                                             "Your responses must be under 50 words and always end with a follow-up question."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50
        }

        print("📨 Sending request to OpenAI:", json.dumps(payload, indent=2))

        response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)

        print(f"🔍 OpenAI API Response Code: {response.status_code}")
        print(f"🔍 OpenAI API Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"❌ OpenAI API Error: {response.status_code} - {response.text}")
            return "Error: Unable to get response."

    except Exception as e:
        print(f"❌ Exception in OpenAI API call: {str(e)}")
        return "Error: Unable to get response."