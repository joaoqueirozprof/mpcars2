import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Edit,
  Trash2,
  Phone,
  Mail,
  MapPin,
  Search,
  ChevronDown,
  AlertCircle,
  Loader,
  Check,
  X,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import { formatDate, formatPhone, formatCPF, validateEmail } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Cliente } from '@/types'

type ClientType = 'todos' | 'pessoa_fisica' | 'pessoa_juridica'

const Clientes: React.FC = () => {
  const queryClient = useQueryClient()
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingClient, setEditingClient] = useState<Cliente | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({
    isOpen: false,
  })
  const [activeTab, setActiveTab] = useState<ClientType>('todos')
  const [searchQuery, setSearchQuery] = useState('')
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    telefone: '',
    cpf_cnpj: '',
    endereco: '',
    cidade: '',
    estado: '',
    cep: '',
    tipo: 'pessoa_fisica' as 'pessoa_fisica' | 'pessoa_juridica',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['clientes', currentPage, pageSize, activeTab, searchQuery],
    queryFn: async () => {
      const params: any = {
        page: currentPage,
        limit: pageSize,
      }
      if (activeTab !== 'todos') {
        params.tipo = activeTab
      }
      if (searchQuery) {
        params.search = searchQuery
      }
      const response = await api.get('/clientes', { params })
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/clientes', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Cliente criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar cliente')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch(`/clientes/${editingClient?.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Cliente atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar cliente')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/clientes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Cliente deletado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar cliente')
    },
  })

  const resetForm = () => {
    setFormData({
      nome: '',
      email: '',
      telefone: '',
      cpf_cnpj: '',
      endereco: '',
      cidade: '',
      estado: '',
      cep: '',
      tipo: 'pessoa_fisica',
    })
    setEditingClient(null)
    setFormErrors({})
  }

  const handleOpenModal = (client?: Cliente) => {
    if (client) {
      setEditingClient(client)
      setFormData({
        nome: client.nome,
        email: client.email,
        telefone: client.telefone,
        cpf_cnpj: client.cpf_cnpj,
        endereco: client.endereco,
        cidade: client.cidade,
        estado: client.estado,
        cep: client.cep,
        tipo: client.tipo,
      })
    } else {
      resetForm()
    }
    setFormErrors({})
    setIsModalOpen(true)
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!formData.nome.trim()) {
      errors.nome = 'Nome é obrigatório'
    }
    if (!formData.email.trim()) {
      errors.email = 'Email é obrigatório'
    } else if (!validateEmail(formData.email)) {
      errors.email = 'Email inválido'
    }
    if (!formData.telefone.trim()) {
      errors.telefone = 'Telefone é obrigatório'
    }

    if (formData.cpf_cnpj.trim()) {
      const cleanCPFCNPJ = formData.cpf_cnpj.replace(/\D/g, '')
      if (formData.tipo === 'pessoa_fisica' && cleanCPFCNPJ.length !== 11) {
        errors.cpf_cnpj = 'CPF deve conter 11 dígitos'
      } else if (formData.tipo === 'pessoa_juridica' && cleanCPFCNPJ.length !== 14) {
        errors.cpf_cnpj = 'CNPJ deve conter 14 dígitos'
      }
    }

    if (formData.cep.trim() && formData.cep.replace(/\D/g, '').length !== 8) {
      errors.cep = 'CEP deve conter 8 dígitos'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      toast.error('Corrija os erros no formulário')
      return
    }

    const submitData = {
      ...formData,
      cpf_cnpj: formData.cpf_cnpj.replace(/\D/g, ''),
      telefone: formData.telefone.replace(/\D/g, ''),
      cep: formData.cep.replace(/\D/g, ''),
    }

    if (editingClient) {
      updateMutation.mutate(submitData)
    } else {
      createMutation.mutate(submitData)
    }
  }

  const handlePhoneChange = (value: string) => {
    const cleaned = value.replace(/\D/g, '')
    const formatted = formatPhone(cleaned)
    setFormData({ ...formData, telefone: formatted })
  }

  const handleCPFCNPJChange = (value: string) => {
    if (formData.tipo === 'pessoa_fisica') {
      const cleaned = value.replace(/\D/g, '').slice(0, 11)
      const formatted = formatCPF(cleaned)
      setFormData({ ...formData, cpf_cnpj: formatted })
    } else {
      const cleaned = value.replace(/\D/g, '').slice(0, 14)
      const formatted = cleaned
      setFormData({ ...formData, cpf_cnpj: formatted })
    }
  }

  const handleCEPChange = (value: string) => {
    const cleaned = value.replace(/\D/g, '').slice(0, 8)
    const formatted = cleaned.length > 5 ? `${cleaned.slice(0, 5)}-${cleaned.slice(5)}` : cleaned
    setFormData({ ...formData, cep: formatted })
  }

  const handleTypeChange = (newType: 'pessoa_fisica' | 'pessoa_juridica') => {
    setFormData({
      ...formData,
      tipo: newType,
      cpf_cnpj: '',
    })
    setFormErrors({ ...formErrors, cpf_cnpj: '' })
  }

  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const getAvatarColor = (name: string): string => {
    const colors = [
      'bg-blue-500',
      'bg-emerald-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-amber-500',
      'bg-cyan-500',
      'bg-red-500',
      'bg-green-500',
    ]
    const hash = name.charCodeAt(0) + name.charCodeAt(Math.floor(name.length / 2))
    return colors[hash % colors.length]
  }

  const isEmpty = !isLoading && (!data?.data || data.data.length === 0)

  const isLoadingState = isLoading || createMutation.isPending || updateMutation.isPending

  return (
    <AppLayout>
      <div className="min-h-screen bg-slate-50">
        {/* Page Header */}
        <div className="bg-white border-b border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
              <div>
                <h1 className="page-title">Clientes</h1>
                <p className="page-subtitle">
                  Gerenciar e manter informações dos seus clientes
                </p>
              </div>
              <button
                onClick={() => handleOpenModal()}
                className="btn-primary flex items-center justify-center gap-2 h-10 px-4 w-full sm:w-auto"
              >
                <Plus size={20} />
                <span>Novo Cliente</span>
              </button>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="space-y-6">
            {/* Filter Tabs */}
            <div className="flex flex-wrap gap-2">
              {['todos', 'pessoa_fisica', 'pessoa_juridica'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setActiveTab(tab as ClientType)
                    setCurrentPage(1)
                  }}
                  className={
                    activeTab === tab ? 'filter-tab filter-tab-active' : 'filter-tab filter-tab-inactive'
                  }
                >
                  {tab === 'todos'
                    ? 'Todos'
                    : tab === 'pessoa_fisica'
                      ? 'Pessoa Física'
                      : 'Pessoa Jurídica'}
                </button>
              ))}
            </div>

            {/* Search Bar */}
            <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all w-full">
              <Search size={18} className="text-slate-400 flex-shrink-0" />
              <input
                type="text"
                placeholder="Buscar por nome, email ou telefone..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setCurrentPage(1)
                }}
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
              />
            </div>

            {/* Table Card */}
            <div className="card overflow-hidden">
              {isLoading ? (
                <div className="space-y-4 p-6">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-slate-200 rounded-full animate-pulse" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-slate-200 rounded w-1/4 animate-pulse" />
                        <div className="h-3 bg-slate-100 rounded w-1/2 animate-pulse" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : isEmpty ? (
                <div className="empty-state p-12">
                  <div className="empty-state-icon text-slate-400 mb-4">
                    <Mail size={48} />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-900 mb-1">Nenhum cliente encontrado</h3>
                  <p className="text-slate-600 mb-6">
                    {searchQuery
                      ? 'Tente alterar seus critérios de busca'
                      : 'Comece criando seu primeiro cliente'}
                  </p>
                  {!searchQuery && (
                    <button
                      onClick={() => handleOpenModal()}
                      className="btn-primary inline-flex items-center gap-2"
                    >
                      <Plus size={20} />
                      Criar Cliente
                    </button>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-slate-50 border-b border-slate-200">
                      <tr>
                        <th className="table-header px-6 py-3 text-left">Nome</th>
                        <th className="table-header px-6 py-3 text-left">Email</th>
                        <th className="table-header px-6 py-3 text-left">Telefone</th>
                        <th className="table-header px-6 py-3 text-left">
                          {activeTab === 'pessoa_juridica' ? 'CNPJ' : 'CPF'}
                        </th>
                        <th className="table-header px-6 py-3 text-left">Cidade/Estado</th>
                        <th className="table-header px-6 py-3 text-left">Status</th>
                        <th className="table-header px-6 py-3 text-center">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data?.data?.map((client: Cliente) => (
                        <tr key={client.id} className="table-row hover:bg-slate-50 transition-colors">
                          <td className="table-cell px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div
                                className={`w-10 h-10 ${getAvatarColor(client.nome)} rounded-full flex items-center justify-center text-white text-sm font-semibold flex-shrink-0`}
                              >
                                {getInitials(client.nome)}
                              </div>
                              <div className="min-w-0">
                                <p className="font-medium text-slate-900 truncate">{client.nome}</p>
                                <p className="text-xs text-slate-500">
                                  {client.tipo === 'pessoa_fisica' ? 'PF' : 'PJ'}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="table-cell px-6 py-4">
                            <div className="flex items-center gap-2 min-w-0">
                              <Mail size={16} className="text-slate-400 flex-shrink-0" />
                              <span className="text-slate-700 truncate text-sm">{client.email}</span>
                            </div>
                          </td>
                          <td className="table-cell px-6 py-4">
                            <div className="flex items-center gap-2">
                              <Phone size={16} className="text-slate-400" />
                              <span className="text-slate-700 text-sm">{formatPhone(client.telefone)}</span>
                            </div>
                          </td>
                          <td className="table-cell px-6 py-4">
                            <span className="text-slate-700 text-sm font-mono">
                              {client.tipo === 'pessoa_fisica'
                                ? formatCPF(client.cpf_cnpj)
                                : client.cpf_cnpj}
                            </span>
                          </td>
                          <td className="table-cell px-6 py-4">
                            <div className="flex items-center gap-1">
                              <MapPin size={16} className="text-slate-400" />
                              <span className="text-slate-700 text-sm">
                                {client.cidade}
                                {client.estado && `/${client.estado}`}
                              </span>
                            </div>
                          </td>
                          <td className="table-cell px-6 py-4">
                            <span
                              className={client.ativo ? 'badge-info' : 'badge-neutral'}
                            >
                              {client.ativo ? 'Ativo' : 'Inativo'}
                            </span>
                          </td>
                          <td className="table-cell px-6 py-4">
                            <div className="flex items-center justify-center gap-2">
                              <button
                                onClick={() => handleOpenModal(client)}
                                className="btn-icon hover:bg-blue-50"
                                title="Editar"
                              >
                                <Edit size={18} className="text-blue-600" />
                              </button>
                              <button
                                onClick={() => setDeleteConfirm({ isOpen: true, id: client.id })}
                                className="btn-icon hover:bg-red-50"
                                title="Deletar"
                              >
                                <Trash2 size={18} className="text-red-600" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Pagination */}
              {!isEmpty && data && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 bg-slate-50">
                  <p className="text-sm text-slate-600">
                    Mostrando {(currentPage - 1) * pageSize + 1} a{' '}
                    {Math.min(currentPage * pageSize, data.total)} de {data.total} clientes
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="btn-secondary btn-sm"
                    >
                      Anterior
                    </button>
                    <span className="px-3 py-2 text-sm text-slate-700">
                      Página {currentPage}
                    </span>
                    <button
                      onClick={() =>
                        setCurrentPage(Math.min(Math.ceil(data.total / pageSize), currentPage + 1))
                      }
                      disabled={currentPage >= Math.ceil(data.total / pageSize)}
                      className="btn-secondary btn-sm"
                    >
                      Próxima
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && !isLoadingState && setIsModalOpen(false)}>
          <div
            className="modal-content max-w-2xl w-full flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingClient ? 'Editar Cliente' : 'Novo Cliente'}
              </h3>
              <button
                onClick={() => !isLoadingState && setIsModalOpen(false)}
                className="btn-icon"
                disabled={isLoadingState}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)] space-y-6">
              {/* Type Selection */}
              <div>
                <input-label>Tipo de Cliente</input-label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      checked={formData.tipo === 'pessoa_fisica'}
                      onChange={() => handleTypeChange('pessoa_fisica')}
                      disabled={isLoadingState}
                      className="w-4 h-4"
                    />
                    <span className="text-sm font-medium text-slate-700">Pessoa Física</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      checked={formData.tipo === 'pessoa_juridica'}
                      onChange={() => handleTypeChange('pessoa_juridica')}
                      disabled={isLoadingState}
                      className="w-4 h-4"
                    />
                    <span className="text-sm font-medium text-slate-700">Pessoa Jurídica</span>
                  </label>
                </div>
              </div>

              {/* Basic Info Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Nome */}
                <div>
                  <input-label>
                    Nome <span className="text-red-500">*</span>
                  </input-label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => {
                      setFormData({ ...formData, nome: e.target.value })
                      setFormErrors({ ...formErrors, nome: '' })
                    }}
                    className="input-field"
                    disabled={isLoadingState}
                    placeholder="Nome completo"
                  />
                  {formErrors.nome && <p className="mt-1 text-sm text-red-500">{formErrors.nome}</p>}
                </div>

                {/* Document Field */}
                <div>
                  <input-label>
                    {formData.tipo === 'pessoa_fisica' ? 'CPF' : 'CNPJ'}{' '}
                    <span className="text-slate-500 text-xs font-normal">
                      {formData.tipo === 'pessoa_fisica' ? '(11 dígitos)' : '(14 dígitos)'}
                    </span>
                  </input-label>
                  <input
                    type="text"
                    value={formData.cpf_cnpj}
                    onChange={(e) => {
                      handleCPFCNPJChange(e.target.value)
                      setFormErrors({ ...formErrors, cpf_cnpj: '' })
                    }}
                    className="input-field"
                    disabled={isLoadingState}
                    placeholder={formData.tipo === 'pessoa_fisica' ? '000.000.000-00' : '00.000.000/0000-00'}
                  />
                  {formErrors.cpf_cnpj && (
                    <p className="mt-1 text-sm text-red-500">{formErrors.cpf_cnpj}</p>
                  )}
                </div>

                {/* Email */}
                <div>
                  <input-label>
                    Email <span className="text-red-500">*</span>
                  </input-label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => {
                      setFormData({ ...formData, email: e.target.value })
                      setFormErrors({ ...formErrors, email: '' })
                    }}
                    className="input-field"
                    disabled={isLoadingState}
                    placeholder="email@example.com"
                  />
                  {formErrors.email && <p className="mt-1 text-sm text-red-500">{formErrors.email}</p>}
                </div>

                {/* Telefone */}
                <div>
                  <input-label>
                    Telefone <span className="text-red-500">*</span>
                  </input-label>
                  <input
                    type="tel"
                    value={formData.telefone}
                    onChange={(e) => {
                      handlePhoneChange(e.target.value)
                      setFormErrors({ ...formErrors, telefone: '' })
                    }}
                    className="input-field"
                    disabled={isLoadingState}
                    placeholder="(11) 98765-4321"
                  />
                  {formErrors.telefone && (
                    <p className="mt-1 text-sm text-red-500">{formErrors.telefone}</p>
                  )}
                </div>
              </div>

              {/* Address Grid */}
              <div className="space-y-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
                <h3 className="font-semibold text-slate-900">Endereço</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* CEP */}
                  <div>
                    <input-label>CEP</input-label>
                    <input
                      type="text"
                      value={formData.cep}
                      onChange={(e) => {
                        handleCEPChange(e.target.value)
                        setFormErrors({ ...formErrors, cep: '' })
                      }}
                      className="input-field"
                      disabled={isLoadingState}
                      placeholder="00000-000"
                    />
                    {formErrors.cep && <p className="mt-1 text-sm text-red-500">{formErrors.cep}</p>}
                  </div>

                  {/* Empty space for alignment */}
                  <div />

                  {/* Endereco */}
                  <div className="md:col-span-2">
                    <input-label>Endereço</input-label>
                    <input
                      type="text"
                      value={formData.endereco}
                      onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                      className="input-field"
                      disabled={isLoadingState}
                      placeholder="Rua, avenida, etc..."
                    />
                  </div>

                  {/* Cidade */}
                  <div>
                    <input-label>Cidade</input-label>
                    <input
                      type="text"
                      value={formData.cidade}
                      onChange={(e) => setFormData({ ...formData, cidade: e.target.value })}
                      className="input-field"
                      disabled={isLoadingState}
                      placeholder="São Paulo"
                    />
                  </div>

                  {/* Estado */}
                  <div>
                    <input-label>Estado</input-label>
                    <input
                      type="text"
                      value={formData.estado}
                      onChange={(e) =>
                        setFormData({ ...formData, estado: e.target.value.toUpperCase() })
                      }
                      className="input-field"
                      disabled={isLoadingState}
                      placeholder="SP"
                      maxLength={2}
                    />
                  </div>
                </div>
              </div>

            </form>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="btn-secondary"
                disabled={isLoadingState}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary flex items-center gap-2"
                disabled={isLoadingState}
                onClick={handleSubmit}
              >
                {isLoadingState && <Loader size={16} className="animate-spin" />}
                {editingClient ? 'Atualizar' : 'Criar'} Cliente
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm.isOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && !deleteMutation.isPending && setDeleteConfirm({ isOpen: false })}>
          <div
            className="modal-content max-w-sm w-full flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Deletar Cliente</h3>
              <button
                onClick={() => setDeleteConfirm({ isOpen: false })}
                className="btn-icon"
                disabled={deleteMutation.isPending}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)]">
              <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
                <AlertCircle size={24} className="text-red-600" />
              </div>

              <p className="text-slate-600 text-center">
                Tem certeza que deseja deletar este cliente? Esta ação não pode ser desfeita.
              </p>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                type="button"
                onClick={() => setDeleteConfirm({ isOpen: false })}
                className="btn-secondary"
                disabled={deleteMutation.isPending}
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)}
                className="btn-danger flex items-center justify-center gap-2"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending && <Loader size={16} className="animate-spin" />}
                Deletar
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

export default Clientes
