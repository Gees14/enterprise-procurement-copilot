import { useEffect, useRef, useState } from 'react'
import { getDocuments, ingestSampleDocuments, uploadDocument } from '../api/documents'
import type { DocumentRecord } from '../types'

export default function Documents() {
  const [docs, setDocs] = useState<DocumentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [ingesting, setIngesting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const reload = () =>
    getDocuments().then((d) => {
      setDocs(d)
      setLoading(false)
    })

  useEffect(() => { reload() }, [])

  const handleIngestSample = async () => {
    setIngesting(true)
    setMessage(null)
    try {
      const res = await ingestSampleDocuments()
      setMessage(`Ingested ${res.ingested.length} documents (${res.total_chunks} chunks)`)
      reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Ingestion failed')
    } finally {
      setIngesting(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setIngesting(true)
    setMessage(null)
    try {
      const res = await uploadDocument(file)
      setMessage(`Uploaded "${res.ingested[0]}" (${res.total_chunks} chunks)`)
      reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIngesting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Documents</h1>
          <p className="text-slate-500 text-sm mt-1">Ingested policy documents available for RAG retrieval</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleIngestSample}
            disabled={ingesting}
            className="bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-200 text-sm px-4 py-2 rounded-lg transition-colors"
          >
            {ingesting ? 'Processing...' : 'Ingest Sample Docs'}
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={ingesting}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-sm px-4 py-2 rounded-lg transition-colors"
          >
            Upload Document
          </button>
          <input ref={fileRef} type="file" accept=".md,.txt,.pdf" className="hidden" onChange={handleUpload} />
        </div>
      </div>

      {message && (
        <div className="bg-blue-950/40 border border-blue-900/50 rounded-lg px-4 py-3 text-sm text-blue-300">
          {message}
        </div>
      )}

      {loading ? (
        <p className="text-slate-500 text-sm">Loading documents...</p>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 text-slate-500 space-y-3">
          <p className="text-4xl">📄</p>
          <p className="font-medium text-slate-400">No documents ingested yet</p>
          <p className="text-sm">Click "Ingest Sample Docs" to load the policy documents.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {docs.map((doc) => (
            <div key={doc.document_name} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-slate-200 break-words">{doc.document_name}</p>
                <span className="flex-shrink-0 text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {doc.document_type}
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span>{doc.chunk_count} chunks</span>
                <span>•</span>
                <span className="text-green-500">✓ {doc.status}</span>
              </div>
              <p className="text-xs text-slate-600">
                {new Date(doc.ingested_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
