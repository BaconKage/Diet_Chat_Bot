from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = FastAPI()

# Enable CORS for all origins (adjust in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema
class ChatRequest(BaseModel):
    message: str
    planType: str

# Load Groq API config
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

@app.post("/ai/chat")
async def chat_endpoint(data: ChatRequest):
    system_prompt = (
        f"You are a certified AI nutritionist. Based on the user's profile, "
        f"generate a personalized {data.planType.lower()} diet plan. "
        f"Only return the diet plan directly, and do not include the prompt or user profile in the response. "
        f"Focus on meals, hydration, workouts, and one motivational tip. Use emoji bullets for each item."
    )

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": [
                    { "role": "system", "content": system_prompt },
                    { "role": "user", "content": data.message }
                ]
            }
        )
        result = response.json()

        # Extract reply
        reply = result["choices"][0]["message"]["content"].strip()

        # Defensive check: reply must not contain prompt phrases
        if "Client Profile" in reply or "you are a certified" in reply.lower():
            return { "error": "Unexpected response format from AI." }

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
