from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ Enable CORS (open for now, restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace this with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check route
@app.get("/")
def read_root():
    return {"status": "FastAPI backend is live"}

# ✅ Chat request schema
class ChatRequest(BaseModel):
    message: str
    planType: str  # e.g., "week", "month"

# ✅ AI Chat Endpoint
@app.post("/ai/chat")
async def chat_endpoint(req: ChatRequest):
    prompt = f"""
You are a smart AI gym assistant. A trainer has asked for a {req.planType} diet plan.
Message from the trainer: "{req.message}"

Generate a practical and healthy {req.planType} diet plan, broken down by day and meal type (Breakfast, Lunch, Snacks, Dinner). Ensure it aligns with standard fitness goals like muscle gain, fat loss, or maintenance depending on the message context.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        reply = response['choices'][0]['message']['content']
        return {"reply": reply}
    except Exception as e:
        return {"error": str(e)}
