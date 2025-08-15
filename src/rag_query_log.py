import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain.chains import RetrievalQA

# Load environment variables
load_dotenv()

# Configure logging with timestamps
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "aks_logs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
RETRIEVAL_MODEL = os.getenv("RETRIEVAL_MODEL", "gpt-4.1-nano")
DEFAULT_K = 5

# Initialize Qdrant client
qdrant_client = QdrantClient(url=QDRANT_URL)

# Initialize embeddings
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

# Check if collection exists
collections = [c.name for c in qdrant_client.get_collections().collections]
if COLLECTION_NAME not in collections:
    logger.error(f"Collection {COLLECTION_NAME} does not exist. Run ingestion first")
    exit(1)

# Check if collection has points
num_points = qdrant_client.get_collection(COLLECTION_NAME).points_count
if num_points == 0:
    logger.error(f"Collection {COLLECTION_NAME} is empty. Run ingestion first")
    exit(1)
else:
    logger.info(f"Collection '{COLLECTION_NAME}' has {num_points} points.")

vector_store = QdrantVectorStore(client=qdrant_client, collection_name=COLLECTION_NAME, embedding=embeddings)

# Query logs with RAG
def query_log(query_text, k):
    logger.info(f"Querying logs with: {query_text}")
    retriever = vector_store.as_retriever(search_kwargs={"k": k})

    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model=RETRIEVAL_MODEL, api_key=OPENAI_API_KEY, temperature=0),
        retriever=retriever,
        return_source_documents=True
    )

    response = qa_chain.invoke({"query": query_text})
    logger.info(f"Question: {query_text}")
    logger.info(f"Answer: {response['result']}")
    for doc in response['source_documents']:
        logger.info(f"Source Document: {doc.metadata['source']}")

if __name__ == "__main__":
    # Example query
    while True:
        query = input("Enter your query (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        k = input(f"Enter the number of results to return (default is {DEFAULT_K}): ")
        k = int(k) if k.isdigit() else DEFAULT_K
        query_log(query, k)