from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
import os
import requests
from datetime import datetime
from bson import ObjectId

# Load environment variables
load_dotenv()

app = FastAPI()

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input schema
class PlanRequest(BaseModel):
    userId: str
    trainerId: str
    planType: str  # "week", "month", "year"

# Configs
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# MongoDB setup
MONGO_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(MONGO_URI)
db = client["my_gym"]
users_collection = db["users"]
foods_collection = db["foods"]
mealplans_collection = db["mealplans"]

# Utility to get allowed food items based on diet type
def get_allowed_foods(diet_type: str):
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")
    foods = foods_collection.find({"type": {"$in": allowed_types}})
    return [item["name"] for item in foods]

@app.post("/ai/chat")
async def generate_diet_plan(data: PlanRequest):
    try:
        # Fetch user profile
        user = users_collection.find_one({"_id": ObjectId(data.userId)})
        if not user:
            return {"error": "User not found"}

        # Prepare profile info
        age = user.get("age", "unknown")
        gender = user.get("gender", "unknown")
        bmi = user.get("BMI", "unknown")
        goal = user.get("goal", "stay fit")
        diet_type = user.get("diet_type", "vegetarian")

        # Fetch allowed food list
        allowed_foods = get_allowed_foods(diet_type)
        food_list = "\n".join([f"- {item}" for item in allowed_foods[:100]])

        # Build system prompt
        profile_text = f"Client Profile:\nAge: {age}\nGender: {gender}\nBMI: {bmi}\nGoal: {goal}\nDiet: {diet_type}\n"
        system_prompt = (
            f"You are a certified AI nutritionist. Based on the following profile, generate a {data.planType} diet plan "
            f"ONLY using the foods below:\n\n{food_list}\n\n"
            f"Format output as:\n- Weekly Summary\n- Daily Plan\n- Hydration & Supplements\n- Motivational Tip."
        )

        # Send to Groq API
        response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": profile_text}
                ]
            }
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"].strip()

        # Store in MongoDB
        mealplans_collection.insert_one({
            "created_by": ObjectId(data.trainerId),
            "created_for": ObjectId(data.userId),
            "for_date": datetime.utcnow(),
            "mealPlan": [reply],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None
        })

        return {"reply": reply}

    except Exception as e:
        return {"error": str(e)}
