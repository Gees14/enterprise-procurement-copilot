import { useEffect, useState } from 'react'
import { getSuppliers } from '../api/suppliers'
import type { Supplier } from '../types'

function RiskBadge({ level }: { level: string }) {
  const cls = {
    LOW: 'bg-green-900/40 text-green-400 border-green-800',
    MEDIUM: 'bg-yellow-900/40 text-yellow-400 border-yellow-800',
    HIGH: 'bg-red-900/40 text-red-400 border-red-800',
  }[level] ?? 'bg-slate-800 text-slate-400'
  return <span className={`text-xs px-2 py-0.5 rounded border ${cls}`}>{level}</span>
}

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    getSuppliers({ limit: 100 })
      .then((data) => {
        setSuppliers(data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = suppliers.filter(
    (s) =>
      s.supplier_name.toLowerCase().includes(filter.toLowerCase()) ||
      s.country.toLowerCase().includes(filter.toLowerCase()) ||
      s.supplier_id.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Suppliers</h1>
          <p className="text-slate-500 text-sm mt-1">{suppliers.length} registered suppliers</p>
        </div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search suppliers..."
          className="bg-slate-800 border border-slate-700 text-slate-300 text-sm rounded-lg px-3 py-2 w-64 focus:outline-none focus:ring-1 focus:ring-blue-500 placeholder:text-slate-500"
        />
      </div>

      {loading ? (
        <p className="text-slate-500 text-sm">Loading suppliers...</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 border-b border-slate-800">
              <tr>
                {['ID', 'Name', 'Country', 'Category', 'Risk', 'Status', 'Missing Docs'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-xs text-slate-500 uppercase tracking-wider font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {filtered.map((s) => (
                <tr key={s.supplier_id} className="bg-slate-900/50 hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.supplier_id}</td>
                  <td className="px-4 py-3 text-slate-200 font-medium">{s.supplier_name}</td>
                  <td className="px-4 py-3 text-slate-400">{s.country}</td>
                  <td className="px-4 py-3 text-slate-400">{s.category ?? '—'}</td>
                  <td className="px-4 py-3"><RiskBadge level={s.risk_level} /></td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded border ${s.approved_status ? 'bg-green-900/40 text-green-400 border-green-800' : 'bg-red-900/40 text-red-400 border-red-800'}`}>
                      {s.approved_status ? 'Approved' : 'Pending'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs max-w-xs truncate">
                    {s.missing_documents ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
