import requests
import openai

# ✅ OpenAI API Key
OPENAI_API_KEY = "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"

# ✅ Define Test Prompt
test_prompt = "How should I structure my speed workouts?"

# ✅ OpenAI API Request
def query_openai(prompt):
    """Send a request to OpenAI GPT-4-turbo and return the response."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4-turbo",
        "messages": [
            {"role": "system", "content": "You are a short, collaborative running coach. "
                                          "Your responses must be under 50 words and always end with a follow-up question."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 50  # ✅ Forces shorter responses
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print(f"❌ OpenAI API Error: {response.status_code} - {response.text}")
        return "Error: Unable to get response."

# ✅ Run Test
print("🔍 GPT-4 API Response:")
print(query_openai(test_prompt))
