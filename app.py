# fastapi/app.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    planType: str

@app.post("/ai/chat")
async def chat_endpoint(data: ChatRequest):
    return {
        "reply": f"Here is your {data.planType} plan based on: '{data.message}'"
    }