# in agents/knowledge_agent.py

import asyncio
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Define the path to your persistent ChromaDB directory and the embedding model
CHROMA_DB_PATH = "chroma_db"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# --- Initialize components once when the module is loaded ---
# This is more efficient than reloading the model and DB on every call.
try:
    print("Knowledge Agent: Initializing embedding model...")
    embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    print(f"Knowledge Agent: Loading vector store from '{CHROMA_DB_PATH}'...")
    vector_store = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embedding_function
    )
    print("Knowledge Agent: Vector store loaded successfully.")
except Exception as e:
    print(f"FATAL: Could not load vector store. Make sure you have run ingest.py first. Error: {e}")
    vector_store = None


async def knowledge_retrieval_agent(user_query: str, k: int = 3) -> str:
    """
    Retrieves the most relevant information from the knowledge base (ChromaDB).

    Args:
        user_query: The user's question or message.
        k: The number of relevant documents to retrieve.

    Returns:
        A formatted string containing the retrieved information, or an error message.
    """
    if vector_store is None:
        return "Error: Knowledge base is not available."

    try:
        print(f"   - Knowledge Agent: Searching for '{user_query}'...")
        # Perform a similarity search in the vector database
        retrieved_docs = await asyncio.to_thread(vector_store.similarity_search, user_query, k=k)

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