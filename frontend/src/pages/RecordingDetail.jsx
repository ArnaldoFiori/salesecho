import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../lib/api'

const statusBadge = {
  summarized: 'bg-green-100 text-green-800',
  transcribed: 'bg-blue-100 text-blue-800',
  transcribing: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
}

export default function RecordingDetail() {
  const { id } = useParams()
  const [rec, setRec] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get(`/api/recordings/${id}`)
        setRec(res.data)
      } catch (err) {
        setError(err.response?.status === 404 ? 'Registro não encontrado' : 'Erro ao carregar')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <Link to="/recordings" className="text-sm text-blue-600 hover:underline mb-4 inline-block">← Voltar</Link>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>
      </div>
    )
  }

  const formatDuration = (sec) => {
    if (!sec) return '-'
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m}:${String(s).padStart(2, '0')}`
  }

  return (
    <div>
      <Link to="/recordings" className="text-sm text-blue-600 hover:underline mb-4 inline-block">← Voltar aos registros</Link>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-xl font-bold text-gray-900">Detalhe do Registro</h2>
          <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${statusBadge[rec.status] || 'bg-gray-100 text-gray-800'}`}>
            {rec.status}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <p className="text-xs text-gray-500">Data</p>
            <p className="text-sm font-medium text-gray-900">
              {rec.created_at ? new Date(rec.created_at).toLocaleString('pt-BR') : '-'}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Vendedor</p>
            <p className="text-sm font-medium text-gray-900">{rec.seller_name || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Cliente</p>
            <p className="text-sm font-medium text-gray-900">{rec.customer_name || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Produto</p>
            <p className="text-sm font-medium text-gray-900">{rec.product || '-'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Duração</p>
            <p className="text-sm font-medium text-gray-900">{formatDuration(rec.audio_duration_sec)}</p>
          </div>
        </div>
      </div>

      {/* Error */}
      {rec.status === 'error' && rec.error_message && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <p className="font-medium text-sm">Erro no processamento</p>
          <p className="text-sm mt-1">{rec.error_message}</p>
        </div>
      )}

      {/* Transcription */}
      {rec.transcript_text && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Transcrição</h3>
          <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{rec.transcript_text}</p>
          </div>
        </div>
      )}

      {/* Summary */}
      {rec.summary_text && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Resumo IA</h3>
          <div className="bg-blue-50 rounded-lg p-4 max-h-64 overflow-y-auto">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{rec.summary_text}</p>
          </div>
        </div>
      )}
    </div>
  )
}
