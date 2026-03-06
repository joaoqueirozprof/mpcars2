import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Calendar, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import StatusBadge from '@/components/shared/StatusBadge'
import { Reserva, Cliente, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { formatDate, calculateDays } from '@/lib/utils'

const Reservas: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingReservation, setEditingReservation] = useState<Reserva | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [formData, setFormData] = useState({
    cliente_id: '',
    veiculo_id: '',
    data_inicio: '',
    data_fim: '',
    status: 'ativa' as 'ativa' | 'cancelada' | 'convertida',
    observacoes: '',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['reservas', pagination, statusFilter],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/reservas', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
        },
      })
      return data
    },
  })

  const { data: clientes } = useQuery({
    queryKey: ['clientes-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/clientes', { params: { limit: 1000 } })
      return data.data || []
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
      })).filter((v) => v.status === 'disponivel')
    },
  })

  const createMutation = useMutation({
    mutationFn: (formData: any) => api.post('/reservas', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reservas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Reserva criada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar reserva')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/reservas/${editingReservation?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reservas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Reserva atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar reserva')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/reservas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reservas'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Reserva deletada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar reserva')
    },
  })

  const resetForm = () => {
    setFormData({
      cliente_id: '',
      veiculo_id: '',
      data_inicio: '',
      data_fim: '',
      status: 'ativa',
      observacoes: '',
    })
    setEditingReservation(null)
  }

  const handleOpenModal = (reservation?: Reserva) => {
    if (reservation) {
      setEditingReservation(reservation)
      setFormData(reservation)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.cliente_id || !formData.veiculo_id || !formData.data_inicio || !formData.data_fim) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (new Date(formData.data_fim) <= new Date(formData.data_inicio)) {
      toast.error('Data fim deve ser posterior à data início')
      return
    }

    if (editingReservation) {
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
      key: 'cliente_id' as const,
      label: 'Cliente',
      render: (_: any, row: any) => <span className="text-slate-900 font-medium">{row.cliente?.nome || '-'}</span>,
    },
    {
      key: 'veiculo_id' as const,
      label: 'Veículo',
      render: (_: any, row: any) => <span className="text-slate-900">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'data_inicio' as const,
      label: 'Data Início',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'data_fim' as const,
      label: 'Data Fim',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'id' as const,
      label: 'Período (dias)',
      render: (_: any, row: any) => {
        if (!row.data_inicio || !row.data_fim) return '-'
        const days = calculateDays(row.data_inicio, row.data_fim)
        return <span className="font-semibold text-slate-900">{days}d</span>
      },
    },
    {
      key: 'status' as const,
      label: 'Status',
      render: (status: string) => (
        <div className="flex items-center gap-1">
          {status === 'ativa' && <span className="badge-info text-xs px-2 py-1">Ativa</span>}
          {status === 'cancelada' && <span className="badge-danger text-xs px-2 py-1">Cancelada</span>}
          {status === 'convertida' && <span className="badge-success text-xs px-2 py-1">Convertida</span>}
        </div>
      ),
    },
    {
      key: 'id_action' as const,
      label: 'Ações',
      render: (_: any, row: Reserva) => (
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
              <Calendar className="text-cyan-600" size={32} />
              Reservas
            </h1>
            <p className="page-subtitle">Gerenciamento de reservas de veículos com períodos definidos</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
            <Plus size={20} />
            Nova Reserva
          </button>
        </div>

        <div className="flex gap-2 flex-wrap">
          {['todos', 'ativa', 'cancelada', 'convertida'].map((status) => (
            <button
              key={status}
              onClick={() => handleStatusFilter(status)}
              className={`filter-tab ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
            >
              {status === 'todos' ? 'Todas' : status === 'ativa' ? 'Ativas' : status === 'cancelada' ? 'Canceladas' : 'Convertidas'}
            </button>
          ))}
        </div>

        <div className="card">
          {isEmpty ? (
            <div className="empty-state py-12">
              <div className="empty-state-icon bg-cyan-50 mb-4">
                <Calendar className="text-cyan-600" size={40} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Nenhuma reserva encontrada</h3>
              <p className="text-slate-600 mb-4">Comece criando a primeira reserva para seus clientes</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="inline mr-2" />
                Nova Reserva
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
                {editingReservation ? 'Editar Reserva' : 'Nova Reserva'}
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
                <label className="input-label">Cliente *</label>
                <select
                  value={formData.cliente_id}
                  onChange={(e) => setFormData({ ...formData, cliente_id: e.target.value })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
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

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Data Início *</label>
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

              {formData.data_inicio && formData.data_fim && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p className="text-sm text-blue-900">
                    Período: <span className="font-semibold">{calculateDays(formData.data_inicio, formData.data_fim)} dias</span>
                  </p>
                </div>
              )}

              <div>
                <label className="input-label">Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="ativa">Ativa</option>
                  <option value="cancelada">Cancelada</option>
                  <option value="convertida">Convertida</option>
                </select>
              </div>

              <div>
                <label className="input-label">Observações</label>
                <textarea
                  value={formData.observacoes}
                  onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Observações sobre a reserva"
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
                {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingReservation ? 'Atualizar' : 'Criar'} Reserva
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Reserva"
        message="Tem certeza que deseja deletar esta reserva? Esta ação não pode ser desfeita."
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

export default Reservas
