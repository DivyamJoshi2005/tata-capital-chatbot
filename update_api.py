with open("api.py", "r") as f:
    content = f.read()

content = content.replace(
    "class ChatRequest(BaseModel):\n    message: str\n    image_base64: Optional[str] = None\n    session_id: Optional[str] = None",
    "class ChatRequest(BaseModel):\n    message: str\n    image_base64: Optional[str] = None\n    session_id: Optional[str] = None\n    model_name: Optional[str] = None"
)

content = content.replace(
    "reply = await master_agent(final_message, client, passed_history=history, model_name=model_name)",
    "target_model = request.model_name if request.model_name else model_name\n        reply = await master_agent(final_message, client, passed_history=history, model_name=target_model)"
)

# Add endpoint for eval results
eval_endpoint = """
@app.get("/api/eval-results")
async def get_eval_results():
    try:
        import json
        with open("eval_results.json", "r") as f:
            return json.load(f)
    except Exception as e:
        return []
"""
content = content.replace("# --- Serve the React frontend (production build) ---", eval_endpoint + "\n# --- Serve the React frontend (production build) ---")

with open("api.py", "w") as f:
    f.write(content)
