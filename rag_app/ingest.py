import os
import nest_asyncio
from dotenv import load_dotenv
from llama_parse import LlamaParse
from llama_index.core import VectorStoreIndex, StorageContext, SimpleDirectoryReader
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import chromadb

load_dotenv()
nest_asyncio.apply()

def ingest_document(file_path, original_filename=None):
    """
    Ingests a single PDF file using LlamaParse (Markdown mode) to preserve table structures.
    Persists the data to a local ChromaDB instance.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    print(f"Starting ingestion for: {file_path}")

    # 1. Initialize LlamaParse
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY not found in environment variables.")

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",  # Crucial for tables
        verbose=True,
        parsing_instruction="The provided document is a technical manual. Please extract all text, tables, and provide detailed textual descriptions for any images, diagrams, or schematics found, so they can be searched."
    )

    # 2. Parse the PDF
    # 2. Parse the PDF
    # Direct load to get list of documents (usually one per page)
    try:
        documents = parser.load_data(file_path)
    except Exception as e:
         raise ValueError(f"LlamaParse failed: {e}")
    
    if not documents:
        raise ValueError("LlamaParse returned 0 documents. Please check the content of the PDF or your LlamaCloud API Key.")

    # --- METADATA FIX: Override temp filename and Assign Page Numbers ---
    print(f"Parsed {len(documents)} chunks. Assigning metadata...")
    for i, doc in enumerate(documents):
        # Assign Page Number (1-indexed) assuming ordered return
        doc.metadata["page_label"] = str(i + 1)
        
        if original_filename:
             doc.metadata["file_name"] = original_filename
        else:
             doc.metadata["file_name"] = os.path.basename(file_path)

    print(f"Successfully parsed {len(documents)} document chunks from {file_path}")

    # 3. Setup ChromaDB and Embeddings
    db_path = "./chroma_db"
    db = chromadb.PersistentClient(path=db_path)
    chroma_collection = db.get_or_create_collection("rag_collection")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

    # 4. Create Index and Persist
    # Note: We pass the embedding model both to the index construction or set it in the global settings.
    # For newer LlamaIndex versions, it's often best to set it in the Settings or pass transformation context.
    # Here we'll pass it explicitly if possible or rely on global Settings if needed, 
    # but the simplest robust way in modern LlamaIndex is using the `embed_model` arg in `from_documents` (via service context deprecated) 
    # or Settings. Let's use the property way or Settings.
    
    from llama_index.core import Settings
    Settings.embed_model = embed_model
    
    # We don't need to specify LLM here for ingestion, just embeddings
    Settings.llm = None 

    print("Creating vector store index...")
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
    )
    
    print("Ingestion complete. Data persisted to ./chroma_db")
    return True

# --- Admin Helpers ---

def get_db_collection():
    """Helper to get the ChromaDB collection"""
    db_path = "./chroma_db"
    db = chromadb.PersistentClient(path=db_path)
    return db.get_or_create_collection("rag_collection")

def list_ingested_files():
    """Returns a list of PDF filenames currently in the data directory."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        
        if not os.path.exists(data_dir):
            return []
            
        files = [f for f in os.listdir(data_dir) if f.lower().endswith('.pdf')]
        return sorted(files)
    except Exception as e:
        print(f"Error listing files from disk: {e}")
        return []

def delete_ingested_file(filename):
    """Deletes all chunks associated with a specific filename and removes the file from data/."""
    try:
        collection = get_db_collection()
        # Delete where metadata 'file_name' matches
        collection.delete(where={"file_name": filename})
        print(f"Deleted metadata for file: {filename}")
        
        # Also remove from data/ directory
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        file_path = os.path.join(data_dir, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted physical file: {file_path}")
        else:
            print(f"Physical file not found: {file_path}")
            
        return True
    except Exception as e:
        print(f"Error deleting file {filename}: {e}")
        return False

