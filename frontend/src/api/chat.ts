import { apiFetch } from './client'
import type { ChatResponse, UserRole } from '../types'

export interface ChatRequest {
  question: string
  user_role: UserRole
  top_k?: number
  session_id?: string
}

export function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}
