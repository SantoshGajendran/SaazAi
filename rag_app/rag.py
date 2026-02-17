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



# Global Singletons
_db_client = None
_embed_model = None
_llm = None

def get_chat_engine(selected_file=None):
    """
    Initializes and returns the Chat Engine.
    Re-creates the Index wrapper on each call to ensure visibility of new uploads,
    while caching heavy resources (LLM, Embeddings, DB Connection).
    """
    global _db_client, _embed_model, _llm

    db_path = "./chroma_db"
    if not os.path.exists(db_path):
        return None

    # 1. Initialize Heavy Resources Once
    if _db_client is None:
        print("Initializing Global ChromaDB Client...")
        _db_client = chromadb.PersistentClient(path=db_path)
    
    if _embed_model is None:
        _embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
    # Always ensure Settings are applied (in case ingest.py cleared them)
    Settings.embed_model = _embed_model

    if _llm is None:
        # Load config from env
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        ollama_key = os.getenv("OLLAMA_API_KEY", "")
        
        print(f"Initializing Ollama with URL={ollama_url}, Model={ollama_model}")
        
        # Prepare kwargs
        llm_kwargs = {
            "model": ollama_model,
            "base_url": ollama_url,
            "request_timeout": 300.0
        }
        
        # Add auth header if key is present
        if ollama_key:
            llm_kwargs["additional_kwargs"] = {
                "headers": {
                    "Authorization": f"Bearer {ollama_key}"
                }
            }
            # Some versions of llama-index might use different param names, 
            # but usually the client underlying it accepts headers. 
            # If "additional_kwargs" fails, we might need to check 'headers' param directly.
            # LlamaIndex Ollama class often passes **kwargs to the client.
        
        _llm = Ollama(**llm_kwargs)
    
    # Always ensure Settings are applied
    Settings.llm = _llm

    # 2. Access Collection (Dynamic)
    chroma_collection = _db_client.get_or_create_collection("rag_collection")
    if chroma_collection.count() == 0:
        return None

    # 3. Create Index Wrapper (Lightweight)
    # We re-create this to ensure it sees the latest state of the collection
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(vector_store)

    # 4. Create Chat Engine with System Prompt AND Filters
    system_prompt = (
        "You are a Technical Assistant. You will be given context that includes Markdown tables and image descriptions. "
        "Your goal is to answer the user's question based ONLY on the provided context. "
        "1. When reading a table row, strictly associate the 'Input/Description' column with the 'Specification/Logic' column. "
        "2. Do not hallucinate values not present in the table. "
        "3. If asked for a diagram, image, or layout, DO NOT generate ASCII art or text-based representations. "
        "Instead, simply state 'Please refer to the Source Visual below.' and summarize the key technical details found in the text description."
        "4. If the user input is a greeting (e.g., 'hi', 'hello', 'good morning') or a general pleasantry, ignore the strict context requirement and respond politely and naturally."
        "5. IDENTITY: If asked about your name or what you do, state: 'My name is SazAi. I am an intelligent Technical Assistant designed to help you analyze, understand, and extract insights from your complex technical documents, schematics, and manuals.'"
        "6. Provide direct, concise answers. Do not copy the entire context unless explicitly asked."
    )
    
    filters = None
    if selected_file:
        filters = MetadataFilters(
            filters=[ExactMatchFilter(key="file_name", value=selected_file)]
        )

    try:
        # Check if model exists by attempting to get metadata (lightweight check)
        # This prevents the hard crash deep inside llama-index
        # Note: We let index.as_chat_engine do the heavy lifting, but we wrap it.
        chat_engine = index.as_chat_engine(
            chat_mode="context",
            system_prompt=system_prompt,
            similarity_top_k=3, 
            filters=filters
        )
    except Exception as e:
        if "not found" in str(e) or "404" in str(e):
             # Make the error very extremely clear
             raise ValueError(
                 f"CRITICAL ERROR: The model '{_llm.model}' was not found at '{_llm.base_url}'. "
                 f"Please run `ollama pull {_llm.model}` in your terminal."
             )
        raise e

    return chat_engine
