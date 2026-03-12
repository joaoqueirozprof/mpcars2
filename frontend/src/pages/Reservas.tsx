import React, { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, CheckCircle2, Edit, FilePlus2, Plus, Trash2, X } from 'lucide-react'
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import DataTable from '@/components/shared/DataTable'
import { useConfig } from '@/contexts/ConfigContext'
import { calculateDays, formatCurrency, formatDate } from '@/lib/utils'
import api from '@/services/api'
import { Cliente, PaginatedResponse, PaginationParams, Reserva, Veiculo } from '@/types'

type ReservationFilter = 'todos' | 'pendente' | 'confirmada' | 'cancelada' | 'convertida'

type ReservationForm = {
  cliente_id: string
  veiculo_id: string
  data_inicio: string
  data_fim: string
  valor_estimado: number
  status: 'pendente' | 'confirmada' | 'cancelada'
}

type ConvertReservationForm = {
  valor_diaria: number
  tipo: 'cliente' | 'empresa'
  hora_saida: string
  combustivel_saida: string
  km_livres: number
  valor_km_excedente: number
  desconto: number
  observacoes: string
}

const fuelOptions = ['1/4', '1/2', '3/4', 'Cheio']

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail || error?.response?.data?.message || fallback

const getRawStatus = (reserva: Reserva) => reserva.status_original || reserva.status

const statusLabel = (status: string) =>
  ({
    pendente: 'Pendente',
    confirmada: 'Confirmada',
    cancelada: 'Cancelada',
    convertida: 'Convertida',
    ativa: 'Ativa',
  }[status] || status)

const statusClass = (status: string) =>
  ({
    pendente: 'badge-warning',
    confirmada: 'badge-success',
    cancelada: 'badge-danger',
    convertida: 'badge-info',
    ativa: 'badge-info',
  }[status] || 'badge-info')

