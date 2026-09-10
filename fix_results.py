import json
import os

if os.path.exists("eval_results.json"):
    with open("eval_results.json", "r") as f:
        results = json.load(f)
    
    # Keep only results that have a real response
    clean_results = [r for r in results if len(r.get("response", "")) > 10]
            
    with open("eval_results.json", "w") as f:
        json.dump(clean_results, f, indent=4)
    print(f"Cleaned up! Kept {len(clean_results)} valid results.")
