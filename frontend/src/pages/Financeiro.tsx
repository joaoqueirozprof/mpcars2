import React, { useEffect, useMemo, useState } from 'react'
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
import { useSearchParams } from 'react-router-dom'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import CurrencyInput from '@/components/shared/CurrencyInput'
import { formatCurrency, formatDate } from '@/lib/utils'
import toast from 'react-hot-toast'

interface Financeiro {
  id: string
  data: string
  tipo: 'receita' | 'despesa'
  categoria: string
  descricao: string
  valor: number
  valor_recebido?: number
  empresa_id: string
  contrato_id?: string
  veiculo_id?: string
  comprovante_url?: string
  origem_tipo?: string
  forma_pagamento?: string
  data_pagamento?: string
  data_vencimento_pagamento?: string
  status: 'pendente' | 'pago' | 'cancelado'
}

interface FinanceiroResumo {
  total_receita: number
  total_receita_recebida: number
  total_receita_pendente: number
  total_despesa: number
  lucro: number
  saldo_realizado: number
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

const EDITABLE_FINANCE_PREFIXES = ['fm-', 'dc-', 'dv-', 'dl-', 'mt-', 'ip-', 'ml-', 'sg-']
const DELETABLE_FINANCE_PREFIXES = ['fm-', 'dc-', 'dv-', 'dl-']
const FINANCE_CATEGORIES = ['Salarios', 'Aluguel', 'Combustivel', 'Manutencao', 'Seguros', 'Publicidade', 'Vendas', 'Juros', 'Outros']

const FinanceiroPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<Financeiro | null>(null)
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false)
  const [editingPaymentRecord, setEditingPaymentRecord] = useState<Financeiro | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [typeFilter, setTypeFilter] = useState<'todos' | 'receita' | 'despesa'>('todos')
  const [statusFilter, setStatusFilter] = useState<'todos' | 'pendente' | 'pago' | 'cancelado'>('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState({
    tipo: 'receita' as 'receita' | 'despesa',
    categoria: '',
    descricao: '',
    valor: 0,
    data: new Date().toISOString().split('T')[0],
    status: 'pendente' as 'pendente' | 'pago' | 'cancelado',
  })
  const [paymentFormData, setPaymentFormData] = useState({
    status_pagamento: 'pendente' as 'pendente' | 'pago' | 'cancelado',
    forma_pagamento: '',
    data_vencimento_pagamento: new Date().toISOString().split('T')[0],
    data_pagamento: new Date().toISOString().split('T')[0],
    valor_recebido: 0,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['financeiro', pagination, typeFilter, statusFilter, searchTerm, periodStart, periodEnd],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Financeiro>>('/financeiro', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          tipo: typeFilter !== 'todos' ? typeFilter : undefined,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
          search: searchTerm || undefined,
          data_inicio: periodStart || undefined,
          data_fim: periodEnd || undefined,
        },
      })
      return data
    },
  })

  const { data: summaryData } = useQuery({
    queryKey: ['financeiro-resumo'],
    queryFn: async () => {
      const { data } = await api.get<FinanceiroResumo>('/financeiro/resumo')
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

  const paymentMutation = useMutation({
    mutationFn: (payload: any) => api.patch(`/contratos/${editingPaymentRecord?.id.split('-')[1]}/pagamento`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeiro'] })
      queryClient.invalidateQueries({ queryKey: ['financeiro-resumo'] })
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setIsPaymentModalOpen(false)
      resetPaymentForm()
      toast.success('Recebimento do contrato atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao atualizar recebimento')
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

  const resetPaymentForm = () => {
    setPaymentFormData({
      status_pagamento: 'pendente',
      forma_pagamento: '',
      data_vencimento_pagamento: new Date().toISOString().split('T')[0],
      data_pagamento: new Date().toISOString().split('T')[0],
      valor_recebido: 0,
    })
    setEditingPaymentRecord(null)
  }

  const handleOpenModal = (record?: Financeiro) => {
    if (record) {
      if (record.id.startsWith('c-')) {
        setEditingPaymentRecord(record)
        setPaymentFormData({
          status_pagamento: record.status,
          forma_pagamento: record.forma_pagamento || '',
          data_vencimento_pagamento: record.data_vencimento_pagamento ? record.data_vencimento_pagamento.slice(0, 10) : new Date().toISOString().split('T')[0],
          data_pagamento: record.data_pagamento ? record.data_pagamento.slice(0, 10) : new Date().toISOString().split('T')[0],
          valor_recebido: record.valor_recebido || (record.status === 'pago' ? record.valor : 0),
        })
        setIsPaymentModalOpen(true)
        return
      }
      if (!EDITABLE_FINANCE_PREFIXES.some((prefix) => record.id.startsWith(prefix))) {
        toast.error('Edite contratos e despesas nos módulos específicos. Aqui só editamos lançamentos manuais.')
        return
      }
      setEditingRecord(record)
      setFormData({
        tipo: record.tipo,
        categoria: record.categoria,
        descricao: record.descricao,
        valor: record.valor,
        data: record.data ? record.data.slice(0, 10) : new Date().toISOString().split('T')[0],
        status: record.status,
      })
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  useEffect(() => {
    if (searchParams.get('quick') !== 'create') return

    handleOpenModal()
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('quick')
    setSearchParams(nextParams, { replace: true })
  }, [searchParams, setSearchParams])

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

  const handlePaymentSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!editingPaymentRecord) return

    if (paymentFormData.valor_recebido < 0) {
      toast.error('O valor recebido nao pode ser negativo')
      return
    }

    paymentMutation.mutate({
      ...paymentFormData,
      data_pagamento:
        paymentFormData.status_pagamento === 'pago'
          ? paymentFormData.data_pagamento
          : '',
      valor_recebido:
        paymentFormData.status_pagamento === 'pago' && paymentFormData.valor_recebido <= 0
          ? editingPaymentRecord.valor
          : paymentFormData.status_pagamento === 'cancelado'
            ? 0
            : paymentFormData.valor_recebido,
    })
  }

  const records = data?.data || []

  const kpiData = useMemo(() => {
    return {
      totalReceita: summaryData?.total_receita || 0,
      totalDespesa: summaryData?.total_despesa || 0,
      saldo: summaryData?.saldo_realizado ?? summaryData?.lucro ?? 0,
      pendentes: summaryData?.total_receita_pendente || 0,
      recebido: summaryData?.total_receita_recebida || 0,
    }
  }, [summaryData])

  const filteredRecords = useMemo(() => records, [records])
  const isManualEditing = !editingRecord || editingRecord.id.startsWith('fm-')
  const categoryOptions = useMemo(() => {
    if (!formData.categoria || FINANCE_CATEGORIES.includes(formData.categoria)) {
      return FINANCE_CATEGORIES
    }
    return [formData.categoria, ...FINANCE_CATEGORIES]
  }, [formData.categoria])

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
              <p className="text-xs text-slate-600">Recebido: {formatCurrency(kpiData.recebido)}</p>
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
              <p className="text-xs text-slate-600">Receitas ainda em aberto</p>
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
                  onChange={(e) => {
                    setSearchTerm(e.target.value)
                    setPagination((current) => ({ ...current, page: 1 }))
                  }}
                  className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
                />
              </div>
            </div>

            <div className="border-t border-slate-200 pt-4">
              <p className="text-sm font-semibold text-slate-900 mb-3">Periodo</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="input-label">Data inicial</label>
                  <input
                    type="date"
                    value={periodStart}
                    onChange={(e) => {
                      setPeriodStart(e.target.value)
                      setPagination((current) => ({ ...current, page: 1 }))
                    }}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Data final</label>
                  <input
                    type="date"
                    value={periodEnd}
                    onChange={(e) => {
                      setPeriodEnd(e.target.value)
                      setPagination((current) => ({ ...current, page: 1 }))
                    }}
                    className="input-field"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    type="button"
                    onClick={() => {
                      setPeriodStart('')
                      setPeriodEnd('')
                      setPagination((current) => ({ ...current, page: 1 }))
                    }}
                    className="btn-secondary w-full"
                  >
                    Limpar periodo
                  </button>
                </div>
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
                      <td className="table-cell text-slate-700">
                        <div>{record.descricao}</div>
                        {record.origem_tipo === 'contrato' && (
                          <div className="mt-1 text-xs text-slate-500">
                            {record.forma_pagamento ? `Forma: ${record.forma_pagamento}` : 'Forma nao definida'}
                            {record.data_vencimento_pagamento ? ` • Vencimento ${formatDate(record.data_vencimento_pagamento)}` : ''}
                            {record.data_pagamento ? ` • Pagamento ${formatDate(record.data_pagamento)}` : ''}
                          </div>
                        )}
                      </td>
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
                          {(() => {
                            const canManageFromFinance =
                              record.id.startsWith('c-') ||
                              EDITABLE_FINANCE_PREFIXES.some((prefix) => record.id.startsWith(prefix))
                            const canDeleteFromFinance = DELETABLE_FINANCE_PREFIXES.some((prefix) => record.id.startsWith(prefix))

                            return (
                              <>
                          <button
                            onClick={() => handleOpenModal(record)}
                            className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title={record.id.startsWith('c-') ? 'Atualizar recebimento' : canManageFromFinance ? 'Editar' : 'Edite no modulo de origem'}
                            disabled={!canManageFromFinance}
                          >
                            <Edit size={18} />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm({ isOpen: true, id: record.id })}
                            className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title={canDeleteFromFinance ? 'Deletar' : 'Exclusao disponivel no modulo de origem'}
                            disabled={!canDeleteFromFinance}
                          >
                            <Trash2 size={18} />
                          </button>
                              </>
                            )
                          })()}
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
                      disabled={createMutation.isPending || updateMutation.isPending || !isManualEditing}
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
                      disabled={createMutation.isPending || updateMutation.isPending || !isManualEditing}
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
                  {categoryOptions.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
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
              <CurrencyInput
                label="Valor *"
                value={formData.valor}
                onChange={(valor) => setFormData({ ...formData, valor })}
                disabled={createMutation.isPending || updateMutation.isPending}
              />

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

      {isPaymentModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && !paymentMutation.isPending && setIsPaymentModalOpen(false)}>
          <div className="modal-content max-w-lg w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Recebimento do Contrato</h3>
              <button
                onClick={() => {
                  setIsPaymentModalOpen(false)
                  resetPaymentForm()
                }}
                className="btn-icon"
                disabled={paymentMutation.isPending}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handlePaymentSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)] space-y-5">
              <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
                <p className="font-semibold">{editingPaymentRecord?.descricao}</p>
                <p className="mt-1">Valor do contrato: {formatCurrency(editingPaymentRecord?.valor || 0)}</p>
              </div>

              <div>
                <label className="input-label">Status do recebimento</label>
                <select
                  value={paymentFormData.status_pagamento}
                  onChange={(e) =>
                    setPaymentFormData({
                      ...paymentFormData,
                      status_pagamento: e.target.value as 'pendente' | 'pago' | 'cancelado',
                      valor_recebido:
                        e.target.value === 'pago' && paymentFormData.valor_recebido <= 0
                          ? editingPaymentRecord?.valor || 0
                          : e.target.value === 'cancelado'
                            ? 0
                            : paymentFormData.valor_recebido,
                    })
                  }
                  className="input-field"
                  disabled={paymentMutation.isPending}
                >
                  <option value="pendente">Pendente</option>
                  <option value="pago">Pago</option>
                  <option value="cancelado">Cancelado</option>
                </select>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Forma de pagamento</label>
                  <select
                    value={paymentFormData.forma_pagamento}
                    onChange={(e) => setPaymentFormData({ ...paymentFormData, forma_pagamento: e.target.value })}
                    className="input-field"
                    disabled={paymentMutation.isPending}
                  >
                    <option value="">Selecione</option>
                    <option value="Pix">Pix</option>
                    <option value="Cartao">Cartao</option>
                    <option value="Dinheiro">Dinheiro</option>
                    <option value="Transferencia">Transferencia</option>
                    <option value="Boleto">Boleto</option>
                    <option value="Faturado">Faturado</option>
                  </select>
                </div>
                <div>
                  <label className="input-label">Valor recebido</label>
                  <CurrencyInput
                    value={paymentFormData.valor_recebido}
                    onChange={(valor_recebido) => setPaymentFormData({ ...paymentFormData, valor_recebido })}
                    disabled={paymentMutation.isPending}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Vencimento</label>
                  <input
                    type="date"
                    value={paymentFormData.data_vencimento_pagamento}
                    onChange={(e) => setPaymentFormData({ ...paymentFormData, data_vencimento_pagamento: e.target.value })}
                    className="input-field"
                    disabled={paymentMutation.isPending}
                  />
                </div>
                <div>
                  <label className="input-label">Data do pagamento</label>
                  <input
                    type="date"
                    value={paymentFormData.data_pagamento}
                    onChange={(e) => setPaymentFormData({ ...paymentFormData, data_pagamento: e.target.value })}
                    className="input-field"
                    disabled={paymentMutation.isPending || paymentFormData.status_pagamento !== 'pago'}
                  />
                </div>
              </div>
            </form>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                type="button"
                onClick={() => {
                  setIsPaymentModalOpen(false)
                  resetPaymentForm()
                }}
                className="btn-secondary"
                disabled={paymentMutation.isPending}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={paymentMutation.isPending}
                onClick={handlePaymentSubmit}
              >
                {paymentMutation.isPending ? 'Salvando...' : 'Atualizar recebimento'}
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
