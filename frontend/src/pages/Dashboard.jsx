import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

const statusBadge = {
  summarized: 'bg-green-100 text-green-800',
  transcribed: 'bg-blue-100 text-blue-800',
  transcribing: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [statsRes, recRes] = await Promise.all([
          api.get('/api/stats'),
          api.get('/api/recordings', { params: { page_size: 10 } }),
        ])
        setStats(statsRes.data)
        setRecent(recRes.data.items)
      } catch (err) {
        setError('Erro ao carregar dados')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Vendedores ativos" value={stats?.sellers_active ?? 0} />
        <StatCard label="Visitas hoje" value={stats?.recordings_today ?? 0} />
        <StatCard label="Visitas (semana)" value={stats?.recordings_week ?? 0} />
        <StatCard label="Visitas (mês)" value={stats?.recordings_month ?? 0} />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">Últimos registros</h3>
          <Link to="/recordings" className="text-sm text-blue-600 hover:underline">Ver todos</Link>
        </div>

        {recent.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            Nenhum registro ainda. Envie um áudio pelo Telegram para começar.
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vendedor</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {recent.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => window.location.href = `/recordings/${r.id}`}>
                  <td className="px-6 py-4 text-sm text-gray-700">
                    {r.created_at ? new Date(r.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{r.seller_name || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">{r.customer_name || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{r.product || '-'}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${statusBadge[r.status] || 'bg-gray-100 text-gray-800'}`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
    </div>
  )
}
