with open("api.py", "r") as f:
    content = f.read()

new_logic = """
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
                    
            combined_reply = "Here is the comparison across all 3 models:\\n\\n"
            for m in ["deepseek-r1:1.5b", "llama3.2:3b", "qwen2.5:3b"]:
                unload_all()
                t0 = time.time()
                ans = await master_agent(final_message, client, passed_history=history, model_name=m)
                t1 = time.time()
                combined_reply += f"### 🤖 `{m}`\\n{ans}\\n\\n*⏱️ Generated in {round(t1-t0, 1)}s*\\n\\n---\\n\\n"
            
            reply = combined_reply
        else:
            reply = await master_agent(final_message, client, passed_history=history, model_name=target_model)
"""

content = content.replace(
    "target_model = request.model_name if request.model_name else model_name\n        reply = await master_agent(final_message, client, passed_history=history, model_name=target_model)",
    new_logic.strip()
)

with open("api.py", "w") as f:
    f.write(content)
