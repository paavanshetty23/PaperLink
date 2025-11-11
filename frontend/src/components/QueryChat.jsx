import React, { useState } from 'react';
import axios from 'axios';

export default function QueryChat({ onAfter }) {
  const [q, setQ] = useState('How do these papers compare in their methods and datasets?');
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const ask = async () => {
    setBusy(true);
    setError('');
    setAnswer('');
    setSources([]);
    try {
      const res = await axios.post('/api/query', { question: q || 'Summarize the relationships across these papers.', k: 6 });
      setAnswer(res.data.answer);
      setSources(res.data.sources || []);
      onAfter && onAfter();
    } catch (e) {
      console.error('Query error', e);
      setError(e?.response?.data?.detail || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h3>Query</h3>
      <textarea className="input" value={q} onChange={e => setQ(e.target.value)} rows={3} />
      <div style={{ marginTop: 8 }}>
        <button className="button" onClick={ask} disabled={busy}>{busy ? 'Asking…' : 'Ask'}</button>
      </div>
      {error && <div style={{ color: '#f87171', marginTop: 8 }}>{error}</div>}
      {answer && (
        <div className="node-info">
          <h4>Answer</h4>
          <div style={{ whiteSpace: 'pre-wrap' }}>{answer}</div>
          <h4 style={{ marginTop: 12 }}>Sources</h4>
          <ul>
            {sources.map(s => (
              <li key={s.chunk_id}>
                <strong>{s.title}</strong> <span className="hint">({s.paper_id})</span> score={s.score.toFixed(3)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
