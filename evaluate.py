import json
import time
import asyncio
import os
import sys
import psutil
import urllib.request
import requests

# Bypass SSL Verification for HuggingFace behind corporate firewalls
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
from llm_client import AsyncOllamaClient
from agents.knowledge_agent import knowledge_retrieval_agent

MODELS_TO_TEST = ["deepseek-r1:1.5b", "llama3.2:3b", "qwen2.5:3b"]
EVAL_DATASET = "eval_dataset.json"
RESULTS_FILE = "eval_results.json"
OLLAMA_URL = "http://localhost:11434/api/generate"

def unload_model(model_name):
    print(f"\nUnloading model {model_name} from memory...")
    try:
        requests.post(OLLAMA_URL, json={"model": model_name, "keep_alive": 0}, timeout=180)
    except Exception as e:
        print(f"Failed to unload {model_name}: {e}")

async def run_evaluation():
    with open(EVAL_DATASET, "r") as f:
        dataset = json.load(f)
    
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
        
        for item in dataset:
            if (model, item["id"]) in completed_pairs:
                print(f"Skipping Q{item['id']} for {model} (already completed)")
                continue
                
            print(f"\nTesting Q{item['id']}: {item['question']}")
            
            # 1. RAG Retrieval
            context = await knowledge_retrieval_agent(item['question'], k=3)
            
            # 2. LLM Inference
            prompt = f"Context:\n{context}\n\nQuestion: {item['question']}\n\nAnswer based on the context:"
            
            start_time = time.time()
            process = psutil.Process(os.getpid())
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.0}
            }
            
            response_text = ""
            eval_count = 0
            eval_duration = 0
            
            try:
                print("Response/Thinking: ", end="", flush=True)
                with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=180) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                text_chunk = chunk["response"]
                                response_text += text_chunk
                                sys.stdout.write(text_chunk)
                                sys.stdout.flush()
                            
                            if chunk.get("done"):
                                eval_count = chunk.get("eval_count", 0)
                                eval_duration = chunk.get("eval_duration", 0) / 1e9
                                break
                                
                            # Timeout to prevent hanging (e.g. infinite loop in <think>)
                            # Stop after 3 minutes for a single question
                            if time.time() - start_time > 180:
                                print("\n\n[TIMEOUT] Model took longer than 3 minutes. Aborting this question to prevent hang.")
                                break
                print() # newline
                
            except Exception as e:
                print(f"\n[ERROR] Error evaluating {model} on Q{item['id']}: {e}")
                
            end_time = time.time()
            mem_after = process.memory_info().rss / 1024 / 1024
            
            latency = end_time - start_time
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
            
            # Save incrementally
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f, indent=4)
                
        # Unload the model before moving to the next one
        unload_model(model)
        await asyncio.sleep(2)
        
    print(f"\nEvaluation complete! Results saved to {RESULTS_FILE}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
