import os
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from PyPDF2 import PdfReader

CHUNK_DIR = os.path.join(os.path.dirname(__file__), '..', 'storage', 'chunks')
PDF_DIR = os.path.join(os.path.dirname(__file__), '..', 'storage', 'pdfs')

os.makedirs(os.path.abspath(CHUNK_DIR), exist_ok=True)

@dataclass
class Paper:
    paper_id: str
    title: str
    path: str
    text: str


def _read_pdf(path: str) -> Tuple[str, str]:
    title = os.path.basename(path).rsplit('.', 1)[0]
    text_pages: List[str] = []
    try:
        reader = PdfReader(path)
        try:
            title_meta = reader.metadata.get('/Title') if reader.metadata else None
            if title_meta:
                title = str(title_meta)
        except Exception:
            pass
        for page in getattr(reader, 'pages', []) or []:
            try:
                txt = page.extract_text() or ''
                text_pages.append(txt)
            except Exception:
                text_pages.append("")
    except Exception:
        # unreadable PDF; keep empty text
        text_pages = []
    full_text = "\n".join(text_pages)
    return title, full_text


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
        if chunk_size <= overlap:
            break
    return chunks


def ingest_pdfs() -> Tuple[List[Dict], List[Dict]]:
    """Parse PDFs in storage/pdfs and write chunks JSONL; return paper metas and chunk records."""
    pdf_dir = os.path.abspath(PDF_DIR)
    chunk_dir = os.path.abspath(CHUNK_DIR)
    os.makedirs(chunk_dir, exist_ok=True)

    papers: List[Dict] = []
    chunks: List[Dict] = []

    for fname in os.listdir(pdf_dir):
        if not fname.lower().endswith('.pdf'):
            continue
        fpath = os.path.join(pdf_dir, fname)
        paper_id = os.path.splitext(fname)[0]
        title, text = _read_pdf(fpath)
        paper = {
            'paper_id': paper_id,
            'title': title,
            'path': fpath,
        }
        papers.append(paper)
        text_chunks = _chunk_text(text)
        for idx, ch in enumerate(text_chunks):
            chunk_id = f"{paper_id}::chunk_{idx:04d}"
            chunks.append({
                'chunk_id': chunk_id,
                'paper_id': paper_id,
                'title': title,
                'text': ch,
            })

    # Persist for reuse
    papers_path = os.path.join(chunk_dir, 'papers.json')
    chunks_path = os.path.join(chunk_dir, 'chunks.jsonl')
    with open(papers_path, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    with open(chunks_path, 'w', encoding='utf-8') as f:
        for rec in chunks:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return papers, chunks


def load_papers_and_chunks() -> Tuple[List[Dict], List[Dict]]:
    chunk_dir = os.path.abspath(CHUNK_DIR)
    papers_path = os.path.join(chunk_dir, 'papers.json')
    chunks_path = os.path.join(chunk_dir, 'chunks.jsonl')
    papers: List[Dict] = []
    chunks: List[Dict] = []
    if os.path.exists(papers_path):
        with open(papers_path, 'r', encoding='utf-8') as f:
            papers = json.load(f)
    if os.path.exists(chunks_path):
        with open(chunks_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
    return papers, chunks
