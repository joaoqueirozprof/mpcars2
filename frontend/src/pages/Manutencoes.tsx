import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Wrench, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import StatusBadge from '@/components/shared/StatusBadge'
import { Manutencao, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { formatCurrency, formatDate } from '@/lib/utils'

const Manutencoes: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingMaintenance, setEditingMaintenance] = useState<Manutencao | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [typeFilter, setTypeFilter] = useState<string>('todos')
  const [formData, setFormData] = useState({
    veiculo_id: '',
    data_manutencao: new Date().toISOString().split('T')[0],
    tipo: 'preventiva' as 'preventiva' | 'corretiva',
    descricao: '',
    valor: 0,
    oficina: '',
    quilometragem: 0,
    status: 'pendente' as 'pendente' | 'em_progresso' | 'concluida' | 'cancelada',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['manutencoes', pagination, statusFilter, typeFilter],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/manutencoes', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
          tipo: typeFilter !== 'todos' ? typeFilter : undefined,
        },
      })
      return data
    },
  })

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Veiculo>>('/veiculos', { params: { limit: 1000 } })
      return data.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (formData: any) => api.post('/manutencoes', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Manutenção criada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar manutenção')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/manutencoes/${editingMaintenance?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Manutenção atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar manutenção')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/manutencoes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Manutenção deletada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar manutenção')
    },
  })

  const resetForm = () => {
    setFormData({
      veiculo_id: '',
      data_manutencao: new Date().toISOString().split('T')[0],
      tipo: 'preventiva',
      descricao: '',
      valor: 0,
      oficina: '',
      quilometragem: 0,
      status: 'pendente',
    })
    setEditingMaintenance(null)
  }

  const handleOpenModal = (maintenance?: Manutencao) => {
    if (maintenance) {
      setEditingMaintenance(maintenance)
      setFormData(maintenance)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.veiculo_id || !formData.descricao || formData.valor <= 0) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (editingMaintenance) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setPagination({ ...pagination, page: 1 })
  }

  const handleTypeFilter = (type: string) => {
    setTypeFilter(type)
    setPagination({ ...pagination, page: 1 })
  }

  const columns = [
    {
      key: 'veiculo_id' as const,
      label: 'Veículo',
      render: (_: any, row: any) => <span className="text-slate-900">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'tipo' as const,
      label: 'Tipo',
      render: (tipo: string) => (
        <div className="flex items-center gap-1">
          {tipo === 'preventiva' ? (
            <span className="badge-info text-xs px-2 py-1">Preventiva</span>
          ) : (
            <span className="badge-danger text-xs px-2 py-1">Corretiva</span>
          )}
        </div>
      ),
    },
    {
      key: 'data_manutencao' as const,
      label: 'Data',
      render: (date: string) => <span className="text-slate-700">{formatDate(date)}</span>,
    },
    {
      key: 'oficina' as const,
      label: 'Oficina',
      render: (oficina: string) => <span className="text-slate-700">{oficina || '-'}</span>,
    },
    {
      key: 'valor' as const,
      label: 'Valor',
      render: (value: number) => <span className="font-semibold text-slate-900">{formatCurrency(value)}</span>,
    },
    {
      key: 'status' as const,
      label: 'Status',
      render: (status: string) => (
        <div className="flex items-center gap-1">
          {status === 'pendente' && <span className="badge-warning text-xs px-2 py-1">Pendente</span>}
          {status === 'em_progresso' && <span className="badge-info text-xs px-2 py-1">Em Progresso</span>}
          {status === 'concluida' && <span className="badge-success text-xs px-2 py-1">Concluída</span>}
          {status === 'cancelada' && <span className="badge-danger text-xs px-2 py-1">Cancelada</span>}
        </div>
      ),
    },
    {
      key: 'id' as const,
      label: 'Ações',
      render: (_: any, row: Manutencao) => (
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
              <Wrench className="text-purple-600" size={32} />
              Manutenções
            </h1>
            <p className="page-subtitle">Gerenciamento de manutenção preventiva e corretiva da frota</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
            <Plus size={20} />
            Nova Manutenção
          </button>
        </div>

        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex gap-2 flex-wrap">
            {['todos', 'pendente', 'em_progresso', 'concluida', 'cancelada'].map((status) => (
              <button
                key={status}
                onClick={() => handleStatusFilter(status)}
                className={`filter-tab text-sm ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos'
                  ? 'Todos'
                  : status === 'em_progresso'
                    ? 'Em Andamento'
                    : status === 'concluida'
                      ? 'Concluídas'
                      : status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
          <div className="flex gap-2 flex-wrap">
            {['todos', 'preventiva', 'corretiva'].map((type) => (
              <button
                key={type}
                onClick={() => handleTypeFilter(type)}
                className={`filter-tab text-sm ${typeFilter === type ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {type === 'todos' ? 'Todos os Tipos' : type === 'preventiva' ? 'Preventiva' : 'Corretiva'}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          {isEmpty ? (
            <div className="empty-state py-12">
              <div className="empty-state-icon bg-purple-50 mb-4">
                <Wrench className="text-purple-600" size={40} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Nenhuma manutenção registrada</h3>
              <p className="text-slate-600 mb-4">Registre a manutenção dos veículos para acompanhar o histórico</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="inline mr-2" />
                Nova Manutenção
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
                {editingMaintenance ? 'Editar Manutenção' : 'Nova Manutenção'}
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
                <label className="input-label">Tipo de Manutenção *</label>
                <select
                  value={formData.tipo}
                  onChange={(e) => setFormData({ ...formData, tipo: e.target.value as any })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="preventiva">Preventiva</option>
                  <option value="corretiva">Corretiva</option>
                </select>
              </div>

              <div>
                <label className="input-label">Data da Manutenção</label>
                <input
                  type="date"
                  value={formData.data_manutencao}
                  onChange={(e) => setFormData({ ...formData, data_manutencao: e.target.value })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              <div>
                <label className="input-label">Descrição *</label>
                <textarea
                  value={formData.descricao}
                  onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Descreva o trabalho realizado ou a ser realizado"
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

              <div>
                <label className="input-label">Oficina</label>
                <input
                  type="text"
                  value={formData.oficina}
                  onChange={(e) => setFormData({ ...formData, oficina: e.target.value })}
                  className="input-field"
                  placeholder="Nome da oficina"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
              </div>

              <div>
                <label className="input-label">Quilometragem</label>
                <input
                  type="number"
                  value={formData.quilometragem}
                  onChange={(e) => setFormData({ ...formData, quilometragem: parseInt(e.target.value) })}
                  min="0"
                  className="input-field"
                  placeholder="Quilometragem do veículo"
                  disabled={createMutation.isPending || updateMutation.isPending}
                />
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
                  <option value="em_progresso">Em Progresso</option>
                  <option value="concluida">Concluída</option>
                  <option value="cancelada">Cancelada</option>
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
                {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingMaintenance ? 'Atualizar' : 'Criar'} Manutenção
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Manutenção"
        message="Tem certeza que deseja deletar este registro de manutenção? Esta ação não pode ser desfeita."
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

export default Manutencoes
