import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use a large context model
model = genai.GenerativeModel("gemini-2.5-pro")

def main():
    print("Loading data...")
    try:
        with open("data/tata_bfsi_data.json", "r") as f:
            scraped_data = json.load(f)
    except:
        print("Crawler output might be incomplete. Trying to parse partial json if needed...")
        with open("data/tata_bfsi_data.json", "r") as f:
            content = f.read().strip()
            if not content.endswith("]"):
                if content.endswith(","):
                    content = content[:-1]
                content += "]"
            scraped_data = json.loads(content)

    print(f"Loaded {len(scraped_data)} scraped pages.")

    with open("eval_dataset.json", "r") as f:
        eval_dataset = json.load(f)

    # Prepare context
    context_chunks = []
    for page in scraped_data:
        title = page.get("title", "")
        text = page.get("text", "")
        url = page.get("url", "")
        context_chunks.append(f"Title: {title}\nURL: {url}\nContent: {text}\n")
    
    full_context = "\n---\n".join(context_chunks)
    
    # Generate Ground Truths
    ground_truths = []
    for item in eval_dataset:
        print(f"Generating GT for Q{item['id']}: {item['question']}")
        prompt = f"""
        You are a financial expert reading Tata Capital's website data.
        Based ONLY on the provided context, please answer the following question accurately and concisely.
        If the answer is not fully in the context, use your general knowledge but mention that it might not be in the exact provided pages.
        
        Question: {item['question']}
        
        Context:
        {full_context[:1000000]} # Limit to 1M chars just in case, but usually small
        """
        
        response = model.generate_content(prompt)
        gt_answer = response.text.strip()
        
        ground_truths.append({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "ground_truth": gt_answer
        })

    with open("eval_dataset_gt.json", "w") as f:
        json.dump(ground_truths, f, indent=4)
    print("Saved ground truths to eval_dataset_gt.json")

if __name__ == "__main__":
    main()
