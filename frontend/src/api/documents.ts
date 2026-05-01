import { apiFetch } from './client'
import type { DocumentRecord } from '../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function getDocuments(): Promise<DocumentRecord[]> {
  return apiFetch<DocumentRecord[]>('/documents')
}

export async function ingestSampleDocuments(): Promise<{ ingested: string[]; total_chunks: number }> {
  return apiFetch('/documents/ingest-sample', { method: 'POST' })
}

export async function uploadDocument(file: File): Promise<{ ingested: string[]; total_chunks: number }> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${BASE_URL}/documents/upload`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail)
  }

  return response.json()
}
