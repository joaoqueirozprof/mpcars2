import React, { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Copy,
  KeyRound,
  Loader2,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  UserCheck,
  UserCog,
  UserX,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import { cn } from '@/lib/utils'
import api from '@/services/api'
import { AccessCatalog } from '@/types'

interface UsuarioType {
  id: number
  nome: string
  email: string
  perfil: 'admin' | 'gerente' | 'operador' | 'owner'
  ativo: boolean
  permitted_pages: string[]
  data_cadastro: string | null
}

interface ResetLinkResponse {
  status: string
  recovery_url: string
  expires_at: string
  instructions: string
}

interface ActivityLogType {
  id: number
  usuario_nome: string | null
  usuario_email: string | null
  acao: string | null
  recurso: string | null
  descricao: string | null
  timestamp: string | null
}

const Usuarios: React.FC = () => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'usuarios' | 'logs'>('usuarios')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UsuarioType | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [generatedReset, setGeneratedReset] = useState<ResetLinkResponse | null>(null)
  const [resetTarget, setResetTarget] = useState<UsuarioType | null>(null)
  const [logAcao, setLogAcao] = useState('')

  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    password: '',
    perfil: 'operador' as UsuarioType['perfil'],
    permitted_pages: [] as string[],
  })

  const { data: accessCatalog } = useQuery({
    queryKey: ['usuarios-catalogo'],
    queryFn: async () => {
      const { data } = await api.get<AccessCatalog>('/usuarios/catalogo-acesso')
      return data
    },
  })

  const { data: usuarios = [], isLoading: loadingUsers } = useQuery({
    queryKey: ['usuarios'],
    queryFn: async () => {
      const { data } = await api.get<UsuarioType[]>('/usuarios/')
      return data
    },
  })

  const { data: logs = [], isLoading: loadingLogs } = useQuery({
    queryKey: ['usuarios-logs', logAcao],
    queryFn: async () => {
      const { data } = await api.get<ActivityLogType[]>('/usuarios/logs', {
        params: {
          limit: 80,
          acao: logAcao || undefined,
        },
      })
      return data
    },
    enabled: activeTab === 'logs',
  })

  const createMutation = useMutation({
    mutationFn: async (payload: typeof formData) => {
      const { data } = await api.post('/usuarios/', payload)
      return data
    },
    onSuccess: () => {
      toast.success('Usuario criado com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      closeModal()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Nao foi possivel criar o usuario.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: Partial<typeof formData> }) => {
      const { data } = await api.put(`/usuarios/${id}`, payload)
      return data
    },
    onSuccess: () => {
      toast.success('Usuario atualizado com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      closeModal()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Nao foi possivel atualizar o usuario.')
    },
  })

  const toggleMutation = useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.patch(`/usuarios/${id}/toggle`)
      return data
    },
    onSuccess: () => {
      toast.success('Status atualizado com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Nao foi possivel alterar o status.')
    },
  })

  const resetMutation = useMutation({
    mutationFn: async (user: UsuarioType) => {
      const { data } = await api.post<ResetLinkResponse>(`/usuarios/${user.id}/reset-senha`, {})
      return { target: user, data }
    },
    onSuccess: ({ target, data }) => {
      setResetTarget(target)
      setGeneratedReset(data)
      toast.success('Link de redefinicao gerado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Nao foi possivel gerar o link de redefinicao.')
    },
  })

  const selectedProfile = useMemo(
    () => accessCatalog?.profiles.find((profile) => profile.id === formData.perfil),
    [accessCatalog, formData.perfil],
  )

  const filteredUsers = useMemo(() => {
    const query = searchQuery.trim().toLowerCase()
    if (!query) return usuarios
    return usuarios.filter(
      (user) =>
        user.nome.toLowerCase().includes(query) ||
        user.email.toLowerCase().includes(query) ||
        user.perfil.toLowerCase().includes(query),
    )
  }, [searchQuery, usuarios])

  const closeModal = () => {
    setIsModalOpen(false)
    setEditingUser(null)
    setFormData({
      nome: '',
      email: '',
      password: '',
      perfil: 'operador',
      permitted_pages: [],
    })
  }

  const openCreate = () => {
    setEditingUser(null)
    setFormData({
      nome: '',
      email: '',
      password: '',
      perfil: 'operador',
      permitted_pages: accessCatalog?.profiles.find((profile) => profile.id === 'operador')?.fixed_pages || [],
    })
    setIsModalOpen(true)
  }

  const openEdit = (user: UsuarioType) => {
    setEditingUser(user)
    setFormData({
      nome: user.nome,
      email: user.email,
      password: '',
      perfil: user.perfil,
      permitted_pages: user.permitted_pages || [],
    })
    setIsModalOpen(true)
  }

  const handleProfileChange = (perfil: UsuarioType['perfil']) => {
    const profile = accessCatalog?.profiles.find((item) => item.id === perfil)
    setFormData((current) => ({
      ...current,
      perfil,
      permitted_pages: profile?.fixed_pages || [],
    }))
  }

  const togglePage = (slug: string) => {
    setFormData((current) => ({
      ...current,
      permitted_pages: current.permitted_pages.includes(slug)
        ? current.permitted_pages.filter((page) => page !== slug)
        : [...current.permitted_pages, slug],
    }))
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()

    const payload = {
      nome: formData.nome,
      email: formData.email,
      password: formData.password,
      perfil: formData.perfil,
      permitted_pages: selectedProfile?.manual_selection ? formData.permitted_pages : selectedProfile?.fixed_pages || [],
    }

    if (editingUser) {
      updateMutation.mutate({
        id: editingUser.id,
        payload: {
          nome: payload.nome,
          email: payload.email,
          perfil: payload.perfil,
          permitted_pages: payload.permitted_pages,
        },
      })
      return
    }

    if (!payload.password) {
      toast.error('Defina uma senha inicial para o usuario.')
      return
    }

    createMutation.mutate(payload)
  }

  const copyResetLink = async () => {
    if (!generatedReset?.recovery_url) return
    await navigator.clipboard.writeText(generatedReset.recovery_url)
    toast.success('Link copiado para a area de transferencia!')
  }

  const profileTone = (perfil: UsuarioType['perfil']) => {
    switch (perfil) {
      case 'admin':
        return 'bg-sky-100 text-sky-700'
      case 'gerente':
        return 'bg-emerald-100 text-emerald-700'
      case 'owner':
        return 'bg-amber-100 text-amber-700'
      default:
        return 'bg-slate-100 text-slate-700'
    }
  }

  return (
    <AppLayout>
      <div className="space-y-6 pb-8">
        <section className="overflow-hidden rounded-[30px] border border-sky-100 bg-[linear-gradient(135deg,#e0f2fe_0%,#ffffff_55%,#f8fbff_100%)] p-6 shadow-[0_20px_55px_rgba(96,165,250,0.12)]">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-700 ring-1 ring-sky-100">
                <UserCog size={13} />
                Controle de acessos
              </div>
              <h1 className="mt-4 text-3xl font-display font-bold text-slate-950">
                Usuarios e permissoes do sistema
              </h1>
              <p className="mt-3 text-sm text-slate-600">
                Perfis mais simples para evitar erro: administrador, gerente, operador e dono da empresa. O dono enxerga apenas backups. A redefinicao de senha agora acontece por link temporario, sem o admin conhecer a senha final.
              </p>
            </div>

            <div className="rounded-[24px] border border-white bg-white/90 p-5 shadow-sm">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Equipe cadastrada</p>
              <p className="mt-3 text-3xl font-display font-bold text-slate-950">{usuarios.length}</p>
              <p className="mt-2 text-sm text-slate-500">
                {usuarios.filter((user) => user.ativo).length} ativo(s) e {usuarios.filter((user) => !user.ativo).length} inativo(s)
              </p>
            </div>
          </div>
        </section>

        <div className="flex gap-2 rounded-[22px] border border-slate-200 bg-white p-1.5">
          {[
            { id: 'usuarios', label: 'Usuarios' },
            { id: 'logs', label: 'Logs de atividade' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as 'usuarios' | 'logs')}
              className={cn(
                'flex-1 rounded-[18px] px-4 py-3 text-sm font-semibold transition-colors',
                activeTab === tab.id
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-sky-50 hover:text-sky-700',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'usuarios' && (
          <section className="card">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="relative max-w-xl flex-1">
                <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Buscar por nome, email ou perfil"
                  className="input-field pl-11"
                />
              </div>
              <button onClick={openCreate} className="btn-primary inline-flex items-center gap-2">
                <Plus size={16} />
                Novo usuario
              </button>
            </div>

            <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_340px]">
              <div className="space-y-3">
                {loadingUsers ? (
                  [...Array(4)].map((_, index) => (
                    <div key={index} className="h-24 animate-pulse rounded-[24px] bg-slate-100" />
                  ))
                ) : filteredUsers.length ? (
                  filteredUsers.map((user) => (
                    <div key={user.id} className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
                      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                        <div className="min-w-0">
                          <div className="flex items-center gap-3">
                            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                              <UserCog size={18} />
                            </div>
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-slate-950">{user.nome}</p>
                              <p className="truncate text-sm text-slate-500">{user.email}</p>
                            </div>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <span className={cn('rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]', profileTone(user.perfil))}>
                              {user.perfil}
                            </span>
                            <span className={cn(
                              'rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]',
                              user.ativo ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700',
                            )}>
                              {user.ativo ? 'ativo' : 'inativo'}
                            </span>
                            <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                              {user.perfil === 'admin'
                                ? 'acesso total'
                                : user.perfil === 'owner'
                                  ? 'somente backups'
                                  : `${user.permitted_pages.length} pagina(s) liberada(s)`}
                            </span>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => openEdit(user)}
                            className="btn-secondary inline-flex items-center gap-2"
                          >
                            <Pencil size={16} />
                            Editar
                          </button>
                          <button
                            onClick={() => resetMutation.mutate(user)}
                            className="btn-secondary inline-flex items-center gap-2"
                          >
                            <KeyRound size={16} />
                            Gerar link de senha
                          </button>
                          <button
                            onClick={() => toggleMutation.mutate(user.id)}
                            className={cn(
                              'inline-flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold transition-colors',
                              user.ativo
                                ? 'bg-red-50 text-red-700 hover:bg-red-100'
                                : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
                            )}
                          >
                            {user.ativo ? <UserX size={16} /> : <UserCheck size={16} />}
                            {user.ativo ? 'Desativar' : 'Ativar'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-state py-12">
                    <div className="empty-state-icon">
                      <UserCog size={24} className="text-slate-400" />
                    </div>
                    <p className="text-sm font-medium text-slate-500">Nenhum usuario encontrado.</p>
                  </div>
                )}
              </div>

              <aside className="space-y-4">
                <div className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-5">
                  <p className="text-sm font-semibold text-slate-950">Perfis prontos para usar</p>
                  <div className="mt-4 space-y-3">
                    {accessCatalog?.profiles.map((profile) => (
                      <div key={profile.id} className="rounded-[20px] border border-white bg-white p-4 shadow-sm">
                        <p className="text-sm font-semibold text-slate-900">{profile.label}</p>
                        <p className="mt-1 text-sm text-slate-500">{profile.description}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[24px] border border-amber-100 bg-amber-50/80 p-5">
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={18} className="mt-0.5 text-amber-600" />
                    <div>
                      <p className="text-sm font-semibold text-amber-900">Recuperacao de senha segura</p>
                      <p className="mt-1 text-sm text-amber-800">
                        O administrador gera um link temporario, mas quem define a senha final e sempre o proprio usuario dono da conta.
                      </p>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </section>
        )}

        {activeTab === 'logs' && (
          <section className="card">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-xl font-display font-bold text-slate-950">Logs de atividade</h2>
                <p className="mt-1 text-sm text-slate-500">Acompanhe criacoes, edicoes e redefinicoes de acesso.</p>
              </div>
              <select
                value={logAcao}
                onChange={(event) => setLogAcao(event.target.value)}
                className="input-field max-w-[220px]"
              >
                <option value="">Todas as acoes</option>
                <option value="LOGIN">Login</option>
                <option value="CRIAR">Criar</option>
                <option value="EDITAR">Editar</option>
                <option value="EXCLUIR">Excluir</option>
              </select>
            </div>

            {loadingLogs ? (
              <div className="mt-6 space-y-3">
                {[...Array(4)].map((_, index) => (
                  <div key={index} className="h-20 animate-pulse rounded-[24px] bg-slate-100" />
                ))}
              </div>
            ) : (
              <div className="mt-6 space-y-3">
                {logs.map((log) => (
                  <div key={log.id} className="rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-slate-900">{log.descricao || 'Sem descricao'}</p>
                        <p className="mt-1 text-sm text-slate-500">
                          {log.usuario_nome || log.usuario_email || 'Usuario desconhecido'} · {log.recurso || 'recurso'}
                        </p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600 ring-1 ring-slate-200">
                        {log.acao || 'acao'}
                      </span>
                    </div>
                    <p className="mt-3 text-xs text-slate-400">{log.timestamp || '-'}</p>
                  </div>
                ))}
                {!logs.length && (
                  <div className="empty-state py-12">
                    <div className="empty-state-icon">
                      <ShieldCheck size={24} className="text-slate-400" />
                    </div>
                    <p className="text-sm font-medium text-slate-500">Nenhum log encontrado para esse filtro.</p>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>

      {isModalOpen && (
        <div className="modal-overlay" onClick={(event) => event.currentTarget === event.target && closeModal()}>
          <div className="modal-content max-w-4xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600">
                  {editingUser ? 'Editar acesso' : 'Novo acesso'}
                </p>
                <h2 className="mt-1 text-2xl font-display font-bold text-slate-950">
                  {editingUser ? 'Editar usuario' : 'Criar usuario'}
                </h2>
              </div>
              <button onClick={closeModal} className="btn-icon">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="modal-scroll-body space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="input-label">Nome</label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(event) => setFormData((current) => ({ ...current, nome: event.target.value }))}
                    className="input-field"
                    required
                  />
                </div>
                <div>
                  <label className="input-label">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(event) => setFormData((current) => ({ ...current, email: event.target.value }))}
                    className="input-field"
                    required
                  />
                </div>
              </div>

              {!editingUser && (
                <div>
                  <label className="input-label">Senha inicial</label>
                  <input
                    type="text"
                    value={formData.password}
                    onChange={(event) => setFormData((current) => ({ ...current, password: event.target.value }))}
                    className="input-field"
                    placeholder="O usuario podera trocá-la depois"
                  />
                </div>
              )}

              <div>
                <label className="input-label">Perfil de acesso</label>
                <div className="grid gap-3 md:grid-cols-2">
                  {accessCatalog?.profiles.map((profile) => (
                    <button
                      key={profile.id}
                      type="button"
                      onClick={() => handleProfileChange(profile.id)}
                      className={cn(
                        'rounded-[22px] border p-4 text-left transition-all',
                        formData.perfil === profile.id
                          ? 'border-sky-300 bg-sky-50 shadow-sm'
                          : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/50',
                      )}
                    >
                      <p className="text-sm font-semibold text-slate-900">{profile.label}</p>
                      <p className="mt-2 text-sm text-slate-500">{profile.description}</p>
                      <div className="mt-3 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                        {profile.manual_selection ? 'pode ajustar paginas' : 'acesso fixo'}
                        <ChevronRight size={14} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-[24px] border border-slate-200 bg-slate-50/70 p-5">
                <p className="text-sm font-semibold text-slate-900">Resumo do perfil</p>
                <p className="mt-2 text-sm text-slate-500">{selectedProfile?.description}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {(selectedProfile?.manual_selection ? formData.permitted_pages : selectedProfile?.fixed_pages || []).map((page) => (
                    <span key={page} className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
                      {page}
                    </span>
                  ))}
                  {!((selectedProfile?.manual_selection ? formData.permitted_pages : selectedProfile?.fixed_pages || []).length) && (
                    <span className="text-sm text-slate-500">Nenhuma pagina operacional liberada.</span>
                  )}
                </div>
              </div>

              {selectedProfile?.manual_selection && (
                <div>
                  <div className="flex items-center justify-between gap-3">
                    <label className="input-label mb-0">Paginas liberadas</label>
                    <span className="text-xs text-slate-500">
                      {formData.permitted_pages.length} selecionada(s)
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {accessCatalog?.assignable_pages.map((page) => (
                      <label
                        key={page.slug}
                        className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 transition-colors hover:border-sky-200 hover:bg-sky-50/50"
                      >
                        <input
                          type="checkbox"
                          checked={formData.permitted_pages.includes(page.slug)}
                          onChange={() => togglePage(page.slug)}
                          className="rounded border-slate-300"
                        />
                        {page.label}
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </form>

            <div className="modal-footer">
              <button type="button" onClick={closeModal} className="btn-secondary">
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={createMutation.isPending || updateMutation.isPending}
                className="btn-primary inline-flex items-center gap-2 disabled:opacity-60"
              >
                {createMutation.isPending || updateMutation.isPending ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <CheckCircle2 size={16} />
                )}
                {editingUser ? 'Salvar alteracoes' : 'Criar usuario'}
              </button>
            </div>
          </div>
        </div>
      )}

      {generatedReset && resetTarget && (
        <div
          className="modal-overlay"
          onClick={(event) => {
            if (event.currentTarget === event.target) {
              setGeneratedReset(null)
              setResetTarget(null)
            }
          }}
        >
          <div className="modal-content max-w-2xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600">Redefinicao segura</p>
                <h2 className="mt-1 text-2xl font-display font-bold text-slate-950">Link de recuperacao pronto</h2>
              </div>
              <button onClick={() => {
                setGeneratedReset(null)
                setResetTarget(null)
              }} className="btn-icon">
                <X size={18} />
              </button>
            </div>

            <div className="modal-scroll-body space-y-5">
              <div className="rounded-[24px] border border-emerald-100 bg-emerald-50 p-4">
                <p className="text-sm font-semibold text-emerald-900">
                  Conta: {resetTarget.nome}
                </p>
                <p className="mt-1 text-sm text-emerald-800">
                  O usuario vai abrir o link abaixo e escolher a propria senha. O administrador nao define nem visualiza a senha final.
                </p>
              </div>

              <div>
                <label className="input-label">Link de redefinicao</label>
                <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4">
                  <p className="break-all text-sm text-slate-700">{generatedReset.recovery_url}</p>
                </div>
                <p className="mt-2 text-xs text-slate-500">Expira em: {generatedReset.expires_at}</p>
              </div>

              <div className="rounded-[24px] border border-amber-100 bg-amber-50/80 p-4 text-sm text-amber-900">
                {generatedReset.instructions}
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" onClick={() => {
                setGeneratedReset(null)
                setResetTarget(null)
              }} className="btn-secondary">
                Fechar
              </button>
              <button type="button" onClick={copyResetLink} className="btn-primary inline-flex items-center gap-2">
                <Copy size={16} />
                Copiar link
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

export default Usuarios
