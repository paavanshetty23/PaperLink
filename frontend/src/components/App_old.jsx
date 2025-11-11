import React, { useEffect, useState } from 'react';
import Upload from './Upload';
import GraphView from './GraphView';
import PaperList from './PaperList';
import axios from 'axios';

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [papers, setPapers] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeInfo, setNodeInfo] = useState(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [error, setError] = useState('');
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [showTooltip, setShowTooltip] = useState(false);
  const [panelCollapsed, setPanelCollapsed] = useState(false);
  const [queryText, setQueryText] = useState('How do these papers compare in their methods and datasets?');
  const [queryAnswer, setQueryAnswer] = useState('');
  const [querySources, setQuerySources] = useState([]);
  const [queryBusy, setQueryBusy] = useState(false);
  const [queryError, setQueryError] = useState('');

  const refreshGraph = async () => {
    const res = await axios.get('/api/graph');
    setGraph(res.data);
  };
  const refreshPapers = async () => {
    const res = await axios.get('/api/papers');
    setPapers(res.data.papers || []);
  };

  const explainNode = async (node, event) => {
    setSelectedNode(node);
    setLoadingExplain(true);
    setError('');
    setNodeInfo(null);
    
    const rect = event?.target?.getBoundingClientRect();
    if (rect) {
      const x = Math.min(rect.left + 20, window.innerWidth - 500);
      const y = Math.min(rect.top - 40, window.innerHeight - 400);
      setTooltipPos({ x: Math.max(20, x), y: Math.max(20, y) });
    }
    setShowTooltip(true);

    try {
      const res = await axios.get('/api/explain-node', { params: { node_id: node.id } });
      setNodeInfo(res.data);
    } catch (e) {
      setError(e?.response?.data?.detail || String(e));
    } finally {
      setLoadingExplain(false);
    }
  };

  const closeTooltip = () => {
    setShowTooltip(false);
    setTimeout(() => {
      setSelectedNode(null);
      setNodeInfo(null);
      setError('');
    }, 200);
  };

  const handleQuery = async () => {
    setQueryBusy(true);
    setQueryError('');
    setQueryAnswer('');
    setQuerySources([]);
    try {
      const q = queryText.trim() || 'Summarize the relationships across these papers.';
      const res = await axios.post('/api/query', { question: q, k: 6 });
      setQueryAnswer(res.data.answer);
      setQuerySources(res.data.sources || []);
      await refreshGraph();
    } catch (e) {
      setQueryError(e?.response?.data?.detail || String(e));
    } finally {
      setQueryBusy(false);
    }
  };

  useEffect(() => {
    refreshGraph();
    refreshPapers();
  }, []);

  return (
    <div className="app-shell">
      {/* Fullscreen graph background */}
      <div className="graph-wrap">
        <GraphView graph={graph} onNodeClick={explainNode} />
        
        {/* Floating node tooltip */}
        {showTooltip && selectedNode && (
          <div 
            className="graph-tooltip"
            style={{ 
              left: `${tooltipPos.x}px`, 
              top: `${tooltipPos.y}px` 
            }}
          >
            <div className="tooltip-header">
              <h3 className="tooltip-title">{selectedNode.label}</h3>
              <button className="tooltip-close" onClick={closeTooltip}>✕</button>
            </div>
            <div style={{ marginBottom: 12 }}>
              <span className="badge">{selectedNode.type}</span>
            </div>
            
            {loadingExplain && (
              <div className="tooltip-content loading-pulse">Generating explanation...</div>
            )}
            {error && (
              <div className="tooltip-content" style={{ color: '#f87171' }}>{error}</div>
            )}
            {nodeInfo && (
              <>
                <div className="tooltip-content">{nodeInfo.text}</div>
                {nodeInfo.neighbors?.length > 0 && (
                  <div className="tooltip-section">
                    <div className="tooltip-section-title">Connected Nodes ({nodeInfo.neighbors.length})</div>
                    <ul className="neighbor-list">
                      {nodeInfo.neighbors.slice(0, 12).map(n => (
                        <li 
                          key={n.id} 
                          className={`neighbor-chip ${n.type}`}
                          title={`${n.label} (${n.type}) - weight: ${n.weight.toFixed(2)}`}
                        >
                          {n.label.length > 20 ? n.label.slice(0, 20) + '…' : n.label}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Floating control panel (top-right) */}
      <div className={`control-panel ${panelCollapsed ? 'collapsed' : ''}`}>
        <button className="panel-toggle" onClick={() => setPanelCollapsed(!panelCollapsed)}>
          {panelCollapsed ? '☰' : '✕'} {!panelCollapsed && 'Controls'}
        </button>
        {!panelCollapsed && (
          <div className="panel-content">
            <h2 className="title" style={{ fontSize: 20 }}>Paper Synthesizer</h2>
            <div className="section">
              <Upload onUploaded={async () => { await refreshPapers(); await refreshGraph(); }} />
              <div className="hint">Upload multiple PDFs to build the graph.</div>
            </div>
            <hr />
            <div className="section">
              <PaperList papers={papers} />
            </div>
          </div>
        )}
      </div>

      {/* Bottom query bar */}
      <div className="query-bar">
        <div className="query-container">
          <div className="query-input-wrap">
            <textarea 
              className="query-textarea"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="Ask a question about the papers..."
              rows={2}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                  handleQuery();
                }
              }}
            />
          </div>
          <button className="query-button" onClick={handleQuery} disabled={queryBusy}>
            {queryBusy ? '⏳ Asking...' : '🚀 Ask'}
          </button>
        </div>
        
        {queryError && (
          <div style={{ maxWidth: 1200, margin: '12px auto 0', color: '#f87171', fontSize: 14 }}>
            {queryError}
          </div>
        )}
        
        {queryAnswer && (
          <div className="answer-panel" style={{ maxWidth: 1200, margin: '0 auto' }}>
            <h4 style={{ margin: '0 0 8px', color: 'var(--primary)' }}>Answer</h4>
            <div style={{ whiteSpace: 'pre-wrap', fontSize: 14, lineHeight: 1.6 }}>{queryAnswer}</div>
            {querySources.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div className="hint" style={{ marginBottom: 6 }}>Sources ({querySources.length})</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {querySources.slice(0, 8).map(s => (
                    <span key={s.chunk_id} className="badge" title={s.text.slice(0, 200)}>
                      {s.title} ({s.score.toFixed(2)})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
