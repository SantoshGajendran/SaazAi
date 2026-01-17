import os
import nest_asyncio
from dotenv import load_dotenv
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

load_dotenv()
nest_asyncio.apply()

from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

def get_chat_engine(selected_file=None):
    """
    Initializes and returns the Chat Engine with the custom system prompt.
    If selected_file is provided, filters context to only that file.
    """
    
    # 1. Load Persisted ChromaDB
    db_path = "./chroma_db"
    if not os.path.exists(db_path):
        # Return None or raise error if DB doesn't exist yet (no files ingested)
        # For this app, we'll return None and let the UI handle it
        return None

    db = chromadb.PersistentClient(path=db_path)
    chroma_collection = db.get_or_create_collection("rag_collection")
    
    # Check if collection is empty
    if chroma_collection.count() == 0:
        return None

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    
    # 2. Setup Embeddings and LLM
    embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
    # Using 127.0.0.1 to avoid localhost IPv6 resolution issues on Windows
    llm = Ollama(model="gpt-oss:120b-cloud", base_url="http://127.0.0.1:11434", request_timeout=300.0)

    Settings.embed_model = embed_model
    Settings.llm = llm

    # 3. Load Index
    index = VectorStoreIndex.from_vector_store(
        vector_store,
    )

    # 4. Create Chat Engine with System Prompt AND Filters
    system_prompt = (
        "You are a Technical Assistant. You will be given context that includes Markdown tables and image descriptions. "
        "1. When reading a table row, strictly associate the 'Input/Description' column with the 'Specification/Logic' column. "
        "2. Do not hallucinate values not present in the table. "
        "3. If asked for a diagram, image, or layout, DO NOT generate ASCII art or text-based representations. "
        "Instead, simply state 'Please refer to the Source Visual below.' and summarize the key technical details found in the text description."
    )
    
    # Define Filters if selected_file is present
    filters = None
    if selected_file:
        filters = MetadataFilters(
            filters=[ExactMatchFilter(key="file_name", value=selected_file)]
        )

    chat_engine = index.as_chat_engine(
        chat_mode="context",
        system_prompt=system_prompt,
        similarity_top_k=10,  # Increased to 10 to capture more relevant chunks (e.g. diagrams)
        filters=filters
    )

    return chat_engine
