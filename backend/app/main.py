import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import orjson
from dotenv import load_dotenv

from .models import UploadResponse, BuildGraphResponse, GraphResponse, PapersResponse, QueryRequest, QueryResponse, GraphNode, GraphEdge
from .pdf_loader import ingest_pdfs, load_papers_and_chunks, PDF_DIR
from .embedding import VectorIndex
from .graph_builder import KnowledgeGraph
from .rag import answer_query, explain_node

load_dotenv()  # load .env if present

app = FastAPI(title="Paper Synthesizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-pdfs", response_model=UploadResponse)
async def upload_pdfs(files: List[UploadFile] = File(...)):
    os.makedirs(os.path.abspath(PDF_DIR), exist_ok=True)
    for f in files:
        dest = os.path.join(os.path.abspath(PDF_DIR), f.filename)
        with open(dest, 'wb') as out:
            out.write(await f.read())
    papers, chunks = ingest_pdfs()
    # Build embeddings index
    index = VectorIndex()
    index.build(chunks)
    return UploadResponse(papers_ingested=len(papers), chunks_indexed=len(chunks))

@app.post("/build-graph", response_model=BuildGraphResponse)
async def build_graph():
    papers, chunks = load_papers_and_chunks()
    kg = KnowledgeGraph()
    kg.build(papers, chunks)
    return BuildGraphResponse(nodes=len(kg.G.nodes), edges=len(kg.G.edges))

@app.get("/graph", response_model=GraphResponse)
async def get_graph():
    kg = KnowledgeGraph()
    kg.load()
    data = kg.to_dict()
    return GraphResponse(
        nodes=[GraphNode(**n) for n in data['nodes']],
        edges=[GraphEdge(**e) for e in data['edges']]
    )

@app.get("/papers", response_model=PapersResponse)
async def list_papers():
    papers, _ = load_papers_and_chunks()
    return PapersResponse(papers=papers)

@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    answer, sources, path, subgraph = answer_query(req.question, k=req.k)
    return QueryResponse(
        answer=answer,
        sources=sources,
        traversal_path=path,
        subgraph=GraphResponse(
            nodes=[GraphNode(**n) for n in subgraph['nodes']],
            edges=[GraphEdge(**e) for e in subgraph['edges']]
        ),
    )

@app.get("/explain-node")
async def explain(node_id: str):
    text, ctx = explain_node(node_id)
    return {"explanation": text, **ctx}

@app.post("/clear-all")
async def clear_all():
    """Clear all stored data (PDFs, chunks, graph, index)"""
    try:
        storage_dir = os.path.join(os.path.dirname(__file__), '..', 'storage')
        storage_dir = os.path.abspath(storage_dir)
        
        # Clear subdirectories
        for subdir in ['pdfs', 'chunks', 'graph', 'index']:
            path = os.path.join(storage_dir, subdir)
            if os.path.exists(path):
                # Remove all files in directory but keep the directory
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
        
        return {"message": "All data cleared successfully"}
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/")
async def root():
    return {"status": "ok"}
