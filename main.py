import os
import asyncio
import json
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Import your agent functions
from agents.knowledge_agent import knowledge_retrieval_agent
from agents.conversation_agent import conversation_agent

# Use Groq instead of Gemini
# pyrefly: ignore [missing-import]
from groq import AsyncGroq

# Suppress warnings and logs
os.environ["GRPC_VERBOSITY"] = "NONE"
os.environ["GRPC_TRACE"] = "none"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" 

# --- 1. Centralized State Management ---
conversation_state = {
    "user_profile": None,
    "risk_score": None,
    "conversation_history":[]
}

# --- NEW: Consolidated Analysis Agent ---
async def run_analysis_agent(user_message: str, client: AsyncGroq) -> dict:
    """
    A single agent that performs profiling, risk assessment, and persuasion strategy selection
    in one API call using Groq JSON mode for maximum efficiency.
    """
    prompt = f"""
    You are a multi-tasking financial analysis AI. Analyze the user's message and provide a complete analysis.
    User Message: "{user_message}"

    Your tasks are:
    1.  **Profile the User:** Determine their sentiment, financial literacy, and persona.
    2.  **Assess Risk:** Provide a preliminary risk score (Low, Medium, High) and a brief justification.
    3.  **Select a Persuasion Tactic:** Choose the best tactic to persuade them to take a loan.

    Return your complete analysis ONLY as a single, valid JSON object with three main keys:
    - "profile": A JSON object with "sentiment", "literacy", and "persona".
    - "risk": A JSON object with "risk_score" and "reasoning".
    - "tactic": A string containing the chosen persuasion tactic.
    """
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a JSON analysis bot. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        cleaned_response = response.choices[0].message.content.strip()
        analysis = json.loads(cleaned_response)
        return analysis
    except Exception as e:
        print(f"Error in consolidated analysis agent: {e}")
        # Return a safe default structure on error
        return {
            "profile": {"sentiment": "unknown", "literacy": "unknown", "persona": "unknown"},
            "risk": {"risk_score": "Medium", "reasoning": "Default score due to analysis error."},
            "tactic": "Build Trust through Transparency"
        }

# --- 2. The Master Agent (Orchestrator) - UPDATED ---
async def master_agent(user_message: str, client: AsyncGroq, passed_history: list = None):
    print("\n🧠 Step 1: Running analysis and knowledge retrieval...")

    # Run the consolidated analysis and knowledge retrieval in parallel
    analysis_task = asyncio.create_task(run_analysis_agent(user_message, client))
    knowledge_task = asyncio.create_task(knowledge_retrieval_agent(user_message))

    # Await both tasks
    analysis_result, product_info = await asyncio.gather(analysis_task, knowledge_task)
    
    # Deconstruct the analysis results
    user_profile = analysis_result['profile']
    risk_info = analysis_result['risk']
    persuasion_tactic = analysis_result['tactic']

    # Update state
    conversation_state["user_profile"] = user_profile
    conversation_state["risk_score"] = risk_info
    print(f"   - Profile: {user_profile}")
    print(f"   - Risk: {risk_info}")
    print(f"   - Tactic: {persuasion_tactic}")

    history = passed_history if passed_history is not None else conversation_state["conversation_history"]

    print("💬 Step 2: Generating final response...")
    final_response = await conversation_agent(
        user_message,
        product_info,
        persuasion_tactic,
        user_profile,
        history,
        client
    )

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": final_response})

    return final_response

# --- 3. Main Application Loop ---
async def main():
    print("🚀 Initializing AI Assistant with Groq (Llama 3.3 70B)...")
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env file.")
        return
    
    client = AsyncGroq(api_key=api_key)
    print("✅ AI Assistant is ready.\n")
    
    print("🤖 Tata Capital AI Assistant (Groq Llama-3 Powered)\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        try:
            reply = await master_agent(user_input, client)
            print(f"Assistant: {reply}")
        except Exception as e:
            print(f"🚨 An error occurred: {e}")
            print("Assistant: I'm sorry, I encountered an issue. Please try rephrasing your question.")

if __name__ == "__main__":
    asyncio.run(main())