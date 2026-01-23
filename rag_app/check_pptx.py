
import chromadb

def check_db():
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection("rag_collection")
        
        # Get all metadatas
        data = collection.get(include=["metadatas"])
        metadatas = data['metadatas']
        
        files = {}
        for m in metadatas:
            fn = m.get('file_name', 'Unknown')
            files[fn] = files.get(fn, 0) + 1
            
        print("Files in DB:", files)
        
        target = "SaazvatTemplate.pptx"
        if target in files:
            print(f"FOUND: {target} has {files[target]} chunks.")
        else:
            print(f"MISSING: {target} not found in DB.")
            
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    check_db()
