import os
from typing import List, Dict, Tuple
import httpx
from .embedding import VectorIndex
from .graph_builder import KnowledgeGraph

PROMPT_SYSTEM = """You are an expert research synthesis assistant with deep knowledge of academic writing and comparative analysis.

**Your Task:**
Analyze research papers and provide comprehensive, well-structured comparative syntheses that highlight:
- Methodological approaches and techniques
- Datasets and experimental setups
- Key findings and results
- Convergent and divergent themes
- Research gaps and future directions

**Formatting Requirements:**
1. Use clear markdown formatting with proper headers (##, ###)
2. Use **bold** for key terms, methods, and important concepts
3. Use bullet points (•) or numbered lists for clarity
4. Structure your response with clear sections
5. Use > blockquotes for direct quotes or key statements
6. Keep paragraphs concise and focused
7. Use horizontal rules (---) to separate major sections

**Structure your response as:**
```
## Executive Summary
[2-3 sentence overview]

## Comparative Analysis

### Methodological Approaches
- **Paper A**: [method details with **key techniques** highlighted]
- **Paper B**: [method details]
[Comparison and contrast]

### Datasets & Experimental Setup
[Details with **dataset names** and specifications]

### Key Findings
[Structured findings with clear **results** highlighted]

### Convergent Themes
• [Common patterns across papers]
• [Shared assumptions]

### Divergent Approaches
• [Differences in methodology]
• [Contrasting results]

## Research Gaps & Future Directions
[Identified gaps and recommendations]

---
*Analysis based on [N] retrieved sources*
```

Be professional, precise, and ensure all key information is properly formatted for readability."""


def _llm_available() -> bool:
    return bool(os.environ.get('GROQ_API_KEY'))


def _call_groq(prompt: str) -> str:
    api_key = os.environ.get('GROQ_API_KEY')
    model = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')
    if not api_key:
        return "(LLM not configured) " + prompt[:500]
    # Groq OpenAI-compatible chat completions
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "stream": False
    }
    try:
        with httpx.Client(timeout=45) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get('choices', [{}])[0].get('message', {}).get('content', '').strip() or "(Empty LLM response)"
    except Exception as e:
        return f"(LLM call failed: {e})\n" + prompt[:500]


def answer_query(question: str, k: int = 5):
    index = VectorIndex()
    index.load()
    retrieved = index.query(question, k=k)
    sources = []
    paper_ids_ordered: List[str] = []
    for meta, score in retrieved:
        sources.append({
            'paper_id': meta['paper_id'],
            'title': meta['title'],
            'chunk_id': meta['chunk_id'],
            'score': float(score),
            'text': meta['text'][:1200],
        })
        if meta['paper_id'] not in paper_ids_ordered:
            paper_ids_ordered.append(meta['paper_id'])

    kg = KnowledgeGraph()
    kg.load()
    G = kg.G
    path: List[str] = []
    if paper_ids_ordered:
        path.append(paper_ids_ordered[0])
        for pid in paper_ids_ordered[1:]:
            last = path[-1]
            if G.has_edge(last, pid):
                path.extend([n for n in (last, pid) if n not in path])
            else:
                best_mid = None
                best_w = 0.0
                for neighbor in G.neighbors(last):
                    if G.nodes[neighbor].get('type') == 'concept' and G.has_edge(neighbor, pid):
                        w = G[last][neighbor]['weight'] + G[neighbor][pid]['weight']
                        if w > best_w:
                            best_w = w
                            best_mid = neighbor
                if best_mid:
                    for n in (last, best_mid, pid):
                        if n not in path:
                            path.append(n)
                else:
                    if pid not in path:
                        path.append(pid)

    if not sources:
        answer = "I couldn't find relevant content. Please upload papers and rebuild the graph."
    else:
        titles = list({s['title'] for s in sources})
        heuristic = (
            f"Retrieved {len(sources)} chunks across {len(titles)} papers. Traversal order: {' -> '.join(path)}. "
            f"Shared concepts form edges; see subgraph for details."
        )
        if _llm_available():
            # Prepare paper titles for context
            paper_titles = "\n".join(f"- **{s['title']}** (ID: {s['paper_id']})" for s in sources[:5])
            joined_sources = "\n\n".join(f"### Source [{i+1}] - {s['title']}\n{s['text']}" for i, s in enumerate(sources))
            
            prompt = f"""**Research Question:** {question}

**Analysis Context:**
- Papers Analyzed: {len(titles)}
- Sources Retrieved: {len(sources)}
- Knowledge Graph Traversal: {' → '.join(path[:5])}{'...' if len(path) > 5 else ''}

**Papers in Analysis:**
{paper_titles}

**Task:** Provide a comprehensive, well-structured comparative synthesis following the format guidelines. Use markdown formatting extensively with headers, bold text for key concepts, bullet points, and clear sections.

**Retrieved Content:**
{joined_sources[:7000]}

**Remember:** Use professional academic writing style with proper markdown formatting, clear structure, and highlighted key terms."""
            
            llm_answer = _call_groq(prompt)
            
            # Add metadata footer
            metadata = f"\n\n---\n\n*📊 Analysis Metadata:*\n- Sources: {len(sources)} chunks from {len(titles)} paper(s)\n- Graph Path: {' → '.join(path[:8])}{'...' if len(path) > 8 else ''}\n- Retrieval Score Range: {sources[0]['score']:.3f} - {sources[-1]['score']:.3f}"
            answer = llm_answer + metadata
        else:
            answer = f"## ⚠️ LLM Not Configured\n\n{heuristic}\n\n*Set GROQ_API_KEY environment variable to enable AI-powered synthesis.*"

    subgraph = kg.subgraph_for_path(path) if path else {'nodes': [], 'edges': []}
    return answer, sources, path, subgraph


