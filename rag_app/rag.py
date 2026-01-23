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
        Settings.embed_model = _embed_model

    if _llm is None:
        # Using 127.0.0.1 to avoid localhost IPv6 resolution issues
        _llm = Ollama(model="gpt-oss:120b-cloud", base_url="http://127.0.0.1:11434", request_timeout=300.0)
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
        "1. When reading a table row, strictly associate the 'Input/Description' column with the 'Specification/Logic' column. "
        "2. Do not hallucinate values not present in the table. "
        "3. If asked for a diagram, image, or layout, DO NOT generate ASCII art or text-based representations. "
        "Instead, simply state 'Please refer to the Source Visual below.' and summarize the key technical details found in the text description."
        "4. If the user input is a greeting (e.g., 'hi', 'hello', 'good morning') or a general pleasantry, ignore the strict context requirement and respond politely and naturally."
        "5. IDENTITY: If asked about your name or what you do, state: 'My name is SazAi. I am an intelligent Technical Assistant designed to help you analyze, understand, and extract insights from your complex technical documents, schematics, and manuals.'"
    )
    
    filters = None
    if selected_file:
        filters = MetadataFilters(
            filters=[ExactMatchFilter(key="file_name", value=selected_file)]
        )

    chat_engine = index.as_chat_engine(
        chat_mode="context",
        system_prompt=system_prompt,
        similarity_top_k=5, 
        filters=filters
    )

    return chat_engine
