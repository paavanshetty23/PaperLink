import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Upload from './Upload';
import GraphView from './GraphView';
import axios from 'axios';

export default function App() {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [papers, setPapers] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeInfo, setNodeInfo] = useState(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [showTooltip, setShowTooltip] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
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
    setNodeInfo(null);
    
    const rect = event?.target?.getBoundingClientRect();
    if (rect) {
      const x = Math.min(rect.left + 20, window.innerWidth - 400);
      const y = Math.min(rect.top - 40, window.innerHeight - 400);
      setTooltipPos({ x: Math.max(20, x), y: Math.max(20, y) });
    }
    setShowTooltip(true);

    try {
      const res = await axios.get('/api/explain-node', { params: { node_id: node.id } });
      setNodeInfo(res.data);
    } catch (e) {
      console.error('Failed to explain node:', e);
    } finally {
      setLoadingExplain(false);
    }
  };

  const closeTooltip = () => {
    setShowTooltip(false);
    setTimeout(() => {
      setSelectedNode(null);
      setNodeInfo(null);
    }, 200);
  };

  const handleQuery = async () => {
    if (!queryText.trim()) return;
    setQueryBusy(true);
    setQueryError('');
    setQueryAnswer('');
    setQuerySources([]);
    try {
      const res = await axios.post('/api/query', { question: queryText, k: 6 });
      setQueryAnswer(res.data.answer);
      setQuerySources(res.data.sources || []);
      await refreshGraph();
    } catch (e) {
      setQueryError(e?.response?.data?.detail || String(e));
    } finally {
      setQueryBusy(false);
    }
  };

  const handleUploadComplete = async () => {
    await refreshGraph();
    await refreshPapers();
  };

  const handleClearGraph = async () => {
    if (window.confirm('⚠️ Clear all papers and graph data? This cannot be undone.')) {
      try {
        // Call backend to clear storage
        await axios.post('/api/clear-all');
        
        // Clear local state
        setGraph({ nodes: [], edges: [] });
        setPapers([]);
        setQueryAnswer('');
        setQuerySources([]);
        setSelectedNode(null);
        setNodeInfo(null);
        setShowTooltip(false);
        setQueryError('');
        setQueryText('');
      } catch (e) {
        console.error('Failed to clear:', e);
        setQueryError('Failed to clear data: ' + (e?.response?.data?.detail || String(e)));
      }
    }
  };

  useEffect(() => {
    // Only load if there's existing data - don't preload empty graph
    const loadExistingData = async () => {
      try {
        const papersRes = await axios.get('/api/papers');
        if (papersRes.data.papers && papersRes.data.papers.length > 0) {
          setPapers(papersRes.data.papers);
          await refreshGraph();
        }
      } catch (e) {
        console.error('Failed to load data:', e);
      }
    };
    loadExistingData();
  }, []);

  return (
    <div className="app-shell">
      {/* Top Bar */}
      <div className="top-bar">
        <div className="top-bar-left">
          <h1 className="top-bar-title">� PaperLink</h1>
          <div className="top-bar-upload">
            <Upload onComplete={handleUploadComplete} />
          </div>
        </div>
        <div className="top-bar-right">
          {papers.length > 0 && (
            <button className="clear-btn" onClick={handleClearGraph} title="Clear all data">
              🗑️ Clear
            </button>
          )}
          <div className="papers-badge" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <span>Papers</span>
            <span className="papers-count">{papers.length}</span>
          </div>
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? '✕' : '☰'}
          </button>
        </div>
      </div>

      {/* Main Content - Large Graph Area */}
      <div className="main-content" onClick={(e) => {
        // Close tooltip when clicking on graph background (not on nodes)
        if (e.target.classList.contains('main-content') || e.target.classList.contains('graph-wrap')) {
          closeTooltip();
        }
      }}>
        <div className={`graph-wrap ${sidebarOpen ? 'sidebar-open' : ''}`}>
          <GraphView graph={graph} onNodeClick={explainNode} selectedNodeId={selectedNode?.id} />
        </div>

        {/* Floating Tooltip */}
        {showTooltip && selectedNode && (
          <div 
            className="graph-tooltip"
            style={{ 
              left: `${tooltipPos.x}px`, 
              top: `${tooltipPos.y}px`,
              position: 'fixed',
              zIndex: 1000
            }}
          >
            <button 
              className="tooltip-close-btn"
              onClick={closeTooltip}
              title="Close"
            >
              ✕
            </button>
            <div className="tooltip-title">{selectedNode.label}</div>
            <div className="tooltip-type">{selectedNode.type}</div>
            {loadingExplain && <div className="hint">⏳ Loading explanation...</div>}
            {!loadingExplain && nodeInfo && (
              <>
                <div className="tooltip-text">{nodeInfo.explanation}</div>
                {nodeInfo.neighbors && nodeInfo.neighbors.length > 0 && (
                  <div className="tooltip-neighbors">
                    <div className="tooltip-neighbors-title">Connected ({nodeInfo.neighbors.length})</div>
                    <div className="neighbor-chips">
                      {nodeInfo.neighbors.slice(0, 6).map((n) => (
                        <span key={n.id} className="neighbor-chip" title={`Weight: ${n.weight}`}>
                          {n.label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Right Sidebar - Paper List */}
        <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-header">
            <h2 className="sidebar-title">Research Papers</h2>
            <button className="sidebar-close" onClick={() => setSidebarOpen(false)}>✕</button>
          </div>
          <div className="sidebar-content">
            {papers.length === 0 && (
              <div className="hint">No papers uploaded yet. Upload PDFs to begin.</div>
            )}
            {papers.map((p) => (
              <div key={p.paper_id} className="paper-item">
                <div className="paper-title">{p.title}</div>
                <div className="paper-id">{p.paper_id}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Chat Bar */}
      <div className="chat-bar">
        <div className="chat-container">
          {queryError && (
            <div className="chat-error">{queryError}</div>
          )}

          {queryAnswer && (
            <div className="chat-answer">
              <div className="chat-answer-title">📊 Analysis Result</div>
              <div className="chat-answer-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {queryAnswer}
                </ReactMarkdown>
              </div>
              {querySources.length > 0 && (
                <div className="chat-sources">
                  <div className="chat-sources-label">Sources ({querySources.length})</div>
                  <div className="source-chips">
                    {querySources.slice(0, 8).map((s) => (
                      <span key={s.chunk_id} className="source-chip" title={s.text.slice(0, 200)}>
                        {s.title} ({s.score.toFixed(2)})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="chat-input-area">
            <textarea
              className="chat-textarea"
              placeholder="Ask a question about the papers..."
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleQuery();
                }
              }}
              disabled={queryBusy}
            />
            <button 
              className="chat-send-btn" 
              onClick={handleQuery}
              disabled={queryBusy || !queryText.trim()}
            >
              {queryBusy ? '⏳ Asking...' : '🚀 Ask'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
