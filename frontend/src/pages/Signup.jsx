import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

const BLOCKED_DOMAINS = ['gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com', 'aol.com', 'icloud.com', 'live.com', 'protonmail.com']

export default function Signup() {
  const [form, setForm] = useState({
    name: '', job_title: '', email: '', company: '',
    estimated_sellers: '', password: '', confirm_password: '', terms: false,
  })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const set = (field) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm((f) => ({ ...f, [field]: val }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (form.name.trim().length < 3) return setError('Nome deve ter pelo menos 3 caracteres')
    if (!form.job_title.trim()) return setError('Cargo é obrigatório')

    const domain = form.email.split('@')[1]?.toLowerCase()
    if (BLOCKED_DOMAINS.includes(domain)) return setError('Use um email corporativo')

    if (!form.estimated_sellers || parseInt(form.estimated_sellers) < 1) return setError('Mínimo 1 vendedor')
    if (form.password.length < 8) return setError('Senha deve ter pelo menos 8 caracteres')
    if (form.password !== form.confirm_password) return setError('Senhas não coincidem')
    if (!form.terms) return setError('Aceite os termos de uso')

    setLoading(true)

    const { error: err } = await supabase.auth.signUp({
      email: form.email,
      password: form.password,
      options: {
        data: {
          name: form.name.trim(),
          job_title: form.job_title.trim(),
          company: form.company.trim(),
          estimated_sellers: parseInt(form.estimated_sellers),
        },
      },
    })

    setLoading(false)

    if (err) {
      if (err.message.includes('already registered')) {
        setError('Email já cadastrado')
      } else {
        setError(err.message)
      }
      return
    }

    setSuccess(true)
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <h1 className="text-2xl font-bold text-blue-600 mb-4">SalesEcho</h1>
          <p className="text-gray-700 mb-2">Verifique seu email para confirmar a conta.</p>
          <p className="text-sm text-gray-500 mb-4">Enviamos um link de confirmação para {form.email}</p>
          <Link to="/login" className="text-sm text-blue-600 hover:underline">Voltar ao login</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-bold text-center text-blue-600 mb-6">Criar conta</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome completo</label>
            <input type="text" value={form.name} onChange={set('name')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cargo</label>
            <input type="text" value={form.job_title} onChange={set('job_title')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email corporativo</label>
            <input type="email" value={form.email} onChange={set('email')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome da empresa</label>
            <input type="text" value={form.company} onChange={set('company')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nº estimado de vendedores</label>
            <input type="number" min="1" value={form.estimated_sellers} onChange={set('estimated_sellers')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
            <input type="password" value={form.password} onChange={set('password')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar senha</label>
            <input type="password" value={form.confirm_password} onChange={set('confirm_password')} required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none" />
          </div>

          <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-4 py-3 rounded-lg">
            Durante o período de teste (30 dias), você pode cadastrar até 5 vendedores gratuitamente.
            Ao final do período, caso não assine um plano, sua conta e todos os dados serão permanentemente excluídos.
          </div>

          <label className="flex items-start gap-2">
            <input type="checkbox" checked={form.terms} onChange={set('terms')}
              className="mt-0.5" />
            <span className="text-sm text-gray-600">Li e aceito os termos de uso</span>
          </label>

          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {loading ? 'Criando conta...' : 'Criar conta'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <Link to="/login" className="text-sm text-blue-600 hover:underline">Já tenho conta</Link>
        </div>
      </div>
    </div>
  )
}
