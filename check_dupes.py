import json
import sys

def dict_raise_on_duplicates(ordered_pairs):
    count = {}
    for k, v in ordered_pairs:
        if k in count:
            print(f"Duplicate key found: {k}")
            sys.exit(1)
        count[k] = 1
    return dict(ordered_pairs)

try:
    with open("eval_results_with_semantics.json", "r") as f:
        json.load(f, object_pairs_hook=dict_raise_on_duplicates)
    print("No duplicate keys")
except Exception as e:
    print(f"Error: {e}")
