# ingest_logs.py
from cmath import log
import os
import json
import time
import logging
from glob import glob
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client.http.models import VectorParams, Distance
from langchain.schema import Document

# Load environment variables
load_dotenv()

# Configure logging with timestamps
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_PATH = os.path.join(PROJECT_ROOT, "input-logs", "*.json")
INGESTION_TRACKER_FILE = os.path.join(PROJECT_ROOT, "ingestracker", "ingested_files.json")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", 1536))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 10))
BATCH_SLEEP_TIME = int(os.getenv("BATCH_SLEEP_TIME", 2))
LOG_BATCH = int(os.getenv("LOG_BATCH", 20))

# Qdrant Client
qdrant_client = QdrantClient(url=QDRANT_URL)

# Embeddings and Vector Store
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

# Text Splitter
text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)

# Track ingested log files
def load_ingested_log_files():
    if os.path.exists(INGESTION_TRACKER_FILE):
        with open(INGESTION_TRACKER_FILE, 'r') as f:
            return set(json.load(f))
    return set()

# Save ingested log files
def save_ingested_log_files(file_path):
    ingested_files = load_ingested_log_files()
    ingested_files.add(file_path)
    os.makedirs(os.path.dirname(INGESTION_TRACKER_FILE), exist_ok=True)
    with open(INGESTION_TRACKER_FILE, 'w') as f:
        json.dump(list(ingested_files), f)

# Create collection if not exists
def create_collection_if_not_exists(collection_name: str):
    if collection_name not in [c.name for c in qdrant_client.get_collections().collections]:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
        logger.info(f"Collection '{collection_name}' created.")
    else:
        logger.info(f"Collection '{collection_name}' already exists.")

# Ingest log files into Qdrant
def ingest_logs(collection_name: str):
    # Create collection if not exists
    create_collection_if_not_exists(collection_name)

    # Initialize vector store
    vector_store = QdrantVectorStore(client=qdrant_client, collection_name=collection_name, embedding=embeddings)
    
    log_files = glob(LOGS_PATH)
    if not log_files:
        logger.error(f"No log files found at path: {LOGS_PATH}")
        return

    ingested_files = load_ingested_log_files()

    for log_file in log_files:
        if log_file in ingested_files:
            logger.info(f"File '{log_file}' already ingested. Skipping.")
            continue

        logger.info(f"Processing file: {log_file}")
        with open(log_file, 'r') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing {log_file}: {e}")
                continue

            # Convert each log entry into a document
        docs = []
        for i in range(0, len(logs), LOG_BATCH):
            log_batch = logs[i:i+LOG_BATCH]
            log_text = "\n".join([json.dumps(log, indent=2) for log in log_batch])
            docs.append(Document(page_content=log_text, metadata={"source": log_file}))

        # Chunk the logs
        chunks = text_splitter.split_documents(docs)

        # Save in Qdrant
        if chunks:
            # Ingest in batches
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i + BATCH_SIZE]
                vector_store.add_documents(batch)
                time.sleep(BATCH_SLEEP_TIME)

            logger.info(f"File '{log_file}' ingested successfully with {len(chunks)} chunks.")
            save_ingested_log_files(log_file)
        else:
            logger.warning(f"No chunks generated for file: {log_file}")

    logger.info(f"Finished incremental ingestion to Qdrant collection '{collection_name}'.")
    return collection_name


if __name__ == "__main__":
    collection_name = str(input("Enter collection name: "))
    if not collection_name:
        logger.error("Collection name is required.")
    else:
        ingest_logs(collection_name)
