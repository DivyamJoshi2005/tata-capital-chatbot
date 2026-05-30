import json
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
import os

# Define the path to your JSON data and the persistent ChromaDB directory
JSON_DATA_PATH = "data/tata_bfsi_data.json"
CHROMA_DB_PATH = "chroma_db"

def create_knowledge_base_from_json():
    """
    Loads data from a JSON file, processes it into searchable chunks,
    and stores it in a ChromaDB vector database.
    """
    # --- 1. Load the JSON Data ---
    print("Loading data from JSON file...")
    with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # --- 2. Create LangChain Document Objects ---
    # We combine the title and text for better contextual understanding during retrieval.
    # The URL is stored as metadata for citation purposes.
    langchain_documents = []
    for item in data:
        # Ensure text content exists to avoid errors
        if 'text' in item and item['text']:
            combined_content = f"Title: {item.get('title', '')}\n\n{item['text']}"
            document = Document(
                page_content=combined_content,
                metadata={"source": item.get('url', '')}
            )
            langchain_documents.append(document)
    
    print(f"Successfully created {len(langchain_documents)} documents.")

    # --- 3. Split Documents into Chunks ---
    print("Splitting documents into manageable chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # The size of each chunk in characters
        chunk_overlap=200   # The overlap between consecutive chunks
    )
    chunked_documents = text_splitter.split_documents(langchain_documents)
    print(f"Split documents into {len(chunked_documents)} chunks.")

    # --- 4. Initialize Embedding Model ---
    # This model runs locally and converts text chunks into numerical vectors.
    print("Initializing embedding model...")
    embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

    # --- 5. Embed and Store Chunks in ChromaDB ---
    print(f"Creating and persisting vector store at '{CHROMA_DB_PATH}'...")
    # This creates the database, embeds the documents, and saves it to disk.
    vectorstore = Chroma.from_documents(
        documents=chunked_documents,
        embedding=embedding_function,
        persist_directory=CHROMA_DB_PATH
    )

    print("\n--- Knowledge Base Creation Complete ---")
    print(f"Vector store has been successfully created and saved to '{CHROMA_DB_PATH}'.")
    print("You can now run your main application.")


if __name__ == "__main__":
    # This ensures the script runs only when executed directly
    create_knowledge_base_from_json()