import json
import os

# Bypass SSL Verification for HuggingFace behind corporate firewalls
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
# pyrefly: ignore [missing-import]
from langchain_core.documents import Document
# pyrefly: ignore [missing-import]
from langchain.text_splitter import RecursiveCharacterTextSplitter
# pyrefly: ignore [missing-import]
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Use absolute paths relative to this file's directory so it works from any CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DATA_PATH = os.path.join(BASE_DIR, "data", "tata_bfsi_data.json")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

def create_knowledge_base_from_json():
    """
    Loads data from a JSON file, processes it into searchable chunks,
    and builds a Chroma vector database with HuggingFace embeddings.
    """
    print("Loading data from JSON file...")
    if not os.path.exists(JSON_DATA_PATH):
        print(f"Error: {JSON_DATA_PATH} not found.")
        return

    with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    langchain_documents = []
    for item in data:
        if 'text' in item and item['text']:
            combined_content = f"Title: {item.get('title', '')}\n\n{item['text']}"
            document = Document(
                page_content=combined_content,
                metadata={"source": item.get('url', '')}
            )
            langchain_documents.append(document)
    
    print(f"Successfully created {len(langchain_documents)} documents.")

    print("Splitting documents into manageable chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunked_documents = text_splitter.split_documents(langchain_documents)
    print(f"Split documents into {len(chunked_documents)} chunks.")

    print("Loading embedding model (all-MiniLM-L6-v2) for Vector Database...")
    # This model is very lightweight and performs well on CPUs
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Building and saving Chroma Vector Database to '{CHROMA_DB_PATH}'...")
    Chroma.from_documents(
        documents=chunked_documents,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH
    )

    print("\n--- Knowledge Base Creation Complete ---")
    print(f"Chroma Vector DB has been successfully created and saved to '{CHROMA_DB_PATH}'.")
    print("You can now run your main application.")

if __name__ == "__main__":
    create_knowledge_base_from_json()
