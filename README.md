# SaazAi (PDFLLM)

SaazAi is a powerful Retrieval-Augmented Generation (RAG) application designed to ingest complex technical PDF manuals (including tables and diagrams) and allow users to chat with them using intelligent local LLMs.

The application features a modern **Angular** frontend and a **FastAPI** backend powered by **LlamaIndex** and **Ollama**.

## 🚀 Features

- **Advanced Ingestion**: Uses **LlamaParse** to accurately extract text, tables, and image descriptions from PDFs.
- **Local RAG**: Queries documents using a local Large Language Model (via Ollama) and **ChromaDB** for vector storage.
- **Modern UI**: A sleek, glassmorphism-inspired interface built with Angular.
- **Visual Context**: Displays relevant diagram/chart snippets alongside answers.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your machine:

1.  **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
2.  **Node.js (LTS)** & **npm**: [Download Node.js](https://nodejs.org/)
3.  **Ollama**: [Download Ollama](https://ollama.com/)
    - Start the Ollama service: `ollama serve`
4.  **LlamaCloud API Key**: Required for parsing complex PDFs. [Get a key here](https://cloud.llamaindex.ai/).

---

## 📦 Installation & Setup

Clone the repository to your local machine:

```bash
git clone <repository_url>
cd Saazai-PDFLLM
```

### 1. Backend Setup

The backend handles document ingestion, vector storage, and the chat API.

1.  Navigate to the backend directory:
    ```bash
    cd rag_app
    ```

2.  Create a virtual environment (optional but recommended):
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    Create a `.env` file in the `rag_app` directory and add your LlamaCloud API Key:
    ```env
    # rag_app/.env
    LLAMA_CLOUD_API_KEY=llx-your-api-key-here
    ```

5.  **Model Setup**:
    The application defaults to using `gpt-oss:120b-cloud` via Ollama. You can pull this model or use a standard one like `llama3`.
    
    To pull the specific model (if available) or a substitute:
    ```bash
    ollama pull llama3
    ```
    
    > **Note**: If you use a different model (e.g., `llama3` or `mistral`), update the `model="..."` parameter in `rag_app/rag.py`.

### 2. Frontend Setup

The frontend is an Angular application serving the user interface.

1.  Navigate to the frontend directory:
    ```bash
    cd ../saazai-ui
    ```

2.  Install Node dependencies:
    ```bash
    npm install
    ```

3.  Install Angular CLI (if not already installed globally):
    ```bash
    npm install -g @angular/cli
    ```

---

## ▶️ Running the Application

You need to run both the backend and frontend servers.

### 1. Start the Backend API
In your **backend** terminal (`rag_app` directory):

```bash
uvicorn api:app --reload
```
*The API will start at `http://127.0.0.1:8000`*

### 2. Start the Frontend
In your **frontend** terminal (`saazai-ui` directory):

```bash
ng serve
```
*The UI will start at `http://localhost:4200`*

---

## 📝 Usage Guide

1.  Open your browser and navigate to **`http://localhost:4200`**.
2.  **Upload**: Use the sidebar/menu to upload a technical PDF manual.
3.  **Chat**: Once processed, type your questions in the chat interface. simpler
4.  **Context**: The bot will answer using the PDF content and show citations/images if available.

## 🐛 Troubleshooting

- **Ollama Connection Error**: Ensure Ollama is running (`ollama serve`). Check `rag_app/rag.py` to ensure the `base_url` matches your Ollama instance (default `http://127.0.0.1:11434`).
- **500 Error during Chat**: Check the backend console logs. Ensure the LLM model name in `rag_app/rag.py` matches a model you have installed via `ollama list`.
- **Parsing Errors**: Verify your `LLAMA_CLOUD_API_KEY` is correct in the `.env` file.
