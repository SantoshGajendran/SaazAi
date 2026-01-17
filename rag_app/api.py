from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
from typing import List

# Import our existing backend logic
from ingest import ingest_document, list_ingested_files, delete_ingested_file
from rag import get_chat_engine

app = FastAPI(title="SaazAi API", description="Backend for SaazAi RAG Application")

# CORS (Cross-Origin Resource Sharing) - Allow Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev, allow all. In prod, lock this down.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class ChatRequest(BaseModel):
    query: str
    selected_file: str

class ChatResponse(BaseModel):
    response: str
    image_base64: str | None = None
    citations: List[str] = []

# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "ok", "message": "SaazAi API is running"}

@app.get("/documents")
def get_documents():
    """List all ingested PDF files"""
    try:
        files = list_ingested_files()
        return {"documents": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and Ingest a PDF file"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Define storage path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        file_path = os.path.join(data_dir, file.filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ingest in a separate thread to guarantee non-blocking response
        import threading
        thread = threading.Thread(target=ingest_document, args=(file_path, file.filename))
        thread.start()
        
        return {"message": f"Successfully processed {file.filename}", "filename": file.filename}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{filename}")
def delete_document(filename: str):
    """Delete a document from index and disk"""
    try:
        success = delete_ingested_file(filename)
        if success:
            return {"message": f"Deleted {filename}"}
        else:
            raise HTTPException(status_code=404, detail="File not found or failed to delete")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Additional Imports ---
import base64
from io import BytesIO

# Reusing image render logic from app.py but adapting for API
import fitz 
from PIL import Image

def render_page_to_base64(file_name, page_number):
    """
    Renders a specific page of a PDF as a Base64 string.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        file_path = os.path.join(data_dir, file_name)
        
        if not os.path.exists(file_path):
            return None
            
        doc = fitz.open(file_path)
        try:
             page_idx = int(page_number) - 1
        except ValueError:
             page_idx = 0
        
        if page_idx < 0 or page_idx >= len(doc):
             return None
             
        page = doc.load_page(page_idx)
        # Higher resolution for frontend display
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
        
        # Convert to bytes
        img_data = pix.tobytes("png")
        base64_str = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/png;base64,{base64_str}"
        
    except Exception as e:
        print(f"Error rendering image: {e}")
        return None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the RAG engine.
    Required: query, selected_file
    """
    try:
        # Initialize engine for the specific file
        # In a production app, we would cache this engine instance
        chat_engine = get_chat_engine(selected_file=request.selected_file)
        
        if not chat_engine:
            raise HTTPException(status_code=400, detail="Chat engine could not be initialized. Ensure documents are ingested.")
            
        response = chat_engine.chat(request.query)
        
        # Process visual context (Image)
        image_b64 = None
        if hasattr(response, 'source_nodes') and response.source_nodes:
             for node in response.source_nodes:
                 if 'file_name' in node.metadata and 'page_label' in node.metadata:
                     # Attempt to render the top match
                     b64 = render_page_to_base64(node.metadata['file_name'], node.metadata['page_label'])
                     if b64:
                         image_b64 = b64
                         break 
        
        # Process citations
        citations = []
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for node in response.source_nodes:
                fn = node.metadata.get('file_name', 'Unknown')
                pg = node.metadata.get('page_label', '?')
                text_snippet = node.get_text()[:150] + "..."
                citations.append(f"{fn} (Page {pg}): {text_snippet}")

        return ChatResponse(
            response=response.response,
            image_base64=image_b64,
            citations=citations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
