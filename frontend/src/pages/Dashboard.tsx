import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPOAnalytics } from '../api/purchaseOrders'
import { getSuppliers } from '../api/suppliers'
import type { POAnalytics, Supplier } from '../types'

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-100">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

function RiskBadge({ level }: { level: string }) {
  const cls = {
    LOW: 'bg-green-900/40 text-green-400 border-green-800',
    MEDIUM: 'bg-yellow-900/40 text-yellow-400 border-yellow-800',
    HIGH: 'bg-red-900/40 text-red-400 border-red-800',
  }[level] ?? 'bg-slate-800 text-slate-400 border-slate-700'
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${cls}`}>{level}</span>
  )
}

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<POAnalytics | null>(null)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getPOAnalytics(), getSuppliers({ limit: 5 })]).then(([a, s]) => {
      setAnalytics(a)
      setSuppliers(s)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const fmt = (n: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Procurement Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Overview of spend, suppliers, and purchase orders</p>
      </div>

      {loading ? (
        <div className="text-slate-500 text-sm">Loading analytics...</div>
      ) : analytics ? (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Total Spend" value={fmt(analytics.total_spend)} />
            <StatCard label="Total Orders" value={analytics.total_orders} />
            <StatCard label="Open Orders" value={analytics.open_orders} />
            <StatCard label="Approved Suppliers" value={suppliers.filter(s => s.approved_status).length} />
          </div>

          {/* Top suppliers */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Top Suppliers by Spend</h2>
              <div className="space-y-3">
                {analytics.top_suppliers.slice(0, 5).map((s) => (
                  <div key={s.supplier_id} className="flex justify-between items-center">
                    <span className="text-sm text-slate-300">{s.supplier_name}</span>
                    <span className="text-sm font-mono text-blue-400">{fmt(s.total_spend)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Spend by Category</h2>
              <div className="space-y-3">
                {analytics.spend_by_category.slice(0, 5).map((c) => (
                  <div key={c.category} className="flex justify-between items-center">
                    <span className="text-sm text-slate-300">{c.category}</span>
                    <span className="text-sm font-mono text-emerald-400">{fmt(c.total_spend)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="text-slate-500 text-sm">
          No analytics data. Start the backend and seed the database: <code className="bg-slate-800 px-1 rounded">make seed</code>
        </div>
      )}

      {/* Quick link to Copilot */}
      <div className="bg-blue-950/40 border border-blue-900/50 rounded-xl p-6 flex items-center justify-between">
        <div>
          <h2 className="text-slate-100 font-semibold">Ask the Copilot</h2>
          <p className="text-slate-400 text-sm mt-1">
            Query procurement policies, analyze supplier risk, or classify items using natural language.
          </p>
        </div>
        <Link
          to="/copilot"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Open Copilot →
        </Link>
      </div>
    </div>
  )
}
