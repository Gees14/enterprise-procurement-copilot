import { apiFetch } from './client'
import type { PurchaseOrder, POAnalytics } from '../types'

export function getPurchaseOrders(params?: {
  supplier_id?: string
  status?: string
  limit?: number
}): Promise<PurchaseOrder[]> {
  const qs = new URLSearchParams()
  if (params?.supplier_id) qs.set('supplier_id', params.supplier_id)
  if (params?.status) qs.set('status', params.status)
  if (params?.limit) qs.set('limit', String(params.limit))
  return apiFetch<PurchaseOrder[]>(`/purchase-orders?${qs}`)
}

export function getPOAnalytics(): Promise<POAnalytics> {
  return apiFetch<POAnalytics>('/purchase-orders/analytics')
}
