from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from typing import Optional, List

app = FastAPI(title="LMCache GPT-OSS", version="1.0.0")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    response: str
    cached: bool = False

@app.get("/")
async def root():
    return {
        "service": "LMCache GPT-OSS",
        "model": os.getenv("MODEL_ID", "openai/gpt-oss-20b"),
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Aquí se integraría LMCache para caching
        # Por ahora es un placeholder
        response = f"Respuesta simulada para {len(request.messages)} mensajes usando {os.getenv('MODEL_ID')}"
        
        return ChatResponse(
            response=response,
            cached=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("LMCACHE_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
