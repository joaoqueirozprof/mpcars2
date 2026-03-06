import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Shield, AlertCircle, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import StatusBadge from '@/components/shared/StatusBadge'
import { Seguro, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { formatCurrency, formatDate, isExpiringSoon, isExpired } from '@/lib/utils'

const Seguros: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingInsurance, setEditingInsurance] = useState<Seguro | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [formData, setFormData] = useState({
    veiculo_id: '',
    seguradora: '',
    numero_apolice: '',
    data_inicio: '',
    data_fim: '',
    valor_mensal: 0,
    cobertura: '',
  })

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
    mutationFn: (formData: any) => api.post('/seguros', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seguros'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Seguro criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar seguro')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/seguros/${editingInsurance?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['seguros'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Seguro atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar seguro')
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
      toast.error(error.response?.data?.message || 'Erro ao deletar seguro')
    },
  })

  const resetForm = () => {
    setFormData({
      veiculo_id: '',
      seguradora: '',
      numero_apolice: '',
      data_inicio: '',
      data_fim: '',
      valor_mensal: 0,
      cobertura: '',
    })
    setEditingInsurance(null)
  }

  const handleOpenModal = (insurance?: Seguro) => {
    if (insurance) {
      setEditingInsurance(insurance)
      setFormData(insurance)
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
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setPagination({ ...pagination, page: 1 })
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
      key: 'valor_mensal' as const,
      label: 'Valor/Mês',
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
              placeholder="Buscar por apólice ou veículo..."
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
          <div className="modal-content max-w-md w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
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
                  {veiculos?.map((v) => (
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

              <div>
                <label className="input-label">Número da Apólice *</label>
                <input
                  type="text"
                  value={formData.numero_apolice}
                  onChange={(e) => setFormData({ ...formData, numero_apolice: e.target.value })}
                  className="input-field"
                  placeholder="Número da apólice"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
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
                  <label className="input-label">Data Fim *</label>
                  <input
                    type="date"
                    value={formData.data_fim}
                    onChange={(e) => setFormData({ ...formData, data_fim: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              <div>
                <label className="input-label">Valor Mensal *</label>
                <input
                  type="number"
                  value={formData.valor_mensal}
                  onChange={(e) => setFormData({ ...formData, valor_mensal: parseFloat(e.target.value) })}
                  step="0.01"
                  min="0"
                  className="input-field"
                  placeholder="0,00"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              <div>
                <label className="input-label">Cobertura</label>
                <textarea
                  value={formData.cobertura}
                  onChange={(e) => setFormData({ ...formData, cobertura: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Descrição da cobertura"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
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
