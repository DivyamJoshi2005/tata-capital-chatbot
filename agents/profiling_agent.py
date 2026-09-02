# agents/profiling_agent.py
import json

async def customer_profiling_agent(user_message: str, model) -> dict:
    """
    Analyzes a user's message using a provided Gemini model instance.
    
    Args:
        user_message: The text message from the user.
        model: An initialized GenerativeModel instance from google.generativeai.
    
    Returns:
        A dictionary containing the analysis.
    """
    # No need to initialize the model here! It's passed in.
    
    prompt = f"""
    You are an expert psychologist and financial analyst.
    Analyze the user's last message: "{user_message}".
    Based on the text, determine:
    - sentiment: (anxious, skeptical, excited, neutral, etc.)
    - literacy: (low, medium, high)
    - persona: (Cautious Planner, Urgent Borrower, Aspirational Spender, etc.)
    
    Return your analysis ONLY as a valid JSON object with the keys:
    'sentiment', 'literacy', and 'persona'.
    """
    
    try:
        if hasattr(model, "chat"):
            response = await model.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a JSON analysis bot. Always output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            cleaned_response = response.choices[0].message.content.strip()
        else:
            response = await model.generate_content_async(prompt)
            cleaned_response = response.text.strip().replace("`", "").replace("json", "")
        
        analysis_result = json.loads(cleaned_response)
        return analysis_result
        
    except Exception as e:
        print(f"Error in profiling agent: {e}")
        return {"sentiment": "unknown", "literacy": "unknown", "persona": "unknown"}