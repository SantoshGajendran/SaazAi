# SaazAi (PDFLLM)

A RAG (Retrieval-Augmented Generation) application for chatting with technical PDF manuals, featuring a FastAPI backend and a modern Angular frontend.

## Features

- **Ingestion**: Parse complex PDFs (including tables) using LlamaParse.
- **RAG**: Interact with documents using a local Llama 3 model (via Ollama) and ChromaDB.
- **Frontend**: Immersive Angular UI with Glassmorphism design.
- **Admin**: Easy document upload and management.

## Tech Stack

- **Backend**: FastAPI, LlamaIndex, ChromaDB, Ollama
- **Frontend**: Angular 17+, TailwindCSS (conceptually), Vanilla CSS (Glassmorphism)
- **AI**: Llama 3 (or custom model), HuggingFace Embeddings

## Setup

1.  **Backend**:
    ```bash
    cd rag_app
    pip install -r requirements.txt
    uvicorn api:app --reload
    ```

2.  **Frontend**:
    ```bash
    cd saazai-ui
    npm install
    ng serve
    ```

## Environment

Create a `.env` in `rag_app/` with:
```
LLAMA_CLOUD_API_KEY=llx-...
ADMIN_PASSWORD=admin123
```
