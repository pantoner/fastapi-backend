import os
import requests

# Make sure you set these environment variables or hard-code them for testing
#ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_API_KEY_HERE")
ELEVENLABS_API_KEY = "sk_92f000c76334a61d644948ebbd37a9ad79b1a4631bf24818"
#ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "YOUR_VOICE_ID_HERE")
ELEVENLABS_VOICE_ID = "T5cu6IU92Krx4mh43osx"

def text_to_speech(text: str) -> bytes:
    """
    Calls ElevenLabs TTS for the given text and returns the audio data as bytes.
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ElevenLabs API key is not set.")
    if not ELEVENLABS_VOICE_ID:
        raise ValueError("ElevenLabs voice ID is not set.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS failed: {response.status_code} - {response.text}")

    return response.content  # The audio file bytes (usually MP3)

def main():
    text = "Hello world from ElevenLabs!"
    print(f"Requesting TTS for text: '{text}'")

    audio_data = text_to_speech(text)

    # Write the MP3 bytes to a file
    output_filename = "output.mp3"
    with open(output_filename, "wb") as f:
        f.write(audio_data)

    print(f"✅ TTS audio saved to '{output_filename}'. Play it to confirm it worked!")

if __name__ == "__main__":
    main()
