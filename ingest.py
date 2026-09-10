import json
import os
import shutil

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


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "tata_bfsi_data.json"
)

CHROMA_DB_PATH = os.path.join(
    BASE_DIR,
    "chroma_db"
)


# ---------------------------------------------------------
# Repeated website navigation that appears on many pages
# ---------------------------------------------------------

NAVIGATION_MARKERS = [
    "Personal Loan Home Loan Business Loan Vehicle Loan",
    "Quick Links for loans",
    "Quick Links for Loans",
    "Moneyfy by Tata Capital",
    "Insurance Apply Offers Quick Pay",
]


def clean_page_text(text: str) -> str:
    """
    Remove large repeated website-navigation sections from
    scraped Tata Capital pages.

    We intentionally keep the actual article/product content.
    """

    if not text:
        return ""

    cleaned = text.strip()

    # Navigation menu removal logic removed to prevent accidental deletion of article body.
    # RecursiveCharacterTextSplitter and vector search will handle noise well enough.

    # Remove excessive whitespace
    cleaned = "\n".join(
        line.strip()
        for line in cleaned.splitlines()
        if line.strip()
    )

    return cleaned.strip()


# ---------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------

def create_knowledge_base_from_json():

    print("=" * 60)
    print("TATA CAPITAL KNOWLEDGE BASE INGESTION")
    print("=" * 60)

    # -----------------------------------------------------
    # Load JSON
    # -----------------------------------------------------

    print("\n1. Loading data from JSON file...")

    if not os.path.exists(JSON_DATA_PATH):
        print(f"ERROR: {JSON_DATA_PATH} not found.")
        return

    with open(
        JSON_DATA_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    print(f"Raw JSON records: {len(data)}")

    # -----------------------------------------------------
    # Deduplicate
    # -----------------------------------------------------

    print("\n2. Deduplicating documents...")

    unique_documents = []
    seen_urls = set()
    seen_content = set()

    duplicate_urls = 0
    duplicate_content = 0
    empty_documents = 0

    for item in data:

        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        text = item.get("text", "").strip()

        # Ignore Tata Capital branch-location pages.
        # These pages contain duplicated generic content and
        # negatively affect product/loan retrieval.
        if "branches.tatacapital.com" in url:
            continue

        if not text:
            empty_documents += 1
            continue
        cleaned_text = clean_page_text(text)

        if not cleaned_text:
            empty_documents += 1
            continue

        # URL-level deduplication
        if url and url in seen_urls:
            duplicate_urls += 1
            continue

        # Content-level deduplication
        content_key = cleaned_text.lower()

        if content_key in seen_content:
            duplicate_content += 1
            continue

        if url:
            seen_urls.add(url)

        seen_content.add(content_key)

        unique_documents.append(
            {
                "title": title,
                "url": url,
                "text": cleaned_text,
            }
        )

    print(f"Unique documents: {len(unique_documents)}")
    print(f"Duplicate URLs removed: {duplicate_urls}")
    print(f"Duplicate content removed: {duplicate_content}")
    print(f"Empty documents removed: {empty_documents}")

    # -----------------------------------------------------
    # Convert to LangChain documents
    # -----------------------------------------------------

    print("\n3. Creating LangChain documents...")

    langchain_documents = []

    for item in unique_documents:

        combined_content = (
            f"Title: {item['title']}\n\n"
            f"{item['text']}"
        )

        document = Document(
            page_content=combined_content,
            metadata={
                "source": item["url"],
                "title": item["title"],
            },
        )

        langchain_documents.append(document)

    print(
        f"LangChain documents created: "
        f"{len(langchain_documents)}"
    )

    # -----------------------------------------------------
    # Split documents
    # -----------------------------------------------------

    print("\n4. Splitting documents into chunks...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunked_documents = text_splitter.split_documents(
        langchain_documents
    )

    print(
        f"Total chunks created: "
        f"{len(chunked_documents)}"
    )

    # -----------------------------------------------------
    # Load embeddings
    # -----------------------------------------------------

    print(
        "\n5. Loading embedding model "
        "(all-MiniLM-L6-v2)..."
    )

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    # -----------------------------------------------------
    # Delete old Chroma DB
    # -----------------------------------------------------

    print("\n6. Removing old Chroma database...")

    if os.path.exists(CHROMA_DB_PATH):
        for filename in os.listdir(CHROMA_DB_PATH):
            file_path = os.path.join(CHROMA_DB_PATH, filename)

       	    if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)

        print("Old Chroma database contents removed.")

    # -----------------------------------------------------
    # Build new Chroma database
    # -----------------------------------------------------

    print("\n7. Building new Chroma vector database...")

    Chroma.from_documents(
        documents=chunked_documents,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
    )

    print("\n" + "=" * 60)
    print("KNOWLEDGE BASE CREATION COMPLETE")
    print("=" * 60)

    print(
        f"Documents: {len(langchain_documents)}"
    )

    print(
        f"Chunks: {len(chunked_documents)}"
    )

    print(
        f"Database: {CHROMA_DB_PATH}"
    )

    print("=" * 60)


if __name__ == "__main__":
    create_knowledge_base_from_json()
