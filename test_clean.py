from ingest import clean_page_text
import json

with open('data/tata_bfsi_data.json', 'r') as f:
    data = json.load(f)

for item in data:
    if "hidden-charges-in-personal-loan" in item["url"]:
        original = item["text"]
        cleaned = clean_page_text(original)
        print("ORIGINAL LENGTH:", len(original))
        print("CLEANED LENGTH:", len(cleaned))
        print("Does cleaned mention 'Personal loan for all your needs'? ", "Personal loan for all your needs" in cleaned)
        break
