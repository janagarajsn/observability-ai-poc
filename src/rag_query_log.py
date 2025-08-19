import os
import logging
from typing import List
from dotenv import load_dotenv
from pydantic import PrivateAttr
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import BaseRetriever, Document

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
DEFAULT_K = int(os.getenv("DEFAULT_K", 5))
CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", 10))
THRESHOLD_LIMIT = float(os.getenv("THRESHOLD_LIMIT", 0.6))

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

# Custom Threshold Retriever
class ThresholdRetriever(BaseRetriever):
    _vectorstore: QdrantVectorStore = PrivateAttr()
    _k: int = PrivateAttr()
    _threshold: float = PrivateAttr()
    def __init__(self, vectorstore=vector_store, k=DEFAULT_K, threshold=THRESHOLD_LIMIT):
        super().__init__()
        self._vectorstore = vectorstore
        self._k = k
        self._threshold = threshold

    def get_relevant_documents(self, query: str) -> List[Document]:
        docs_and_scores = self._vectorstore.similarity_search_with_score(query, k=self._k)
        filtered_docs = [doc for doc, score in docs_and_scores if score >= self._threshold]
        if not filtered_docs:
            logger.info(f"No documents passed the similarity score {self._threshold}")
        return filtered_docs

    # Async version for compatibility
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)

# Query logs with RAG
def query_log(query_text, k=DEFAULT_K, threshold=THRESHOLD_LIMIT, chat_history=None):
    logger.info(f"Querying logs with: {query_text}")

    chat_history = chat_history or []

    retriever = ThresholdRetriever(vectorstore=vector_store, k=k, threshold=threshold)

    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(model=RETRIEVAL_MODEL, api_key=OPENAI_API_KEY, temperature=0),
        retriever=retriever,
        return_source_documents=True
    )

    response = qa_chain.invoke({"query": query_text})
    # If retriever returned no documents, enforce safe answer
    if not response.get("source_documents", []):
        logger.info("No relevant documents found.")
        return "Sorry, the question is out of my scope", []

    answer = response["result"]
    source_docs = response.get("source_documents", [])

    logger.info(f"Question: {query_text}")
    logger.info(f"Answer: {answer}")

    return answer, source_docs

if __name__ == "__main__":
    # Query
    while True:
        query = input("Enter your query (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        k = input(f"Enter the number of results to return (default is {DEFAULT_K}): ")
        k = int(k) if k.isdigit() else DEFAULT_K
        threshold = input(f"Enter the threshold score (default is {THRESHOLD_LIMIT}): ")
        threshold = float(threshold) if threshold else THRESHOLD_LIMIT
        query_log(query, k, threshold)