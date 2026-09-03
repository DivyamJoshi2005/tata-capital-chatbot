import os
import asyncio
import json
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Import your agent functions
from agents.knowledge_agent import knowledge_retrieval_agent
from agents.conversation_agent import conversation_agent
from llm_client import get_llm_client

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

# --- Consolidated Analysis Agent ---
async def run_analysis_agent(user_message: str, client, model_name: str = None) -> dict:
    """
    A single agent that performs profiling, risk assessment, and persuasion strategy
    selection in one call using JSON mode.

    Handles DeepSeek reasoning output and Markdown JSON fences safely.
    """
    prompt = f"""
    You are a multi-tasking financial analysis AI. Analyze the user's message and provide a complete analysis.
    User Message: "{user_message}"

    Your tasks are:
    1. Profile the User: Determine their sentiment, financial literacy, and persona.
    2. Assess Risk: Provide a preliminary risk score (Low, Medium, High) and a brief justification.
    3. Select a Persuasion Tactic: Choose the best tactic to persuade them to take a loan.

    Return your complete analysis ONLY as a single valid JSON object with three main keys:
    - "profile": A JSON object with "sentiment", "literacy", and "persona".
    - "risk": A JSON object with "risk_score" and "reasoning".
    - "tactic": A string containing the chosen persuasion tactic.
    """

    try:
        kwargs = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a JSON analysis bot. "
                        "Return only the JSON object. "
                        "Do not include explanations, reasoning, Markdown, or code fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
	    "max_tokens":256,
        }

        if model_name:
            kwargs["model"] = model_name

        response = await client.chat.completions.create(**kwargs)

        raw_response = response.choices[0].message.content or ""
        cleaned_response = raw_response.strip()

        # Remove DeepSeek reasoning if present.
        if "</think>" in cleaned_response:
            cleaned_response = cleaned_response.split("</think>", 1)[1].strip()

        # Remove Markdown code fences if present.
        if cleaned_response.startswith("```"):
            lines = cleaned_response.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned_response = "\n".join(lines).strip()

        # Extract the JSON object if there is still surrounding text.
        start = cleaned_response.find("{")
        end = cleaned_response.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"No valid JSON object found in model response: {raw_response[:500]}"
            )

        json_text = cleaned_response[start:end + 1]

        analysis = json.loads(json_text)

        # Validate the expected structure.
        if not isinstance(analysis, dict):
            raise ValueError("Analysis response is not a JSON object.")

        if not isinstance(analysis.get("profile"), dict):
            raise ValueError("Missing or invalid 'profile' object.")

        if not isinstance(analysis.get("risk"), dict):
            raise ValueError("Missing or invalid 'risk' object.")

        if not isinstance(analysis.get("tactic"), str):
            raise ValueError("Missing or invalid 'tactic'.")

        return analysis

    except Exception as e:
        print(f"Error in consolidated analysis agent: {e}")

        # Return a safe default structure on error.
        return {
            "profile": {
                "sentiment": "neutral",
                "literacy": "medium",
                "persona": "Inquirer",
            },
            "risk": {
                "risk_score": "Medium",
                "reasoning": "Default score due to analysis error.",
            },
            "tactic": "Build Trust through Transparency",
        }

# --- 2. The Master Agent (Orchestrator) ---
async def master_agent(user_message: str, client, passed_history: list = None, model_name: str = None):
    print("\n🧠 Step 1: Running analysis and knowledge retrieval...")

    # Run the consolidated analysis and knowledge retrieval in parallel
    analysis_task = asyncio.create_task(run_analysis_agent(user_message, client, model_name=model_name))
    knowledge_task = asyncio.create_task(knowledge_retrieval_agent(user_message))

    # Await both tasks
    analysis_result, product_info = await asyncio.gather(analysis_task, knowledge_task)
    
    # Deconstruct the analysis results
    user_profile = analysis_result.get('profile', {})
    risk_info = analysis_result.get('risk', {})
    persuasion_tactic = analysis_result.get('tactic', 'Build Trust through Transparency')

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
        client,
        model=model_name
    )

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": final_response})

    return final_response

# --- 3. Main Application Loop ---
async def main():
    load_dotenv()
    client, model_name, provider = get_llm_client()
    print(f"🚀 Initialized AI Assistant with {provider.upper()} ({model_name})")
    print("🤖 Tata Capital AI Assistant is ready.\n")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        
        try:
            reply = await master_agent(user_input, client, model_name=model_name)
            print(f"Assistant: {reply}\n")
        except Exception as e:
            print(f"🚨 An error occurred: {e}")
            print("Assistant: I'm sorry, I encountered an issue. Please try rephrasing your question.\n")

if __name__ == "__main__":
    asyncio.run(main())
