import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, CheckCircle2, KeyRound, Lock } from 'lucide-react'
import toast from 'react-hot-toast'

import api from '@/services/api'

const ResetPassword: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [isValidating, setIsValidating] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const token = searchParams.get('token') || ''

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setError('Link de redefinicao invalido.')
        setIsValidating(false)
        return
      }

      try {
        const { data } = await api.post('/auth/password-reset/validate', { token })
        setUserName(data.usuario?.nome || '')
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Nao foi possivel validar o link.')
      } finally {
        setIsValidating(false)
      }
    }

    validateToken()
  }, [token])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')

    if (!password || !confirmPassword) {
      setError('Preencha e confirme a nova senha.')
      return
    }

    if (password !== confirmPassword) {
      setError('As senhas nao conferem.')
      return
    }

    setIsSaving(true)
    try {
      const { data } = await api.post('/auth/password-reset/complete', {
        token,
        senha_nova: password,
      })
      toast.success(data.status || 'Senha redefinida com sucesso!')
      navigate('/login', { replace: true })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Nao foi possivel redefinir a senha.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#eff6ff_0%,#ffffff_55%,#f8fafc_100%)] px-4 py-10">
      <div className="mx-auto w-full max-w-md">
        <div className="rounded-[30px] border border-sky-100 bg-white p-8 shadow-[0_24px_70px_rgba(96,165,250,0.14)]">
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[24px] bg-sky-100 text-sky-700">
              <KeyRound size={28} />
            </div>
            <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-600">
              Recuperacao segura
            </p>
            <h1 className="mt-3 text-3xl font-display font-bold text-slate-950">
              Definir nova senha
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              O link foi gerado pelo administrador, mas a nova senha e escolhida apenas por voce.
            </p>
          </div>

          {isValidating ? (
            <div className="mt-8 space-y-3">
              <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
              <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
              <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
            </div>
          ) : error ? (
            <div className="mt-8 rounded-[24px] border border-red-100 bg-red-50 p-4 text-red-700">
              <div className="flex items-start gap-3">
                <AlertCircle size={18} className="mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold">Link indisponivel</p>
                  <p className="mt-1 text-sm">{error}</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/login')}
                className="mt-4 w-full rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-red-700 ring-1 ring-red-100 transition-colors hover:bg-red-100"
              >
                Voltar para o login
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="mt-8 space-y-4">
              <div className="rounded-[24px] border border-emerald-100 bg-emerald-50/80 p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={18} className="mt-0.5 text-emerald-600" />
                  <div>
                    <p className="text-sm font-semibold text-emerald-800">
                      Link validado com sucesso
                    </p>
                    <p className="mt-1 text-sm text-emerald-700">
                      {userName ? `Conta: ${userName}.` : 'Conta pronta para redefinicao.'} Escolha uma senha forte e pessoal.
                    </p>
                  </div>
                </div>
              </div>

              <div>
                <label className="input-label">Nova senha</label>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 focus-within:border-primary/40 focus-within:bg-white focus-within:ring-4 focus-within:ring-primary/10">
                  <Lock size={18} className="text-slate-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full bg-transparent text-sm text-slate-900 outline-none"
                    placeholder="Use letras e numeros"
                  />
                </div>
              </div>

              <div>
                <label className="input-label">Confirmar nova senha</label>
                <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 focus-within:border-primary/40 focus-within:bg-white focus-within:ring-4 focus-within:ring-primary/10">
                  <Lock size={18} className="text-slate-400" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    className="w-full bg-transparent text-sm text-slate-900 outline-none"
                    placeholder="Repita a senha"
                  />
                </div>
              </div>

              {error && (
                <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSaving}
                className="btn-primary w-full py-3 text-base font-semibold disabled:opacity-60"
              >
                {isSaving ? 'Salvando nova senha...' : 'Salvar nova senha'}
              </button>

              <p className="text-center text-xs text-slate-500">
                O administrador nao define sua senha final e nao consegue ver o que voce digitou aqui.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

export default ResetPassword
