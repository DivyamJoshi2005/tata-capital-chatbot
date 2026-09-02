import os
import io
import base64
import traceback

# Suppress warnings
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["GRPC_TRACE"] = "none"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from groq import AsyncGroq
from PIL import Image
import pytesseract

import database

# Initialize FastAPI app
app = FastAPI(title="Tata Capital Chatbot API")

# Enable CORS for local development (Vite dev server on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables and configure LLM Client (Ollama or Groq)
load_dotenv()
from llm_client import get_llm_client
client, model_name, provider_name = get_llm_client()

# --- Auto-generate Chroma index if missing ---
from ingest import CHROMA_DB_PATH, create_knowledge_base_from_json
if not os.path.exists(CHROMA_DB_PATH):
    print("⚠️  Chroma DB not found. Running ingestion automatically...")
    create_knowledge_base_from_json()
    print("✅ Ingestion complete.")

# Import the master_agent AFTER configuring everything
from main import master_agent

# --- Pydantic Models ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    image_base64: Optional[str] = None
    session_id: Optional[str] = None
    model_name: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    title: str

def extract_text_from_base64(image_b64: str) -> str:
    """Decodes a base64 image and extracts text using Tesseract OCR."""
    try:
        # Strip header if present (e.g. "data:image/png;base64,")
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
            
        img_data = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        print(f"OCR Error (Is Tesseract installed on your system?): {e}")
        return "[Image received, but OCR failed. Please ensure Tesseract is installed or provide text directly.]"

# --- API Endpoints ---
@app.get("/api/sessions")
async def get_sessions():
    return database.get_sessions()

@app.post("/api/sessions")
async def create_session():
    session_id = database.create_session()
    return {"id": session_id, "title": "New Chat"}

@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    return database.get_session_history(session_id)

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    database.delete_session(session_id)
    return {"status": "success", "message": "Session deleted"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        session_id = request.session_id
        if not session_id:
            # Fallback if the frontend didn't send one
            session_id = database.create_session()
            
        # 1. Process Image if present
        final_message = request.message
        if request.image_base64:
            extracted_text = extract_text_from_base64(request.image_base64)
            if extracted_text:
                final_message += f"\n\n[Attached Image OCR Text]: {extracted_text}"

        # 2. Get existing history for context
        history = database.get_session_history(session_id)
        
        # We need to update the title if it's the very first message
        if len(history) == 0:
            # Generate a short title from the first message
            title = request.message[:30] + "..." if len(request.message) > 30 else request.message
            database.update_session_title(session_id, title)
            
        # Add user's message to database
        database.add_message(session_id, "user", final_message)

        # 3. Call the Agent (Ollama or Groq)
        target_model = request.model_name if request.model_name else model_name
        
        if target_model == "compare_all":
            import time
            import urllib.request
            import json
            
            def unload_all():
                for m in ["deepseek-r1:1.5b", "llama3.2:3b", "qwen2.5:3b"]:
                    try:
                        req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps({"model": m, "keep_alive": 0}).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                        urllib.request.urlopen(req, timeout=2)
                    except: pass
                    
            combined_reply = "Here is the comparison across all 3 models:\n\n"
            for m in ["deepseek-r1:1.5b", "llama3.2:3b", "qwen2.5:3b"]:
                unload_all()
                t0 = time.time()
                ans = await master_agent(final_message, client, passed_history=history, model_name=m)
                t1 = time.time()
                combined_reply += f"### 🤖 `{m}`\n{ans}\n\n*⏱️ Generated in {round(t1-t0, 1)}s*\n\n---\n\n"
            
            reply = combined_reply
        else:
            reply = await master_agent(final_message, client, passed_history=history, model_name=target_model)

        import re
        # Parse `<think>` tags into HTML details tags for the frontend
        def format_think_tags(text):
            pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
            replacement = r'<details className="mb-4 bg-[#1e1e1e] border border-[#333] rounded-lg overflow-hidden"><summary className="bg-[#2a2a2a] px-4 py-2 cursor-pointer text-sm font-semibold text-blue-400 hover:bg-[#333] transition-colors">🧠 View Model Reasoning</summary><div className="p-4 text-xs text-gray-400 italic bg-[#1e1e1e] whitespace-pre-wrap max-h-96 overflow-y-auto"></div></details>'
            # Wait, react-markdown + rehype-raw requires standard HTML class attributes
            # So `class="mb-4..."` instead of `className`!
            replacement = r'<details class="mb-4 bg-[#1e1e1e] border border-[#333] rounded-lg overflow-hidden"><summary class="bg-[#2a2a2a] px-4 py-2 cursor-pointer text-sm font-semibold text-blue-400 hover:bg-[#333] transition-colors outline-none select-none">🧠 View Model Reasoning</summary><div class="p-4 text-xs text-gray-400 italic bg-[#1e1e1e] whitespace-pre-wrap max-h-96 overflow-y-auto"></div></details>'
            return pattern.sub(replacement, text)

        reply = format_think_tags(reply)
        
        # Add assistant's reply to database
        database.add_message(session_id, "assistant", reply)

        # Return updated history
        updated_history = database.get_session_history(session_id)
        return {
            "reply": reply,
            "session_id": session_id,
            "updated_history": updated_history,
        }
    except Exception as e:
        print(f"Error in /api/chat: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing your request.",
        )



@app.get("/api/eval-results")
async def get_eval_results():
    try:
        import json
        with open("eval_results.json", "r") as f:
            return json.load(f)
    except Exception as e:
        return []

# --- Serve the React frontend (production build) ---
DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")

if os.path.isdir(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(os.path.join(DIST_DIR, "favicon.svg"))

    @app.get("/icons.svg")
    async def icons():
        return FileResponse(os.path.join(DIST_DIR, "icons.svg"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