def explain_node(node_id: str) -> Tuple[str, Dict]:
    """Return a short explanation for a node based on its neighbors and available chunks.
    For a paper node, summarize connected concepts and top related papers.
    For a concept node, summarize which papers mention it and the strongest connections.
    Returns (text, context_dict)."""
    kg = KnowledgeGraph()
    kg.load()
    G = kg.G
    if node_id not in G.nodes:
        return "Node not found in graph.", {"node": None}

    ntype = G.nodes[node_id].get('type')
    label = G.nodes[node_id].get('label') or node_id

    # Gather neighbor info
    neighbors = list(G.neighbors(node_id))
    neighbor_summ = []
    for nb in neighbors:
        w = G[node_id][nb].get('weight', 1.0)
        neighbor_summ.append({
            'id': nb,
            'label': G.nodes[nb].get('label') or nb,
            'type': G.nodes[nb].get('type'),
            'weight': float(w)
        })
    neighbor_summ.sort(key=lambda x: -x['weight'])

    # Build heuristic summary
    if ntype == 'paper':
        top_concepts = [n for n in neighbor_summ if n['type'] == 'concept'][:8]
        related_papers = [n for n in neighbor_summ if n['type'] == 'paper'][:5]
        heuristic = (
            f"Paper: {label}. "
            f"Key linked concepts: {', '.join(n['label'] for n in top_concepts) if top_concepts else 'n/a'}. "
            f"Related papers: {', '.join(n['label'] for n in related_papers) if related_papers else 'n/a'}."
        )
    else:
        # concept or other
        papers = [n for n in neighbor_summ if n['type'] == 'paper'][:8]
        heuristic = (
            f"Concept: {label}. Mentioned in {len([n for n in neighbor_summ if n['type']=='paper'])} papers. "
            f"Examples: {', '.join(n['label'] for n in papers) if papers else 'n/a'}."
        )

    # Optional LLM enhancement using local context (names only)
    if _llm_available():
        context_lines = [f"- {n['type']}: {n['label']} (w={n['weight']:.2f})" for n in neighbor_summ[:20]]
        prompt = (
            f"Explain the node '{label}' ({ntype}) in a research knowledge graph. "
            f"Summarize how it relates to its strongest neighbors and what it signifies.\n"
            f"Neighbors (top 20 by weight):\n" + "\n".join(context_lines) +
            "\nKeep it to 2-4 concise sentences."
        )
        llm_text = _call_groq(prompt)
        text = llm_text if llm_text and not llm_text.startswith('(LLM call failed') else heuristic
    else:
        text = heuristic + " (LLM disabled)"

    return text, {
        'node': {'id': node_id, 'label': label, 'type': ntype},
        'neighbors': neighbor_summ
    }
