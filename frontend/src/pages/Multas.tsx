import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, AlertTriangle, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import StatusBadge from '@/components/shared/StatusBadge'
import { Multa, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { formatCurrency, formatDate } from '@/lib/utils'

const Multas: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingFine, setEditingFine] = useState<Multa | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [formData, setFormData] = useState({
    veiculo_id: '',
    numero_infracao: '',
    data_infracao: '',
    valor: 0,
    data_vencimento: '',
    data_pagamento: '',
    status: 'pendente' as 'pendente' | 'pago' | 'vencido',
    descricao: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['multas', pagination, statusFilter, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Multa>>('/multas', {
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
    mutationFn: (formData: any) => api.post('/multas', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['multas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Multa criada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar multa')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/multas/${editingFine?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['multas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Multa atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar multa')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/multas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['multas'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Multa deletada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar multa')
    },
  })

  const resetForm = () => {
    setFormData({
      veiculo_id: '',
      numero_infracao: '',
      data_infracao: '',
      valor: 0,
      data_vencimento: '',
      data_pagamento: '',
      status: 'pendente',
      descricao: '',
    })
    setEditingFine(null)
  }

  const handleOpenModal = (fine?: Multa) => {
    if (fine) {
      setEditingFine(fine)
      setFormData(fine)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.veiculo_id || !formData.numero_infracao || formData.valor <= 0) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (editingFine) {
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
      key: 'numero_infracao' as const,
      label: 'Número Infração',
      sortable: true,
      width: '15%',
      render: (numero: string) => <span className="font-medium text-slate-900">{numero}</span>,
    },
    {
      key: 'veiculo_id' as const,
      label: 'Veículo',
      render: (_: any, row: any) => <span className="text-slate-900">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'data_infracao' as const,
      label: 'Data Infração',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'valor' as const,
      label: 'Valor',
      render: (value: number) => <span className="font-semibold text-red-600">{formatCurrency(value)}</span>,
    },
    {
      key: 'data_vencimento' as const,
      label: 'Vencimento',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'status' as const,
      label: 'Status',
      render: (status: string) => (
        <div className="flex items-center gap-1">
          {status === 'pago' && <span className="badge-success">Pago</span>}
          {status === 'pendente' && <span className="badge-warning">Pendente</span>}
          {status === 'vencido' && <span className="badge-danger">Vencido</span>}
        </div>
      ),
    },
    {
      key: 'id' as const,
      label: 'Ações',
      render: (_: any, row: Multa) => (
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
              <AlertTriangle className="text-red-600" size={32} />
              Multas
            </h1>
            <p className="page-subtitle">Gerenciamento de multas de trânsito e infrações</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
            <Plus size={20} />
            Nova Multa
          </button>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex gap-2 flex-wrap">
            {['todos', 'pendente', 'pago', 'vencido'].map((status) => (
              <button
                key={status}
                onClick={() => handleStatusFilter(status)}
                className={`filter-tab ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos' ? 'Todos' : status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex-1">
            <input
              type="text"
              placeholder="Buscar por número de infração ou placa..."
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
              <div className="empty-state-icon bg-red-50 mb-4">
                <AlertTriangle className="text-red-600" size={40} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Nenhuma multa registrada</h3>
              <p className="text-slate-600 mb-4">Esperamos que não haja infrações, mas quando houver, registre aqui</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="inline mr-2" />
                Nova Multa
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
                {editingFine ? 'Editar Multa' : 'Nova Multa'}
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
                <label className="input-label">Número da Infração *</label>
                <input
                  type="text"
                  value={formData.numero_infracao}
                  onChange={(e) => setFormData({ ...formData, numero_infracao: e.target.value })}
                  className="input-field"
                  placeholder="Número da infração"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Data Infração</label>
                  <input
                    type="date"
                    value={formData.data_infracao}
                    onChange={(e) => setFormData({ ...formData, data_infracao: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Valor *</label>
                  <input
                    type="number"
                    value={formData.valor}
                    onChange={(e) => setFormData({ ...formData, valor: parseFloat(e.target.value) })}
                    step="0.01"
                    min="0"
                    className="input-field"
                    placeholder="0,00"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Data Vencimento</label>
                  <input
                    type="date"
                    value={formData.data_vencimento}
                    onChange={(e) => setFormData({ ...formData, data_vencimento: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Data Pagamento</label>
                  <input
                    type="date"
                    value={formData.data_pagamento}
                    onChange={(e) => setFormData({ ...formData, data_pagamento: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              <div>
                <label className="input-label">Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="pendente">Pendente</option>
                  <option value="pago">Pago</option>
                  <option value="vencido">Vencido</option>
                </select>
              </div>

              <div>
                <label className="input-label">Descrição da Infração</label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Descreva a infração cometida"
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
                {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingFine ? 'Atualizar' : 'Criar'} Multa
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Multa"
        message="Tem certeza que deseja deletar esta multa? Esta ação não pode ser desfeita."
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

export default Multas
