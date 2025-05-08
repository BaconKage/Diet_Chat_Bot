from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
import os
import requests
from datetime import datetime
from bson import ObjectId

load_dotenv()

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema
class PlanRequest(BaseModel):
    trainerId: str
    userId: str
    planType: str  # e.g. week, month, etc.

# API config
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# MongoDB config
MONGO_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(MONGO_URI)
db = client["my_gym"]

users_collection = db["users"]
foods_collection = db["foods"]
mealplans_collection = db["mealplans"]

# Food filter logic
def get_allowed_foods(diet_type: str):
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")
    foods = foods_collection.find({ "type": { "$in": allowed_types } })
    return [item["name"] for item in foods]

@app.post("/ai/auto-plan")
async def auto_generate_diet(data: PlanRequest):
    try:
        # Fetch user
        user = users_collection.find_one({ "_id": ObjectId(data.userId) })
        if not user:
            return { "error": "User not found in database." }

        age = user.get("age", 30)
        gender = user.get("gender", "male")
        BMI = user.get("BMI", 22.0)
        goal = user.get("goal", "stay fit")
        diet_type = user.get("diet_type", "vegetarian").lower()

        allowed_foods = get_allowed_foods(diet_type)
        food_list = ", ".join([f'"{food}"' for food in allowed_foods])
        plan_type = data.planType

        # Prompt to AI
        system_prompt = (
            f"You are a certified AI nutritionist.\n"
            f"Your job is to generate a strict {plan_type} diet plan using ONLY the food items listed below.\n"
            f"⚠️ You are NOT allowed to invent or assume foods not in this list.\n"
            f"The allowed foods are: {food_list}\n\n"
            f"Design a 7-day meal plan with 3 meals and 2 snacks per day.\n"
            f"Include hydration, supplements (if needed), and a motivational quote.\n"
            f"Use bullet points and emojis to keep it engaging."
        )

        # Call GROQ
        response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": [
                    { "role": "system", "content": system_prompt },
                    { "role": "user", "content": "Generate my personalized diet plan." }
                ]
            }
        )

        reply = response.json()["choices"][0]["message"]["content"].strip()

        # Insert plan to mealplans collection
        mealplans_collection.insert_one({
            "created_by": ObjectId(data.trainerId),
            "created_for": ObjectId(data.userId),
            "for_date": datetime.utcnow(),
            "mealPlan": [reply],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None
        })

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
