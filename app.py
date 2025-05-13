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

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["dietPlanner"]
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

    meals = list(meals_collection.find())
    foods = list(foods_collection.find())

    if not meals or not foods:
        return {"error": "Missing meals or food entries in the database."}

    meal_plan = []
    for meal in meals:
        selected_foods = random.sample(foods, min(3, len(foods)))
        foods_list = []
        for food in selected_foods:
            food_detail_id = ObjectId()
            food_entry_id = ObjectId()
            food_entry = {
                "_id": food_entry_id,
                "food": ObjectId(food["_id"]),
                "serving": 1,
                "details": {
                    "_id": food_detail_id,
                    "protein": food["details"].get("protein", ""),
                    "weight": food["details"].get("weight", ""),
                    "cals": food["details"].get("cals", ""),
                    "carbs": food["details"].get("carbs", ""),
                    "zinc": food["details"].get("zinc", ""),
                    "iron": food["details"].get("iron", ""),
                    "magnesium": food["details"].get("magnesium", ""),
                    "sulphur": food["details"].get("sulphur", ""),
                    "fats": food["details"].get("fats", ""),
                    "others": food["details"].get("others", "")
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
