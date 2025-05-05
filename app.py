from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# Allow frontend + gateway to access
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
async def chat_endpoint(data: ChatRequest):
    message = data.message
    plan_type = data.planType.lower()

    # Simulated diet plan (replace this with actual LLM/Groq/OpenAI call)
    reply = f"""
🥗 Diet Plan ({plan_type.capitalize()}) for:
📝 {message}

🍳 Breakfast: Oats with almond milk + banana
🍽️ Lunch: Grilled tofu or paneer + brown rice + veggies
🥤 Snack: Mixed nuts and green tea
🍲 Dinner: Quinoa salad with chickpeas and spinach
💧 Water: 3–4 liters daily
🏋️‍♀️ Workout: 30 mins cardio + light weights

🧘 Stay consistent and track your progress!
"""

    return { "reply": reply }
