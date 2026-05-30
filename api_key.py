import os
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["GRPC_TRACE"] = "none"

from dotenv import load_dotenv
import google.generativeai as genai

# Load API key
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-pro")

print("💬 Gemini Chat Started (type 'exit' to quit)\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ["exit", "quit", "bye"]:
        print("👋 Goodbye Divyam!")
        break
    
    try:
        response = model.generate_content(user_input)
        print("Gemini:", response.text, "\n")
    except Exception as e:
        print("⚠️ Error:", e, "\n")
