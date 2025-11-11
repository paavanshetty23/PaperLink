import os
import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    r = client.get('/')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_upload_and_build_graph_empty():
    # Upload no file should fail; upload with a tiny fake PDF buffer
    # Create a minimal PDF header bytes
    pdf_bytes = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    files = [('files', ('test.pdf', io.BytesIO(pdf_bytes), 'application/pdf'))]
    r = client.post('/upload-pdfs', files=files)
    assert r.status_code == 200
    data = r.json()
    assert 'papers_ingested' in data
    assert 'chunks_indexed' in data

    r2 = client.post('/build-graph')
    assert r2.status_code == 200
    ginfo = r2.json()
    assert 'nodes' in ginfo and 'edges' in ginfo


def test_query_endpoint():
    r = client.post('/query', json={'question': 'Compare methods across papers', 'k': 3})
    assert r.status_code == 200
    data = r.json()
    assert 'answer' in data
    assert 'sources' in data
    assert 'subgraph' in data
