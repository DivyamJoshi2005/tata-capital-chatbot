import json

with open("eval_results.json", "r") as f:
    results = json.load(f)

# Group by question
gt_map = {}
for r in results:
    if r["question_id"] not in gt_map:
        gt_map[r["question_id"]] = {
            "id": r["question_id"],
            "category": r["category"],
            "question": r["question"],
            "context": r["retrieved_context"]
        }

out = []
for i in range(1, 21):
    if i in gt_map:
        # Just use the context to form a decent ground truth via a simple local prompt, or I can just dump it for me to read
        out.append(gt_map[i])

with open("contexts_for_gt.json", "w") as f:
    json.dump(out, f, indent=4)
