import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Edit2,
  Trash2,
  Search,
  Car,
  AlertCircle,
  X,
  CheckCircle,
  AlertTriangle,
  Wrench,
  XCircle,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import { Veiculo } from '@/types'
import toast from 'react-hot-toast'

const Veiculos: React.FC = () => {
  const queryClient = useQueryClient()
  const [searchTerm, setSearchTerm] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingVehicle, setEditingVehicle] = useState<Veiculo | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string; placa?: string }>({
    isOpen: false,
  })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [formData, setFormData] = useState({
    placa: '',
    marca: '',
    modelo: '',
    ano: new Date().getFullYear(),
    cor: '',
    quilometragem: 0,
    status: 'disponivel' as const,
    valor_aquisicao: 0,
    data_compra: '',
    observacoes: '',
  })

  const currentYear = new Date().getFullYear()

  // Fetch all vehicles
  const { data: vehiclesData, isLoading: isLoadingVehicles } = useQuery({
    queryKey: ['veiculos'],
    queryFn: async () => {
      const { data } = await api.get<{ data: Veiculo[]; total: number }>('/veiculos', {
        params: { limit: 1000 },
      })
      return data.data || []
    },
  })

  // Filter vehicles based on status and search
  const filteredVehicles = useMemo(() => {
    let filtered = vehiclesData || []

    if (statusFilter !== 'todos') {
      filtered = filtered.filter((v) => v.status === statusFilter)
    }

    if (searchTerm.trim()) {
      const search = searchTerm.toLowerCase()
      filtered = filtered.filter(
        (v) =>
          v.placa.toLowerCase().includes(search) ||
          v.marca.toLowerCase().includes(search) ||
          v.modelo.toLowerCase().includes(search) ||
          v.cor.toLowerCase().includes(search),
      )
    }

    return filtered
  }, [vehiclesData, statusFilter, searchTerm])

  // Create vehicle mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/veiculos', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Veículo criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar veículo')
    },
  })

  // Update vehicle mutation
  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch(`/veiculos/${editingVehicle?.id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Veículo atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar veículo')
    },
  })

  // Delete vehicle mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/veiculos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Veículo deletado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar veículo')
    },
  })

  // Form validation
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!formData.placa.trim()) {
      errors.placa = 'Placa é obrigatória'
    } else if (!/^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$/.test(formData.placa)) {
      errors.placa = 'Formato inválido (ABC1234 ou ABC1D23)'
    }

    if (!formData.marca.trim()) {
      errors.marca = 'Marca é obrigatória'
    }

    if (!formData.modelo.trim()) {
      errors.modelo = 'Modelo é obrigatório'
    }

    if (!formData.ano || formData.ano < 1990 || formData.ano > currentYear + 1) {
      errors.ano = `Ano deve estar entre 1990 e ${currentYear + 1}`
    }

    if (formData.quilometragem < 0) {
      errors.quilometragem = 'Quilometragem não pode ser negativa'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  const resetForm = () => {
    setFormData({
      placa: '',
      marca: '',
      modelo: '',
      ano: currentYear,
      cor: '',
      quilometragem: 0,
      status: 'disponivel',
      valor_aquisicao: 0,
      data_compra: '',
      observacoes: '',
    })
    setFormErrors({})
    setEditingVehicle(null)
  }

  const handleOpenModal = (vehicle?: Veiculo) => {
    if (vehicle) {
      setEditingVehicle(vehicle)
      setFormData({
        placa: vehicle.placa,
        marca: vehicle.marca,
        modelo: vehicle.modelo,
        ano: vehicle.ano,
        cor: vehicle.cor,
        quilometragem: vehicle.quilometragem,
        status: vehicle.status,
        valor_aquisicao: vehicle.valor_aquisicao,
        data_compra: vehicle.data_compra,
        observacoes: vehicle.observacoes,
      })
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    if (editingVehicle) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'disponivel':
        return 'badge-success'
      case 'alugado':
        return 'badge-info'
      case 'manutencao':
        return 'badge-warning'
      case 'inativo':
        return 'badge-danger'
      default:
        return 'badge-neutral'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'disponivel':
        return <CheckCircle size={16} />
      case 'alugado':
        return <AlertTriangle size={16} />
      case 'manutencao':
        return <Wrench size={16} />
      case 'inativo':
        return <XCircle size={16} />
      default:
        return null
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'disponivel':
        return 'Disponível'
      case 'alugado':
        return 'Alugado'
      case 'manutencao':
        return 'Manutenção'
      case 'inativo':
        return 'Inativo'
      default:
        return status
    }
  }

  const statusFilters = [
    { key: 'todos', label: 'Todos' },
    { key: 'disponivel', label: 'Disponível' },
    { key: 'alugado', label: 'Alugado' },
    { key: 'manutencao', label: 'Manutenção' },
    { key: 'inativo', label: 'Inativo' },
  ]

  const isLoading = isLoadingVehicles
  const isMutating = createMutation.isPending || updateMutation.isPending

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Veículos</h1>
            <p className="page-subtitle">Gerenciar e controlar frota de veículos</p>
          </div>
          <button
            onClick={() => handleOpenModal()}
            className="btn-primary flex items-center gap-2 transition-all duration-200"
          >
            <Plus size={20} />
            Novo Veículo
          </button>
        </div>

        {/* Search Bar */}
        <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-2.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
          <Search size={18} className="text-slate-400 flex-shrink-0" />
          <input
            type="text"
            placeholder="Buscar por placa, marca, modelo ou cor..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {statusFilters.map((filter) => (
            <button
              key={filter.key}
              onClick={() => {
                setStatusFilter(filter.key)
                setSearchTerm('')
              }}
              className={`filter-tab transition-all duration-200 whitespace-nowrap ${
                statusFilter === filter.key ? 'filter-tab-active' : 'filter-tab-inactive'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="card">
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-slate-200 rounded-lg animate-pulse" />
              ))}
            </div>
          </div>
        ) : filteredVehicles.length === 0 ? (
          <div className="card">
            <div className="empty-state">
              <div className="empty-state-icon">
                <Car size={48} />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mt-4">Nenhum veículo encontrado</h3>
              <p className="text-slate-600 mt-2">
                {searchTerm
                  ? 'Nenhum veículo corresponde à sua busca'
                  : 'Comece a adicionar veículos à sua frota'}
              </p>
              {!searchTerm && (
                <button
                  onClick={() => handleOpenModal()}
                  className="btn-primary mt-6 inline-flex items-center gap-2"
                >
                  <Plus size={18} />
                  Adicionar Primeiro Veículo
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="table-header text-left">Placa</th>
                    <th className="table-header text-left">Marca/Modelo</th>
                    <th className="table-header text-left">Ano</th>
                    <th className="table-header text-left">Cor</th>
                    <th className="table-header text-left">Status</th>
                    <th className="table-header text-left">Km</th>
                    <th className="table-header text-center">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVehicles.map((vehicle) => (
                    <tr
                      key={vehicle.id}
                      className="border-b border-slate-200 hover:bg-slate-50 transition-colors duration-150"
                    >
                      <td className="table-cell">
                        <span className="font-semibold text-slate-900">{vehicle.placa}</span>
                      </td>
                      <td className="table-cell">
                        <div>
                          <p className="font-medium text-slate-900">{vehicle.marca}</p>
                          <p className="text-sm text-slate-600">{vehicle.modelo}</p>
                        </div>
                      </td>
                      <td className="table-cell">
                        <span className="text-slate-900">{vehicle.ano}</span>
                      </td>
                      <td className="table-cell">
                        <span className="text-slate-900">{vehicle.cor}</span>
                      </td>
                      <td className="table-cell">
                        <div className={`${getStatusBadgeClass(vehicle.status)} inline-flex items-center gap-2`}>
                          {getStatusIcon(vehicle.status)}
                          {getStatusLabel(vehicle.status)}
                        </div>
                      </td>
                      <td className="table-cell">
                        <span className="text-slate-900">{vehicle.quilometragem.toLocaleString('pt-BR')} km</span>
                      </td>
                      <td className="table-cell text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handleOpenModal(vehicle)}
                            className="btn-icon transition-colors duration-200"
                            title="Editar"
                          >
                            <Edit2 size={18} />
                          </button>
                          <button
                            onClick={() =>
                              setDeleteConfirm({
                                isOpen: true,
                                id: vehicle.id,
                                placa: vehicle.placa,
                              })
                            }
                            className="btn-icon bg-red-50 hover:bg-red-100 text-red-600 transition-colors duration-200"
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
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && !isMutating && setIsModalOpen(false)}>
          <div
            className="modal-content max-w-2xl w-full flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingVehicle ? 'Editar Veículo' : 'Novo Veículo'}
              </h3>
              <button
                onClick={() => !isMutating && setIsModalOpen(false)}
                className="btn-icon"
                disabled={isMutating}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Placa */}
                <div>
                  <label className="input-label">
                    Placa <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.placa}
                    onChange={(e) => setFormData({ ...formData, placa: e.target.value.toUpperCase() })}
                    placeholder="ABC1234 ou ABC1D23"
                    className={`input-field ${formErrors.placa ? 'border-red-500 focus:ring-red-500' : ''}`}
                    disabled={isMutating}
                  />
                  {formErrors.placa && <p className="text-sm text-red-500 mt-2">{formErrors.placa}</p>}
                </div>

                {/* Marca */}
                <div>
                  <label className="input-label">
                    Marca <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.marca}
                    onChange={(e) => setFormData({ ...formData, marca: e.target.value })}
                    placeholder="Fiat, Toyota, Honda..."
                    className={`input-field ${formErrors.marca ? 'border-red-500 focus:ring-red-500' : ''}`}
                    disabled={isMutating}
                  />
                  {formErrors.marca && <p className="text-sm text-red-500 mt-2">{formErrors.marca}</p>}
                </div>

                {/* Modelo */}
                <div>
                  <label className="input-label">
                    Modelo <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.modelo}
                    onChange={(e) => setFormData({ ...formData, modelo: e.target.value })}
                    placeholder="Uno, Camry, Civic..."
                    className={`input-field ${formErrors.modelo ? 'border-red-500 focus:ring-red-500' : ''}`}
                    disabled={isMutating}
                  />
                  {formErrors.modelo && <p className="text-sm text-red-500 mt-2">{formErrors.modelo}</p>}
                </div>

                {/* Ano */}
                <div>
                  <label className="input-label">
                    Ano <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={formData.ano}
                    onChange={(e) => setFormData({ ...formData, ano: parseInt(e.target.value) })}
                    min="1990"
                    max={currentYear + 1}
                    className={`input-field ${formErrors.ano ? 'border-red-500 focus:ring-red-500' : ''}`}
                    disabled={isMutating}
                  />
                  {formErrors.ano && <p className="text-sm text-red-500 mt-2">{formErrors.ano}</p>}
                </div>

                {/* Cor */}
                <div>
                  <label className="input-label">Cor</label>
                  <input
                    type="text"
                    value={formData.cor}
                    onChange={(e) => setFormData({ ...formData, cor: e.target.value })}
                    placeholder="Preto, Branco, Prata..."
                    className="input-field"
                    disabled={isMutating}
                  />
                </div>

                {/* Quilometragem */}
                <div>
                  <label className="input-label">Quilometragem</label>
                  <input
                    type="number"
                    value={formData.quilometragem}
                    onChange={(e) => setFormData({ ...formData, quilometragem: parseInt(e.target.value) || 0 })}
                    min="0"
                    placeholder="0"
                    className={`input-field ${formErrors.quilometragem ? 'border-red-500 focus:ring-red-500' : ''}`}
                    disabled={isMutating}
                  />
                  {formErrors.quilometragem && (
                    <p className="text-sm text-red-500 mt-2">{formErrors.quilometragem}</p>
                  )}
                </div>

                {/* Valor Aquisição */}
                <div>
                  <label className="input-label">Valor Aquisição</label>
                  <input
                    type="number"
                    value={formData.valor_aquisicao}
                    onChange={(e) => setFormData({ ...formData, valor_aquisicao: parseFloat(e.target.value) || 0 })}
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    className="input-field"
                    disabled={isMutating}
                  />
                </div>

                {/* Data Compra */}
                <div>
                  <label className="input-label">Data Compra</label>
                  <input
                    type="date"
                    value={formData.data_compra}
                    onChange={(e) => setFormData({ ...formData, data_compra: e.target.value })}
                    className="input-field"
                    disabled={isMutating}
                  />
                </div>

                {/* Status */}
                <div>
                  <label className="input-label">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                    className="input-field"
                    disabled={isMutating}
                  >
                    <option value="disponivel">Disponível</option>
                    <option value="alugado">Alugado</option>
                    <option value="manutencao">Manutenção</option>
                    <option value="inativo">Inativo</option>
                  </select>
                </div>

                {/* Observações */}
                <div className="md:col-span-2">
                  <label className="input-label">Observações</label>
                  <textarea
                    value={formData.observacoes}
                    onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                    placeholder="Adicione notas sobre o veículo..."
                    rows={3}
                    className="input-field resize-none"
                    disabled={isMutating}
                  />
                </div>
              </div>

            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="btn-secondary"
                disabled={isMutating}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary inline-flex items-center gap-2"
                disabled={isMutating}
              >
                {isMutating && <div className="animate-spin">⟳</div>}
                {editingVehicle ? 'Atualizar' : 'Criar'} Veículo
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm.isOpen && (
        <div
          className="modal-overlay"
          onClick={(e) => e.target === e.currentTarget && !deleteMutation.isPending && setDeleteConfirm({ isOpen: false })}
        >
          <div
            className="modal-content max-w-sm w-full flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Deletar Veículo</h3>
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
              <div className="flex flex-col items-center text-center">
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
                  <AlertCircle size={24} className="text-red-600" />
                </div>

                <p className="text-slate-600 mt-2">
                  Tem certeza que deseja deletar o veículo <span className="font-semibold">{deleteConfirm.placa}</span>?
                </p>
                <p className="text-sm text-slate-500 mt-2">Esta ação não pode ser desfeita.</p>
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
                className="btn-danger inline-flex items-center justify-center gap-2"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending && <div className="animate-spin">⟳</div>}
                Deletar
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

export default Veiculos