const Reservas: React.FC = () => {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const config = useConfig()

  const buildForm = (): ReservationForm => ({
    cliente_id: '',
    veiculo_id: '',
    data_inicio: '',
    data_fim: '',
    valor_estimado: 0,
    status: 'pendente',
  })

  const buildConvertForm = (): ConvertReservationForm => ({
    valor_diaria: config.valor_diaria_padrao || 0,
    tipo: 'cliente',
    hora_saida: '',
    combustivel_saida: '',
    km_livres: 0,
    valor_km_excedente: 0,
    desconto: 0,
    observacoes: '',
  })

  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [statusFilter, setStatusFilter] = useState<ReservationFilter>('todos')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingReservation, setEditingReservation] = useState<Reserva | null>(null)
  const [convertReservation, setConvertReservation] = useState<Reserva | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState<ReservationForm>(buildForm())
  const [convertForm, setConvertForm] = useState<ConvertReservationForm>(buildConvertForm())

  const { data: reservas, isLoading } = useQuery({
    queryKey: ['reservas', pagination, statusFilter],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Reserva>>('/reservas', {
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
      const { data } = await api.get<PaginatedResponse<Cliente>>('/clientes', { params: { limit: 1000 } })
      return data.data || []
    },
  })

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Veiculo>>('/veiculos', { params: { limit: 1000 } })
      return (data.data || []).map((veiculo: any) => ({
        ...veiculo,
        quilometragem: veiculo.quilometragem ?? veiculo.km_atual ?? 0,
      }))
    },
  })

  const availableVehicles = useMemo(
    () =>
      (veiculos || []).filter(
        (veiculo) => veiculo.status === 'disponivel' || String(veiculo.id) === String(formData.veiculo_id)
      ),
    [veiculos, formData.veiculo_id]
  )

  const selectedVehicle = (veiculos || []).find((veiculo) => String(veiculo.id) === String(formData.veiculo_id))
  const selectedConvertVehicle = convertReservation
    ? (veiculos || []).find((veiculo) => String(veiculo.id) === String(convertReservation.veiculo_id))
    : undefined

  const invalidateQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['reservas'] })
    queryClient.invalidateQueries({ queryKey: ['veiculos-select'] })
    queryClient.invalidateQueries({ queryKey: ['contratos'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    queryClient.invalidateQueries({ queryKey: ['financeiro'] })
  }

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/reservas', payload),
    onSuccess: () => {
      invalidateQueries()
      setIsModalOpen(false)
      setEditingReservation(null)
      setFormData(buildForm())
      toast.success('Reserva criada com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao criar reserva')),
  })

  const updateMutation = useMutation({
    mutationFn: (payload: any) => api.patch(`/reservas/${editingReservation?.id}`, payload),
    onSuccess: () => {
      invalidateQueries()
      setIsModalOpen(false)
      setEditingReservation(null)
      setFormData(buildForm())
      toast.success('Reserva atualizada com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao atualizar reserva')),
  })

  const confirmMutation = useMutation({
    mutationFn: (reservaId: string) => api.post(`/reservas/${reservaId}/confirmar`),
    onSuccess: () => {
      invalidateQueries()
      toast.success('Reserva confirmada com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao confirmar reserva')),
  })

  const convertMutation = useMutation({
    mutationFn: (payload: ConvertReservationForm) => api.post(`/reservas/${convertReservation?.id}/converter`, payload),
    onSuccess: ({ data }) => {
      const numero = data?.numero
      invalidateQueries()
      setConvertReservation(null)
      setConvertForm(buildConvertForm())
      toast.success(numero ? `Reserva convertida no contrato ${numero}` : 'Reserva convertida com sucesso!')
      navigate('/contratos')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao converter reserva')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/reservas/${id}`),
    onSuccess: () => {
      invalidateQueries()
      setDeleteConfirm({ isOpen: false })
      toast.success('Reserva deletada com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao deletar reserva')),
  })

  const diasReserva = formData.data_inicio && formData.data_fim ? calculateDays(formData.data_inicio, formData.data_fim) : 0
  const valorDiariaReserva = selectedVehicle?.valor_diaria || config.valor_diaria_padrao || 0
  const valorEstimadoReserva = Math.max(diasReserva * valorDiariaReserva, 0)

  const diasConversao = convertReservation ? calculateDays(convertReservation.data_inicio, convertReservation.data_fim) : 0
  const valorPrevistoConversao = Math.max((diasConversao * convertForm.valor_diaria) - convertForm.desconto, 0)

  const summary = useMemo(() => {
    const list = reservas?.data || []
    return {
      total: reservas?.total || 0,
      pendentes: list.filter((reserva) => getRawStatus(reserva) === 'pendente').length,
      confirmadas: list.filter((reserva) => getRawStatus(reserva) === 'confirmada').length,
      convertidas: list.filter((reserva) => getRawStatus(reserva) === 'convertida').length,
      valor: list.reduce((total, reserva) => total + (reserva.valor_estimado || 0), 0),
    }
  }, [reservas])

  const handleOpenModal = (reservation?: Reserva) => {
    if (reservation) {
      setEditingReservation(reservation)
      setFormData({
        cliente_id: reservation.cliente_id,
        veiculo_id: reservation.veiculo_id,
        data_inicio: reservation.data_inicio.slice(0, 10),
        data_fim: reservation.data_fim.slice(0, 10),
        valor_estimado: reservation.valor_estimado || 0,
        status: (getRawStatus(reservation) as ReservationForm['status']) || 'pendente',
      })
    } else {
      setEditingReservation(null)
      setFormData(buildForm())
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

  const handleOpenConvertModal = (reservation: Reserva) => {
    const veiculo = (veiculos || []).find((item) => String(item.id) === String(reservation.veiculo_id))
    setConvertReservation(reservation)
    setConvertForm({
      ...buildConvertForm(),
      valor_diaria: veiculo?.valor_diaria || config.valor_diaria_padrao || 0,
    })
  }

  const handleVehicleChange = (vehicleId: string) => {
    const veiculo = (veiculos || []).find((item) => String(item.id) === String(vehicleId))
    const diaria = veiculo?.valor_diaria || config.valor_diaria_padrao || 0
    const days = formData.data_inicio && formData.data_fim ? calculateDays(formData.data_inicio, formData.data_fim) : 0

    setFormData((current) => ({
      ...current,
      veiculo_id: vehicleId,
      valor_estimado: Math.max(days * diaria, 0),
    }))
  }

  const handleDateChange = (field: 'data_inicio' | 'data_fim', value: string) => {
    const next = { ...formData, [field]: value }
    const veiculo = (veiculos || []).find((item) => String(item.id) === String(next.veiculo_id))
    const diaria = veiculo?.valor_diaria || config.valor_diaria_padrao || 0
    const days = next.data_inicio && next.data_fim ? calculateDays(next.data_inicio, next.data_fim) : 0
    setFormData({
      ...next,
      valor_estimado: Math.max(days * diaria, 0),
    })
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()

    if (!formData.cliente_id || !formData.veiculo_id || !formData.data_inicio || !formData.data_fim) {
      toast.error('Preencha cliente, veiculo e periodo da reserva.')
      return
    }

    if (new Date(formData.data_fim) <= new Date(formData.data_inicio)) {
      toast.error('A data final precisa ser maior que a inicial.')
      return
    }

    const payload = {
      cliente_id: formData.cliente_id,
      veiculo_id: formData.veiculo_id,
      data_inicio: formData.data_inicio,
      data_fim: formData.data_fim,
      valor_estimado: valorEstimadoReserva,
      ...(editingReservation ? { status: formData.status } : {}),
    }

    if (editingReservation) {
      updateMutation.mutate(payload)
      return
    }
    createMutation.mutate(payload)
  }

  const handleConvert = () => {
    if (!convertReservation) return
    if (convertForm.valor_diaria <= 0) {
      toast.error('Informe o valor da diaria para converter a reserva.')
      return
    }
    convertMutation.mutate(convertForm)
  }

  const columns = [
    {
      key: 'cliente_id' as const,
      label: 'Cliente',
      render: (_: any, row: Reserva) => <span className="font-medium text-slate-900">{row.cliente?.nome || '-'}</span>,
    },
    {
      key: 'veiculo_id' as const,
      label: 'Veiculo',
      render: (_: any, row: Reserva) => <span className="text-slate-700">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'data_inicio' as const,
      label: 'Inicio',
      render: (value: string) => <span className="text-slate-700">{formatDate(value)}</span>,
    },
    {
      key: 'data_fim' as const,
      label: 'Fim',
      render: (value: string) => <span className="text-slate-700">{formatDate(value)}</span>,
    },
    {
      key: 'id' as const,
      label: 'Periodo',
      render: (_: any, row: Reserva) => <span className="font-semibold text-slate-900">{calculateDays(row.data_inicio, row.data_fim)} dia(s)</span>,
    },
    {
      key: 'valor_estimado' as const,
      label: 'Estimativa',
      render: (value: number) => <span className="font-semibold text-slate-900">{formatCurrency(value || 0)}</span>,
    },
    {
      key: 'status' as const,
      label: 'Status',
      render: (_: string, row: Reserva) => {
        const rawStatus = getRawStatus(row)
        return <span className={statusClass(rawStatus)}>{statusLabel(rawStatus)}</span>
      },
    },
    {
      key: 'id_action' as const,
      label: 'Acoes',
      render: (_: any, row: Reserva) => {
        const rawStatus = getRawStatus(row)
        return (
          <div className="flex items-center gap-2">
            {rawStatus === 'pendente' && (
              <button
                onClick={() => confirmMutation.mutate(row.id)}
                className="btn-icon p-2 text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 rounded transition-colors"
                title="Confirmar reserva"
                disabled={confirmMutation.isPending}
              >
                <CheckCircle2 size={16} />
              </button>
            )}
            {rawStatus === 'confirmada' && (
              <button
                onClick={() => handleOpenConvertModal(row)}
                className="btn-icon p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                title="Converter em contrato"
                disabled={convertMutation.isPending}
              >
                <FilePlus2 size={16} />
              </button>
            )}
            {rawStatus !== 'convertida' && (
              <button
                onClick={() => handleOpenModal(row)}
                className="btn-icon p-2 text-slate-600 hover:text-cyan-600 hover:bg-cyan-50 rounded transition-colors"
                title="Editar"
              >
                <Edit size={16} />
              </button>
            )}
            <button
              onClick={() => setDeleteConfirm({ isOpen: true, id: row.id })}
              className="btn-icon p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              title="Deletar"
              disabled={deleteMutation.isPending}
            >
              <Trash2 size={16} />
            </button>
          </div>
        )
      },
    },
  ]

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="page-header">
          <div>
            <h1 className="page-title">Reservas</h1>
            <p className="page-subtitle">Organize o calendario da frota e transforme reservas confirmadas em contratos ativos.</p>
          </div>
          <button onClick={() => handleOpenModal()} className="btn-primary flex items-center gap-2">
            <Plus size={18} />
            Nova Reserva
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
          <div className="kpi-card"><p className="kpi-label">Total</p><p className="kpi-value">{summary.total}</p></div>
          <div className="kpi-card"><p className="kpi-label">Pendentes</p><p className="kpi-value text-amber-600">{summary.pendentes}</p></div>
          <div className="kpi-card"><p className="kpi-label">Confirmadas</p><p className="kpi-value text-emerald-600">{summary.confirmadas}</p></div>
          <div className="kpi-card"><p className="kpi-label">Convertidas</p><p className="kpi-value text-cyan-600">{summary.convertidas}</p></div>
          <div className="kpi-card"><p className="kpi-label">Valor Estimado</p><p className="kpi-value">{formatCurrency(summary.valor)}</p></div>
        </div>

        <div className="flex gap-2 flex-wrap">
          {[
            { key: 'todos', label: 'Todas' },
            { key: 'pendente', label: 'Pendentes' },
            { key: 'confirmada', label: 'Confirmadas' },
            { key: 'convertida', label: 'Convertidas' },
            { key: 'cancelada', label: 'Canceladas' },
          ].map((item) => (
            <button
              key={item.key}
              onClick={() => {
                setStatusFilter(item.key as ReservationFilter)
                setPagination((current) => ({ ...current, page: 1 }))
              }}
              className={`filter-tab ${statusFilter === item.key ? 'filter-tab-active' : 'filter-tab-inactive'}`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="card">
          <DataTable
            columns={columns}
            data={reservas?.data || []}
            isLoading={isLoading}
            pagination={{
              page: pagination.page,
              limit: pagination.limit,
              total: reservas?.total || 0,
              onPageChange: (page) => setPagination((current) => ({ ...current, page })),
            }}
          />
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-2xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">{editingReservation ? 'Editar Reserva' : 'Nova Reserva'}</h3>
              <button onClick={() => setIsModalOpen(false)} className="btn-icon"><X size={20} /></button>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-1 min-h-0 flex-col overflow-hidden">
              <div className="modal-scroll-body space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Cliente *</label>
                    <select value={formData.cliente_id} onChange={(event) => setFormData({ ...formData, cliente_id: event.target.value })} className="input-field">
                      <option value="">Selecione</option>
                      {clientes?.map((cliente) => <option key={cliente.id} value={cliente.id}>{cliente.nome}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="input-label">Veiculo *</label>
                    <select value={formData.veiculo_id} onChange={(event) => handleVehicleChange(event.target.value)} className="input-field">
                      <option value="">Selecione</option>
                      {availableVehicles.map((veiculo) => (
                        <option key={veiculo.id} value={veiculo.id}>
                          {veiculo.placa} - {veiculo.marca} {veiculo.modelo}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Data Inicio *</label>
                    <input type="date" value={formData.data_inicio} onChange={(event) => handleDateChange('data_inicio', event.target.value)} className="input-field" />
                  </div>
                  <div>
                    <label className="input-label">Data Fim *</label>
                    <input type="date" value={formData.data_fim} onChange={(event) => handleDateChange('data_fim', event.target.value)} className="input-field" />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-xs uppercase tracking-wide text-blue-700">Periodo da Reserva</p>
                    <p className="text-2xl font-bold text-blue-950 mt-2">{diasReserva}</p>
                    <p className="text-sm text-blue-900/80 mt-1">dia(s) previstos</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Valor Estimado</p>
                    <p className="text-2xl font-bold text-slate-900 mt-2">{formatCurrency(valorEstimadoReserva)}</p>
                    <p className="text-sm text-slate-500 mt-1">Baseado no periodo e na diaria do veiculo</p>
                  </div>
                </div>

                {editingReservation && (
                  <div>
                    <label className="input-label">Status</label>
                    <select value={formData.status} onChange={(event) => setFormData({ ...formData, status: event.target.value as ReservationForm['status'] })} className="input-field">
                      <option value="pendente">Pendente</option>
                      <option value="confirmada">Confirmada</option>
                      <option value="cancelada">Cancelada</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                  {createMutation.isPending || updateMutation.isPending ? 'Salvando...' : editingReservation ? 'Atualizar Reserva' : 'Criar Reserva'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {convertReservation && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && !convertMutation.isPending && setConvertReservation(null)}>
          <div className="modal-content max-w-3xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Converter Reserva em Contrato</h3>
              <button onClick={() => setConvertReservation(null)} className="btn-icon" disabled={convertMutation.isPending}><X size={20} /></button>
            </div>

            <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
              <div className="modal-scroll-body space-y-5">
                <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-950">
                  <p className="font-semibold">Conversao operacional</p>
                  <p className="mt-1 text-blue-900/80">A reserva confirmada vai gerar um contrato ativo, ja atualizando a disponibilidade da frota e a previsao financeira.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Cliente</p>
                    <p className="text-base font-semibold text-slate-900 mt-2">{convertReservation.cliente?.nome || '-'}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Veiculo</p>
                    <p className="text-base font-semibold text-slate-900 mt-2">{convertReservation.veiculo?.placa || '-'}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Periodo</p>
                    <p className="text-base font-semibold text-slate-900 mt-2">{diasConversao} dia(s)</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Tipo</label>
                    <select value={convertForm.tipo} onChange={(event) => setConvertForm({ ...convertForm, tipo: event.target.value as ConvertReservationForm['tipo'] })} className="input-field">
                      <option value="cliente">Cliente</option>
                      <option value="empresa">Empresa</option>
                    </select>
                  </div>
                  <div>
                    <label className="input-label">Valor Diaria *</label>
                    <input type="number" step="0.01" value={convertForm.valor_diaria} onChange={(event) => setConvertForm({ ...convertForm, valor_diaria: Number(event.target.value) || 0 })} className="input-field" />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Hora de Saida</label>
                    <input type="time" value={convertForm.hora_saida} onChange={(event) => setConvertForm({ ...convertForm, hora_saida: event.target.value })} className="input-field" />
                  </div>
                  <div>
                    <label className="input-label">Combustivel na Saida</label>
                    <select value={convertForm.combustivel_saida} onChange={(event) => setConvertForm({ ...convertForm, combustivel_saida: event.target.value })} className="input-field">
                      <option value="">Selecione</option>
                      {fuelOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="input-label">KM Livres</label>
                    <input type="number" value={convertForm.km_livres} onChange={(event) => setConvertForm({ ...convertForm, km_livres: Number(event.target.value) || 0 })} className="input-field" />
                  </div>
                  <div>
                    <label className="input-label">Valor KM Excedente</label>
                    <input type="number" step="0.01" value={convertForm.valor_km_excedente} onChange={(event) => setConvertForm({ ...convertForm, valor_km_excedente: Number(event.target.value) || 0 })} className="input-field" />
                  </div>
                  <div>
                    <label className="input-label">Desconto</label>
                    <input type="number" step="0.01" value={convertForm.desconto} onChange={(event) => setConvertForm({ ...convertForm, desconto: Number(event.target.value) || 0 })} className="input-field" />
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm space-y-2">
                  <div className="flex justify-between"><span>KM atual do veiculo</span><strong>{(selectedConvertVehicle?.km_atual || selectedConvertVehicle?.quilometragem || 0).toLocaleString('pt-BR')}</strong></div>
                  <div className="flex justify-between"><span>Valor previsto do contrato</span><strong>{formatCurrency(valorPrevistoConversao)}</strong></div>
                </div>

                <div>
                  <label className="input-label">Observacoes</label>
                  <textarea rows={4} value={convertForm.observacoes} onChange={(event) => setConvertForm({ ...convertForm, observacoes: event.target.value })} className="input-field" />
                </div>
              </div>

              <div className="modal-footer">
                <button onClick={() => setConvertReservation(null)} className="btn-secondary" disabled={convertMutation.isPending}>Cancelar</button>
                <button onClick={handleConvert} className="btn-primary" disabled={convertMutation.isPending}>
                  {convertMutation.isPending ? 'Convertendo...' : 'Gerar Contrato'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Deletar Reserva"
        message="Tem certeza que deseja deletar esta reserva? Esta acao nao pode ser desfeita."
        confirmText="Deletar"
        cancelText="Cancelar"
        isDanger
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)}
        onCancel={() => setDeleteConfirm({ isOpen: false })}
      />
    </AppLayout>
  )
}

export default Reservas
