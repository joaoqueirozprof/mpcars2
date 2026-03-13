import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Shield, AlertCircle, X, CreditCard } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import CurrencyInput from '@/components/shared/CurrencyInput'
import StatusBadge from '@/components/shared/StatusBadge'
import { Seguro, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { formatCurrency, formatDate, isExpiringSoon, isExpired } from '@/lib/utils'

interface ParcelaForm {
  valor: number
  vencimento: string
}

const Seguros: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingInsurance, setEditingInsurance] = useState<Seguro | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [parcelar, setParcelar] = useState(false)
  const [qtdParcelas, setQtdParcelas] = useState(1)
  const [parcelas, setParcelas] = useState<ParcelaForm[]>([])
  const [formData, setFormData] = useState({
    veiculo_id: '',
    seguradora: '',
    numero_apolice: '',
    tipo_seguro: 'completo',
    data_inicio: '',
    data_fim: '',
    valor: 0,
    valor_franquia: 0,
  })

  // Auto-generate parcelas when toggling or changing qtd/valor
  useEffect(() => {
    if (parcelar && qtdParcelas > 0 && formData.valor > 0) {
      const valorParcela = parseFloat((formData.valor / qtdParcelas).toFixed(2))
      const startDate = formData.data_inicio ? new Date(formData.data_inicio + 'T12:00:00') : new Date()
      const newParcelas: ParcelaForm[] = []
      for (let i = 0; i < qtdParcelas; i++) {
        const d = new Date(startDate)
        d.setMonth(d.getMonth() + i)
        newParcelas.push({
          valor: i === qtdParcelas - 1 ? parseFloat((formData.valor - valorParcela * (qtdParcelas - 1)).toFixed(2)) : valorParcela,
          vencimento: d.toISOString().split('T')[0],
        })
      }
      setParcelas(newParcelas)
    } else if (!parcelar) {
      setParcelas([])
    }
  }, [parcelar, qtdParcelas, formData.valor, formData.data_inicio])

  const { data, isLoading } = useQuery({
    queryKey: ['seguros', pagination, statusFilter, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/seguros', {
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

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/veiculos', { params: { limit: 1000 } })
      return (data.data || []).map((v: any) => ({
        ...v,
        quilometragem: v.km_atual || 0,
        cor: v.cor || '',
      }))
    },
  })

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/seguros', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seguros'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Seguro criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao criar seguro')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: any) => api.patch(`/seguros/${editingInsurance?.id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seguros'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Seguro atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar seguro')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/seguros/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seguros'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Seguro deletado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao deletar seguro')
    },
  })

  const resetForm = () => {
    setFormData({
      veiculo_id: '',
      seguradora: '',
      numero_apolice: '',
      tipo_seguro: 'completo',
      data_inicio: '',
      data_fim: '',
      valor: 0,
      valor_franquia: 0,
    })
    setEditingInsurance(null)
    setParcelar(false)
    setQtdParcelas(1)
    setParcelas([])
  }

  const handleOpenModal = (insurance?: Seguro) => {
    if (insurance) {
      setEditingInsurance(insurance)
      setFormData({
        veiculo_id: insurance.veiculo_id || '',
        seguradora: insurance.seguradora || '',
        numero_apolice: insurance.numero_apolice || '',
        tipo_seguro: insurance.tipo_seguro || 'completo',
        data_inicio: insurance.data_inicio || '',
        data_fim: insurance.data_fim || '',
        valor: insurance.valor || 0,
        valor_franquia: insurance.valor_franquia || 0,
      })
      setParcelar(false)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.veiculo_id || !formData.seguradora || !formData.numero_apolice) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (editingInsurance) {
      updateMutation.mutate({
        seguradora: formData.seguradora,
        tipo_seguro: formData.tipo_seguro,
        data_fim: formData.data_fim,
        valor: formData.valor,
      })
    } else {
      const payload: any = {
        veiculo_id: parseInt(formData.veiculo_id as any),
        seguradora: formData.seguradora,
        numero_apolice: formData.numero_apolice,
        tipo_seguro: formData.tipo_seguro,
        data_inicio: formData.data_inicio,
        data_fim: formData.data_fim,
        valor: formData.valor,
        valor_franquia: formData.valor_franquia,
        qtd_parcelas: parcelar ? qtdParcelas : 1,
      }

      if (parcelar && parcelas.length > 0) {
        payload.parcelas = parcelas.map(p => ({
          valor: p.valor,
          vencimento: p.vencimento,
        }))
      }

      createMutation.mutate(payload)
    }
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setPagination({ ...pagination, page: 1 })
  }

  const updateParcela = (index: number, field: keyof ParcelaForm, value: any) => {
    const updated = [...parcelas]
    updated[index] = { ...updated[index], [field]: field === 'valor' ? parseFloat(value) || 0 : value }
    setParcelas(updated)
  }

  const columns = [
    {
      key: 'numero_apolice' as const,
      label: 'Apólice',
      sortable: true,
      width: '15%',
      render: (apolice: string) => <span className="font-medium text-slate-900">{apolice}</span>,
    },
    {
      key: 'veiculo_id' as const,
      label: 'Veículo',
      render: (_: any, row: any) => <span className="text-slate-900">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'seguradora' as const,
      label: 'Seguradora',
      sortable: true,
      render: (seguradora: string) => <span className="text-slate-900">{seguradora}</span>,
    },
    {
      key: 'valor' as const,
      label: 'Valor Total',
      render: (value: number) => <span className="font-semibold text-slate-900">{formatCurrency(value)}</span>,
    },
    {
      key: 'data_fim' as const,
      label: 'Vencimento',
      render: (date: string) => (
        <div className="flex items-center gap-2">
          <span className="text-slate-700">{formatDate(date)}</span>
          {isExpired(date) && <span className="badge-danger text-xs px-2 py-1">Vencido</span>}
          {isExpiringSoon(date) && !isExpired(date) && <span className="badge-warning text-xs px-2 py-1">Vence em breve</span>}
        </div>
      ),
    },
    {
      key: 'id' as const,
      label: 'Ações',
      render: (_: any, row: Seguro) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleOpenModal(row)}
            className="btn-icon p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
            title="Editar"
          >
            <Edit size={16} />
          </button>
          <button
            onClick={() => setDeleteConfirm({ isOpen: true, id: row.id })}
            className="btn-icon p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Deletar"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ),
    },
  ]

  const isLoaded = !isLoading && data?.data
  const isEmpty = isLoaded && data.data.length === 0

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-2">
              <Shield className="text-green-600" size={32} />
              Seguros
            </h1>
            <p className="page-subtitle">Gerenciamento de seguros dos veículos da frota</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
            <Plus size={20} />
            Novo Seguro
          </button>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex gap-2 flex-wrap">
            {['todos', 'ativo', 'vencendo', 'vencido'].map((status) => (
              <button
                key={status}
                onClick={() => handleStatusFilter(status)}
                className={`filter-tab ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos' ? 'Todos' : status === 'vencendo' ? 'Vencendo em breve' : status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex-1">
            <input
              type="text"
              placeholder="Buscar por apólice ou seguradora..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setPagination({ ...pagination, page: 1 })
              }}
              className="input-field w-full"
            />
          </div>
        </div>

        <div className="card">
          {isEmpty ? (
            <div className="empty-state py-12">
              <div className="empty-state-icon bg-green-50 mb-4">
                <Shield className="text-green-600" size={40} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Nenhum seguro encontrado</h3>
              <p className="text-slate-600 mb-4">Comece adicionando o primeiro seguro para seus veículos</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="inline mr-2" />
                Novo Seguro
              </button>
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={data?.data || []}
              isLoading={isLoading}
              pagination={{
                page: pagination.page,
                limit: pagination.limit,
                total: data?.total || 0,
                onPageChange: (page) => setPagination({ ...pagination, page }),
              }}
            />
          )}
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-lg w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingInsurance ? 'Editar Seguro' : 'Novo Seguro'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn-icon"
                title="Fechar"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)] space-y-4">
              <div>
                <label className="input-label">Veículo *</label>
                <select
                  value={formData.veiculo_id}
                  onChange={(e) => setFormData({ ...formData, veiculo_id: e.target.value })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="">Selecione um veículo</option>
                  {veiculos?.map((v: any) => (
                    <option key={v.id} value={v.id}>
                      {v.placa} - {v.marca} {v.modelo}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="input-label">Seguradora *</label>
                <input
                  type="text"
                  value={formData.seguradora}
                  onChange={(e) => setFormData({ ...formData, seguradora: e.target.value })}
                  className="input-field"
                  placeholder="Nome da seguradora"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Nº Apólice *</label>
                  <input
                    type="text"
                    value={formData.numero_apolice}
                    onChange={(e) => setFormData({ ...formData, numero_apolice: e.target.value })}
                    className="input-field"
                    placeholder="Número da apólice"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
                <div>
                  <label className="input-label">Tipo Seguro</label>
                  <select
                    value={formData.tipo_seguro}
                    onChange={(e) => setFormData({ ...formData, tipo_seguro: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    <option value="completo">Completo</option>
                    <option value="terceiros">Terceiros</option>
                    <option value="incendio_roubo">Incêndio e Roubo</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Data Início</label>
                  <input
                    type="date"
                    value={formData.data_inicio}
                    onChange={(e) => setFormData({ ...formData, data_inicio: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
                <div>
                  <label className="input-label">Data Fim</label>
                  <input
                    type="date"
                    value={formData.data_fim}
                    onChange={(e) => setFormData({ ...formData, data_fim: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <CurrencyInput
                  label="Valor Total *"
                  value={formData.valor}
                  onChange={(valor) => setFormData({ ...formData, valor })}
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
                <CurrencyInput
                  label="Valor Franquia"
                  value={formData.valor_franquia}
                  onChange={(valor_franquia) => setFormData({ ...formData, valor_franquia })}
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              {/* Parcelas section - only show on create */}
              {!editingInsurance && (
                <div className="border-t border-slate-200 pt-4 mt-4">
                  <div className="flex items-center gap-3 mb-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={parcelar}
                        onChange={(e) => setParcelar(e.target.checked)}
                        className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                        disabled={createMutation.isPending}
                      />
                      <span className="text-sm font-semibold text-slate-700 flex items-center gap-1">
                        <CreditCard size={16} />
                        Parcelar pagamento
                      </span>
                    </label>
                  </div>

                  {parcelar && (
                    <div className="space-y-3 bg-slate-50 p-4 rounded-lg">
                      <div>
                        <label className="input-label">Quantidade de Parcelas</label>
                        <input
                          type="number"
                          value={qtdParcelas}
                          onChange={(e) => setQtdParcelas(Math.max(1, parseInt(e.target.value) || 1))}
                          min="1"
                          max="48"
                          className="input-field w-32"
                          disabled={createMutation.isPending}
                        />
                      </div>

                      {parcelas.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Parcelas (edite datas e valores se necessário)</p>
                          <div className="max-h-48 overflow-y-auto space-y-2">
                            {parcelas.map((p, i) => (
                              <div key={i} className="flex items-center gap-2 bg-white p-2 rounded border border-slate-200">
                                <span className="text-xs font-bold text-slate-500 w-8">{i + 1}x</span>
                                <input
                                  type="number"
                                  value={p.valor}
                                  onChange={(e) => updateParcela(i, 'valor', e.target.value)}
                                  step="0.01"
                                  min="0"
                                  className="input-field flex-1 text-sm py-1.5"
                                  placeholder="Valor"
                                />
                                <input
                                  type="date"
                                  value={p.vencimento}
                                  onChange={(e) => updateParcela(i, 'vencimento', e.target.value)}
                                  className="input-field flex-1 text-sm py-1.5"
                                />
                              </div>
                            ))}
                          </div>
                          <p className="text-xs text-slate-500">
                            Total parcelas: {formatCurrency(parcelas.reduce((s, p) => s + p.valor, 0))}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
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
                {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingInsurance ? 'Atualizar' : 'Criar'} Seguro
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Seguro"
        message="Tem certeza que deseja deletar este seguro? Esta ação não pode ser desfeita."
        confirmText="Deletar"
        cancelText="Cancelar"
        isDanger={true}
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)}
        onCancel={() => setDeleteConfirm({ isOpen: false })}
      />
    </AppLayout>
  )
}

export default Seguros
