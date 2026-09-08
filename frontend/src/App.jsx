import { useState } from 'react'
import axios from 'axios'
import { UploadCloud, Database, Activity, Loader2, FileText, CheckCircle, XCircle } from 'lucide-react'

function App() {
  const [file, setFile] = useState(null)
  const [facts, setFacts] = useState([])
  const [analysis, setAnalysis] = useState([])
  
  // Loading states for UI feedback
  const [isUploading, setIsUploading] = useState(false)
  const [isLoadingFacts, setIsLoadingFacts] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [uploadStatus, setUploadStatus] = useState("")

  const handleUpload = async () => {
    if (!file) return alert("Please select a file first!")
    setIsUploading(true)
    setUploadStatus("")
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await axios.post('http://localhost:8000/upload', formData)
      setUploadStatus(`Success! Extracted ${res.data.facts_extracted} facts.`)
    } catch (err) {
      setUploadStatus("Upload failed. Check the backend console.")
    } finally {
      setIsUploading(false)
    }
  }

  const fetchFacts = async () => {
    setIsLoadingFacts(true)
    try {
      const res = await axios.get('http://localhost:8000/facts')
      setFacts(res.data.facts)
    } finally {
      setIsLoadingFacts(false)
    }
  }

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    try {
      const res = await axios.get('http://localhost:8000/analyze')
      setAnalysis(res.data.comparisons)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Modern UI Styles
  const styles = {
    container: { maxWidth: '1000px', margin: '0 auto', padding: '2rem', fontFamily: 'system-ui, sans-serif', color: '#1f2937' },
    card: { background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)', marginBottom: '1.5rem', border: '1px solid #e5e7eb' },
    header: { display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '2px solid #f3f4f6', paddingBottom: '1rem', marginBottom: '1.5rem' },
    btn: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '0.75rem 1.5rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600', width: '200px' },
    btnDisabled: { background: '#93c5fd', cursor: 'not-allowed' },
    factItem: { padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '8px', marginBottom: '0.5rem', background: '#f9fafb' },
    tag: { padding: '0.25rem 0.75rem', borderRadius: '999px', fontSize: '0.875rem', fontWeight: '600', background: '#dbeafe', color: '#1e40af', display: 'inline-block' }
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <Database size={32} color="#2563eb" />
        <h1 style={{ margin: 0 }}>Fact Knowledge Layer</h1>
      </div>
      
      {/* Upload Section */}
      <div style={styles.card}>
        <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}><UploadCloud /> 1. Document Ingestion</h3>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input type="file" onChange={(e) => setFile(e.target.files[0])} style={{ padding: '0.5rem' }} />
          <button 
            style={{ ...styles.btn, ...(isUploading ? styles.btnDisabled : {}) }} 
            onClick={handleUpload} 
            disabled={isUploading}
          >
            {isUploading ? <><Loader2 className="lucide-spin" size={20} /> Processing...</> : "Process PDF"}
          </button>
        </div>
        {uploadStatus && <p style={{ color: uploadStatus.includes('Success') ? 'green' : 'red', fontWeight: '500', marginTop: '1rem' }}>{uploadStatus}</p>}
      </div>

      {/* Knowledge Base Section */}
      <div style={styles.card}>
        <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}><FileText /> 2. Knowledge Base</h3>
        <button 
          style={{ ...styles.btn, ...(isLoadingFacts ? styles.btnDisabled : {}) }} 
          onClick={fetchFacts} 
          disabled={isLoadingFacts}
        >
          {isLoadingFacts ? <><Loader2 className="lucide-spin" size={20} /> Loading...</> : "Load Extracted Facts"}
        </button>
        
        <div style={{ marginTop: '1.5rem', maxHeight: '400px', overflowY: 'auto' }}>
          {facts.length === 0 && !isLoadingFacts && <p style={{ color: '#6b7280' }}>No facts loaded yet.</p>}
          {facts.map((f, i) => (
            <div key={i} style={styles.factItem}>
              <div style={styles.tag}>{f.entity}</div>
              <strong style={{ marginLeft: '10px', fontSize: '1.1rem' }}>{f.metric_or_attribute}: {f.value}</strong>
              <div style={{ fontSize: '0.9rem', color: '#4b5563', marginTop: '8px' }}>
                <em>"{f.source_sentence}"</em> — ({f.source_filename}, Pg {f.page_number})
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Auditor Section */}
      <div style={styles.card}>
        <h3 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '8px' }}><Activity /> 3. Cross-Document Auditor</h3>
        <button 
          style={{ ...styles.btn, ...(isAnalyzing ? styles.btnDisabled : {}) }} 
          onClick={runAnalysis} 
          disabled={isAnalyzing}
        >
          {isAnalyzing ? <><Loader2 className="lucide-spin" size={20} /> Auditing...</> : "Run Analysis"}
        </button>

        <div style={{ marginTop: '1.5rem' }}>
          {analysis.length === 0 && !isAnalyzing && <p style={{ color: '#6b7280' }}>Run analysis to check for conflicts or corroborations.</p>}
          {analysis.map((comp, i) => {
            const isConflict = comp.relationship === 'CONTRADICTION';
            const isCorrob = comp.relationship === 'CORROBORATION';
            
            return (
              <div key={i} style={{ ...styles.factItem, borderLeft: `6px solid ${isConflict ? '#ef4444' : isCorrob ? '#10b981' : '#f59e0b'}`, background: 'white' }}>
                <h4 style={{ margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px', color: isConflict ? '#ef4444' : isCorrob ? '#10b981' : '#f59e0b' }}>
                  {isConflict ? <XCircle size={20}/> : <CheckCircle size={20}/>} 
                  {comp.relationship.replace(/_/g, ' ')}
                </h4>
                {comp.reconciliation_dimension && <p style={{ margin: '0 0 8px 0', fontSize: '0.9rem' }}><strong>Dimension:</strong> {comp.reconciliation_dimension}</p>}
                <p style={{ margin: 0, color: '#374151', lineHeight: '1.5' }}>{comp.explanation}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Add a global CSS spin animation for the loader icons */}
      <style>
        {`
          .lucide-spin { animation: spin 2s linear infinite; }
          @keyframes spin { 100% { transform: rotate(360deg); } }
        `}
      </style>
    </div>
  )
}

export default App