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

# Enable CORS for development (adjust for production)
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

# Groq API configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# MongoDB food collection connection
FOOD_DB_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(FOOD_DB_URI)
food_collection = client["my_gym"]["foods"]

def get_allowed_foods(diet_type: str):
    # Fetch foods matching diet type
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")  # Vegans & Vegetarians can share many items
    foods = food_collection.find({ "type": { "$in": allowed_types } })
    food_names = [item["name"] for item in foods]
    return food_names

@app.post("/ai/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        # Extract diet_type and allowed foods
        user_prompt = data.message
        plan_type = data.planType.lower()

        # Extract diet_type from user_prompt (assumes it's in the text)
        diet_type = "vegetarian"
        if "non-vegetarian" in user_prompt.lower():
            diet_type = "non-vegetarian"
        elif "vegan" in user_prompt.lower():
            diet_type = "vegan"

        allowed_foods = get_allowed_foods(diet_type)
        food_list = "\n".join([f"- {food}" for food in allowed_foods[:100]])  # limit to 100 items

        # Build system prompt
        system_prompt = (
            f"You are a certified AI nutritionist. Based on the user's profile and goals, generate a {plan_type} diet plan. "
            f"⚠️ ONLY use foods from this list:\n{food_list}\n\n"
            f"Focus on 3 meals + 2 snacks daily, hydration tips, supplements, and one motivational note. Use emojis for each bullet."
        )

        # Send to Groq
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

        # Simple response validation
        if "Client Profile" in reply or "you are a certified" in reply.lower():
            return { "error": "Unexpected response format from AI." }

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
