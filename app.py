from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
import os
import requests
from datetime import datetime
from bson import ObjectId
from collections import defaultdict
import re

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB config
MONGO_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(MONGO_URI)
db = client["my_gym"]
users_collection = db["users"]
foods_collection = db["foods"]
meals_collection = db["meals"]
mealplans_collection = db["mealplans"]

# Groq API config
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama3-8b-8192"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

class PlanRequest(BaseModel):
    trainerId: str
    userId: str
    planType: str

# Match foods from MongoDB
def get_allowed_foods(diet_type):
    allowed_types = [diet_type.capitalize()]
    if diet_type.lower() != "non-vegetarian":
        allowed_types.append("Vegetarian")
    return list(foods_collection.find({"type": {"$in": allowed_types}}))

def match_foods(text, foods):
    matched = []
    food_lookup = {f["name"].lower(): f for f in foods}
    for name in food_lookup:
        if re.search(rf"\b{re.escape(name)}\b", text.lower()):
            matched.append(food_lookup[name])
    return matched

def build_mealPlan_structure(foods, meal_docs):
    meals_by_id = defaultdict(list)
    for food in foods:
        food_name = food["name"].lower()
        for meal in meal_docs:
            if meal["name"].lower() in food_name:
                meals_by_id[str(meal["_id"])].append({
                    "food": food["_id"],
                    "serving": 0,
                    "completed": False,
                    "details": {
                        "protein": food.get("protein", ""),
                        "weight": food.get("weight", ""),
                        "cals": food.get("cals", ""),
                        "carbs": food.get("carbs", ""),
                        "others": food.get("others", "")
                    }
                })
    return [
        {
            "meals": ObjectId(meal_id),
            "foodsList": items
        }
        for meal_id, items in meals_by_id.items()
    ]

@app.post("/ai/auto-plan")
async def generate_diet_plan(data: PlanRequest):
    try:
        user = users_collection.find_one({ "_id": ObjectId(data.userId) })
        if not user:
            return { "error": "User not found" }

        age = user.get("age", 30)
        gender = user.get("gender", "male")
        bmi = user.get("BMI", 22.0)
        goal = user.get("goal", "stay fit")
        diet_type = user.get("diet_type", "vegetarian")

        foods = get_allowed_foods(diet_type)
        food_list = "\n".join(f"- {f['name']}" for f in foods)

        system_prompt = (
            f"You are a certified AI nutritionist.\n"
            f"Generate a {data.planType} vegetarian diet plan for a {age}-year-old {gender} with BMI {bmi} and goal '{goal}'.\n"
            f"⚠️ Use ONLY foods from this list:\n{food_list}\n"
            f"Design a weekly meal plan with 3 meals and 2 snacks per day, hydration advice, and a motivational tip."
        )

        response = requests.post(
            GROQ_API_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Generate the diet plan."}
                ]
            }
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"]

        matched_foods = match_foods(reply, foods)
        meal_docs = list(meals_collection.find({}))
        structured_plan = build_mealPlan_structure(matched_foods, meal_docs)

        mealplans_collection.insert_one({
            "created_by": ObjectId(data.trainerId),
            "created_for": ObjectId(data.userId),
            "for_date": datetime.utcnow(),
            "mealPlan": structured_plan,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None
        })

        return { "reply": reply }

    except Exception as e:
        return { "error": str(e) }
