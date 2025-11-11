import React, { useState } from 'react';
import axios from 'axios';

export default function Upload({ onComplete }) {
  const [busy, setBusy] = useState(false);
  const [fileCount, setFileCount] = useState(0);

  const handleFiles = async (e) => {
    const files = e.target.files;
    if (!files?.length) return;
    
    setFileCount(files.length);
    const form = new FormData();
    for (const f of files) form.append('files', f);
    
    setBusy(true);
    try {
      await axios.post('/api/upload-pdfs', form, { 
        headers: { 'Content-Type': 'multipart/form-data' } 
      });
      await axios.post('/api/build-graph');
      onComplete && onComplete();
      e.target.value = ''; // Reset file input
      setFileCount(0);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <input 
        type="file" 
        id="pdf-upload" 
        accept="application/pdf" 
        multiple 
        onChange={handleFiles} 
        disabled={busy} 
      />
      <label 
        htmlFor="pdf-upload" 
        className={`file-input-label ${busy ? 'disabled' : ''}`}
      >
        {busy ? '⏳ Uploading...' : '📁 Upload PDFs'}
      </label>
      {busy && fileCount > 0 && (
        <span className="upload-hint">
          Processing {fileCount} file{fileCount > 1 ? 's' : ''}...
        </span>
      )}
    </>
  );
}
