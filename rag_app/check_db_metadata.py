import chromadb
import pandas as pd

def check_metadata():
    db_path = "./chroma_db"
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection("rag_collection")
    
    data = collection.get(include=['metadatas'])
    metadatas = data['metadatas']
    
    if not metadatas:
        print("No documents found in DB.")
        return

    print(f"Total Chunks: {len(metadatas)}")
    
    # Analyze Page Labels
    page_counts = {}
    files = set()
    
    for m in metadatas:
        if m:
            f = m.get('file_name', 'unknown')
            files.add(f)
            p = m.get('page_label', 'N/A')
            key = f"{f} - Page {p}"
            page_counts[key] = page_counts.get(key, 0) + 1
            
    print(f"\nUnique Files: {files}")
    print("\nPage Distribution (Top 20):")
    for k, v in list(page_counts.items())[:20]:
        print(f"{k}: {v} chunks")

if __name__ == "__main__":
    check_metadata()
