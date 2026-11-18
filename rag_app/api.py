from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
from typing import List
import traceback

# Import our existing backend logic
from ingest import ingest_document, list_ingested_files, delete_ingested_file, get_storage_stats
from rag import get_chat_engine

app = FastAPI(title="SzAi API", description="Backend for SzAi RAG Application")

# In-memory progress tracker: { filename: "Status Message" }
upload_progress = {}

def update_progress(filename, message):
    upload_progress[filename] = message

def run_ingest_background(file_path, filename):
    try:
        update_progress(filename, "Starting...")
        ingest_document(file_path, filename, callback=lambda msg: update_progress(filename, msg))
    except Exception as e:
        update_progress(filename, f"Error: {str(e)}")
    # Note: "Completed" is set by ingest_document's last callback or could be done here.
    # We rely on the callback for fine-grained steps.

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
    return {"status": "ok", "message": "SzAi API is running"}

@app.get("/documents")
def get_documents():
    """List all ingested PDF files"""
    try:
        files = list_ingested_files()
        return {"documents": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    """Get storage statistics"""
    try:
        return get_storage_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/upload_status/{filename}")
def get_upload_status(filename: str):
    """Get current upload/ingestion status"""
    status = upload_progress.get(filename, "Not Started")
    return {"filename": filename, "status": status}

@app.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload and Ingest a file (PDF, PPTX, DOCX)"""
    allowed_exts = (".pdf", ".pptx", ".docx", ".ppt", ".doc")
    if not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(status_code=400, detail=f"Only PDF, PPTX, and DOCX files are allowed. Got: {file.filename}")
    
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
            
        # Ingest in background with progress tracking
        background_tasks.add_task(run_ingest_background, file_path, file.filename)
        
        return {"message": f"Processing started for {file.filename}", "filename": file.filename}
        
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

@app.get("/documents/{filename}/raw")
def get_raw_document(filename: str):
    """Streams raw PDF binary file with HTTP Range support."""
    clean_name = os.path.basename(filename)
    if clean_name != filename or not clean_name:
        raise HTTPException(status_code=400, detail="Invalid filename parameter.")
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    file_path = os.path.join(data_dir, clean_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found.")
        
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=clean_name
    )

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
        
        # PyMuPDF (fitz) only reliably renders PDFs/XPS/Images. 
        # For Word/PPT, we skip rendering for now to avoid errors.
        if not file_name.lower().endswith('.pdf'):
            return None
        
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
        print("Error in chat endpoint:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
