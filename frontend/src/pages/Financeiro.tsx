import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Edit,
  Trash2,
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  Clock,
  Check,
  X,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import { formatCurrency, formatDate } from '@/lib/utils'
import toast from 'react-hot-toast'

interface Financeiro {
  id: string
  data: string
  tipo: 'receita' | 'despesa'
  categoria: string
  descricao: string
  valor: number
  empresa_id: string
  contrato_id?: string
  veiculo_id?: string
  comprovante_url?: string
  status: 'pendente' | 'pago' | 'cancelado'
}

interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
}

interface PaginationParams {
  page: number
  limit: number
}

const FinanceiroPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<Financeiro | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [typeFilter, setTypeFilter] = useState<'todos' | 'receita' | 'despesa'>('todos')
  const [statusFilter, setStatusFilter] = useState<'todos' | 'pendente' | 'pago' | 'cancelado'>('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [formData, setFormData] = useState({
    tipo: 'receita' as 'receita' | 'despesa',
    categoria: '',
    descricao: '',
    valor: 0,
    data: new Date().toISOString().split('T')[0],
    status: 'pendente' as 'pendente' | 'pago' | 'cancelado',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['financeiro', pagination, typeFilter, statusFilter],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Financeiro>>('/financeiro', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          tipo: typeFilter !== 'todos' ? typeFilter : undefined,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
        },
      })
      return data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/financeiro', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeiro'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Registro criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao criar registro')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch(`/financeiro/${editingRecord?.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeiro'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Registro atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao atualizar registro')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/financeiro/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeiro'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Registro deletado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao deletar registro')
    },
  })

  const resetForm = () => {
    setFormData({
      tipo: 'receita',
      categoria: '',
      descricao: '',
      valor: 0,
      data: new Date().toISOString().split('T')[0],
      status: 'pendente',
    })
    setEditingRecord(null)
  }

  const handleOpenModal = (record?: Financeiro) => {
    if (record) {
      if (!record.id.startsWith('fm-')) {
        toast.error('Edite contratos e despesas nos módulos específicos. Aqui só editamos lançamentos manuais.')
        return
      }
      setEditingRecord(record)
      setFormData(record)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.categoria || !formData.descricao || formData.valor <= 0) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (editingRecord) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const records = data?.data || []

  const kpiData = useMemo(() => {
    const totalReceita = records.filter((r) => r.tipo === 'receita').reduce((sum, r) => sum + r.valor, 0)
    const totalDespesa = records.filter((r) => r.tipo === 'despesa').reduce((sum, r) => sum + r.valor, 0)
    const saldo = totalReceita - totalDespesa
    const pendentes = records.filter((r) => r.status === 'pendente').reduce((sum, r) => sum + r.valor, 0)

    return { totalReceita, totalDespesa, saldo, pendentes }
  }, [records])

  const filteredRecords = useMemo(() => {
    return records.filter((record) => {
      if (searchTerm === '') return true
      const searchLower = searchTerm.toLowerCase()
      return (
        record.descricao.toLowerCase().includes(searchLower) ||
        record.categoria.toLowerCase().includes(searchLower) ||
        record.id.toLowerCase().includes(searchLower)
      )
    })
  }, [records, searchTerm])

  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'pago':
        return 'badge-success'
      case 'pendente':
        return 'badge-warning'
      case 'cancelado':
        return 'badge-danger'
      default:
        return 'badge-success'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pago':
        return <Check size={16} />
      case 'pendente':
        return <Clock size={16} />
      case 'cancelado':
        return <X size={16} />
      default:
        return null
    }
  }

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case 'pago':
        return 'Pago'
      case 'pendente':
        return 'Pendente'
      case 'cancelado':
        return 'Cancelado'
      default:
        return status
    }
  }

  const totalPages = Math.ceil((data?.total || 0) / pagination.limit)

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="page-header">
          <div className="flex-1">
            <h1 className="page-title">Financeiro</h1>
            <p className="page-subtitle">Gerencie receitas, despesas e saldo financeiro da sua empresa</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2">
            <Plus size={20} />
            Novo Registro
          </button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Receitas Card */}
          <div className="kpi-card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="kpi-label">Receitas</p>
                <p className="kpi-value text-green-600">{formatCurrency(kpiData.totalReceita)}</p>
              </div>
              <div className="kpi-icon bg-green-100 text-green-600">
                <TrendingUp size={24} />
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-green-100">
              <p className="text-xs text-slate-600">Total de receitas registradas</p>
            </div>
          </div>

          {/* Despesas Card */}
          <div className="kpi-card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="kpi-label">Despesas</p>
                <p className="kpi-value text-red-600">{formatCurrency(kpiData.totalDespesa)}</p>
              </div>
              <div className="kpi-icon bg-red-100 text-red-600">
                <TrendingDown size={24} />
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-red-100">
              <p className="text-xs text-slate-600">Total de despesas registradas</p>
            </div>
          </div>

          {/* Saldo Card */}
          <div className={`kpi-card ${kpiData.saldo >= 0 ? 'border-blue-200 bg-blue-50' : 'border-red-200 bg-red-50'}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="kpi-label">Saldo</p>
                <p className={`kpi-value ${kpiData.saldo >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {formatCurrency(kpiData.saldo)}
                </p>
              </div>
              <div className={`kpi-icon ${kpiData.saldo >= 0 ? 'bg-blue-100 text-blue-600' : 'bg-red-100 text-red-600'}`}>
                <DollarSign size={24} />
              </div>
            </div>
            <div className={`mt-3 pt-3 ${kpiData.saldo >= 0 ? 'border-t border-blue-100' : 'border-t border-red-100'}`}>
              <p className="text-xs text-slate-600">Receitas menos despesas</p>
            </div>
          </div>

          {/* Pendentes Card */}
          <div className="kpi-card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="kpi-label">Pendentes</p>
                <p className="kpi-value text-amber-600">{formatCurrency(kpiData.pendentes)}</p>
              </div>
              <div className="kpi-icon bg-amber-100 text-amber-600">
                <AlertCircle size={24} />
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-amber-100">
              <p className="text-xs text-slate-600">Registros aguardando pagamento</p>
            </div>
          </div>
        </div>

        {/* Filters Section */}
        <div className="card">
          <div className="space-y-4">
            {/* Type Filters */}
            <div>
              <p className="text-sm font-semibold text-slate-900 mb-3">Tipo de Transação</p>
              <div className="flex gap-2 flex-wrap">
                {['todos', 'receita', 'despesa'].map((type) => (
                  <button
                    key={type}
                    onClick={() => {
                      setTypeFilter(type as any)
                      setPagination({ ...pagination, page: 1 })
                    }}
                    className={
                      typeFilter === type
                        ? 'filter-tab filter-tab-active'
                        : 'filter-tab filter-tab-inactive'
                    }
                  >
                    {type === 'todos' ? 'Todos' : type === 'receita' ? 'Receitas' : 'Despesas'}
                  </button>
                ))}
              </div>
            </div>

            {/* Status Filters */}
            <div className="border-t border-slate-200 pt-4">
              <p className="text-sm font-semibold text-slate-900 mb-3">Status</p>
              <div className="flex gap-2 flex-wrap">
                {['todos', 'pendente', 'pago', 'cancelado'].map((status) => (
                  <button
                    key={status}
                    onClick={() => {
                      setStatusFilter(status as any)
                      setPagination({ ...pagination, page: 1 })
                    }}
                    className={
                      statusFilter === status
                        ? 'filter-tab filter-tab-active'
                        : 'filter-tab filter-tab-inactive'
                    }
                  >
                    {status === 'todos'
                      ? 'Todos'
                      : status === 'pendente'
                        ? 'Pendente'
                        : status === 'pago'
                          ? 'Pago'
                          : 'Cancelado'}
                  </button>
                ))}
              </div>
            </div>

            {/* Search */}
            <div className="border-t border-slate-200 pt-4">
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
                <Search size={18} className="text-slate-400 flex-shrink-0" />
                <input
                  type="text"
                  placeholder="Buscar por descrição, categoria ou ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Table Section */}
        <div className="card card-hover">
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">
                <AlertCircle size={48} />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">Nenhum registro encontrado</h3>
              <p className="mt-2 text-slate-600">Crie um novo registro para começar a gerenciar suas finanças</p>
              <button onClick={() => handleOpenModal()} className="btn-primary mt-4 flex items-center gap-2 mx-auto">
                <Plus size={18} />
                Novo Registro
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header">
                    <th className="text-left py-4 px-6 font-semibold text-slate-900">Data</th>
                    <th className="text-left py-4 px-6 font-semibold text-slate-900">Tipo</th>
                    <th className="text-left py-4 px-6 font-semibold text-slate-900">Categoria</th>
                    <th className="text-left py-4 px-6 font-semibold text-slate-900">Descrição</th>
                    <th className="text-right py-4 px-6 font-semibold text-slate-900">Valor</th>
                    <th className="text-center py-4 px-6 font-semibold text-slate-900">Status</th>
                    <th className="text-center py-4 px-6 font-semibold text-slate-900">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecords.map((record) => (
                    <tr key={record.id} className="table-row">
                      <td className="table-cell text-slate-900 font-medium">{formatDate(record.data)}</td>
                      <td className="table-cell">
                        <span
                          className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
                            record.tipo === 'receita'
                              ? 'badge-success'
                              : 'badge-danger'
                          }`}
                        >
                          {record.tipo === 'receita' ? 'Receita' : 'Despesa'}
                        </span>
                      </td>
                      <td className="table-cell text-slate-700">{record.categoria}</td>
                      <td className="table-cell text-slate-700">{record.descricao}</td>
                      <td className="table-cell text-right">
                        <span
                          className={`font-semibold ${
                            record.tipo === 'receita'
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {record.tipo === 'receita' ? '+' : '-'} {formatCurrency(record.valor)}
                        </span>
                      </td>
                      <td className="table-cell text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${getStatusBadgeClass(
                            record.status
                          )}`}
                        >
                          {getStatusIcon(record.status)}
                          {getStatusLabel(record.status)}
                        </span>
                      </td>
                      <td className="table-cell text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handleOpenModal(record)}
                            className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Editar"
                            disabled={!record.id.startsWith('fm-')}
                          >
                            <Edit size={18} />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm({ isOpen: true, id: record.id })}
                            className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Deletar"
                          >
                            <Trash2 size={18} />
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
          {!isLoading && filteredRecords.length > 0 && (
            <div className="flex items-center justify-between mt-6 pt-6 border-t border-slate-200">
              <p className="text-sm text-slate-600">
                Mostrando <span className="font-semibold">{(pagination.page - 1) * pagination.limit + 1}</span> a{' '}
                <span className="font-semibold">
                  {Math.min(pagination.page * pagination.limit, data?.total || 0)}
                </span>{' '}
                de <span className="font-semibold">{data?.total || 0}</span> registros
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() =>
                    setPagination({
                      ...pagination,
                      page: Math.max(1, pagination.page - 1),
                    })
                  }
                  disabled={pagination.page === 1}
                  className="btn-secondary p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={20} />
                </button>
                <div className="flex items-center gap-2">
                  {[...Array(totalPages)].map((_, i) => {
                    const pageNum = i + 1
                    if (
                      pageNum === 1 ||
                      pageNum === totalPages ||
                      (pageNum >= pagination.page - 1 && pageNum <= pagination.page + 1)
                    ) {
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setPagination({ ...pagination, page: pageNum })}
                          className={`w-10 h-10 rounded-lg font-medium transition-colors ${
                            pageNum === pagination.page
                              ? 'bg-blue-600 text-white'
                              : 'bg-slate-100 text-slate-900 hover:bg-slate-200'
                          }`}
                        >
                          {pageNum}
                        </button>
                      )
                    } else if (pageNum === pagination.page - 2 || pageNum === pagination.page + 2) {
                      return (
                        <span key={pageNum} className="text-slate-600">
                          ...
                        </span>
                      )
                    }
                    return null
                  })}
                </div>
                <button
                  onClick={() =>
                    setPagination({
                      ...pagination,
                      page: Math.min(totalPages, pagination.page + 1),
                    })
                  }
                  disabled={pagination.page === totalPages}
                  className="btn-secondary p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={20} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal Form */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-lg w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingRecord ? 'Editar Registro' : 'Novo Registro'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn-icon"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)] space-y-5">
              {/* Tipo - Radio Buttons */}
              <div>
                <label className="input-label">Tipo de Transação *</label>
                <div className="flex gap-4 mt-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      value="receita"
                      checked={formData.tipo === 'receita'}
                      onChange={(e) => setFormData({ ...formData, tipo: e.target.value as any })}
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="w-4 h-4"
                    />
                    <span className="text-slate-700 font-medium">Receita</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      value="despesa"
                      checked={formData.tipo === 'despesa'}
                      onChange={(e) => setFormData({ ...formData, tipo: e.target.value as any })}
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="w-4 h-4"
                    />
                    <span className="text-slate-700 font-medium">Despesa</span>
                  </label>
                </div>
              </div>

              {/* Categoria - Select */}
              <div>
                <label htmlFor="categoria" className="input-label">
                  Categoria *
                </label>
                <select
                  id="categoria"
                  value={formData.categoria}
                  onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="">Selecione uma categoria</option>
                  <option value="Salários">Salários</option>
                  <option value="Aluguel">Aluguel</option>
                  <option value="Combustível">Combustível</option>
                  <option value="Manutenção">Manutenção</option>
                  <option value="Seguros">Seguros</option>
                  <option value="Publicidade">Publicidade</option>
                  <option value="Vendas">Vendas</option>
                  <option value="Juros">Juros</option>
                  <option value="Outros">Outros</option>
                </select>
              </div>

              {/* Descrição */}
              <div>
                <label htmlFor="descricao" className="input-label">
                  Descrição *
                </label>
                <textarea
                  id="descricao"
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Digite a descrição do registro"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              {/* Valor - Currency Input */}
              <div>
                <label htmlFor="valor" className="input-label">
                  Valor *
                </label>
                <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
                  <span className="text-slate-600 flex-shrink-0">R$</span>
                  <input
                    id="valor"
                    type="number"
                    value={formData.valor}
                    onChange={(e) => setFormData({ ...formData, valor: parseFloat(e.target.value) || 0 })}
                    step="0.01"
                    min="0"
                    placeholder="0,00"
                    className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              {/* Data */}
              <div>
                <label htmlFor="data" className="input-label">
                  Data
                </label>
                <input
                  id="data"
                  type="date"
                  value={formData.data}
                  onChange={(e) => setFormData({ ...formData, data: e.target.value })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              {/* Status */}
              <div>
                <label htmlFor="status" className="input-label">
                  Status
                </label>
                <select
                  id="status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="pendente">Pendente</option>
                  <option value="pago">Pago</option>
                  <option value="cancelado">Cancelado</option>
                </select>
              </div>

            </form>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="btn-secondary"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={createMutation.isPending || updateMutation.isPending}
                onClick={handleSubmit}
              >
                {createMutation.isPending || updateMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Salvando...
                  </span>
                ) : editingRecord ? (
                  'Atualizar'
                ) : (
                  'Criar'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm.isOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && !deleteMutation.isPending && setDeleteConfirm({ isOpen: false })}>
          <div className="modal-content max-w-sm w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Deletar Registro</h3>
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
              <div className="flex items-center gap-4 mb-4">
                <div className="flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                </div>
                <p className="text-sm text-slate-600">Esta ação não pode ser desfeita</p>
              </div>

              <p className="text-slate-700">
                Tem certeza que deseja deletar este registro? Todos os dados associados serão removidos permanentemente.
              </p>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                onClick={() => setDeleteConfirm({ isOpen: false })}
                className="btn-secondary"
                disabled={deleteMutation.isPending}
              >
                Cancelar
              </button>
              <button
                onClick={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)}
                className="btn-danger"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Deletando...' : 'Deletar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

export default FinanceiroPage
