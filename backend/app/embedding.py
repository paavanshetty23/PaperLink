import os
import json
from typing import List, Dict, Tuple
import numpy as np

_TRANSFORMERS_AVAILABLE = True
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    _TRANSFORMERS_AVAILABLE = False
try:
    import faiss  # type: ignore
except Exception:
    faiss = None

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

CHUNK_DIR = os.path.join(os.path.dirname(__file__), '..', 'storage', 'chunks')
INDEX_DIR = os.path.join(os.path.dirname(__file__), '..', 'storage', 'index')
MODEL_NAME = os.environ.get('EMBED_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')

os.makedirs(os.path.abspath(INDEX_DIR), exist_ok=True)

class VectorIndex:
    def __init__(self):
        self.transformer_model = None
        self.tfidf_vectorizer: TfidfVectorizer | None = None
        self.svd: TruncatedSVD | None = None
        self.embeddings: np.ndarray | None = None
        self.index_path = os.path.join(os.path.abspath(INDEX_DIR), 'faiss.index')
        self.meta_path = os.path.join(os.path.abspath(INDEX_DIR), 'meta.json')
        self.faiss_index = None
        self.meta: List[Dict] = []
        self.backend = 'transformer' if _TRANSFORMERS_AVAILABLE and faiss is not None else 'tfidf'
        if self.backend == 'transformer':
            try:
                self.transformer_model = SentenceTransformer(MODEL_NAME)
            except Exception:
                self.backend = 'tfidf'

    def _embed_transformer(self, texts: List[str]) -> np.ndarray:
        emb = self.transformer_model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        return emb.astype('float32')

    def _embed_tfidf(self, texts: List[str]) -> np.ndarray:
        if self.tfidf_vectorizer is None:
            self.tfidf_vectorizer = TfidfVectorizer(max_features=4000, ngram_range=(1,2))
            X = self.tfidf_vectorizer.fit_transform(texts)
            self.svd = TruncatedSVD(n_components=256, random_state=42)
            reduced = self.svd.fit_transform(X)
            # Normalize
            norms = np.linalg.norm(reduced, axis=1, keepdims=True) + 1e-9
            self.embeddings = (reduced / norms).astype('float32')
        else:
            X = self.tfidf_vectorizer.transform(texts)
            reduced = self.svd.transform(X)
            norms = np.linalg.norm(reduced, axis=1, keepdims=True) + 1e-9
            return (reduced / norms).astype('float32')
        return self.embeddings

    def build(self, chunks: List[Dict]):
        texts = [c['text'] for c in chunks]
        if self.backend == 'transformer':
            vecs = self._embed_transformer(texts)
            d = vecs.shape[1]
            index = faiss.IndexFlatIP(d)
            index.add(vecs)
            self.faiss_index = index
            self.embeddings = vecs
        else:
            vecs = self._embed_tfidf(texts)
        self.meta = chunks
        # Persist meta only (embedding rebuild is fast for tfidf)
        with open(self.meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f)
        if self.backend == 'transformer' and self.faiss_index is not None:
            faiss.write_index(self.faiss_index, self.index_path)

    def load(self):
        if os.path.exists(self.meta_path):
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                self.meta = json.load(f)
        if self.backend == 'transformer' and faiss is not None and os.path.exists(self.index_path):
            try:
                self.faiss_index = faiss.read_index(self.index_path)
            except Exception:
                self.faiss_index = None
        # For tfidf we lazily rebuild embeddings when first query arrives if not built.

    def query(self, text: str, k: int = 5) -> List[Tuple[Dict, float]]:
        if not self.meta:
            self.load()
        if not self.meta:
            return []
        k = min(k, len(self.meta))
        if self.backend == 'transformer' and self.faiss_index is not None:
            q = self._embed_transformer([text])
            scores, idxs = self.faiss_index.search(q, k)
            results: List[Tuple[Dict, float]] = []
            for i, sc in zip(idxs[0], scores[0]):
                if i == -1:
                    continue
                meta = self.meta[i]
                results.append((meta, float(sc)))
            return results
        # TF-IDF cosine similarity
        if self.embeddings is None or self.tfidf_vectorizer is None:
            # rebuild embeddings
            texts = [c['text'] for c in self.meta]
            self._embed_tfidf(texts)
        q_vec = self._embed_tfidf([text])
        sims = (self.embeddings @ q_vec.T).ravel()
        top_idx = np.argsort(-sims)[:k]
        results: List[Tuple[Dict, float]] = []
        for i in top_idx:
            results.append((self.meta[i], float(sims[i])))
        return results
