import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
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
  Camera,
  CircleDollarSign,
  Upload,
  Image as ImageIcon,
  Loader2,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import CurrencyInput from '@/components/shared/CurrencyInput'
import { Veiculo } from '@/types'
import toast from 'react-hot-toast'
import { formatCurrency, formatDate } from '@/lib/utils'

const API_BASE = (() => {
  const hostname = window.location.hostname
  if (hostname === '72.61.129.78' || hostname === 'localhost') {
    return `http://${hostname}:8002/api/v1`
  }
  return '/api/v1'
})()

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
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)
  const [viewingPhoto, setViewingPhoto] = useState<{ isOpen: boolean; url?: string; placa?: string }>({ isOpen: false })
  const [historyVehicle, setHistoryVehicle] = useState<Veiculo | null>(null)
  const [financialHistory, setFinancialHistory] = useState<any | null>(null)
  const [financialHistoryError, setFinancialHistoryError] = useState('')
  const [isLoadingFinancialHistory, setIsLoadingFinancialHistory] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [searchParams, setSearchParams] = useSearchParams()
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
      const { data } = await api.get<{ data: any[]; total: number }>('/veiculos', {
        params: { limit: 1000 },
      })
      return (data.data || []).map((v: any) => ({
        ...v,
        quilometragem: v.km_atual || 0,
        data_compra: v.data_aquisicao || '',
        observacoes: v.observacoes || '',
        cor: v.cor || '',
        foto_url: v.foto_url || null,
      }))
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
          (v.placa || '').toLowerCase().includes(search) ||
          (v.marca || '').toLowerCase().includes(search) ||
          (v.modelo || '').toLowerCase().includes(search) ||
          (v.cor || '').toLowerCase().includes(search),
      )
    }

    return filtered
  }, [vehiclesData, statusFilter, searchTerm])

  // Create vehicle mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/veiculos', data),
    onSuccess: async (response) => {
      const newVehicleId = response.data.id
      // Upload photo if selected
      if (photoFile && newVehicleId) {
        await uploadPhoto(newVehicleId)
      }
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Veiculo criado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao criar veiculo')
    },
  })

  // Update vehicle mutation
  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch(`/veiculos/${editingVehicle?.id}`, data),
    onSuccess: async () => {
      // Upload photo if new one selected
      if (photoFile && editingVehicle?.id) {
        await uploadPhoto(Number(editingVehicle.id))
      }
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Veiculo atualizado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao atualizar veiculo')
    },
  })

  // Delete vehicle mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/veiculos/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Veiculo deletado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Erro ao deletar veiculo')
    },
  })

  const uploadPhoto = async (vehicleId: number) => {
    if (!photoFile) return
    setUploadingPhoto(true)
    try {
      const formDataUpload = new FormData()
      formDataUpload.append('foto', photoFile)
      await api.post(`/veiculos/${vehicleId}/foto`, formDataUpload, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    } catch (err: any) {
      toast.error('Erro ao enviar foto: ' + (err.response?.data?.detail || 'Erro desconhecido'))
    } finally {
      setUploadingPhoto(false)
    }
  }

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)) {
      toast.error('Tipo de arquivo nao permitido. Use JPEG, PNG, WebP ou GIF.')
      return
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Arquivo muito grande. Maximo 10MB.')
      return
    }

    setPhotoFile(file)
    const reader = new FileReader()
    reader.onloadend = () => setPhotoPreview(reader.result as string)
    reader.readAsDataURL(file)
  }

  const removePhoto = async () => {
    setPhotoFile(null)
    setPhotoPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''

    // If editing and vehicle has a photo, delete it from server
    if (editingVehicle?.foto_url) {
      try {
        await api.delete(`/veiculos/${editingVehicle.id}/foto`)
        queryClient.invalidateQueries({ queryKey: ['veiculos'] })
        toast.success('Foto removida!')
      } catch {
        toast.error('Erro ao remover foto')
      }
    }
  }

  const getVehiclePhotoUrl = (vehicle: Veiculo) => {
    if (!vehicle.foto_url) return null
    return `${API_BASE}/veiculos/foto/${vehicle.id}?t=${Date.now()}`
  }

  // Form validation
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    if (!formData.placa.trim()) {
      errors.placa = 'Placa e obrigatoria'
    } else if (!/^[A-Z]{3}\d{4}$|^[A-Z]{3}\d[A-Z]\d{2}$/.test(formData.placa)) {
      errors.placa = 'Formato invalido (ABC1234 ou ABC1D23)'
    }

    if (!formData.marca.trim()) {
      errors.marca = 'Marca e obrigatoria'
    }

    if (!formData.modelo.trim()) {
      errors.modelo = 'Modelo e obrigatorio'
    }

    if (!formData.ano || formData.ano < 1990 || formData.ano > currentYear + 1) {
      errors.ano = `Ano deve estar entre 1990 e ${currentYear + 1}`
    }

    if (formData.quilometragem < 0) {
      errors.quilometragem = 'Quilometragem nao pode ser negativa'
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
    setPhotoFile(null)
    setPhotoPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
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
        observacoes: vehicle.observacoes || '',
      })
      // Set photo preview if vehicle has a photo
      if (vehicle.foto_url) {
        setPhotoPreview(getVehiclePhotoUrl(vehicle))
      } else {
        setPhotoPreview(null)
      }
      setPhotoFile(null)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const openFinancialHistory = async (vehicle: Veiculo) => {
    setHistoryVehicle(vehicle)
    setFinancialHistory(null)
    setFinancialHistoryError('')
    setIsLoadingFinancialHistory(true)
    try {
      const { data } = await api.get(`/veiculos/historico-financeiro/${vehicle.id}`)
      setFinancialHistory(data)
    } catch (error: any) {
      setFinancialHistoryError(error.response?.data?.detail || 'Nao foi possivel carregar o historico financeiro desse veiculo.')
    } finally {
      setIsLoadingFinancialHistory(false)
    }
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

    if (!validateForm()) {
      return
    }

    const payload = {
      placa: formData.placa,
      marca: formData.marca,
      modelo: formData.modelo,
      ano: formData.ano,
      cor: formData.cor,
      km_atual: formData.quilometragem,
      status: formData.status,
      valor_aquisicao: formData.valor_aquisicao,
      data_aquisicao: formData.data_compra || null,
      observacoes: formData.observacoes,
    }

    if (editingVehicle) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
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
        return 'Disponivel'
      case 'alugado':
        return 'Alugado'
      case 'manutencao':
        return 'Manutencao'
      case 'inativo':
        return 'Inativo'
      default:
        return status
    }
  }

  const statusFilters = [
    { key: 'todos', label: 'Todos' },
    { key: 'disponivel', label: 'Disponivel' },
    { key: 'alugado', label: 'Alugado' },
    { key: 'manutencao', label: 'Manutencao' },
    { key: 'inativo', label: 'Inativo' },
  ]

  const isLoading = isLoadingVehicles
  const isMutating = createMutation.isPending || updateMutation.isPending || uploadingPhoto

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Veiculos</h1>
            <p className="page-subtitle">Gerenciar e controlar frota de veiculos</p>
          </div>
          <button
            onClick={() => handleOpenModal()}
            className="btn-primary flex items-center gap-2 transition-all duration-200"
          >
            <Plus size={20} />
            Novo Veiculo
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
              <h3 className="text-xl font-semibold text-slate-900 mt-4">Nenhum veiculo encontrado</h3>
              <p className="text-slate-600 mt-2">
                {searchTerm
                  ? 'Nenhum veiculo corresponde a sua busca'
                  : 'Comece a adicionar veiculos a sua frota'}
              </p>
              {!searchTerm && (
                <button
                  onClick={() => handleOpenModal()}
                  className="btn-primary mt-6 inline-flex items-center gap-2"
                >
                  <Plus size={18} />
                  Adicionar Primeiro Veiculo
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
                    <th className="table-header text-left">Foto</th>
                    <th className="table-header text-left">Placa</th>
                    <th className="table-header text-left">Marca/Modelo</th>
                    <th className="table-header text-left">Ano</th>
                    <th className="table-header text-left">Cor</th>
                    <th className="table-header text-left">Status</th>
                    <th className="table-header text-left">Km</th>
                    <th className="table-header text-center">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredVehicles.map((vehicle) => (
                    <tr
                      key={vehicle.id}
                      className="border-b border-slate-200 hover:bg-slate-50 transition-colors duration-150"
                    >
                      <td className="table-cell">
                        {vehicle.foto_url ? (
                          <img
                            src={getVehiclePhotoUrl(vehicle)!}
                            alt={`${vehicle.marca} ${vehicle.modelo}`}
                            className="w-12 h-12 rounded-lg object-cover cursor-pointer border border-slate-200 hover:opacity-80 transition-opacity"
                            onClick={() => setViewingPhoto({ isOpen: true, url: getVehiclePhotoUrl(vehicle)!, placa: vehicle.placa })}
                            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg bg-slate-100 flex items-center justify-center">
                            <Car size={20} className="text-slate-400" />
                          </div>
                        )}
                      </td>
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
                        <span className="text-slate-900">{(vehicle.quilometragem || 0).toLocaleString('pt-BR')} km</span>
                      </td>
                      <td className="table-cell text-center">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            type="button"
                            onClick={() => openFinancialHistory(vehicle)}
                            className="btn-icon transition-colors duration-200"
                            title="Historico financeiro do veiculo"
                          >
                            <CircleDollarSign size={18} />
                          </button>
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
                {editingVehicle ? 'Editar Veiculo' : 'Novo Veiculo'}
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
            <form onSubmit={handleSubmit} className="flex flex-col overflow-hidden flex-1">
            <div className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)]">

              {/* Photo Upload Section */}
              <div className="mb-6">
                <label className="input-label flex items-center gap-2">
                  <Camera size={16} />
                  Foto do Veiculo
                </label>
                <div className="flex items-center gap-4 mt-2">
                  {/* Photo Preview */}
                  <div className="relative">
                    {photoPreview ? (
                      <div className="relative group">
                        <img
                          src={photoPreview}
                          alt="Preview"
                          className="w-32 h-32 rounded-xl object-cover border-2 border-slate-200"
                        />
                        <button
                          type="button"
                          onClick={removePhoto}
                          className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
                          disabled={isMutating}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <div
                        className="w-32 h-32 rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-all"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <ImageIcon size={28} className="text-slate-400 mb-1" />
                        <span className="text-xs text-slate-500">Sem foto</span>
                      </div>
                    )}
                  </div>

                  {/* Upload Button */}
                  <div className="flex flex-col gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="btn-secondary inline-flex items-center gap-2 text-sm"
                      disabled={isMutating}
                    >
                      <Upload size={16} />
                      {photoPreview ? 'Trocar Foto' : 'Enviar Foto'}
                    </button>
                    <p className="text-xs text-slate-500">JPEG, PNG, WebP ou GIF. Max 10MB.</p>
                  </div>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    onChange={handlePhotoChange}
                    className="hidden"
                  />
                </div>
              </div>

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
                    value={formData.quilometragem === 0 ? '' : formData.quilometragem}
                    onChange={(e) => setFormData({ ...formData, quilometragem: e.target.value === '' ? 0 : parseInt(e.target.value) || 0 })}
                    min="0"
                    placeholder="0"
                    className={`input-field ${formErrors.quilometragem ? 'border-red-500 focus:ring-red-500' : ''}`}
                    disabled={isMutating}
                  />
                  {formErrors.quilometragem && (
                    <p className="text-sm text-red-500 mt-2">{formErrors.quilometragem}</p>
                  )}
                </div>

                {/* Valor Aquisicao */}
                <CurrencyInput
                  label="Valor Aquisicao"
                  value={formData.valor_aquisicao}
                  onChange={(valor_aquisicao) => setFormData({ ...formData, valor_aquisicao })}
                  disabled={isMutating}
                />

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
                    <option value="disponivel">Disponivel</option>
                    <option value="alugado">Alugado</option>
                    <option value="manutencao">Manutencao</option>
                    <option value="inativo">Inativo</option>
                  </select>
                </div>

                {/* Observacoes */}
                <div className="md:col-span-2">
                  <label className="input-label">Observacoes</label>
                  <textarea
                    value={formData.observacoes}
                    onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                    placeholder="Adicione notas sobre o veiculo..."
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
                {isMutating && <div className="animate-spin">&#x27F3;</div>}
                {editingVehicle ? 'Atualizar' : 'Criar'} Veiculo
              </button>
            </div>
          </form>
        </div>
      </div>
      )}

      {/* Photo Viewer Modal */}
      {viewingPhoto.isOpen && viewingPhoto.url && (
        <div
          className="modal-overlay"
          onClick={() => setViewingPhoto({ isOpen: false })}
        >
          <div
            className="modal-content max-w-3xl w-full flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                Foto - {viewingPhoto.placa}
              </h3>
              <button
                onClick={() => setViewingPhoto({ isOpen: false })}
                className="btn-icon"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 flex items-center justify-center">
              <img
                src={viewingPhoto.url}
                alt={`Veiculo ${viewingPhoto.placa}`}
                className="max-w-full max-h-[60vh] rounded-xl object-contain"
              />
            </div>
          </div>
        </div>
      )}

      {historyVehicle && (
        <div className="modal-overlay" onClick={() => setHistoryVehicle(null)}>
          <div className="modal-content max-w-5xl w-full flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <div>
                <h3 className="text-lg font-display font-bold text-slate-900">Historico financeiro do veiculo</h3>
                <p className="text-sm text-slate-500">{historyVehicle.placa} - {historyVehicle.marca} {historyVehicle.modelo}</p>
              </div>
              <button onClick={() => setHistoryVehicle(null)} className="btn-icon">
                <X size={20} />
              </button>
            </div>

            <div className="px-6 py-5 overflow-y-auto space-y-5">
              {isLoadingFinancialHistory ? (
                <div className="flex items-center justify-center py-16 text-slate-500">
                  <Loader2 size={22} className="animate-spin mr-2" />
                  Carregando historico financeiro...
                </div>
              ) : financialHistoryError ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-8 text-center text-red-700">
                  <p className="font-semibold">Nao foi possivel abrir o historico financeiro.</p>
                  <p className="mt-2 text-sm">{financialHistoryError}</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Receita acumulada</p>
                      <p className="mt-2 text-2xl font-display font-bold text-emerald-600">{formatCurrency(Number(financialHistory?.total_receita || 0))}</p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Despesa acumulada</p>
                      <p className="mt-2 text-2xl font-display font-bold text-rose-600">{formatCurrency(Number(financialHistory?.total_despesa || 0))}</p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Saldo do veiculo</p>
                      <p className="mt-2 text-2xl font-display font-bold text-blue-700">{formatCurrency(Number(financialHistory?.saldo || 0))}</p>
                    </div>
                  </div>

                  {/* Detalhamento de Despesas por Categoria */}
                  <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 mt-4">
                    <p className="text-sm font-semibold text-slate-800 mb-4">Detalhamento Estratégico de Despesas</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                      {Object.entries(
                        (financialHistory?.records || []).reduce((acc: any, record: any) => {
                          if (record.tipo === 'despesa') {
                            const cat = record.categoria.split('/')[0].split('-')[0].trim()
                            acc[cat] = (acc[cat] || 0) + (Number(record.valor) || 0)
                          }
                          return acc
                        }, {} as Record<string, number>)
                      ).map(([cat, val]: any) => (
                        <div key={cat} className="bg-white border border-slate-100 rounded-xl px-4 py-3 shadow-sm">
                          <p className="text-xs uppercase tracking-[0.12em] text-slate-400 font-medium mb-1 truncate" title={cat}>{cat}</p>
                          <p className="text-lg font-display font-bold text-rose-600">{formatCurrency(val)}</p>
                        </div>
                      ))}
                      {Object.keys(
                        (financialHistory?.records || []).reduce((acc: any, record: any) => {
                          if (record.tipo === 'despesa') {
                            const cat = record.categoria.split('/')[0].split('-')[0].trim()
                            acc[cat] = (acc[cat] || 0) + (Number(record.valor) || 0)
                          }
                          return acc
                        }, {} as Record<string, number>)
                      ).length === 0 && (
                        <p className="text-sm text-slate-400 italic col-span-full">Nenhuma despesa para detalhar.</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 overflow-hidden">
                    <div className="grid grid-cols-[140px_120px_1fr_140px] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      <span>Data</span>
                      <span>Tipo</span>
                      <span>Descricao</span>
                      <span className="text-right">Valor</span>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {(financialHistory?.records || []).length === 0 ? (
                        <div className="px-5 py-10 text-center text-slate-500">Nenhum lancamento encontrado para este veiculo.</div>
                      ) : (
                        (financialHistory?.records || []).map((record: any) => (
                          <div key={record.id} className="grid grid-cols-[140px_120px_1fr_140px] gap-4 px-5 py-4 text-sm">
                            <span className="text-slate-600">{formatDate(record.data)}</span>
                            <span className={`font-medium ${record.tipo === 'receita' ? 'text-emerald-600' : 'text-rose-600'}`}>
                              {record.tipo === 'receita' ? 'Receita' : 'Despesa'}
                            </span>
                            <div>
                              <p className="font-medium text-slate-900">{record.descricao}</p>
                              <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">{record.categoria}</p>
                            </div>
                            <span className={`text-right font-semibold ${record.tipo === 'receita' ? 'text-emerald-600' : 'text-rose-600'}`}>
                              {record.tipo === 'receita' ? '+' : '-'} {formatCurrency(Number(record.valor || 0))}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
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
              <h3 className="text-lg font-display font-bold text-slate-900">Deletar Veiculo</h3>
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
                  Tem certeza que deseja deletar o veiculo <span className="font-semibold">{deleteConfirm.placa}</span>?
                </p>
                <p className="text-sm text-slate-500 mt-2">Esta acao nao pode ser desfeita.</p>
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
                {deleteMutation.isPending && <div className="animate-spin">&#x27F3;</div>}
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
