import json
import urllib.request

def ollama_generate(prompt):
    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        res = json.loads(response.read().decode("utf-8"))
        return res.get("response", "")

def main():
    print("Loading Ground Truths...")
    with open("eval_dataset_gt.json", "r") as f:
        ground_truths = json.load(f)
    
    gt_dict = {item['id']: item['ground_truth'] for item in ground_truths}
    
    print("Loading Evaluation Results...")
    with open("eval_results.json", "r") as f:
        eval_results = json.load(f)
        
    semantic_scores = []
    
    for res in eval_results:
        q_id = res['question_id']
        question = res['question']
        model_name = res['model']
        response = res['response']
        
        gt_answer = gt_dict.get(q_id)
        if not gt_answer:
            continue
            
        print(f"Scoring {model_name} on Q{q_id}...")
        
        prompt = f"""You are an expert evaluating a chatbot's response.
Compare the actual response from the chatbot with the Ground Truth answer.
Rate the Semantic Correctness & Similarity on a scale of 0 to 10.
0 means completely wrong or irrelevant.
10 means perfect semantic match with all facts present.

Question: {question}

Ground Truth:
{gt_answer}

Chatbot Response ({model_name}):
{response}

Provide ONLY the integer score (0-10) in your response, nothing else. No text, no explanation. Just the number.
"""
        
        try:
            score_str = ollama_generate(prompt).strip()
            # extract only digits
            score_digits = ''.join(filter(str.isdigit, score_str))
            score = int(score_digits) if score_digits else 0
            score = min(10, max(0, score)) # clamp 0-10
        except Exception as e:
            print(f"Error scoring: {e}. Output was {score_str}. Defaulting to 0.")
            score = 0
            
        res['metrics']['semantic_score'] = score
        semantic_scores.append(res)
        
    with open("eval_results_with_semantics.json", "w") as f:
        json.dump(semantic_scores, f, indent=4)
        
    print("Saved scored results to eval_results_with_semantics.json")
    
    summary = {}
    for res in semantic_scores:
        m = res['model']
        if m not in summary:
            summary[m] = {'total_score': 0, 'count': 0, 'total_latency': 0, 'total_tps': 0}
        summary[m]['total_score'] += res['metrics']['semantic_score']
        summary[m]['count'] += 1
        summary[m]['total_latency'] += res['metrics']['latency_seconds']
        summary[m]['total_tps'] += res['metrics']['tokens_per_second']
        
    print("\n--- Model Comparison ---")
    for m, data in summary.items():
        avg_score = data['total_score'] / data['count']
        avg_lat = data['total_latency'] / data['count']
        avg_tps = data['total_tps'] / data['count']
        print(f"Model: {m}")
        print(f"  Avg Semantic Score (out of 10): {avg_score:.2f}")
        print(f"  Avg Latency (s): {avg_lat:.2f}")
        print(f"  Avg Tokens/s: {avg_tps:.2f}")
        print("-" * 25)

if __name__ == "__main__":
    main()
