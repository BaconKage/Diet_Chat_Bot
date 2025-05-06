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

# CORS Middleware (Open for development; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection for foods
FOOD_DB_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(FOOD_DB_URI)
food_collection = client["my_gym"]["foods"]

# Groq API setup
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Request schema
class ChatRequest(BaseModel):
    message: str
    planType: str

# Fetch allowed food names based on type
def get_allowed_foods(diet_type: str):
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")  # Vegetarians & vegans overlap
    foods = food_collection.find({ "type": { "$in": allowed_types } })
    return [item["name"] for item in foods]

@app.post("/ai/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        user_prompt = data.message
        plan_type = data.planType.lower()

        # Guess diet type from user input (default to vegetarian)
        diet_type = "vegetarian"
        if "non-vegetarian" in user_prompt.lower():
            diet_type = "non-vegetarian"
        elif "vegan" in user_prompt.lower():
            diet_type = "vegan"

        # Get food list from MongoDB
        allowed_foods = get_allowed_foods(diet_type)
        food_list = "\n".join([f"- {food}" for food in allowed_foods[:100]])  # limit to 100

        system_prompt = (
            f"You are a certified AI nutritionist. Only use the following foods in the meal plan:\n\n"
            f"{food_list}\n\n"
            f"Now, based on the user's profile, create a personalized {plan_type} diet plan. "
            f"Include 3 meals, 2 snacks daily, hydration advice, supplements, and one motivational tip. "
            f"⚠️ Do NOT use ingredients outside this list."
        )

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

        # Validate AI reply
        if any(x in reply.lower() for x in ["client profile", "you are a certified"]):
            return { "error": "Unexpected AI response format." }

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
