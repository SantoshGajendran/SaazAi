import os
import pytest
from fastapi.testclient import TestClient
import sys

# Ensure rag_app is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import app

client = TestClient(app)

def test_get_raw_document_success():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    sample_file = os.path.join(data_dir, "test_manual.pdf")
    with open(sample_file, "wb") as f:
        f.write(b"%PDF-1.4 sample content for testing range requests")
    
    try:
        response = client.get("/documents/test_manual.pdf/raw")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-1.4")
    finally:
        if os.path.exists(sample_file):
            os.remove(sample_file)

def test_get_raw_document_range_request():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    sample_file = os.path.join(data_dir, "test_range.pdf")
    with open(sample_file, "wb") as f:
        f.write(b"%PDF-1.4 sample content for testing range requests")
    
    try:
        response = client.get("/documents/test_range.pdf/raw", headers={"Range": "bytes=0-7"})
        assert response.status_code == 206
        assert response.content == b"%PDF-1.4"
        assert "bytes 0-7/" in response.headers.get("content-range", "")
    finally:
        if os.path.exists(sample_file):
            os.remove(sample_file)

def test_get_raw_document_path_traversal():
    response = client.get("/documents/..%2F..%2F.env/raw")
    assert response.status_code in (400, 404)

def test_get_raw_document_not_found():
    response = client.get("/documents/non_existent_file_999.pdf/raw")
    assert response.status_code == 404
