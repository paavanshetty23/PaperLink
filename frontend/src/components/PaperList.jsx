import React from 'react';

export default function PaperList({ papers }) {
  return (
    <div>
      <h3>Papers</h3>
      <ul style={{ margin: 0, paddingLeft: 16 }}>
        {papers.map(p => (
          <li key={p.paper_id} style={{ marginBottom: 8 }}>
            <strong>{p.title}</strong>
            <div className="hint" style={{ fontSize: 12 }}>{p.paper_id}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
