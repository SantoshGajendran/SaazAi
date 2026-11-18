import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import app

client = TestClient(app)

def test_chat_stream_missing_body():
    response = client.post("/chat/stream", json={})
    assert response.status_code == 422

def test_chat_stream_empty_query():
    response = client.post("/chat/stream", json={"query": "", "selected_file": "manual.pdf"})
    assert response.status_code in (400, 422)

def test_chat_stream_whitespace_query():
    response = client.post("/chat/stream", json={"query": "   ", "selected_file": "manual.pdf"})
    assert response.status_code in (400, 422)

def test_chat_stream_engine_not_initialized():
    with patch("api.get_chat_engine", return_value=None):
        response = client.post("/chat/stream", json={"query": "hello", "selected_file": "manual.pdf"})
        assert response.status_code == 400

def test_chat_stream_success_sse():
    mock_chat_engine = MagicMock()
    mock_stream = MagicMock()
    mock_stream.response_gen = iter(["Hello", " ", "world"])

    mock_node = MagicMock()
    mock_node.metadata = {"file_name": "manual.pdf", "page_label": "2"}
    mock_node.score = 0.892
    mock_node.get_text.return_value = "Snippet text from manual"
    mock_stream.source_nodes = [mock_node]

    mock_chat_engine.stream_chat.return_value = mock_stream

    with patch("api.get_chat_engine", return_value=mock_chat_engine):
        response = client.post("/chat/stream", json={"query": "explain spec", "selected_file": "manual.pdf"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert "event: token" in content
        assert "delta" in content
        assert "event: citation" in content
        assert "manual.pdf" in content
        assert "event: done" in content
