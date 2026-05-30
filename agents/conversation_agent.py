# in agents/conversation_agent.py

import asyncio

async def conversation_agent(
    user_message: str,
    product_info: str,
    persuasion_tactic: str,
    user_profile: dict,
    conversation_history: list,
    client
) -> str:
    """
    Generates the final, user-facing response by synthesizing all available information using Groq.

    Args:
        user_message: The user's latest message.
        product_info: Factual information from the knowledge agent.
        persuasion_tactic: The recommended strategy from the persuasion agent.
        user_profile: The user's analyzed profile.
        conversation_history: A list of previous user/agent turns.
        client: An initialized AsyncGroq client instance.

    Returns:
        A string containing the final, natural language response for the user.
    """
    # Format the conversation history for the prompt
    history_str = "\n".join([f"{turn['role']}: {turn['content']}" for turn in conversation_history])

    system_prompt = f"""
    You are a friendly, professional, and highly competent financial advisor for Tata Capital. Your goal is to be helpful and persuasive, guiding the user towards applying for a personal loan if it's a good fit for them.

    **Conversation Context:**
    - Previous Conversation:
    {history_str}
    - User's Latest Message: "{user_message}"
    - User's Profile: {user_profile}

    **Your Strategic Directives:**
    1.  **Grounding Facts:** Base your response on the following information. DO NOT invent product details, interest rates, or fees.
        <facts>
        {product_info}
        </facts>
    2.  **Persuasion Tactic:** Your primary communication strategy for this response should be: "{persuasion_tactic}". Weave this tactic naturally into your reply.
    
    **Your Task:**
    Craft a warm, clear, and helpful response to the user.
    - Directly address their last message.
    - Use the provided facts to answer their questions accurately.
    - Apply the persuasion tactic subtly.
    - Maintain a conversational and empathetic tone.
    - Keep the response concise and easy to understand.
    """
    
    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in conversation_agent: {e}")
        return "I'm sorry, I'm having a little trouble processing that. Could you please rephrase your question?"