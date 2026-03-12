import React, { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/services/api'
import toast from 'react-hot-toast'
import { Settings, Building2, User, Sliders, ShieldCheck, Database, TriangleAlert } from 'lucide-react'
import { OpsReadiness } from '@/types'

const Configuracoes: React.FC = () => {
  const { user, setUser } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'empresa' | 'usuario' | 'sistema' | 'operacao'>('empresa')
  const [isSaving, setIsSaving] = useState(false)

  const { data: configs } = useQuery({
    queryKey: ['configuracoes'],
    queryFn: async () => {
      const { data } = await api.get('/configuracoes/')
      return data
    },
  })

  const { data: opsReadiness, isLoading: isLoadingOps } = useQuery({
    queryKey: ['ops-readiness'],
    queryFn: async () => {
      const { data } = await api.get<OpsReadiness>('/ops/readiness')
      return data
    },
    enabled: user?.perfil === 'admin',
    retry: false,
  })

  const [empresaForm, setEmpresaForm] = useState({
    nome: 'MPCARS Brasil',
    cnpj: '00.000.000/0000-00',
    telefone: '(11) 9999-9999',
    email: 'contato@mpcars.com.br',
    endereco: 'Rua Principal, 123',
    cidade: 'São Paulo',
    estado: 'SP',
    cep: '01234-567',
  })

  const [userForm, setUserForm] = useState({
    nome: user?.nome || '',
    email: user?.email || '',
    role: user?.role || 'Administrador',
    senhaAtual: '',
    senhaNova: '',
    confirmarSenha: '',
  })

  const [systemForm, setSystemForm] = useState({
    idioma: 'pt-BR',
    tema: 'light',
    notificacoes_email: true,
    notificacoes_sms: false,
    valor_diaria_padrao: 150,
    taxa_juros: 2,
  })

  useEffect(() => {
    if (configs && Array.isArray(configs)) {
      const configMap: Record<string, string> = {}
      configs.forEach((c: any) => { configMap[c.chave] = c.valor })
      setEmpresaForm({
        nome: configMap['empresa_nome'] || 'MPCARS Brasil',
        cnpj: configMap['empresa_cnpj'] || '',
        telefone: configMap['empresa_telefone'] || '',
        email: configMap['empresa_email'] || '',
        endereco: configMap['empresa_endereco'] || '',
        cidade: configMap['empresa_cidade'] || '',
        estado: configMap['empresa_estado'] || '',
        cep: configMap['empresa_cep'] || '',
      })
      setSystemForm({
        idioma: configMap['sistema_idioma'] || 'pt-BR',
        tema: configMap['sistema_tema'] || 'light',
        notificacoes_email: configMap['sistema_notificacoes_email'] === 'true',
        notificacoes_sms: configMap['sistema_notificacoes_sms'] === 'true',
        valor_diaria_padrao: parseFloat(configMap['sistema_valor_diaria_padrao'] || '150'),
        taxa_juros: parseFloat(configMap['sistema_taxa_juros'] || '2'),
      })
    }
  }, [configs])

  const handleSaveEmpresa = async () => {
    setIsSaving(true)
    try {
      const items = Object.entries(empresaForm).map(([key, valor]) => ({
        chave: `empresa_${key}`,
        valor: String(valor),
      }))
      await api.put('/configuracoes/batch/update', { items })
      queryClient.invalidateQueries({ queryKey: ['configuracoes'] })
      toast.success('Configurações da empresa salvas com sucesso!')
    } catch (error) {
      toast.error('Erro ao salvar configurações')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveUser = async () => {
    if (userForm.senhaNova && userForm.senhaNova !== userForm.confirmarSenha) {
      toast.error('As senhas não conferem')
      return
    }

    setIsSaving(true)
    try {
      // Update profile (nome/email) if changed
      if (userForm.nome || userForm.email) {
        await api.put('/auth/profile', {
          nome: userForm.nome || undefined,
          email: userForm.email || undefined,
        })

        const { data: currentUser } = await api.get('/auth/me')
        localStorage.setItem('user', JSON.stringify(currentUser))
        setUser(currentUser)
      }

      // Change password if provided
      if (userForm.senhaNova && userForm.senhaAtual) {
        await api.put('/auth/change-password', {
          senha_atual: userForm.senhaAtual,
          senha_nova: userForm.senhaNova,
        })
        toast.success('Senha alterada com sucesso!')
      }

      toast.success('Dados do usuário atualizados com sucesso!')
      setUserForm({ ...userForm, senhaAtual: '', senhaNova: '', confirmarSenha: '' })
    } catch (error: any) {
      const msg = error?.response?.data?.detail || 'Erro ao atualizar dados do usuário'
      toast.error(msg)
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveSystem = async () => {
    setIsSaving(true)
    try {
      const items = [
        { chave: 'sistema_idioma', valor: systemForm.idioma },
        { chave: 'sistema_tema', valor: systemForm.tema },
        { chave: 'sistema_notificacoes_email', valor: String(systemForm.notificacoes_email) },
        { chave: 'sistema_notificacoes_sms', valor: String(systemForm.notificacoes_sms) },
        { chave: 'sistema_valor_diaria_padrao', valor: String(systemForm.valor_diaria_padrao) },
        { chave: 'sistema_taxa_juros', valor: String(systemForm.taxa_juros) },
      ]
      await api.put('/configuracoes/batch/update', { items })
      queryClient.invalidateQueries({ queryKey: ['configuracoes'] })
      toast.success('Configurações do sistema salvas com sucesso!')
    } catch (error) {
      toast.error('Erro ao salvar configurações')
    } finally {
      setIsSaving(false)
    }
  }

  const tabs = [
    { id: 'empresa', label: 'Empresa', icon: Building2 },
    { id: 'usuario', label: 'Usuário', icon: User },
    { id: 'sistema', label: 'Sistema', icon: Sliders },
    { id: 'operacao', label: 'Operacao', icon: ShieldCheck, adminOnly: true },
  ].filter((tab) => !tab.adminOnly || user?.perfil === 'admin')

  return (
    <AppLayout>
      <div className="space-y-6">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <Settings className="text-slate-700" size={32} />
            Configurações
          </h1>
          <p className="page-subtitle">Gerencie as configurações da empresa, seu perfil e do sistema</p>
        </div>

        <div className="flex gap-2 border-b border-slate-200 overflow-x-auto">
          {tabs.map((tab) => {
            const IconComponent = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-6 py-3 font-medium transition-colors border-b-2 flex items-center gap-2 whitespace-nowrap ${
                  isActive ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                <IconComponent size={18} />
                {tab.label}
              </button>
            )
          })}
        </div>

        {activeTab === 'empresa' && (
          <div className="card max-w-3xl">
            <h2 className="text-xl font-display font-bold text-slate-900 mb-6">Dados da Empresa</h2>

            <form className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Nome da Empresa</label>
                  <input
                    type="text"
                    value={empresaForm.nome}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, nome: e.target.value })}
                    className="input-field"
                    placeholder="MPCARS Brasil"
                  />
                </div>

                <div>
                  <label className="input-label">CNPJ</label>
                  <input
                    type="text"
                    value={empresaForm.cnpj}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, cnpj: e.target.value })}
                    className="input-field"
                    placeholder="00.000.000/0000-00"
                  />
                </div>

                <div>
                  <label className="input-label">Email Comercial</label>
                  <input
                    type="email"
                    value={empresaForm.email}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, email: e.target.value })}
                    className="input-field"
                    placeholder="contato@empresa.com"
                  />
                </div>

                <div>
                  <label className="input-label">Telefone</label>
                  <input
                    type="tel"
                    value={empresaForm.telefone}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, telefone: e.target.value })}
                    className="input-field"
                    placeholder="(11) 9999-9999"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="input-label">Endereço</label>
                  <input
                    type="text"
                    value={empresaForm.endereco}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, endereco: e.target.value })}
                    className="input-field"
                    placeholder="Rua, número, complemento"
                  />
                </div>

                <div>
                  <label className="input-label">Cidade</label>
                  <input
                    type="text"
                    value={empresaForm.cidade}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, cidade: e.target.value })}
                    className="input-field"
                    placeholder="São Paulo"
                  />
                </div>

                <div>
                  <label className="input-label">Estado</label>
                  <input
                    type="text"
                    value={empresaForm.estado}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, estado: e.target.value.toUpperCase() })}
                    maxLength={2}
                    className="input-field"
                    placeholder="SP"
                  />
                </div>

                <div>
                  <label className="input-label">CEP</label>
                  <input
                    type="text"
                    value={empresaForm.cep}
                    onChange={(e) => setEmpresaForm({ ...empresaForm, cep: e.target.value })}
                    className="input-field"
                    placeholder="01234-567"
                  />
                </div>
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={handleSaveEmpresa}
                  className="btn-primary"
                  disabled={isSaving}
                >
                  {isSaving ? 'Salvando...' : 'Salvar Configurações'}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'usuario' && (
          <div className="card max-w-3xl">
            <h2 className="text-xl font-display font-bold text-slate-900 mb-6">Dados do Usuário</h2>

            <form className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Nome Completo</label>
                  <input
                    type="text"
                    value={userForm.nome}
                    onChange={(e) => setUserForm({ ...userForm, nome: e.target.value })}
                    className="input-field"
                    placeholder="Seu nome"
                  />
                </div>

                <div>
                  <label className="input-label">Email</label>
                  <input
                    type="email"
                    value={userForm.email}
                    onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                    className="input-field"
                    placeholder="seu.email@empresa.com"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="input-label">Função</label>
                  <input
                    type="text"
                    value={userForm.role}
                    disabled
                    className="input-field disabled:opacity-60 disabled:cursor-not-allowed bg-slate-50"
                  />
                  <p className="text-xs text-slate-500 mt-1">A função não pode ser alterada. Contacte um administrador para mudanças de permissões.</p>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Alterar Senha</h3>
                <div className="space-y-4">
                  <div>
                    <label className="input-label">Senha Atual</label>
                    <input
                      type="password"
                      value={userForm.senhaAtual}
                      onChange={(e) => setUserForm({ ...userForm, senhaAtual: e.target.value })}
                      className="input-field"
                      placeholder="Digite sua senha atual"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="input-label">Nova Senha</label>
                      <input
                        type="password"
                        value={userForm.senhaNova}
                        onChange={(e) => setUserForm({ ...userForm, senhaNova: e.target.value })}
                        className="input-field"
                        placeholder="Digite a nova senha"
                      />
                    </div>

                    <div>
                      <label className="input-label">Confirmar Senha</label>
                      <input
                        type="password"
                        value={userForm.confirmarSenha}
                        onChange={(e) => setUserForm({ ...userForm, confirmarSenha: e.target.value })}
                        className="input-field"
                        placeholder="Confirme a nova senha"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={handleSaveUser}
                  className="btn-primary"
                  disabled={isSaving}
                >
                  {isSaving ? 'Salvando...' : 'Atualizar Dados'}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'sistema' && (
          <div className="card max-w-3xl">
            <h2 className="text-xl font-display font-bold text-slate-900 mb-6">Configurações do Sistema</h2>

            <form className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Idioma</label>
                  <select
                    value={systemForm.idioma}
                    onChange={(e) => setSystemForm({ ...systemForm, idioma: e.target.value })}
                    className="input-field"
                  >
                    <option value="pt-BR">Português (Brasil)</option>
                    <option value="en-US">English (USA)</option>
                    <option value="es-ES">Español (España)</option>
                  </select>
                </div>

                <div>
                  <label className="input-label">Tema da Interface</label>
                  <select
                    value={systemForm.tema}
                    onChange={(e) => setSystemForm({ ...systemForm, tema: e.target.value })}
                    className="input-field"
                  >
                    <option value="light">Claro</option>
                    <option value="dark">Escuro</option>
                    <option value="auto">Automático (Sistema)</option>
                  </select>
                </div>

                <div>
                  <label className="input-label">Valor Diária Padrão (R$)</label>
                  <input
                    type="number"
                    value={systemForm.valor_diaria_padrao}
                    onChange={(e) => setSystemForm({ ...systemForm, valor_diaria_padrao: parseFloat(e.target.value) })}
                    min="0"
                    step="0.01"
                    className="input-field"
                    placeholder="150,00"
                  />
                </div>

                <div>
                  <label className="input-label">Taxa de Juros Padrão (%)</label>
                  <input
                    type="number"
                    value={systemForm.taxa_juros}
                    onChange={(e) => setSystemForm({ ...systemForm, taxa_juros: parseFloat(e.target.value) })}
                    step="0.01"
                    min="0"
                    className="input-field"
                    placeholder="2,00"
                  />
                </div>
              </div>

              <div className="border-t border-slate-200 pt-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Notificações</h3>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer p-3 rounded hover:bg-slate-50 transition-colors">
                    <input
                      type="checkbox"
                      checked={systemForm.notificacoes_email}
                      onChange={(e) => setSystemForm({ ...systemForm, notificacoes_email: e.target.checked })}
                      className="w-4 h-4 rounded border-slate-300"
                    />
                    <div>
                      <span className="font-medium text-slate-900 block">Notificações por Email</span>
                      <span className="text-sm text-slate-500">Receba alertas importantes por e-mail</span>
                    </div>
                  </label>

                  <label className="flex items-center gap-3 cursor-pointer p-3 rounded hover:bg-slate-50 transition-colors">
                    <input
                      type="checkbox"
                      checked={systemForm.notificacoes_sms}
                      onChange={(e) => setSystemForm({ ...systemForm, notificacoes_sms: e.target.checked })}
                      className="w-4 h-4 rounded border-slate-300"
                    />
                    <div>
                      <span className="font-medium text-slate-900 block">Notificações por SMS</span>
                      <span className="text-sm text-slate-500">Receba alertas críticos por mensagem de texto</span>
                    </div>
                  </label>
                </div>
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={handleSaveSystem}
                  className="btn-primary"
                  disabled={isSaving}
                >
                  {isSaving ? 'Salvando...' : 'Salvar Configurações'}
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'operacao' && (
          <div className="space-y-6">
            {user?.perfil !== 'admin' ? (
              <div className="card max-w-3xl">
                <h2 className="text-xl font-display font-bold text-slate-900">Operacao e Producao</h2>
                <p className="mt-2 text-sm text-slate-500">
                  Esta area e reservada para administradores porque mostra checklist de producao, seguranca e backup.
                </p>
              </div>
            ) : (
              <>
                <div className="rounded-[28px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(191,219,254,0.75),transparent_28%),linear-gradient(135deg,#eff6ff_0%,#ffffff_65%,#f8fafc_100%)] p-6 shadow-sm">
                  <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                    <div className="max-w-3xl">
                      <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-blue-700 ring-1 ring-blue-100">
                        <ShieldCheck size={13} />
                        Checklist de producao
                      </div>
                      <h2 className="mt-4 text-3xl font-display font-bold text-slate-950">
                        Seguranca, backup e prontidao operacional
                      </h2>
                      <p className="mt-3 text-sm text-slate-600">
                        Antes de operar com cadastros reais, confirme segredos, dominios, backup e politicas de startup.
                      </p>
                    </div>

                    <div className={`rounded-[24px] border px-5 py-4 shadow-sm ${
                      opsReadiness?.ready_for_production
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                        : 'border-amber-200 bg-amber-50 text-amber-800'
                    }`}>
                      <p className="text-xs font-semibold uppercase tracking-[0.2em]">
                        Status geral
                      </p>
                      <p className="mt-3 text-2xl font-display font-bold">
                        {opsReadiness?.ready_for_production ? 'Pronto para producao' : 'Pede ajustes'}
                      </p>
                      <p className="mt-2 text-sm">
                        {isLoadingOps
                          ? 'Conferindo ambiente...'
                          : `${opsReadiness?.summary.critical || 0} critico(s) e ${opsReadiness?.summary.warning || 0} alerta(s) detectados.`}
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                    <div className="rounded-[24px] border border-white/80 bg-white/90 p-4 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Checks ok</p>
                      <p className="mt-3 text-3xl font-display font-bold text-slate-950">{opsReadiness?.summary.ok || 0}</p>
                    </div>
                    <div className="rounded-[24px] border border-white/80 bg-white/90 p-4 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Alertas</p>
                      <p className="mt-3 text-3xl font-display font-bold text-amber-600">{opsReadiness?.summary.warning || 0}</p>
                    </div>
                    <div className="rounded-[24px] border border-white/80 bg-white/90 p-4 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Criticos</p>
                      <p className="mt-3 text-3xl font-display font-bold text-red-600">{opsReadiness?.summary.critical || 0}</p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)]">
                  <div className="card">
                    <div className="flex items-center gap-3">
                      <ShieldCheck className="text-blue-600" size={22} />
                      <div>
                        <h3 className="text-lg font-display font-bold text-slate-900">Checklist do ambiente</h3>
                        <p className="text-sm text-slate-500">Cada item abaixo mostra o que precisa ser conferido antes de ir para producao.</p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3">
                      {(opsReadiness?.checks || []).map((check) => (
                        <div
                          key={check.id}
                          className={`rounded-[22px] border p-4 ${
                            check.status === 'ok'
                              ? 'border-emerald-200 bg-emerald-50/70'
                              : check.status === 'critical'
                                ? 'border-red-200 bg-red-50/70'
                                : 'border-amber-200 bg-amber-50/70'
                          }`}
                        >
                          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                            <div className="min-w-0">
                              <p className="text-sm font-semibold text-slate-900">{check.title}</p>
                              <p className="mt-1 text-sm text-slate-600">{check.details}</p>
                              <p className="mt-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                                Acao recomendada
                              </p>
                              <p className="mt-1 text-sm text-slate-700">{check.action}</p>
                            </div>
                            <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${
                              check.status === 'ok'
                                ? 'bg-emerald-100 text-emerald-700'
                                : check.status === 'critical'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-amber-100 text-amber-700'
                            }`}>
                              {check.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div className="card">
                      <div className="flex items-center gap-3">
                        <Database className="text-emerald-600" size={22} />
                        <div>
                          <h3 className="text-lg font-display font-bold text-slate-900">Rotina de backup</h3>
                          <p className="text-sm text-slate-500">O sistema agora tem scripts de backup e restore para a operacao real.</p>
                        </div>
                      </div>

                      <div className="mt-4 space-y-3">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Diretorio</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">{opsReadiness?.backup.directory || '/backups'}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Retencao</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">{opsReadiness?.backup.retention_days || 14} dias</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Scripts</p>
                          <p className="mt-2 text-sm text-slate-700">{opsReadiness?.backup.scripts.backup || 'ops/backup_mpcars2.sh'}</p>
                          <p className="mt-1 text-sm text-slate-700">{opsReadiness?.backup.scripts.restore || 'ops/restore_mpcars2.sh'}</p>
                        </div>
                      </div>
                    </div>

                    <div className="card">
                      <div className="flex items-center gap-3">
                        <TriangleAlert className="text-amber-600" size={22} />
                        <div>
                          <h3 className="text-lg font-display font-bold text-slate-900">Proximos passos</h3>
                          <p className="text-sm text-slate-500">Resumo prático do que falta antes do go-live.</p>
                        </div>
                      </div>

                      <div className="mt-4 space-y-3">
                        {(opsReadiness?.next_steps || []).length === 0 ? (
                          <p className="text-sm text-slate-500">Nenhum ajuste pendente detectado no momento.</p>
                        ) : (
                          (opsReadiness?.next_steps || []).map((item, index) => (
                            <div key={`${index}-${item}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                              {item}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  )
}

export default Configuracoes
