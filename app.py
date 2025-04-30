import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    planType: str

@app.post("/ai/chat")
async def chat_endpoint(req: ChatRequest):
    prompt = f"""
You are a fitness assistant AI. Create a {req.planType} diet plan based on this message:
"{req.message}"

Include meal types: Breakfast, Lunch, Snacks, Dinner.
    """

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )
        reply = response.json()["choices"][0]["message"]["content"]
        return {"reply": reply}
    except Exception as e:
        return {"error": str(e)}
