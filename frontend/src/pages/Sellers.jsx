import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

export default function Sellers() {
  const [items, setItems] = useState([])
  const [sellerCount, setSellerCount] = useState(0)
  const [sellerLimit, setSellerLimit] = useState(5)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/sellers')
      setItems(res.data.items)
      setSellerCount(res.data.seller_count)
      setSellerLimit(res.data.seller_limit)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (seller) => {
    try {
      await api.put(`/api/sellers/${seller.id}`, { is_active: !seller.is_active })
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao atualizar')
    }
  }

  const unlinkTelegram = async (seller) => {
    if (!confirm(`Desvincular Telegram de ${seller.name}?`)) return
    try {
      await api.delete(`/api/sellers/${seller.id}/telegram`)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    }
  }

  const atLimit = sellerCount >= sellerLimit

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Vendedores</h2>
          <p className="text-sm text-gray-500 mt-1">{sellerCount} de {sellerLimit} vendedores</p>
        </div>
        {atLimit ? (
          <span className="text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
            Limite atingido. Faça upgrade do plano.
          </span>
        ) : (
          <Link to="/sellers/new"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
            Adicionar Vendedor
          </Link>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : items.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">Nenhum vendedor cadastrado.</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nome</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Telefone</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Telegram</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Visitas (mês)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{s.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-700">{s.phone}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${s.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                      {s.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {s.telegram_linked ? (
                      <span className="text-green-600">✓ Vinculado</span>
                    ) : (
                      <span className="text-gray-400">✗ Não vinculado</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700">{s.recordings_month}</td>
                  <td className="px-6 py-4 text-sm flex gap-2">
                    <Link to={`/sellers/${s.id}`} className="text-blue-600 hover:underline">Editar</Link>
                    <button onClick={() => toggleActive(s)} className="text-amber-600 hover:underline">
                      {s.is_active ? 'Desativar' : 'Ativar'}
                    </button>
                    {s.telegram_linked && (
                      <button onClick={() => unlinkTelegram(s)} className="text-red-600 hover:underline">
                        Desvincular
                      </button>
                    )}
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
