import { apiFetch } from './client'
import type { Supplier, SupplierDetail } from '../types'

export function getSuppliers(params?: {
  risk_level?: string
  approved?: boolean
  limit?: number
}): Promise<Supplier[]> {
  const qs = new URLSearchParams()
  if (params?.risk_level) qs.set('risk_level', params.risk_level)
  if (params?.approved !== undefined) qs.set('approved', String(params.approved))
  if (params?.limit) qs.set('limit', String(params.limit))
  return apiFetch<Supplier[]>(`/suppliers?${qs}`)
}

export function getSupplierDetail(supplierId: string): Promise<SupplierDetail> {
  return apiFetch<SupplierDetail>(`/suppliers/${supplierId}`)
}
