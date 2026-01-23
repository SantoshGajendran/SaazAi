
print("Start")
import sys
print("Imports started")
try:
    print("Importing chromadb...")
    import chromadb
    print("Importing llama_index.core...")
    from llama_index.core import VectorStoreIndex
    print("Importing HuggingFaceEmbedding...")
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    print("Importing Ollama...")
    from llama_index.llms.ollama import Ollama
    print("Done imports")
except Exception as e:
    print(e)
