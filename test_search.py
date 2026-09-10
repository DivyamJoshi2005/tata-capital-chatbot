import json

with open('data/tata_bfsi_data.json', 'r') as f:
    data = json.load(f)

for item in data:
    if "personal" in item["url"].lower() or "personal" in item["title"].lower() or "personal" in item["text"].lower():
        text = item["text"].lower()
        if "lakh" in text and "personal loan" in text:
            # try to extract context
            idx = text.find("personal loan")
            # print snippet
            print(f"URL: {item['url']}")
            print(f"TITLE: {item['title']}")
            start = max(0, idx - 100)
            end = min(len(text), idx + 200)
            print(f"SNIPPET: {text[start:end]}\n")
