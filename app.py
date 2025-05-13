from bson import ObjectId
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional
import random
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI not set in environment variables!")

client = MongoClient(MONGO_URI)
db = client["my_gym"]  # <- FIXED
foods_collection = db["foods"]
meals_collection = db["meals"]
plans_collection = db["mealPlans"]


class PlanRequest(BaseModel):
    trainerId: str
    userId: str
    planType: Optional[str] = "week"

@app.post("/ai/auto-plan")
async def generate_plan(request: PlanRequest):
    trainer_id = request.trainerId
    user_id = request.userId
    plan_type = request.planType or "week"

    # ✅ Allow regeneration: no blocking for existing plan
    meals = list(meals_collection.find())
    foods = list(foods_collection.find())

    if not meals or not foods:
        return {"error": "Missing meals or food entries in the database."}

    used_food_ids = set()
    meal_plan = []

    for meal in meals:
        available_foods = [f for f in foods if str(f["_id"]) not in used_food_ids]
        if not available_foods:
            break  # no more foods to choose from

        selected_foods = random.sample(available_foods, min(3, len(available_foods)))
        foods_list = []

        for food in selected_foods:
            food_id_str = str(food["_id"])
            used_food_ids.add(food_id_str)

            food_entry = {
                "_id": ObjectId(),
                "food": ObjectId(food["_id"]),
                "serving": 1,
                "details": {
                    "_id": ObjectId(),
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
            }
            foods_list.append(food_entry)

        meal_plan.append({
            "_id": ObjectId(),
            "meals": ObjectId(meal["_id"]),
            "foodsList": foods_list
        })

    now = datetime.utcnow()
    doc = {
        "for_date": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "created_by": ObjectId(trainer_id),
        "created_for": ObjectId(user_id),
        "deleted_at": None,
        "created_at": now,
        "updated_at": now,
        "mealPlan": meal_plan,
        "__v": 1
    }

    result = plans_collection.insert_one(doc)
    return {"message": "Plan created successfully", "planId": str(result.inserted_id)}
