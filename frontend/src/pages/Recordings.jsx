import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

const statusBadge = {
  summarized: 'bg-green-100 text-green-800',
  transcribed: 'bg-blue-100 text-blue-800',
  transcribing: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
}

export default function Recordings() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [sellers, setSellers] = useState([])
  const [filters, setFilters] = useState({
    page: 1, page_size: 20, seller_id: '', status: '', date_from: '', date_to: '',
  })
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/api/sellers').then(r => setSellers(r.data.items)).catch(() => {})
  }, [])

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const params = {}
        Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v })
        const res = await api.get('/api/recordings', { params })
        setItems(res.data.items)
        setTotal(res.data.total)
        setPages(res.data.pages)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [filters])

  const setFilter = (key, value) => {
    setFilters(f => ({ ...f, [key]: value, page: 1 }))
  }

  const handleExport = async () => {
    try {
      const params = {}
      Object.entries(filters).forEach(([k, v]) => {
        if (v && k !== 'page' && k !== 'page_size') params[k] = v
      })
      const res = await api.get('/api/recordings/export', { params, responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = 'recordings.xlsx'
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('Erro ao exportar')
    }
  }

  const formatDuration = (sec) => {
    if (!sec) return '-'
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m}:${String(s).padStart(2, '0')}`
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Registros</h2>
        <button onClick={handleExport}
          className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors">
          Exportar Excel
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex flex-wrap gap-4">
        <select value={filters.seller_id} onChange={e => setFilter('seller_id', e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">Todos vendedores</option>
          {sellers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>

        <select value={filters.status} onChange={e => setFilter('status', e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
          <option value="">Todos status</option>
          <option value="summarized">Summarized</option>
          <option value="transcribed">Transcribed</option>
          <option value="error">Error</option>
        </select>

        <input type="date" value={filters.date_from} onChange={e => setFilter('date_from', e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />

        <input type="date" value={filters.date_to} onChange={e => setFilter('date_to', e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : items.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">Nenhum registro encontrado.</div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vendedor</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Produto</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duração</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {items.map(r => (
                  <tr key={r.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => navigate(`/recordings/${r.id}`)}>
                    <td className="px-6 py-4 text-sm text-gray-700">
                      {r.created_at ? new Date(r.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{r.seller_name || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{r.customer_name || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-700">{r.product || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-700">{formatDuration(r.audio_duration_sec)}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${statusBadge[r.status] || 'bg-gray-100 text-gray-800'}`}>
                        {r.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {pages > 1 && (
              <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
                <p className="text-sm text-gray-500">{total} registros - Página {filters.page} de {pages}</p>
                <div className="flex gap-2">
                  <button disabled={filters.page <= 1}
                    onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}
                    className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50">
                    Anterior
                  </button>
                  <button disabled={filters.page >= pages}
                    onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}
                    className="px-3 py-1 text-sm border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50">
                    Próxima
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
