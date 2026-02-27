import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import api from '../lib/api'

export default function Account() {
  const [data, setData] = useState(null)
  const [form, setForm] = useState({ user_name: '', job_title: '', org_name: '' })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [passwordForm, setPasswordForm] = useState({ password: '', confirm: '' })
  const [passwordMsg, setPasswordMsg] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get('/api/account')
        setData(res.data)
        setForm({
          user_name: res.data.user.name || '',
          job_title: res.data.user.job_title || '',
          org_name: res.data.organization.name || '',
        })
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMsg('')
    try {
      await api.put('/api/account', form)
      setMsg('Dados atualizados')
    } catch (err) {
      setMsg('Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handlePassword = async (e) => {
    e.preventDefault()
    setPasswordMsg('')
    if (passwordForm.password.length < 8) return setPasswordMsg('Mínimo 8 caracteres')
    if (passwordForm.password !== passwordForm.confirm) return setPasswordMsg('Senhas não coincidem')

    try {
      const { error } = await supabase.auth.updateUser({ password: passwordForm.password })
      if (error) throw error
      setPasswordMsg('Senha alterada com sucesso')
      setPasswordForm({ password: '', confirm: '' })
    } catch (err) {
      setPasswordMsg(err.message || 'Erro ao alterar senha')
    }
  }

  const handleCheckout = async () => {
    try {
      const res = await api.post('/api/billing/checkout')
      window.location.href = res.data.checkout_url
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao criar checkout')
    }
  }

  const handlePortal = async () => {
    try {
      const res = await api.post('/api/billing/portal')
      window.location.href = res.data.portal_url
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao abrir portal')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const sub = data?.subscription
  const statusLabel = {
    trial: 'Período de teste',
    active: 'Ativa',
    past_due: 'Pagamento pendente',
    canceled: 'Cancelada',
    expired: 'Expirada',
  }
  const statusColor = {
    trial: 'bg-blue-100 text-blue-800',
    active: 'bg-green-100 text-green-800',
    past_due: 'bg-amber-100 text-amber-800',
    canceled: 'bg-red-100 text-red-800',
    expired: 'bg-red-100 text-red-800',
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Conta</h2>

      {/* Company data */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Dados da Empresa</h3>
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome do gestor</label>
            <input type="text" value={form.user_name}
              onChange={e => setForm(f => ({ ...f, user_name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={data?.user?.email || ''} disabled
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 text-gray-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cargo</label>
            <input type="text" value={form.job_title}
              onChange={e => setForm(f => ({ ...f, job_title: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome da empresa</label>
            <input type="text" value={form.org_name}
              onChange={e => setForm(f => ({ ...f, org_name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>
          {msg && <p className={`text-sm ${msg.includes('Erro') ? 'text-red-600' : 'text-green-600'}`}>{msg}</p>}
          <button type="submit" disabled={saving}
            className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </form>
      </div>

      {/* Subscription */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Assinatura</h3>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">Status:</span>
            <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${statusColor[sub?.status] || 'bg-gray-100'}`}>
              {statusLabel[sub?.status] || sub?.status}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">Vendedores:</span>
            <span className="text-sm text-gray-900">{sub?.seller_count} de {sub?.seller_limit}</span>
          </div>
          {sub?.status === 'trial' && sub?.trial_ends_at && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Trial expira em:</span>
              <span className="text-sm text-gray-900">{new Date(sub.trial_ends_at).toLocaleDateString('pt-BR')}</span>
            </div>
          )}
          {sub?.current_period_end && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Próxima cobrança:</span>
              <span className="text-sm text-gray-900">{new Date(sub.current_period_end).toLocaleDateString('pt-BR')}</span>
            </div>
          )}

          <div className="pt-3 flex gap-3">
            {(sub?.status === 'trial' || sub?.status === 'canceled' || sub?.status === 'expired') && (
              <button onClick={handleCheckout}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
                Assinar
              </button>
            )}
            {sub?.has_stripe && (
              <button onClick={handlePortal}
                className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
                Gerenciar assinatura
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Password */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Segurança</h3>
        <form onSubmit={handlePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nova senha</label>
            <input type="password" value={passwordForm.password}
              onChange={e => setPasswordForm(f => ({ ...f, password: e.target.value }))}
              minLength={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar nova senha</label>
            <input type="password" value={passwordForm.confirm}
              onChange={e => setPasswordForm(f => ({ ...f, confirm: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>
          {passwordMsg && <p className={`text-sm ${passwordMsg.includes('sucesso') ? 'text-green-600' : 'text-red-600'}`}>{passwordMsg}</p>}
          <button type="submit"
            className="bg-gray-800 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-900 transition-colors">
            Alterar senha
          </button>
        </form>
      </div>
    </div>
  )
}
