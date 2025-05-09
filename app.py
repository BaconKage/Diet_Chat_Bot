from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
import os
import requests
import random
from datetime import datetime

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PlanRequest(BaseModel):
    trainerId: str
    userId: str
    planType: str

MONGO_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(MONGO_URI)
db = client["my_gym"]

users_collection = db["users"]
foods_collection = db["foods"]
meals_collection = db["meals"]
mealplans_collection = db["mealplans"]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama3-8b-8192"

HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

def get_allowed_foods(diet_type: str):
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")
    foods = list(foods_collection.find({"type": {"$in": allowed_types}}))
    return foods

@app.post("/ai/auto-plan")
async def auto_generate_diet(data: PlanRequest):
    try:
        user = users_collection.find_one({"_id": ObjectId(data.userId)})
        if not user:
            return {"error": "User not found."}

        age = user.get("age", 25)
        gender = user.get("gender", "male")
        BMI = user.get("BMI", 22.0)
        goal = user.get("goal", "stay fit")
        diet_type = user.get("diet_type", "vegetarian").lower()
        seed = random.randint(1000, 9999)

        foods = get_allowed_foods(diet_type)
        food_names = [f["name"] for f in foods]
        food_name_to_doc = {f["name"].lower(): f for f in foods}

        system_prompt = (
            f"You are a certified AI nutritionist.\n"
            f"Generate a strict {data.planType} diet plan using only the following foods:\n"
            f"{', '.join(food_names)}.\n\n"
            f"User Profile:\n"
            f"- Age: {age}\n"
            f"- Gender: {gender}\n"
            f"- BMI: {BMI}\n"
            f"- Goal: {goal}\n"
            f"- Diet Type: {diet_type.capitalize()}\n"
            f"- Personalization Seed: {seed}\n\n"
            f"Rules:\n"
            f"- You MUST only use foods from the list provided.\n"
            f"- Make 3 meals and 2 snacks per day.\n"
            f"- Do not repeat the exact same set of items every day.\n"
            f"- Keep it goal-aligned, structured, and engaging with bullet points and emojis."
        )

        ai_response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Generate my personalized meal plan."}
                ]
            }
        )

        reply = ai_response.json()["choices"][0]["message"]["content"]

        used_foods = []
        for name in food_names:
            if name.lower() in reply.lower():
                used_foods.append(food_name_to_doc[name.lower()])

        meal_ids = list(meals_collection.find().limit(3))
        if len(meal_ids) < 3:
            return {"error": "Define at least 3 meals in 'meals' collection."}

        meal_plan = []
        for idx, meal_doc in enumerate(meal_ids):
            portion = used_foods[idx::3][:5]
            meal_plan.append({
                "meals": meal_doc["_id"],
                "foodsList": [
                    {
                        "food": food["_id"],
                        "serving": 0,
                        "details": {
                            "protein": food.get("protein", ""),
                            "weight": food.get("weight", ""),
                            "cals": food.get("cals", ""),
                            "carbs": food.get("carbs", ""),
                            "zinc": food.get("zinc", ""),
                            "iron": food.get("iron", ""),
                            "magnesium": food.get("magnesium", ""),
                            "sulphur": food.get("sulphur", ""),
                            "fats": food.get("fats", ""),
                            "others": food.get("others", "")
                        },
                        "completed": False
                    } for food in portion
                ]
            })

        mealplans_collection.insert_one({
            "created_by": ObjectId(data.trainerId),
            "created_for": ObjectId(data.userId),
            "for_date": datetime.utcnow(),
            "mealPlan": meal_plan,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None
        })

        return {
            "status": "success",
            "message": f"Meal plan generated for user {data.userId}",
            "used_foods": [f["name"] for f in used_foods]
        }

    except Exception as e:
        return {"error": str(e)}
