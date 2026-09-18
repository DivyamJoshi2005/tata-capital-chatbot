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
            "max_tokens": 1024,
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

async def update_profile_background(user_message: str, client, model_name: str = None):
    try:
        analysis_result = await run_analysis_agent(user_message, client, model_name=model_name)
        conversation_state["user_profile"] = analysis_result.get('profile', {})
        conversation_state["risk_score"] = analysis_result.get('risk', {})
        conversation_state["tactic"] = analysis_result.get('tactic', 'Build Trust through Transparency')
        print(f"   [Background] Profile Updated: {conversation_state['user_profile']}")
    except Exception as e:
        print(f"Background profiling error: {e}")

# --- 2. The Master Agent (Orchestrator) ---
async def master_agent(user_message: str, client, passed_history: list = None, model_name: str = None):
    # --- Guardrail: Input Checking ---
    from guardrails import is_input_safe, check_scope_and_relevance
    
    is_safe, reason = is_input_safe(user_message)
    if not is_safe:
        yield reason
        return
        
    is_in_scope, scope_reason = await check_scope_and_relevance(user_message, client, model_name)
    if not is_in_scope:
        yield scope_reason
        return

    print("\n🧠 Step 1: Starting background analysis and knowledge retrieval...")

    # Start analysis in the background so it doesn't block the response!
    asyncio.create_task(update_profile_background(user_message, client, model_name))
    
    # Only wait for knowledge retrieval
    product_info = await knowledge_retrieval_agent(user_message)
    
    # Use the existing state (which updates in the background for the NEXT turn)
    user_profile = conversation_state.get("user_profile", {})
    risk_info = conversation_state.get("risk_score", {})
    persuasion_tactic = conversation_state.get("tactic", "Build Trust through Transparency")

    history = passed_history if passed_history is not None else conversation_state["conversation_history"]

    print("💬 Step 2: Generating streaming response...")
    
    # Yield chunks from the streaming conversation agent
    async for chunk in conversation_agent(
        user_message,
        product_info,
        persuasion_tactic,
        user_profile,
        history,
        client,
        model=model_name
    ):
        yield chunk

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": "[Streamed Response]"})

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
            print("Assistant: ", end="", flush=True)
            full_reply = ""
            async for chunk in master_agent(user_input, client, model_name=model_name):
                print(chunk, end="", flush=True)
                full_reply += chunk
            print("\n")
        except Exception as e:
            print(f"🚨 An error occurred: {e}")
            print("Assistant: I'm sorry, I encountered an issue. Please try rephrasing your question.\n")

if __name__ == "__main__":
    asyncio.run(main())
