from ingest import clean_page_text
import json

with open('data/tata_bfsi_data.json', 'r') as f:
    data = json.load(f)

for item in data:
    if "personal-loan.html" in item["url"]:
        print("URL:", item["url"])
        original = item["text"]
        cleaned = clean_page_text(original)
        
        print("IN ORIGINAL:", "35 lakh" in original.lower())
        print("IN CLEANED:", "35 lakh" in cleaned.lower())
