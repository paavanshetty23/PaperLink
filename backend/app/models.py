from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class UploadResponse(BaseModel):
    papers_ingested: int
    chunks_indexed: int

class BuildGraphResponse(BaseModel):
    nodes: int
    edges: int

class PaperMeta(BaseModel):
    paper_id: str
    title: str
    path: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    keyphrases: Optional[List[str]] = None

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # paper | concept | dataset | method | result

class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    relation: str

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class QueryRequest(BaseModel):
    question: str
    k: int = 5

class SourceChunk(BaseModel):
    paper_id: str
    title: str
    chunk_id: str
    score: float
    text: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    traversal_path: List[str]
    subgraph: GraphResponse

class PapersResponse(BaseModel):
    papers: List[PaperMeta]
