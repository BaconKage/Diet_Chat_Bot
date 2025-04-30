from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS config (allow any origin for testing, tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # use ["https://yourdomain.com"] in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Health check route for Render
@app.get("/")
def read_root():
    return {"status": "FastAPI backend is live"}

# ✅ Chat request schema
class ChatRequest(BaseModel):
    message: str
    planType: str  # e.g., "week", "month", "year"

# ✅ Chat endpoint
@app.post("/ai/chat")
async def chat_endpoint(req: ChatRequest):
    message = req.message.lower()
    plan = req.planType.lower()

    # Simple dummy logic (replace with real AI/gen logic)
    if "fat loss" in message:
        response = f"Here is your {plan} plan for fat loss: eat high-protein meals, reduce sugar, and do cardio 3x a week."
    elif "muscle" in message:
        response = f"Here is your {plan} plan for muscle gain: lift heavy 5x a week, eat in a calorie surplus, focus on compound lifts."
    else:
        response = f"Sorry, I couldn’t understand the goal in your message. Please try asking again more clearly."

    return {"reply": response}
