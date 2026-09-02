# in agents/persuasion_agent.py

import asyncio
import json

async def persuasion_strategy_agent(user_profile: dict, user_message: str, model) -> str:
    """
    Recommends a persuasion tactic based on the user's profile and message.

    Args:
        user_profile: A dictionary containing the user's persona, sentiment, etc.
        user_message: The latest message from the user.
        model: An initialized GenerativeModel instance.

    Returns:
        A string describing the recommended persuasion tactic.
    """
    prompt = f"""
    You are a master persuasion strategist for a financial institution.
    A user has sent the following message: "{user_message}"
    Our analysis of this user's profile is: {json.dumps(user_profile)}

    Based on their profile and message, select the SINGLE most effective persuasion tactic to use in our next response from the list below.
    
    Available Tactics:
    - "Emphasize Urgency": Create a sense of time-sensitivity.
    - "Use Social Proof": Mention that others find this product helpful.
    - "Focus on Long-Term Value": Highlight the benefits over the loan's lifetime, not just the cost.
    - "Highlight Flexibility & Control": Emphasize features like flexible EMIs or prepayment options.
    - "Build Trust through Transparency": Be upfront about costs and processes to address skepticism.
    - "Frame as an Enabler": Position the loan as a tool to achieve a goal (e.g., education, travel).
    - "Keep it Simple": If literacy is low, avoid jargon and explain concepts clearly.

    Return ONLY the name of the chosen tactic as a single string (e.g., "Emphasize Urgency").
    """
    
    try:
        if hasattr(model, "chat"):
            response = await model.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a persuasion strategist bot."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            tactic = response.choices[0].message.content.strip().replace('"', '')
        else:
            response = await model.generate_content_async(prompt)
            tactic = response.text.strip().replace('"', '')
        return tactic
    except Exception as e:
        print(f"Error in persuasion_strategy_agent: {e}")
        return "Build Trust through Transparency" # A safe default tactic

# --- Example of how to run this async function ---
async def main():
    # This requires a mock/dummy model object for standalone testing
    class MockModel:
        async def generate_content_async(self, prompt_text):
            class MockResponse:
                def __init__(self, text):
                    self.text = text
            # Simulate a model response based on the prompt
            if "worried about the cost" in prompt_text:
                return MockResponse('"Build Trust through Transparency"')
            else:
                return MockResponse('"Frame as an Enabler"')
    
    mock_model = MockModel()
    
    test_profile = {'sentiment': 'anxious', 'literacy': 'medium', 'persona': 'Cautious Planner'}
    test_message = "I'm just worried about the cost and all the hidden fees."
    
    tactic = await persuasion_strategy_agent(test_profile, test_message, mock_model)
    print(f"Recommended Tactic: {tactic}")

if __name__ == "__main__":
    asyncio.run(main())