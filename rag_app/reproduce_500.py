
import sys
import os
import traceback

# Ensure we can import modules from current directory
sys.path.append(os.getcwd())

try:
    print("1. Importing rag module...")
    from rag import get_chat_engine
    print("   Success.")

    print("2. Initializing Chat Engine...")
    # Mocking a selected file if needed, or None
    engine = get_chat_engine()
    
    if engine is None:
        print("   Warning: Engine returned None (maybe no docs ingested?)")
    else:
        print("   Success. Engine initialized.")

        print("3. Sending test query...")
        response = engine.chat("Hello, are you working?")
        print(f"   Success. Response: {response}")

except Exception as e:
    print("\n!!! CRASH DETECTED !!!")
    print("-" * 30)
    traceback.print_exc()
    print("-" * 30)
