from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime
import requests
import os

# Load environment variables
load_dotenv()

# FastAPI setup
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URI = os.getenv("FOOD_DB_URI")
client = MongoClient(MONGO_URI)
db = client["my_gym"]
users_collection = db["users"]
foods_collection = db["foods"]
mealplans_collection = db["mealplans"]
meals_collection = db["meals"]

# GROQ setup
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

# Helper to match foods
def match_foods(ai_text, food_docs):
    matched = []
    for food in food_docs:
        if food["name"].lower() in ai_text.lower():
            matched.append({
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
            })
    return matched

@app.post("/ai/auto-plan")
async def auto_generate_diet(data: PlanRequest):
    try:
        user = users_collection.find_one({ "_id": ObjectId(data.userId) })
        if not user:
            return { "error": "User not found in DB." }

        # Pull user profile info
        age = user.get("age", 30)
        gender = user.get("gender", "male")
        bmi = user.get("BMI", 22.0)
        goal = user.get("goal", "stay fit")
        diet_type = user.get("diet_type", "vegetarian").lower()

        # Filter allowed foods
        types = [diet_type.capitalize()]
        if diet_type != "non-vegetarian":
            types.append("Vegetarian")
        foods = list(foods_collection.find({ "type": { "$in": types } }))
        food_names = [f["name"] for f in foods]
        food_list = "\n".join([f"- {f}" for f in food_names])

        # Generate prompt
        system_prompt = (
            f"You are a certified AI nutritionist.\n"
            f"Create a {data.planType} meal plan using ONLY the foods below:\n"
            f"{food_list}\n\n"
            f"❗ Do NOT use items not listed.\n"
            f"Include 3 meals and 2 snacks per day.\n"
            f"Format must mention meal names clearly (e.g. Breakfast, Lunch, Snack).\n"
            f"Use emojis and bullet points to keep it engaging.\n"
        )

        # AI call
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
        ai_reply = response.json()["choices"][0]["message"]["content"]

        # Match food IDs to response
        structured_plan = []
        all_meals = list(meals_collection.find({}))
        for meal in all_meals:
            meal_name = meal.get("name", "").lower()
            if meal_name in ai_reply.lower():
                matched_foods = match_foods(ai_reply, foods)
                structured_plan.append({
                    "meals": meal["_id"],
                    "foodsList": matched_foods
                })

        # Insert into mealplans
        mealplans_collection.insert_one({
            "created_by": ObjectId(data.trainerId),
            "created_for": ObjectId(data.userId),
            "for_date": datetime.utcnow(),
            "mealPlan": structured_plan,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "deleted_at": None
        })

        return {
            "message": "Plan saved to database.",
            "meals_matched": len(structured_plan),
            "foods_used": sum(len(m["foodsList"]) for m in structured_plan)
        }

    except Exception as e:
        return { "error": str(e) }
