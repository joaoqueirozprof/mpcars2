import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Edit,
  Trash2,
  DollarSign,
  FileText,
  Calendar,
  Users,
  AlertCircle,
  ChevronRight,
  Search,
  X,
  CheckCircle,
  Clock,
  Download,
  Printer,
  Loader2,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import { Contrato, Cliente, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { formatCurrency, formatDate, calculateDays } from '@/lib/utils'
import toast from 'react-hot-toast'

interface FormData {
  cliente_id: string
  veiculo_id: string
  data_inicio: string
  data_fim: string
  quilometragem_inicial: number
  valor_diaria: number
  observacoes: string
}

type StatusFilter = 'todos' | 'ativo' | 'finalizado' | 'cancelado' | 'atraso'

const Contratos: React.FC = () => {
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [searchTerm, setSearchTerm] = useState('')
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingContract, setEditingContract] = useState<Contrato | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('todos')
  const [dateError, setDateError] = useState<string>('')
  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null)

  const handleDownloadPdf = async (contratoId: string, numero: string) => {
    setDownloadingPdf(contratoId)
    try {
      const response = await api.get(`/relatorios/contrato/${contratoId}/pdf`, {
        responseType: 'blob',
      })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `contrato_${numero}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success('PDF do contrato gerado com sucesso!')
    } catch (error) {
      toast.error('Erro ao gerar PDF do contrato')
    } finally {
      setDownloadingPdf(null)
    }
  }

  const handlePrintPdf = async (contratoId: string) => {
    setDownloadingPdf(contratoId)
    try {
      const response = await api.get(`/relatorios/contrato/${contratoId}/pdf`, {
        responseType: 'blob',
      })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const printWindow = window.open(url, '_blank')
      if (printWindow) {
        printWindow.onload = () => printWindow.print()
      }
    } catch (error) {
      toast.error('Erro ao imprimir contrato')
    } finally {
      setDownloadingPdf(null)
    }
  }

  const [formData, setFormData] = useState<FormData>({
    cliente_id: '',
    veiculo_id: '',
    data_inicio: '',
    data_fim: '',
    quilometragem_inicial: 0,
    valor_diaria: 0,
    observacoes: '',
  })

  const { data: contratos, isLoading } = useQuery({
    queryKey: ['contratos', pagination, statusFilter, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Contrato>>('/contratos', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
          search: searchTerm || undefined,
        },
      })
      return data
    },
  })

  const { data: clientes } = useQuery({
    queryKey: ['clientes-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Cliente>>('/clientes', { params: { limit: 1000 } })
      return data.data
    },
  })

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Veiculo>>('/veiculos', { params: { limit: 1000 } })
      return data.data.filter((v) => v.status === 'disponivel')
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/contratos', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Contrato criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar contrato')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch(`/contratos/${editingContract?.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Contrato atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar contrato')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/contratos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contratos'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Contrato deletado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar contrato')
    },
  })

  const resetForm = () => {
    setFormData({
      cliente_id: '',
      veiculo_id: '',
      data_inicio: '',
      data_fim: '',
      quilometragem_inicial: 0,
      valor_diaria: 0,
      observacoes: '',
    })
    setEditingContract(null)
    setStep(1)
    setDateError('')
  }

  const handleOpenModal = (contract?: Contrato) => {
    if (contract) {
      setEditingContract(contract)
      setFormData({
        cliente_id: contract.cliente_id,
        veiculo_id: contract.veiculo_id,
        data_inicio: contract.data_inicio,
        data_fim: contract.data_fim,
        quilometragem_inicial: contract.quilometragem_inicial,
        valor_diaria: contract.valor_diaria,
        observacoes: contract.observacoes,
      })
      setStep(3)
    } else {
      resetForm()
      setStep(1)
    }
    setIsModalOpen(true)
  }

  const validateDates = (inicio: string, fim: string): boolean => {
    if (!inicio || !fim) {
      setDateError('')
      return false
    }
    const inicioDate = new Date(inicio)
    const fimDate = new Date(fim)
    if (fimDate <= inicioDate) {
      setDateError('Data de fim deve ser posterior à data de início')
      return false
    }
    setDateError('')
    return true
  }

  const handleDateChange = (field: 'data_inicio' | 'data_fim', value: string) => {
    const newFormData = { ...formData, [field]: value }
    setFormData(newFormData)
    if (newFormData.data_inicio && newFormData.data_fim) {
      validateDates(newFormData.data_inicio, newFormData.data_fim)
    }
  }

  const handleNextStep = () => {
    if (step === 1) {
      if (formData.cliente_id && formData.veiculo_id) {
        setStep(2)
      } else {
        toast.error('Selecione um cliente e um veículo')
      }
    } else if (step === 2) {
      if (!formData.data_inicio || !formData.data_fim) {
        toast.error('Preencha as datas')
        return
      }
      if (!validateDates(formData.data_inicio, formData.data_fim)) {
        return
      }
      if (formData.valor_diaria <= 0) {
        toast.error('Valor da diária deve ser maior que zero')
        return
      }
      setStep(3)
    }
  }

  const handlePrevStep = () => {
    if (step > 1) setStep((step - 1) as 1 | 2 | 3)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (
      !formData.cliente_id ||
      !formData.veiculo_id ||
      !formData.data_inicio ||
      !formData.data_fim ||
      formData.valor_diaria <= 0
    ) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (!validateDates(formData.data_inicio, formData.data_fim)) {
      return
    }

    const dias = calculateDays(formData.data_inicio, formData.data_fim)
    const payload = {
      ...formData,
      valor_total: dias * formData.valor_diaria,
    }

    if (editingContract) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  const dias = formData.data_inicio && formData.data_fim ? calculateDays(formData.data_inicio, formData.data_fim) : 0
  const valor_total = dias * formData.valor_diaria

  const clienteInfo = clientes?.find((c) => c.id === formData.cliente_id)
  const veiculoInfo = veiculos?.find((v) => v.id === formData.veiculo_id)

  // Calculate KPIs
  const kpis = useMemo(() => {
    const contractsList = contratos?.data || []
    const totalContratos = contratos?.total || 0
    const ativos = contractsList.filter((c) => c.status === 'ativo').length
    const atrasados = contractsList.filter((c) => c.status === 'atraso').length
    const valorTotal = contractsList.reduce((sum, c) => sum + c.valor_total, 0)

    return { totalContratos, ativos, atrasados, valorTotal }
  }, [contratos])

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      ativo: 'badge-success',
      finalizado: 'badge-info',
      cancelado: 'badge-danger',
      atraso: 'badge-warning',
    }
    return colors[status] || 'badge-info'
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      ativo: 'Ativo',
      finalizado: 'Finalizado',
      cancelado: 'Cancelado',
      atraso: 'Atraso',
    }
    return labels[status] || status
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Contratos</h1>
            <p className="page-subtitle">Gerenciamento completo de contratos de aluguel</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2">
            <Plus size={20} />
            Novo Contrato
          </button>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="kpi-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="kpi-label">Total de Contratos</p>
                <p className="kpi-value">{kpis.totalContratos}</p>
              </div>
              <div className="kpi-icon bg-blue-100 text-blue-600">
                <FileText size={24} />
              </div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="kpi-label">Contratos Ativos</p>
                <p className="kpi-value text-green-600">{kpis.ativos}</p>
              </div>
              <div className="kpi-icon bg-green-100 text-green-600">
                <CheckCircle size={24} />
              </div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="kpi-label">Atrasados</p>
                <p className="kpi-value text-red-600">{kpis.atrasados}</p>
              </div>
              <div className="kpi-icon bg-red-100 text-red-600">
                <AlertCircle size={24} />
              </div>
            </div>
          </div>

          <div className="kpi-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="kpi-label">Valor Total</p>
                <p className="kpi-value text-purple-600">{formatCurrency(kpis.valorTotal)}</p>
              </div>
              <div className="kpi-icon bg-purple-100 text-purple-600">
                <DollarSign size={24} />
              </div>
            </div>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center">
            <div className="flex-1 flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
              <Search size={18} className="text-slate-400 flex-shrink-0" />
              <input
                type="text"
                placeholder="Buscar por número, cliente ou veículo..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setPagination({ ...pagination, page: 1 })
                }}
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
              />
            </div>
          </div>

          {/* Status Filter Tabs */}
          <div className="flex flex-wrap gap-2">
            {['todos', 'ativo', 'finalizado', 'cancelado', 'atraso'].map((status) => (
              <button
                key={status}
                onClick={() => {
                  setStatusFilter(status as StatusFilter)
                  setPagination({ ...pagination, page: 1 })
                }}
                className={`filter-tab ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos' ? 'Todos' : getStatusLabel(status)}
              </button>
            ))}
          </div>
        </div>

        {/* Contracts Table */}
        <div className="card">
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-slate-100 rounded animate-pulse" />
              ))}
            </div>
          ) : contratos?.data && contratos.data.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header border-b border-slate-200">
                    <th className="table-cell text-left">Número</th>
                    <th className="table-cell text-left">Cliente</th>
                    <th className="table-cell text-left">Veículo</th>
                    <th className="table-cell text-left">Período</th>
                    <th className="table-cell text-right">Valor</th>
                    <th className="table-cell text-center">Status</th>
                    <th className="table-cell text-center">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {contratos.data.map((contrato) => (
                    <tr key={contrato.id} className="table-row hover:bg-slate-50">
                      <td className="table-cell font-semibold text-slate-900">{contrato.numero}</td>
                      <td className="table-cell text-slate-700">{contrato.cliente?.nome || '-'}</td>
                      <td className="table-cell text-slate-700">
                        {contrato.veiculo ? `${contrato.veiculo.marca} ${contrato.veiculo.modelo}` : '-'}
                      </td>
                      <td className="table-cell text-slate-600 text-sm">
                        {formatDate(contrato.data_inicio)} a {formatDate(contrato.data_fim)}
                      </td>
                      <td className="table-cell text-right font-semibold text-slate-900">
                        {formatCurrency(contrato.valor_total)}
                      </td>
                      <td className="table-cell text-center">
                        <span className={`badge-success inline-block ${getStatusColor(contrato.status)}`}>
                          {getStatusLabel(contrato.status)}
                        </span>
                      </td>
                      <td className="table-cell text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => handleDownloadPdf(contrato.id, contrato.numero)}
                            disabled={downloadingPdf === contrato.id}
                            className="p-1.5 text-slate-600 hover:text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50"
                            title="Baixar PDF"
                          >
                            {downloadingPdf === contrato.id ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                          </button>
                          <button
                            onClick={() => handlePrintPdf(contrato.id)}
                            className="p-1.5 text-slate-600 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
                            title="Imprimir"
                          >
                            <Printer size={16} />
                          </button>
                          <button
                            onClick={() => handleOpenModal(contrato)}
                            className="p-1.5 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                            title="Editar"
                          >
                            <Edit size={16} />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm({ isOpen: true, id: contrato.id })}
                            className="p-1.5 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Deletar"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-600">
                  Mostrando {contratos.data.length} de {contratos.total} contratos
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPagination({ ...pagination, page: Math.max(1, pagination.page - 1) })}
                    disabled={pagination.page === 1}
                    className="btn-secondary btn-sm disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <span className="px-4 py-2 text-sm font-medium text-slate-700">
                    Página {pagination.page} de {Math.ceil((contratos.total || 0) / pagination.limit)}
                  </span>
                  <button
                    onClick={() =>
                      setPagination({
                        ...pagination,
                        page: Math.min(
                          Math.ceil((contratos.total || 0) / pagination.limit),
                          pagination.page + 1
                        ),
                      })
                    }
                    disabled={pagination.page * pagination.limit >= (contratos.total || 0)}
                    className="btn-secondary btn-sm disabled:opacity-50"
                  >
                    Próximo
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon bg-slate-100">
                <FileText className="text-slate-400" size={48} />
              </div>
              <h3 className="mt-4 font-semibold text-slate-900">Nenhum contrato encontrado</h3>
              <p className="text-slate-600 mt-1">Crie seu primeiro contrato para começar</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-2xl w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingContract ? 'Editar Contrato' : 'Novo Contrato'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn-icon"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)]">
            {/* Step Indicator */}
            <div className="mb-8">
              <div className="flex items-center justify-between">
                {[1, 2, 3].map((s, index) => (
                  <div key={s} className="flex items-center flex-1">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors ${
                        s <= step
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {s}
                    </div>
                    {index < 2 && (
                      <div
                        className={`flex-1 h-1 mx-2 transition-colors ${
                          s < step ? 'bg-blue-600' : 'bg-slate-200'
                        }`}
                      />
                    )}
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-2 text-xs text-slate-600">
                <span>Cliente & Veículo</span>
                <span>Datas & Valores</span>
                <span>Revisão</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Step 1: Cliente e Veículo */}
              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="input-label">Cliente *</label>
                    <select
                      value={formData.cliente_id}
                      onChange={(e) => setFormData({ ...formData, cliente_id: e.target.value })}
                      className="input-field"
                    >
                      <option value="">Selecione um cliente</option>
                      {clientes?.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nome}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="input-label">Veículo *</label>
                    <select
                      value={formData.veiculo_id}
                      onChange={(e) => setFormData({ ...formData, veiculo_id: e.target.value })}
                      className="input-field"
                    >
                      <option value="">Selecione um veículo</option>
                      {veiculos?.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.placa} - {v.marca} {v.modelo}
                        </option>
                      ))}
                    </select>
                  </div>

                  {clienteInfo && veiculoInfo && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                      <p className="text-sm text-blue-900">
                        <strong>Resumo:</strong> {clienteInfo.nome} alugando {veiculoInfo.marca} {veiculoInfo.modelo}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Step 2: Datas e Valor */}
              {step === 2 && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="input-label">Data Início *</label>
                      <input
                        type="date"
                        value={formData.data_inicio}
                        onChange={(e) => handleDateChange('data_inicio', e.target.value)}
                        className="input-field"
                      />
                    </div>

                    <div>
                      <label className="input-label">Data Fim *</label>
                      <input
                        type="date"
                        value={formData.data_fim}
                        onChange={(e) => handleDateChange('data_fim', e.target.value)}
                        className="input-field"
                      />
                    </div>
                  </div>

                  {dateError && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex gap-2">
                      <AlertCircle size={18} className="text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-red-800">{dateError}</p>
                    </div>
                  )}

                  <div>
                    <label className="input-label">Quilometragem Inicial</label>
                    <input
                      type="number"
                      value={formData.quilometragem_inicial}
                      onChange={(e) =>
                        setFormData({ ...formData, quilometragem_inicial: parseInt(e.target.value) || 0 })
                      }
                      min="0"
                      className="input-field"
                    />
                  </div>

                  <div>
                    <label className="input-label">Valor da Diária *</label>
                    <input
                      type="number"
                      value={formData.valor_diaria}
                      onChange={(e) => setFormData({ ...formData, valor_diaria: parseFloat(e.target.value) || 0 })}
                      step="0.01"
                      min="0"
                      className="input-field"
                    />
                  </div>

                  {formData.data_inicio && formData.data_fim && !dateError && (
                    <div className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-600">Período:</span>
                        <span className="font-semibold text-slate-900">{dias} dias</span>
                      </div>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-slate-600">Valor/Dia:</span>
                        <span className="font-semibold text-slate-900">{formatCurrency(formData.valor_diaria)}</span>
                      </div>
                      <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-200">
                        <span className="font-medium text-slate-900">Total:</span>
                        <span className="font-bold text-blue-600 text-lg">{formatCurrency(valor_total)}</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Step 3: Review */}
              {step === 3 && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="card bg-slate-50">
                      <div className="flex items-start gap-3">
                        <Users className="text-blue-600 flex-shrink-0 mt-1" size={20} />
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-600">Cliente</p>
                          <p className="font-semibold text-slate-900 mt-1">{clienteInfo?.nome}</p>
                        </div>
                      </div>
                    </div>

                    <div className="card bg-slate-50">
                      <div className="flex items-start gap-3">
                        <FileText className="text-green-600 flex-shrink-0 mt-1" size={20} />
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-600">Veículo</p>
                          <p className="font-semibold text-slate-900 mt-1">
                            {veiculoInfo?.marca} {veiculoInfo?.modelo}
                          </p>
                          <p className="text-sm text-slate-600">{veiculoInfo?.placa}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="card bg-slate-50">
                      <div className="flex items-start gap-3">
                        <Calendar className="text-purple-600 flex-shrink-0 mt-1" size={20} />
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-600">Início</p>
                          <p className="font-semibold text-slate-900 mt-1">{formatDate(formData.data_inicio)}</p>
                        </div>
                      </div>
                    </div>

                    <div className="card bg-slate-50">
                      <div className="flex items-start gap-3">
                        <Clock className="text-orange-600 flex-shrink-0 mt-1" size={20} />
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-600">Fim</p>
                          <p className="font-semibold text-slate-900 mt-1">{formatDate(formData.data_fim)}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="card bg-blue-50 border border-blue-200">
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-700">Período</span>
                        <span className="font-semibold text-slate-900">{dias} dias</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-700">Valor/Dia</span>
                        <span className="font-semibold text-slate-900">{formatCurrency(formData.valor_diaria)}</span>
                      </div>
                      <div className="border-t border-blue-200 pt-3 flex justify-between items-center">
                        <span className="font-bold text-blue-900">Valor Total</span>
                        <span className="font-bold text-blue-600 text-xl">{formatCurrency(valor_total)}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="input-label">Observações</label>
                    <textarea
                      value={formData.observacoes}
                      onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                      className="input-field"
                      rows={3}
                      placeholder="Adicione observações sobre o contrato (opcional)"
                    />
                  </div>
                </div>
              )}

            {/* Modal Footer */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <div className="flex gap-2">
                {step > 1 && (
                  <button
                    type="button"
                    onClick={handlePrevStep}
                    className="btn-secondary btn-sm flex items-center gap-2"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    Voltar
                  </button>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  Cancelar
                </button>

                {step < 3 ? (
                  <button
                    type="button"
                    onClick={handleNextStep}
                    className="btn-primary flex items-center gap-2"
                  >
                    Próximo
                    <ChevronRight size={18} />
                  </button>
                ) : (
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    {createMutation.isPending || updateMutation.isPending ? 'Processando...' : 'Confirmar'}
                  </button>
                )}
              </div>
            </div>
            </form>
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
              <h3 className="text-lg font-display font-bold text-slate-900">Deletar Contrato</h3>
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
              <div className="flex items-start gap-4">
                <div className="bg-red-100 rounded-lg p-3">
                  <AlertCircle className="text-red-600" size={24} />
                </div>
                <div className="flex-1">
                  <p className="text-slate-600 text-sm">Esta ação não pode ser desfeita. O contrato será removido do sistema.</p>
                </div>
              </div>
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

export default Contratos
