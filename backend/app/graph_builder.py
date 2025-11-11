import os
import json
from typing import List, Dict, Tuple
import networkx as nx
import yake

GRAPH_DIR = os.path.join(os.path.dirname(__file__), '..', 'storage', 'graph')
CHUNK_DIR = os.path.join(os.path.dirname(__file__), '..', 'storage', 'chunks')

os.makedirs(os.path.abspath(GRAPH_DIR), exist_ok=True)

KEYPHRASE_MAX = 15

class KnowledgeGraph:
    def __init__(self):
        self.graph_path = os.path.join(os.path.abspath(GRAPH_DIR), 'graph.json')
        self.G = nx.Graph()

    def build(self, papers: List[Dict], chunks: List[Dict]):
        kw_extractor = yake.KeywordExtractor(n=1, top=KEYPHRASE_MAX)
        # Add paper nodes
        for p in papers:
            self.G.add_node(p['paper_id'], label=p['title'], type='paper')
        # Collect keyphrases per paper
        paper_phrases: Dict[str, List[str]] = {}
        for p in papers:
            p_chunks = [c for c in chunks if c['paper_id'] == p['paper_id']]
            joined = " ".join(c['text'] for c in p_chunks[:10])  # sample first chunks
            kws = [kp for kp, score in kw_extractor.extract_keywords(joined)]
            paper_phrases[p['paper_id']] = kws
            # add concept nodes
            for kw in kws:
                node_id = f"concept::{kw.lower()}"
                if not self.G.has_node(node_id):
                    self.G.add_node(node_id, label=kw, type='concept')
                # edge paper -> concept
                self._add_edge(p['paper_id'], node_id, relation='mentions', weight=1.0)
        # Paper-paper similarity via shared concepts
        for i in range(len(papers)):
            for j in range(i+1, len(papers)):
                p1 = papers[i]['paper_id']
                p2 = papers[j]['paper_id']
                set1 = set(paper_phrases.get(p1, []))
                set2 = set(paper_phrases.get(p2, []))
                inter = set1 & set2
                if inter:
                    self._add_edge(p1, p2, relation='related', weight=float(len(inter)))
        self._persist()

    def _add_edge(self, s: str, t: str, relation: str, weight: float):
        if self.G.has_edge(s, t):
            # increment weight
            self.G[s][t]['weight'] += weight
        else:
            self.G.add_edge(s, t, relation=relation, weight=weight)

    def _persist(self):
        data = {
            'nodes': [
                {'id': n, 'label': self.G.nodes[n].get('label'), 'type': self.G.nodes[n].get('type')} for n in self.G.nodes
            ],
            'edges': [
                {'source': u, 'target': v, 'relation': self.G[u][v].get('relation'), 'weight': self.G[u][v].get('weight')} for u, v in self.G.edges
            ]
        }
        with open(self.graph_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        if not os.path.exists(self.graph_path):
            return
        with open(self.graph_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.G = nx.Graph()
        for node in data.get('nodes', []):
            self.G.add_node(node['id'], label=node.get('label'), type=node.get('type'))
        for edge in data.get('edges', []):
            self.G.add_edge(edge['source'], edge['target'], relation=edge.get('relation'), weight=edge.get('weight', 1.0))

    def subgraph_for_path(self, path: List[str]):
        sg = self.G.subgraph(path)
        return {
            'nodes': [ {'id': n, 'label': sg.nodes[n].get('label'), 'type': sg.nodes[n].get('type')} for n in sg.nodes ],
            'edges': [ {'source': u, 'target': v, 'relation': sg[u][v].get('relation'), 'weight': sg[u][v].get('weight')} for u, v in sg.edges ]
        }

    def to_dict(self):
        return {
            'nodes': [ {'id': n, 'label': self.G.nodes[n].get('label'), 'type': self.G.nodes[n].get('type')} for n in self.G.nodes ],
            'edges': [ {'source': u, 'target': v, 'relation': self.G[u][v].get('relation'), 'weight': self.G[u][v].get('weight')} for u, v in self.G.edges ]
        }
