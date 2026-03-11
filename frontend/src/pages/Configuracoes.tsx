import React, { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/services/api'
import toast from 'react-hot-toast'
import { Settings, Building2, User, Sliders } from 'lucide-react'

const Configuracoes: React.FC = () => {
  const { user, setUser } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'empresa' | 'usuario' | 'sistema'>('empresa')
  const [isSaving, setIsSaving] = useState(false)

  const { data: configs } = useQuery({
    queryKey: ['configuracoes'],
    queryFn: async () => {
      const { data } = await api.get('/configuracoes/')
      return data
    },
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
  ]

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
      </div>
    </AppLayout>
  )
}

export default Configuracoes
