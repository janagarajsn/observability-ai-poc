# Observability AI PoC

A proof-of-concept project for observability and AI-driven log analysis.

This project demonstrates a practical approach to observability using AI techniques for log analysis. It provides tools to ingest, generate, and analyze logs, leveraging Retrieval-Augmented Generation (RAG) to enable advanced querying and insights from log data.

## Key features:

- Automated log ingestion and tracking
- Synthetic log generation for testing and simulation
- RAG-based querying for intelligent log search and summarization
- Integration with vector databases (e.g., Qdrant) for efficient semantic search
- Modular Python codebase for easy extension and experimentation

The project is ideal for experimenting with AI-driven observability workflows, building prototypes for log analytics, and exploring how LLMs and - vector search can enhance traditional monitoring systems.

## Project Structure

```
.
├── ingestracker/
│   └── ingested_files.json
├── input-logs/
│   └── aks_logs_2025-08-01.json
│   └── ... (other log files)
├── lenv/
│   └── (Python virtual environment)
├── logs/
├── src/
│   ├── ingest-logs.py
│   ├── log-generator.py
│   └── rag_query_log.py
├── requirements.txt
└── README.md
```

- `ingestracker/`: Tracks ingested log files.
- `input-logs/`: Contains input log files for processing. You can generate them using log-generator.py
- `src/`: Source code for log ingestion, generation, and RAG-based querying.
- `requirements.txt`: Python dependencies.

## Setup

1. **Run Qdrant DB in localhost**
     ```
     docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
     ```

2. **Clone the repository:**
	 ```sh
	 git clone <repo-url>
	 cd observability-ai-poc
	 ```

3. **Create and activate a virtual environment (optional if `lenv/` is not used):**
	 ```sh
	 python -m venv lenv
	 . lenv\Scripts\activate
	 ```

4. **Install dependencies:**
	 ```sh
	 pip install -r requirements.txt
	 ```

## Usage

- **Generate Sample logs:**
	```sh
	python src/log-generator.py <YYYY-MM-DD> <Number of log entries you need per file>
	```

- **Ingest logs into Qdrant:**
	```sh
	python src/ingest-logs.py
	```


- **Query logs using RAG:**
	```sh
	python src/rag_query_log.py
	```
