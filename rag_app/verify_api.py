from fpdf import FPDF
from llama_parse import LlamaParse
import os
import nest_asyncio
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()

def create_test_pdf(filename="test_doc.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Hello, World!", ln=1, align="C")
    pdf.output(filename)
    print(f"Created {filename}")

def test_parsing(filename="test_doc.pdf"):
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    print(f"Using API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    
    if not api_key:
        print("Error: No API Key found.")
        return

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=True
    )

    try:
        print("Attempting to parse...")
        documents = parser.load_data(filename)
        if not documents:
            print("FAILURE: LlamaParse returned 0 documents.")
        else:
            print(f"SUCCESS: LlamaParse returned {len(documents)} documents.")
            print(f"Content preview: {documents[0].get_content()[:100]}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    create_test_pdf()
    test_parsing()
