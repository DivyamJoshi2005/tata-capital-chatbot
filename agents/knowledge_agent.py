import asyncio
import os
import pickle

# Resolve path relative to the project root (parent of this file's directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BM25_INDEX_PATH = os.path.join(PROJECT_ROOT, "bm25_index.pkl")

try:
    print(f"Knowledge Agent: Loading BM25 Index from '{BM25_INDEX_PATH}'...")
    if os.path.exists(BM25_INDEX_PATH):
        with open(BM25_INDEX_PATH, 'rb') as f:
            retriever = pickle.load(f)
        print("Knowledge Agent: BM25 Index loaded successfully.")
    else:
        print("Knowledge Agent: No BM25 index found. Please run ingest.py first.")
        retriever = None
except Exception as e:
    print(f"FATAL: Could not load BM25 index. Error: {e}")
    retriever = None


async def knowledge_retrieval_agent(user_query: str, k: int = 3) -> str:
    """
    Retrieves the most relevant information from the knowledge base using BM25 keyword search.

    Args:
        user_query: The user's question or message.
        k: The number of relevant documents to retrieve.

    Returns:
        A formatted string containing the retrieved information, or an error message.
    """
    if retriever is None:
        return "Error: Knowledge base is not available."

    try:
        print(f"   - Knowledge Agent: Searching for '{user_query}'...")
        # Since BM25 is CPU-bound, we still run it in a thread to avoid blocking the async event loop
        # We need to temporarily set the 'k' parameter on the retriever
        retriever.k = k
        retrieved_docs = await asyncio.to_thread(retriever.invoke, user_query)

        if not retrieved_docs:
            return "No specific product information found. Please answer based on general knowledge."

        # Format the retrieved documents into a single string for the conversation agent
        context_str = "--- Relevant Information ---\n"
        for i, doc in enumerate(retrieved_docs):
            context_str += f"Source {i+1} (from {doc.metadata.get('source', 'N/A')}):\n"
            context_str += f"{doc.page_content}\n\n"
        
        return context_str.strip()

    except Exception as e:
        print(f"Error in knowledge_retrieval_agent: {e}")
        return "Error: Could not retrieve information from the knowledge base."

# --- Example of how to run this async function ---
async def main():
    test_query = "what are the interest rates for a personal loan?"
    retrieved_info = await knowledge_retrieval_agent(test_query)
    print("\n--- Retrieved Knowledge ---")
    print(retrieved_info)
    print("-------------------------\n")
    
    test_query_2 = "documents required for salaried person"
    retrieved_info_2 = await knowledge_retrieval_agent(test_query_2)
    print("\n--- Retrieved Knowledge ---")
    print(retrieved_info_2)
    print("-------------------------\n")

if __name__ == "__main__":
    asyncio.run(main())