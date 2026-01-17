import chromadb
import sys

def check_db():
    db_path = "./chroma_db"
    try:
        db = chromadb.PersistentClient(path=db_path)
        print(f"Collections: {db.list_collections()}")
        
        # collection name is 'rag_collection' as per rag.py
        try:
            collection = db.get_collection("rag_collection")
            count = collection.count()
            print(f"Item count in 'rag_collection': {count}")
        except ValueError:
            print("'rag_collection' does not exist.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
