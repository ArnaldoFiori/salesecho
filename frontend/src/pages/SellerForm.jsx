import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import api from '../lib/api'

export default function SellerForm() {
  const { id } = useParams()
  const isEdit = !!id
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', phone: '' })
  const [info, setInfo] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingData, setLoadingData] = useState(isEdit)

  useEffect(() => {
    if (!isEdit) return
    async function load() {
      try {
        const res = await api.get('/api/sellers')
        const seller = res.data.items.find(s => s.id === id)
        if (seller) {
          setForm({ name: seller.name, phone: seller.phone })
          setInfo(seller)
        } else {
          setError('Vendedor não encontrado')
        }
      } catch (err) {
        setError('Erro ao carregar')
      } finally {
        setLoadingData(false)
      }
    }
    load()
  }, [id, isEdit])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isEdit) {
        await api.put(`/api/sellers/${id}`, form)
      } else {
        await api.post('/api/sellers', form)
      }
      navigate('/sellers')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setLoading(false)
    }
  }

  if (loadingData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div>
      <Link to="/sellers" className="text-sm text-blue-600 hover:underline mb-4 inline-block">← Voltar</Link>

      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-lg">
        <h2 className="text-xl font-bold text-gray-900 mb-6">
          {isEdit ? 'Editar Vendedor' : 'Novo Vendedor'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome completo</label>
            <input type="text" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              required minLength={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Celular</label>
            <input type="tel" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
              required placeholder="11999998888"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          {isEdit && info && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2">
              <p className="text-xs text-gray-500">Telegram: {info.telegram_linked ? '✓ Vinculado' : '✗ Não vinculado'}</p>
              <p className="text-xs text-gray-500">Cadastro: {info.created_at ? new Date(info.created_at).toLocaleDateString('pt-BR') : '-'}</p>
            </div>
          )}

          <button type="submit" disabled={loading}
            className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {loading ? 'Salvando...' : isEdit ? 'Salvar' : 'Cadastrar'}
          </button>
        </form>
      </div>
    </div>
  )
}
