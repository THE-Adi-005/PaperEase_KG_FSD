import { useState, useRef } from 'react';
import { Upload, FileText, Loader } from 'lucide-react';
import { uploadPaper } from '../utils/api';

export default function PaperUploader({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  const handleFile = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) return;
    setUploading(true);
    try {
      const result = await uploadPaper(file);
      onUpload?.(result);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  return (
    <div
      className={`upload-zone ${dragging ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      {uploading ? (
        <>
          <Loader size={24} className="upload-icon loading-spinner" />
          <p>Uploading...</p>
        </>
      ) : (
        <>
          <Upload size={24} className="upload-icon" />
          <p>Drop PDF here or click to upload</p>
          <span className="upload-hint">Supports research paper PDFs</span>
        </>
      )}
    </div>
  );
}
