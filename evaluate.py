import json
import time
import asyncio
import os
import psutil
import urllib.request
import urllib.error

# Bypass SSL Verification for HuggingFace behind corporate firewalls
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
from llm_client import AsyncOllamaClient
from agents.knowledge_agent import knowledge_retrieval_agent

MODELS_TO_TEST = ["deepseek-r1:1.5b", "llama3.2:3b", "qwen2.5:3b"]
EVAL_DATASET = "eval_dataset.json"
RESULTS_FILE = "eval_results.json"

def unload_model(model_name):
    print(f"Unloading model {model_name} from memory...")
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            pass
    except Exception as e:
        print(f"Failed to unload {model_name}: {e}")

async def run_evaluation():
    with open(EVAL_DATASET, "r") as f:
        dataset = json.load(f)
    
    # Load existing results if any to avoid re-running everything
    results = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as f:
                results = json.load(f)
        except:
            pass
            
    completed_pairs = {(r["model"], r["question_id"]) for r in results}
    
    for model in MODELS_TO_TEST:
        print(f"\n========== EVALUATING MODEL: {model} ==========")
        client = AsyncOllamaClient(default_model=model)
        
        for item in dataset:
            if (model, item["id"]) in completed_pairs:
                print(f"Skipping Q{item['id']} for {model} (already completed)")
                continue
                
            print(f"Testing Q{item['id']}: {item['question']}")
            
            # 1. RAG Retrieval
            context = await knowledge_retrieval_agent(item['question'], k=3)
            
            # 2. LLM Inference
            prompt = f"Context:\n{context}\n\nQuestion: {item['question']}\n\nAnswer based on the context:"
            
            start_time = time.time()
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss / 1024 / 1024
            
            try:
                # Use raw completion call to capture full metrics with a MASSIVE timeout for CPU
                endpoint = f"{client.chat.completions.base_url}/api/generate"
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                }
                
                # Using 1800 seconds (30 minutes) timeout for CPU-bound DeepSeek reasoning
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    endpoint,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                def sync_post():
                    with urllib.request.urlopen(req, timeout=1800) as response:
                        return json.loads(response.read().decode("utf-8"))
                        
                response_data = await asyncio.to_thread(sync_post)
                
                end_time = time.time()
                mem_after = process.memory_info().rss / 1024 / 1024
                
                latency = end_time - start_time
                response_text = response_data.get("response", "")
                
                eval_count = response_data.get("eval_count", 0)
                eval_duration = response_data.get("eval_duration", 0) / 1e9
                tps = (eval_count / eval_duration) if eval_duration > 0 else 0
                
                result_entry = {
                    "model": model,
                    "question_id": item["id"],
                    "question": item["question"],
                    "category": item["category"],
                    "retrieved_context": context,
                    "response": response_text,
                    "metrics": {
                        "latency_seconds": round(latency, 2),
                        "tokens_generated": eval_count,
                        "tokens_per_second": round(tps, 2),
                        "memory_used_mb": round(mem_after, 2)
                    }
                }
                results.append(result_entry)
                
                # Save incrementally so we don't lose data on crash
                with open(RESULTS_FILE, "w") as f:
                    json.dump(results, f, indent=4)
                
            except Exception as e:
                print(f"Error evaluating {model} on Q{item['id']}: {e}")
                
        # Unload the model before moving to the next one to prevent Out-Of-Memory crashes
        unload_model(model)
        # Give the OS a few seconds to reclaim memory
        await asyncio.sleep(5)
        
    print(f"\nEvaluation complete! Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
