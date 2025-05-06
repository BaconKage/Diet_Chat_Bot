from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()

app = FastAPI()

# Enable CORS for all origins (adjust in prod)
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

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
foods_collection = client["my_gym"]["foods"]

# Food recommendation logic
def recommend_foods(goal, diet_type):
    query = {
        "is_private": False,
        "type": {"$regex": diet_type, "$options": "i"}
    }
    all_foods = list(foods_collection.find(query))

    if goal.lower() == "lose fat":
        sorted_foods = sorted(all_foods, key=lambda x: float(x.get("cals", "0")))
    elif goal.lower() == "gain muscle":
        sorted_foods = sorted(all_foods, key=lambda x: float(x.get("protein", "0")), reverse=True)
    elif goal.lower() == "stay fit":
        sorted_foods = sorted(all_foods, key=lambda x: abs(float(x.get("cals", "0")) - 300))
    else:
        sorted_foods = all_foods

    return sorted_foods[:5]  # Top 5

@app.post("/ai/chat")
async def chat_endpoint(data: ChatRequest):
    try:
        # Extract basic keywords from message (basic fallback, better if parsed from structured data)
        text = data.message.lower()
        goal = "gain muscle" if "gain" in text else "lose fat" if "lose" in text else "stay fit"
        diet_type = "vegetarian" if "vegetarian" in text else "non-vegetarian" if "non" in text else "vegan"

        foods = recommend_foods(goal, diet_type)

        if not foods:
            return {"reply": "No matching foods found in the database."}

        plan = f"🍽️ {data.planType.capitalize()} Diet Plan for Goal: {goal.title()}\n\n"
        for food in foods:
            plan += f"✅ {food['name']} — {food['cals']} kcal, {food['protein']}g protein, {food.get('carbs', 'N/A')}g carbs\n"

        plan += "\n💧 Stay hydrated and aim for consistency!"

        return {"reply": plan}

    except Exception as e:
        return {"error": str(e)}
