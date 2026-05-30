import json
import os
import pickle
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever

JSON_DATA_PATH = "data/tata_bfsi_data.json"
BM25_INDEX_PATH = "bm25_index.pkl"

def create_knowledge_base_from_json():
    """
    Loads data from a JSON file, processes it into searchable chunks,
    and builds a lightweight BM25 keyword index to save memory.
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

    print("Building BM25 Index (Memory-Efficient Keyword Search)...")
    retriever = BM25Retriever.from_documents(chunked_documents)

    print(f"Saving BM25 Index to '{BM25_INDEX_PATH}'...")
    with open(BM25_INDEX_PATH, 'wb') as f:
        pickle.dump(retriever, f)

    print("\n--- Knowledge Base Creation Complete ---")
    print(f"BM25 Index has been successfully created and saved to '{BM25_INDEX_PATH}'.")
    print("You can now run your main application.")

if __name__ == "__main__":
    create_knowledge_base_from_json()