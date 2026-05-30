# in agents/risk_agent.py

import asyncio
import json

async def preliminary_risk_agent(user_message: str, model) -> dict:
    """
    Performs a preliminary risk assessment based on the user's message.

    Args:
        user_message: The latest message from the user.
        model: An initialized GenerativeModel instance.

    Returns:
        A dictionary with a risk score and reasoning.
    """
    prompt = f"""
    You are a junior credit risk analyst. Analyze the user's message for subtle cues related to their financial responsibility and potential credit risk.

    User Message: "{user_message}"

    Look for:
    - Red Flags: Vague or inconsistent answers, mentions of many other loans, extreme urgency or desperation, poor grammar that might indicate fraud.
    - Positive Indicators: Clear statements about income, questions about long-term costs (like total interest), mentions of a good credit history, financially prudent language.

    Based on the message, provide a preliminary risk assessment.
    Return your analysis ONLY as a valid JSON object with two keys:
    - "risk_score": (Low, Medium, High)
    - "reasoning": (A brief, one-sentence explanation for your score)
    """
    
    try:
        response = await model.generate_content_async(prompt)
        # Clean up potential markdown formatting from the model
        cleaned_response = response.text.strip().replace("`", "").replace("json", "")
        risk_info = json.loads(cleaned_response)
        return risk_info
    except Exception as e:
        print(f"Error in preliminary_risk_agent: {e}")
        return {"risk_score": "Medium", "reasoning": "Default score due to analysis error."}

# --- Example of how to run this async function ---
async def main():
    class MockModel:
        async def generate_content_async(self, prompt_text):
            class MockResponse:
                def __init__(self, text):
                    self.text = text
            if "pay off my other cards" in prompt_text:
                return MockResponse('{"risk_score": "High", "reasoning": "User mentions multiple other debts, indicating potential over-leveraging."}')
            else:
                return MockResponse('{"risk_score": "Low", "reasoning": "User is asking about long-term costs, showing financial prudence."}')

    mock_model = MockModel()

    test_message_1 = "I really need money fast to pay off my other cards, it's an emergency."
    risk_1 = await preliminary_risk_agent(test_message_1, mock_model)
    print(f"Risk Assessment 1: {risk_1}")

    test_message_2 = "Can you show me how the total interest paid changes if I choose a 3-year tenure versus a 5-year one?"
    risk_2 = await preliminary_risk_agent(test_message_2, mock_model)
    print(f"Risk Assessment 2: {risk_2}")

if __name__ == "__main__":
    asyncio.run(main())