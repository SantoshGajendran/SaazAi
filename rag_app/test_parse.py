import os
from dotenv import load_dotenv
from llama_parse import LlamaParse
import nest_asyncio

load_dotenv()
nest_asyncio.apply()

def test_parse():
    # Use the existing file in data/ if possible, or any pdf
    data_dir = os.path.join("rag_app", "data")
    files = os.listdir(data_dir)
    if not files:
        print("No files in rag_app/data to test.")
        return

    file_path = os.path.join(data_dir, files[0])
    print(f"Testing parse on: {file_path}")

    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=True,
        # parsing_instruction="Extract text." # simplified
    )

    # Method 1: Direct load_data
    docs = parser.load_data(file_path)
    print(f"\nDirect load_data yielded {len(docs)} documents.")
    if docs:
        print(f"Sample Metadata: {docs[0].metadata}")
        if 'page_label' in docs[0].metadata:
            print(f"Page Label Present: {docs[0].metadata['page_label']}")
        else:
            print("Page Label MISSING in direct load.")

if __name__ == "__main__":
    test_parse()
