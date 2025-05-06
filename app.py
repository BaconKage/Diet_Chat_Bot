from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
import os
import requests

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS (adjust for production later)
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

# Groq API setup
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# MongoDB setup for foods
FOOD_DB_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(FOOD_DB_URI)
food_collection = client["my_gym"]["foods"]

# 🥦 Helper: Get allowed foods from DB
def get_allowed_foods(diet_type: str):
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")
    foods = food_collection.find({ "type": { "$in": allowed_types } })
    return [food["name"] for food in foods]

# 📬 POST /ai/chat
@app.post("/ai/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        user_prompt = data.message
        plan_type = data.planType.lower()

        # Guess diet type from message
        if "non-vegetarian" in user_prompt.lower():
            diet_type = "non-vegetarian"
        elif "vegan" in user_prompt.lower():
            diet_type = "vegan"
        else:
            diet_type = "vegetarian"

        # Get food list from DB
        allowed_foods = get_allowed_foods(diet_type)
        food_list = "\n".join(f"- {food}" for food in allowed_foods[:100])

        # Build Groq system prompt
        system_prompt = (
            f"You are a certified AI nutritionist. Generate a {plan_type} diet plan. "
            f"Only use these foods:\n{food_list}\n\n"
            f"Include: 3 meals + 2 snacks daily, hydration tips, and a motivational note. Use emojis for bullets. "
            f"DO NOT include user profile or repeat the food list."
        )

        # Call Groq
        response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": [
                    { "role": "system", "content": system_prompt },
                    { "role": "user", "content": user_prompt }
                ]
            }
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()

        if not reply or "you are a certified" in reply.lower():
            return { "error": "Invalid AI response." }

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
