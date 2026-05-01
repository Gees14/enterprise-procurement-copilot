// ─── Chat & Agent ─────────────────────────────────────────────────────────────

export interface SourceChunk {
  document_name: string
  chunk_id: string
  excerpt: string
  score: number
}

export interface ToolCall {
  name: string
  input: Record<string, unknown>
  output_summary: string
}

export interface ChatResponse {
  answer: string
  sources: SourceChunk[]
  tools_called: ToolCall[]
  grounding_status: 'grounded' | 'partially_grounded' | 'not_grounded' | 'mock'
  trace: string[]
  latency_ms: number
  model_used: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  response?: ChatResponse
}

export type UserRole = 'analyst' | 'manager' | 'admin'

// ─── Suppliers ────────────────────────────────────────────────────────────────

export interface Supplier {
  supplier_id: string
  supplier_name: string
  country: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH'
  approved_status: boolean
  missing_documents: string | null
  contact_email: string | null
  category: string | null
  created_at: string
  updated_at: string
}

export interface SupplierDetail extends Supplier {
  total_po_amount: number
  po_count: number
  open_po_count: number
}

// ─── Purchase Orders ──────────────────────────────────────────────────────────

export interface PurchaseOrder {
  po_id: string
  supplier_id: string
  item_description: string
  category: string | null
  unspsc_code: string | null
  amount: string
  currency: string
  po_date: string
  status: 'OPEN' | 'CLOSED' | 'CANCELLED'
  created_at: string
}

export interface POAnalytics {
  total_spend: number
  total_orders: number
  open_orders: number
  closed_orders: number
  cancelled_orders: number
  top_suppliers: Array<{
    supplier_id: string
    supplier_name: string
    total_spend: number
    po_count: number
  }>
  spend_by_category: Array<{ category: string; total_spend: number }>
  monthly_spend: Array<{ month: string; total_spend: number }>
}

// ─── Documents ────────────────────────────────────────────────────────────────

export interface DocumentRecord {
  document_name: string
  document_type: string
  chunk_count: number
  ingested_at: string
  status: string
}
