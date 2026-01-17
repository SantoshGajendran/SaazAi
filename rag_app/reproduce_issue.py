import sys
import os

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from rag import get_chat_engine

def main():
    print("Initializing chat engine...")
    engine = get_chat_engine()
    
    if engine is None:
        print("Engine is None. No vector store found?")
        return

    print("Sending query: 'what is this document about'")
    try:
        response = engine.chat("what is this document about")
        print(f"RAW RESPONSE OBJECT: {response}")
        print(f"RESPONSE TEXT: '{response.response}'")
        
        if hasattr(response, 'source_nodes'):
            print(f"Num Source Nodes: {len(response.source_nodes)}")
            for node in response.source_nodes:
                print(f" - Node Score: {node.score}")
                print(f" - Content Preview: {node.get_text()[:50]}...")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
