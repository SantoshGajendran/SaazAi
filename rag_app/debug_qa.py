
from rag import get_chat_engine

def debug_chat():
    fname = "SaazvatTemplate.pptx"
    print(f"Initializing engine for {fname}...")
    engine = get_chat_engine(selected_file=fname)
    
    if not engine:
        print("Engine is None!")
        return

    query = "what is this ppt about"
    print(f"Querying: {query}")
    response = engine.chat(query)
    
    print("-" * 20)
    print(f"Raw Response: '{response.response}'")
    print("-" * 20)
    
    if hasattr(response, "source_nodes"):
        print(f"Source Nodes: {len(response.source_nodes)}")
        for node in response.source_nodes:
            print(f" - Node score: {node.score}")
            print(f" - Content Preview: {node.get_text()[:50]}...")

if __name__ == "__main__":
    debug_chat()
