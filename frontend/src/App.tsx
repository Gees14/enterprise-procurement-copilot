import { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import type { ChatMessage, UserRole } from './types'
import Dashboard from './pages/Dashboard'
import Copilot from './pages/Copilot'
import Suppliers from './pages/Suppliers'
import Documents from './pages/Documents'

const NAV_LINKS = [
  { to: '/', label: 'Dashboard', exact: true },
  { to: '/copilot', label: 'Copilot' },
  { to: '/suppliers', label: 'Suppliers' },
  { to: '/documents', label: 'Documents' },
]

function NavItem({ to, label, exact }: { to: string; label: string; exact?: boolean }) {
  return (
    <NavLink
      to={to}
      end={exact}
      className={({ isActive }) =>
        `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-blue-600 text-white'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

export default function App() {
  // Lift chat state so conversation persists across navigation
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [userRole, setUserRole] = useState<UserRole>('analyst')

  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        {/* Header */}
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
                PC
              </div>
              <span className="font-semibold text-slate-100">Procurement Copilot</span>
              <span className="text-slate-600 text-xs">Enterprise Edition</span>
            </div>

            <nav className="flex items-center gap-1">
              {NAV_LINKS.map((l) => (
                <NavItem key={l.to} {...l} />
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-500">Role:</label>
              <select
                value={userRole}
                onChange={(e) => setUserRole(e.target.value as UserRole)}
                className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="analyst">Analyst</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route
              path="/copilot"
              element={
                <Copilot
                  messages={chatMessages}
                  setMessages={setChatMessages}
                  userRole={userRole}
                />
              }
            />
            <Route path="/suppliers" element={<Suppliers />} />
            <Route path="/documents" element={<Documents />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
