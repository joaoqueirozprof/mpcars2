import React, { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Building2, CarFront, X } from 'lucide-react'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import CurrencyInput from '@/components/shared/CurrencyInput'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import { Empresa, PaginatedResponse, PaginationParams, Veiculo } from '@/types'
import { formatPhone, formatCNPJ, formatCurrency, formatDate } from '@/lib/utils'

type EmpresaUso = {
  id: string
  veiculo_id: string
  placa?: string
  modelo?: string
  marca?: string
  data_inicio?: string | null
  data_fim?: string | null
  status: string
  km_inicial?: number | null
  km_final?: number | null
  km_referencia?: number | null
  valor_km_extra?: number | null
  valor_diaria_empresa?: number | null
}

type EmpresaUsoForm = {
  veiculo_id: string
  data_inicio: string
  data_fim: string
  km_inicial: number
  km_referencia: number
  valor_km_extra: number
  valor_diaria_empresa: number
}

const Empresas: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingCompany, setEditingCompany] = useState<Empresa | null>(null)
  const [fleetCompany, setFleetCompany] = useState<Empresa | null>(null)
  const [editingUsage, setEditingUsage] = useState<EmpresaUso | null>(null)
  const [usageDeleteConfirm, setUsageDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [searchTerm, setSearchTerm] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState({
    nome: '',
    cnpj: '',
    telefone: '',
    email: '',
    endereco: '',
    cidade: '',
    estado: '',
    cep: '',
    responsavel: '',
  })
  const [usageForm, setUsageForm] = useState<EmpresaUsoForm>({
    veiculo_id: '',
    data_inicio: new Date().toISOString().split('T')[0],
    data_fim: '',
    km_inicial: 0,
    km_referencia: 0,
    valor_km_extra: 0,
    valor_diaria_empresa: 0,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['empresas', pagination, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Empresa>>('/empresas', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          search: searchTerm || undefined,
        },
      })
      return data
    },
  })

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select-empresa'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Veiculo>>('/veiculos', { params: { limit: 1000 } })
      return (data.data || []).map((veiculo: any) => ({
        ...veiculo,
        km_atual: veiculo.km_atual ?? veiculo.quilometragem ?? 0,
      }))
    },
  })

  const { data: usosEmpresa, isLoading: isLoadingUsos } = useQuery({
    queryKey: ['empresa-usos', fleetCompany?.id],
    enabled: Boolean(fleetCompany?.id),
    queryFn: async () => {
      const { data } = await api.get(`/empresas/${fleetCompany?.id}/usos`)
      return data as EmpresaUso[]
    },
  })

  const availableVehicles = useMemo(
    () =>
      (veiculos || []).filter((veiculo: any) => {
        const jaVinculado = (usosEmpresa || []).some(
          (uso) => uso.status === 'ativo' && String(uso.veiculo_id) === String(veiculo.id) && String(uso.id) !== String(editingUsage?.id)
        )
        return !jaVinculado || String(editingUsage?.veiculo_id) === String(veiculo.id)
      }),
    [editingUsage?.id, editingUsage?.veiculo_id, usosEmpresa, veiculos]
  )

  const createMutation = useMutation({
    mutationFn: (formData: any) => api.post('/empresas', formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['empresas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Empresa criada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao criar empresa')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/empresas/${editingCompany?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['empresas'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Empresa atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao atualizar empresa')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/empresas/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['empresas'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Empresa deletada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Erro ao deletar empresa')
    },
  })

  const invalidateCompanyViews = () => {
    queryClient.invalidateQueries({ queryKey: ['empresas'] })
    queryClient.invalidateQueries({ queryKey: ['empresa-usos'] })
    queryClient.invalidateQueries({ queryKey: ['contratos'] })
    queryClient.invalidateQueries({ queryKey: ['relatorios'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const createUsageMutation = useMutation({
    mutationFn: (payload: EmpresaUsoForm) => api.post(`/empresas/${fleetCompany?.id}/usos`, payload),
    onSuccess: () => {
      invalidateCompanyViews()
      setEditingUsage(null)
      resetUsageForm()
      toast.success('Veiculo associado com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao associar veiculo')
    },
  })

  const updateUsageMutation = useMutation({
    mutationFn: (payload: Partial<EmpresaUsoForm>) => api.put(`/empresas/usos/${editingUsage?.id}`, payload),
    onSuccess: () => {
      invalidateCompanyViews()
      setEditingUsage(null)
      resetUsageForm()
      toast.success('Associacao atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao atualizar associacao')
    },
  })

  const deleteUsageMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/empresas/usos/${id}`),
    onSuccess: () => {
      invalidateCompanyViews()
      setUsageDeleteConfirm({ isOpen: false })
      toast.success('Veiculo removido da empresa!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao remover veiculo')
    },
  })

  const resetForm = () => {
    setFormData({
      nome: '',
      cnpj: '',
      telefone: '',
      email: '',
      endereco: '',
      cidade: '',
      estado: '',
      cep: '',
      responsavel: '',
    })
    setEditingCompany(null)
  }

  const resetUsageForm = () => {
    setUsageForm({
      veiculo_id: '',
      data_inicio: new Date().toISOString().split('T')[0],
      data_fim: '',
      km_inicial: 0,
      km_referencia: 0,
      valor_km_extra: 0,
      valor_diaria_empresa: 0,
    })
  }

  const handleOpenModal = (company?: Empresa) => {
    if (company) {
      setEditingCompany(company)
      setFormData(company)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const handleOpenFleetModal = (company: Empresa) => {
    setFleetCompany(company)
    setEditingUsage(null)
    resetUsageForm()
  }

  const handleEditUsage = (uso: EmpresaUso) => {
    setEditingUsage(uso)
    setUsageForm({
      veiculo_id: String(uso.veiculo_id),
      data_inicio: uso.data_inicio ? uso.data_inicio.slice(0, 10) : new Date().toISOString().split('T')[0],
      data_fim: uso.data_fim ? uso.data_fim.slice(0, 10) : '',
      km_inicial: Number(uso.km_inicial || 0),
      km_referencia: Number(uso.km_referencia || 0),
      valor_km_extra: Number(uso.valor_km_extra || 0),
      valor_diaria_empresa: Number(uso.valor_diaria_empresa || 0),
    })
  }

  useEffect(() => {
    if (searchParams.get('quick') !== 'create') return

    handleOpenModal()
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('quick')
    setSearchParams(nextParams, { replace: true })
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (!usageForm.veiculo_id || editingUsage) return
    const veiculo = (veiculos || []).find((item: any) => String(item.id) === String(usageForm.veiculo_id))
    if (!veiculo) return

    setUsageForm((current) => ({
      ...current,
      km_inicial: current.km_inicial > 0 ? current.km_inicial : Number(veiculo.km_atual || 0),
      valor_diaria_empresa:
        current.valor_diaria_empresa > 0 ? current.valor_diaria_empresa : Number(veiculo.valor_diaria || 0),
    }))
  }, [editingUsage, usageForm.veiculo_id, veiculos])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.nome || !formData.cnpj) {
      toast.error('Preencha todos os campos obrigatórios')
      return
    }

    if (editingCompany) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleUsageSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!fleetCompany?.id) return
    if (!usageForm.veiculo_id || !usageForm.data_inicio) {
      toast.error('Selecione o veiculo e a data inicial.')
      return
    }

    const payload = {
      ...usageForm,
      data_fim: usageForm.data_fim || undefined,
      km_inicial: usageForm.km_inicial || 0,
      km_referencia: usageForm.km_referencia || 0,
      valor_km_extra: usageForm.valor_km_extra || 0,
      valor_diaria_empresa: usageForm.valor_diaria_empresa || 0,
    }

    if (editingUsage) {
      updateUsageMutation.mutate(payload)
      return
    }

    createUsageMutation.mutate(payload)
  }

  const handleSearch = (value: string) => {
    setSearchTerm(value)
    setPagination({ ...pagination, page: 1 })
  }

  const columns = [
    {
      key: 'nome' as const,
      label: 'Nome',
      sortable: true,
      width: '25%',
      render: (nome: string) => <span className="font-medium text-slate-900">{nome}</span>,
    },
    { key: 'cnpj' as const, label: 'CNPJ', width: '15%', render: (cnpj: string) => formatCNPJ(cnpj) },
    { key: 'telefone' as const, label: 'Telefone', render: (phone: string) => formatPhone(phone) || '-' },
    { key: 'email' as const, label: 'Email', width: '20%', render: (email: string) => email || '-' },
    { key: 'cidade' as const, label: 'Cidade', render: (cidade: string) => cidade || '-' },
    {
      key: 'id' as const,
      label: 'Ações',
      render: (_: any, row: Empresa) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleOpenFleetModal(row)}
            className="btn-icon p-2 text-slate-600 hover:text-cyan-600 hover:bg-cyan-50 rounded transition-colors"
            title="Gerir frota da empresa"
          >
            <CarFront size={16} />
          </button>
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
              <Building2 className="text-blue-600" size={32} />
              Empresas
            </h1>
            <p className="page-subtitle">Gerenciamento de empresas cadastradas no sistema</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2 whitespace-nowrap">
            <Plus size={20} />
            Nova Empresa
          </button>
        </div>

        <div className="card">
          <div className="mb-6">
            <label className="input-label">Buscar Empresa</label>
            <input
              type="text"
              placeholder="Digite o nome ou CNPJ da empresa..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="input-field"
            />
          </div>

          {isEmpty ? (
            <div className="empty-state py-12">
              <div className="empty-state-icon bg-blue-50 mb-4">
                <Building2 className="text-blue-600" size={40} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Nenhuma empresa encontrada</h3>
              <p className="text-slate-600 mb-4">Comece adicionando a primeira empresa ao sistema</p>
              <button onClick={() => handleOpenModal()} className="btn-primary">
                <Plus size={20} className="inline mr-2" />
                Criar Empresa
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
          <div className="modal-content max-w-2xl w-full flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                {editingCompany ? 'Editar Empresa' : 'Nova Empresa'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="btn-icon"
                title="Fechar"
              >
                <X size={20} />
              </button>
            </div>

            <form id="empresa-form" onSubmit={handleSubmit} className="px-6 py-5 overflow-y-auto max-h-[calc(85vh-130px)] space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="input-label">Nome *</label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                    className="input-field"
                    placeholder="Nome da empresa"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">CNPJ *</label>
                  <input
                    type="text"
                    value={formData.cnpj}
                    onChange={(e) => setFormData({ ...formData, cnpj: e.target.value })}
                    className="input-field"
                    placeholder="00.000.000/0000-00"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="input-field"
                    placeholder="email@empresa.com"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Telefone</label>
                  <input
                    type="tel"
                    value={formData.telefone}
                    onChange={(e) => setFormData({ ...formData, telefone: e.target.value })}
                    className="input-field"
                    placeholder="(11) 9999-9999"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="input-label">Endereço</label>
                  <input
                    type="text"
                    value={formData.endereco}
                    onChange={(e) => setFormData({ ...formData, endereco: e.target.value })}
                    className="input-field"
                    placeholder="Rua, número, complemento"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Cidade</label>
                  <input
                    type="text"
                    value={formData.cidade}
                    onChange={(e) => setFormData({ ...formData, cidade: e.target.value })}
                    className="input-field"
                    placeholder="São Paulo"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">Estado</label>
                  <input
                    type="text"
                    value={formData.estado}
                    onChange={(e) => setFormData({ ...formData, estado: e.target.value.toUpperCase() })}
                    maxLength={2}
                    className="input-field"
                    placeholder="SP"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div>
                  <label className="input-label">CEP</label>
                  <input
                    type="text"
                    value={formData.cep}
                    onChange={(e) => setFormData({ ...formData, cep: e.target.value })}
                    className="input-field"
                    placeholder="01234-567"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="input-label">Responsável</label>
                  <input
                    type="text"
                    value={formData.responsavel}
                    onChange={(e) => setFormData({ ...formData, responsavel: e.target.value })}
                    className="input-field"
                    placeholder="Nome do responsável"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
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
                form="empresa-form"
                className="btn-primary"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending ? 'Processando...' : editingCompany ? 'Atualizar Empresa' : 'Criar Empresa'}
              </button>
            </div>
          </div>
        </div>
      )}

      {fleetCompany && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setFleetCompany(null)}>
          <div className="modal-content max-w-6xl w-full flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <div>
                <h3 className="text-lg font-display font-bold text-slate-900">Frota locada para {fleetCompany.nome}</h3>
                <p className="text-sm text-slate-500">Associe veiculos, parametros mensais e custos de KM extra para a empresa.</p>
              </div>
              <button onClick={() => setFleetCompany(null)} className="btn-icon" title="Fechar">
                <X size={20} />
              </button>
            </div>

            <div className="grid flex-1 min-h-0 grid-cols-1 gap-6 overflow-hidden px-6 py-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
              <form onSubmit={handleUsageSubmit} className="card overflow-y-auto border border-slate-200 p-5 space-y-4">
                <div>
                  <h4 className="text-lg font-semibold text-slate-900">{editingUsage ? 'Editar associacao' : 'Adicionar veiculo a empresa'}</h4>
                  <p className="mt-1 text-sm text-slate-500">Defina o valor mensal, KM permitida e a cobranca por excedente.</p>
                </div>

                <div>
                  <label className="input-label">Veiculo *</label>
                  <select
                    value={usageForm.veiculo_id}
                    onChange={(e) => setUsageForm({ ...usageForm, veiculo_id: e.target.value })}
                    className="input-field"
                    disabled={createUsageMutation.isPending || updateUsageMutation.isPending}
                  >
                    <option value="">Selecione</option>
                    {availableVehicles.map((veiculo: any) => (
                      <option key={veiculo.id} value={veiculo.id}>
                        {veiculo.placa} - {veiculo.marca} {veiculo.modelo}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Inicio da locacao</label>
                    <input type="date" value={usageForm.data_inicio} onChange={(e) => setUsageForm({ ...usageForm, data_inicio: e.target.value })} className="input-field" />
                  </div>
                  <div>
                    <label className="input-label">Fim do vinculo</label>
                    <input type="date" value={usageForm.data_fim} onChange={(e) => setUsageForm({ ...usageForm, data_fim: e.target.value })} className="input-field" />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">KM inicial</label>
                    <input type="number" value={usageForm.km_inicial} onChange={(e) => setUsageForm({ ...usageForm, km_inicial: Number(e.target.value) || 0 })} className="input-field" min="0" />
                  </div>
                  <div>
                    <label className="input-label">KM permitida por mes</label>
                    <input type="number" value={usageForm.km_referencia} onChange={(e) => setUsageForm({ ...usageForm, km_referencia: Number(e.target.value) || 0 })} className="input-field" min="0" />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <CurrencyInput
                    label="Valor mensal / periodo"
                    value={usageForm.valor_diaria_empresa}
                    onChange={(valor_diaria_empresa) => setUsageForm({ ...usageForm, valor_diaria_empresa })}
                  />
                  <CurrencyInput
                    label="Valor por KM extra"
                    value={usageForm.valor_km_extra}
                    onChange={(valor_km_extra) => setUsageForm({ ...usageForm, valor_km_extra })}
                  />
                </div>

                <div className="rounded-2xl border border-blue-100 bg-blue-50/70 p-4 text-sm text-slate-700">
                  <div className="flex justify-between gap-4">
                    <span>Valor base mensal</span>
                    <strong className="text-slate-900">{formatCurrency(usageForm.valor_diaria_empresa || 0)}</strong>
                  </div>
                  <div className="mt-2 flex justify-between gap-4">
                    <span>KM permitida</span>
                    <strong className="text-slate-900">{Number(usageForm.km_referencia || 0).toLocaleString('pt-BR')} km</strong>
                  </div>
                  <div className="mt-2 flex justify-between gap-4">
                    <span>KM excedente</span>
                    <strong className="text-slate-900">{formatCurrency(usageForm.valor_km_extra || 0)} / km</strong>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  {editingUsage && (
                    <button type="button" onClick={() => { setEditingUsage(null); resetUsageForm() }} className="btn-secondary">
                      Cancelar edicao
                    </button>
                  )}
                  <button type="submit" className="btn-primary" disabled={createUsageMutation.isPending || updateUsageMutation.isPending}>
                    {createUsageMutation.isPending || updateUsageMutation.isPending ? 'Salvando...' : editingUsage ? 'Atualizar associacao' : 'Associar veiculo'}
                  </button>
                </div>
              </form>

              <div className="card overflow-y-auto border border-slate-200 p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-lg font-semibold text-slate-900">Veiculos vinculados</h4>
                    <p className="mt-1 text-sm text-slate-500">Historico operacional da frota atendida por esta empresa.</p>
                  </div>
                  <button type="button" onClick={() => queryClient.invalidateQueries({ queryKey: ['empresa-usos', fleetCompany.id] })} className="btn-secondary btn-sm">
                    Atualizar lista
                  </button>
                </div>

                <div className="mt-5 space-y-3">
                  {isLoadingUsos ? (
                    [...Array(3)].map((_, index) => <div key={index} className="h-24 rounded-2xl bg-slate-100 animate-pulse" />)
                  ) : (usosEmpresa || []).length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-10 text-center text-slate-500">
                      Nenhum veiculo associado ainda.
                    </div>
                  ) : (
                    (usosEmpresa || []).map((uso) => (
                      <div key={uso.id} className="rounded-2xl border border-slate-200 bg-white px-5 py-4">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <h5 className="text-base font-semibold text-slate-900">{uso.placa} - {uso.marca} {uso.modelo}</h5>
                              <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${uso.status === 'ativo' ? 'badge-success' : 'badge-info'}`}>
                                {uso.status}
                              </span>
                            </div>
                            <div className="mt-3 grid grid-cols-1 gap-2 text-sm text-slate-600 md:grid-cols-2">
                              <p>Inicio: <strong className="text-slate-900">{formatDate(uso.data_inicio || null)}</strong></p>
                              <p>Fim: <strong className="text-slate-900">{uso.data_fim ? formatDate(uso.data_fim) : 'Indeterminado'}</strong></p>
                              <p>KM inicial: <strong className="text-slate-900">{Number(uso.km_inicial || 0).toLocaleString('pt-BR')}</strong></p>
                              <p>KM permitida: <strong className="text-slate-900">{Number(uso.km_referencia || 0).toLocaleString('pt-BR')} km</strong></p>
                              <p>Valor mensal: <strong className="text-slate-900">{formatCurrency(Number(uso.valor_diaria_empresa || 0))}</strong></p>
                              <p>KM extra: <strong className="text-slate-900">{formatCurrency(Number(uso.valor_km_extra || 0))} / km</strong></p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button type="button" onClick={() => handleEditUsage(uso)} className="btn-icon p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Editar associacao">
                              <Edit size={16} />
                            </button>
                            <button type="button" onClick={() => setUsageDeleteConfirm({ isOpen: true, id: uso.id })} className="btn-icon p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors" title="Remover associacao">
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Empresa"
        message="Tem certeza que deseja deletar esta empresa? Esta ação não pode ser desfeita."
        confirmText="Deletar"
        cancelText="Cancelar"
        isDanger={true}
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)}
        onCancel={() => setDeleteConfirm({ isOpen: false })}
      />

      <ConfirmDialog
        isOpen={usageDeleteConfirm.isOpen}
        title="Remover veiculo da empresa"
        message="Tem certeza que deseja remover esta associacao? O historico de faturamento vinculado a ela pode ser afetado."
        confirmText="Remover"
        cancelText="Cancelar"
        isDanger={true}
        isLoading={deleteUsageMutation.isPending}
        onConfirm={() => usageDeleteConfirm.id && deleteUsageMutation.mutate(usageDeleteConfirm.id)}
        onCancel={() => setUsageDeleteConfirm({ isOpen: false })}
      />
    </AppLayout>
  )
}

export default Empresas
