import re
import json

def is_input_safe(user_message: str) -> tuple[bool, str]:
    """
    Input guardrails:
    1. Restrict excessively long inputs.
    2. Prevent clearly inappropriate inputs (basic keyword check or regex).
    """
    # 1. Length check
    if len(user_message) > 1000:
        return False, "Your request is too long. Please keep it under 1000 characters."

    # 2. Inappropriate content check (basic example)
    inappropriate_keywords = ['hack', 'bypass', 'ignore all previous instructions', 'system prompt', 'jailbreak']
    msg_lower = user_message.lower()
    for kw in inappropriate_keywords:
        if kw in msg_lower:
            return False, "I cannot fulfill this request as it violates my usage guidelines."

    return True, ""


async def _extract_json_from_response(content: str) -> dict:
    """Helper to cleanly extract JSON ignoring <think> blocks and Markdown."""
    if "</think>" in content:
        content = content.split("</think>", 1)[-1]
        
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
        
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        return json.loads(content[start:end+1])
    return {}

async def check_scope_and_relevance(user_message: str, client, model_name: str) -> tuple[bool, str]:
    """
    LLM-based input guardrail:
    Prevent questions outside the application's intended scope (finance, loans, Tata Capital).
    """
    prompt = f"""
    You are a classification assistant for Tata Capital.
    Determine if the following user message is related to finance, loans, credit, banking, or Tata Capital products.
    If it is a greeting or general pleasantry, it is allowed.
    If it is asking about coding, politics, recipes, or other unrelated topics, it is NOT allowed.

    User Message: "{user_message}"

    Return ONLY a JSON object with two keys:
    - "is_in_scope": boolean (true if allowed, false if not allowed)
    - "reason": string (brief reason for your decision)
    """
    
    try:
        kwargs = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 512,
        }
        if model_name:
            kwargs["model"] = model_name
            
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        
        data = await _extract_json_from_response(content)
        
        if not data.get("is_in_scope", True):
            return False, "I am a Tata Capital financial assistant. I can only help with questions related to loans, finance, and our products. Please ask a relevant question."
        return True, ""
    except Exception as e:
        print(f"Scope check failed: {e}")
        return True, "" # Fail open

async def evaluate_output(question: str, context: str, answer: str, client, model_name: str) -> dict:
    """
    AI Output Testing: Treat LLM output as something that must be tested.
    Evaluates the response against specific criteria.
    """
    prompt = f"""
    You are an evaluator for a financial chatbot.
    Please evaluate the chatbot's answer based on the given context and user question.
    
    User Question: {question}
    Retrieved Context: {context}
    Chatbot Answer: {answer}
    
    Evaluate the answer based on the following criteria and return a JSON object:
    1. is_relevant: true/false (Is the answer relevant to the question?)
    2. is_supported: true/false (Is the answer supported by the retrieved context? Does it avoid unsupported claims?)
    3. handles_unavailability: true/false (Does it appropriately refuse or state lack of knowledge when the context doesn't contain the answer, OR answer correctly if the info exists?)
    4. pass_overall: true/false (Does the answer pass all checks?)
    5. feedback: string (Explanation of the evaluation)

    Return ONLY valid JSON.
    """
    try:
        kwargs = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 512,
        }
        if model_name:
            kwargs["model"] = model_name
            
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        
        data = await _extract_json_from_response(content)
        if not data:
            return {"error": "Failed to parse evaluation JSON", "raw_content": content[:100]}
        return data
    except Exception as e:
        return {"error": str(e)}
