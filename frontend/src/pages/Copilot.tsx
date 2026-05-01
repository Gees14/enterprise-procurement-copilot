import { useEffect, useRef, useState } from 'react'
import { sendMessage } from '../api/chat'
import type { ChatMessage, ChatResponse, UserRole } from '../types'

let _id = 0
const newId = () => String(++_id)

interface CopilotProps {
  messages: ChatMessage[]
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
  userRole: UserRole
}

function GroundingBadge({ status }: { status: ChatResponse['grounding_status'] }) {
  const map = {
    grounded: 'bg-green-900/40 text-green-400 border-green-800',
    partially_grounded: 'bg-yellow-900/40 text-yellow-400 border-yellow-800',
    not_grounded: 'bg-red-900/40 text-red-400 border-red-800',
    mock: 'bg-slate-800 text-slate-400 border-slate-700',
  }
  const label = {
    grounded: '✓ Grounded',
    partially_grounded: '~ Partial',
    not_grounded: '⚠ Not grounded',
    mock: '◌ Mock',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${map[status]}`}>
      {label[status]}
    </span>
  )
}

export default function Copilot({ messages, setMessages, userRole }: CopilotProps) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topK, setTopK] = useState(5)
  const [activeTrace, setActiveTrace] = useState<string[] | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    const userMsg: ChatMessage = {
      id: newId(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setError(null)
    setLoading(true)

    try {
      const response = await sendMessage({ question, user_role: userRole, top_k: topK })
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: 'assistant',
          content: response.answer,
          timestamp: new Date(),
          response,
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 h-[calc(100vh-64px)] flex gap-6">
      {/* Chat column */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto space-y-6 pb-4 min-h-0">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full text-slate-500 text-sm text-center">
              <div className="max-w-md space-y-3">
                <p className="text-lg font-medium text-slate-300">Procurement Copilot</p>
                <p>Ask about supplier policies, classify items, analyze spend, or draft emails.</p>
                <div className="text-left space-y-1 text-xs text-slate-600 bg-slate-900 rounded-lg p-4">
                  <p>• "What documents are required for supplier approval?"</p>
                  <p>• "Which suppliers had the highest purchase order volume?"</p>
                  <p>• "Classify: hydraulic hose assembly 3/4 inch SAE"</p>
                  <p>• "Summarize supplier SUP-001 risk"</p>
                </div>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className="max-w-[80%] space-y-2">
                <div
                  className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-slate-800 text-slate-200 rounded-bl-sm border border-slate-700'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {msg.role === 'assistant' && msg.response && (
                  <div className="flex items-center gap-2 flex-wrap px-1">
                    <GroundingBadge status={msg.response.grounding_status} />
                    <span className="text-xs text-slate-500">{msg.response.latency_ms}ms</span>
                    <span className="text-xs text-slate-500">{msg.response.sources.length} sources</span>
                    {msg.response.trace.length > 0 && (
                      <button
                        onClick={() =>
                          setActiveTrace(
                            activeTrace === msg.response!.trace ? null : msg.response!.trace
                          )
                        }
                        className="text-xs text-blue-400 hover:text-blue-300"
                      >
                        {activeTrace === msg.response.trace ? 'Hide trace' : 'Show trace'}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 border border-slate-700 px-4 py-3 rounded-2xl rounded-bl-sm">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" />
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-900/30 border border-red-800 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-slate-800 pt-4 flex items-end gap-2">
          <div className="flex-shrink-0">
            <label className="text-xs text-slate-500 block mb-1">Top-k</label>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5"
            >
              {[3, 5, 8, 10].map((k) => <option key={k}>{k}</option>)}
            </select>
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            rows={2}
            className="flex-1 resize-none bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-slate-500"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="h-10 w-10 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white flex items-center justify-center"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Side panel: sources + trace */}
      {activeTrace && (
        <div className="w-80 flex-shrink-0 bg-slate-900 border border-slate-800 rounded-xl p-4 overflow-y-auto">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Agent Trace
          </h3>
          <ol className="space-y-2">
            {activeTrace.map((step, i) => (
              <li key={i} className="flex gap-2 text-xs text-slate-400">
                <span className="text-slate-600 font-mono">{i + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
