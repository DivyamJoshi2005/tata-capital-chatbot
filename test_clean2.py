from ingest import clean_page_text
import json

with open('data/tata_bfsi_data.json', 'r') as f:
    data = json.load(f)

for item in data:
    if "hidden-charges-in-personal-loan" in item["url"]:
        original = item["text"]
        start = original.find("Personal Loan Home Loan Business Loan Vehicle Loan")
        end = -1
        for m in ["Register as a Selling Agent.", "Explore all Business Loans", "Pioneering Climate Finance"]:
            pos = original.find(m, start)
            if pos != -1:
                e = pos + len(m)
                if end == -1 or e < end:
                    end = e
        print("CUT TEXT:\n", original[start:end])
        break
