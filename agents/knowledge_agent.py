import asyncio
import os

# Bypass SSL Verification for HuggingFace behind corporate firewalls
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Resolve path relative to the project root (parent of this file's directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")

try:
    print(f"Knowledge Agent: Loading Chroma Vector DB from '{CHROMA_DB_PATH}'...")
    if os.path.exists(CHROMA_DB_PATH):
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH, 
            embedding_function=embeddings
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        print("Knowledge Agent: Chroma DB loaded successfully.")
    else:
        print("Knowledge Agent: No Chroma DB found. Please run ingest.py first.")
        retriever = None
except Exception as e:
    print(f"FATAL: Could not load Chroma DB. Error: {e}")
    retriever = None


async def knowledge_retrieval_agent(user_query: str, k: int = 3) -> str:
    """
    Retrieves the most relevant information from the knowledge base using vector similarity search.

    Args:
        user_query: The user's question or message.
        k: The number of relevant documents to retrieve.

    Returns:
        A formatted string containing the retrieved information, or an error message.
    """
    if retriever is None:
        return "Error: Knowledge base is not available."

    try:
        print(f"   - Knowledge Agent: Searching vector DB for '{user_query}'...")
        retriever.search_kwargs["k"] = k
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
