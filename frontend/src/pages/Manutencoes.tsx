import React, { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CalendarClock, CheckCircle2, Edit, Gauge, Plus, Sparkles, Trash2, Wrench, X } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import toast from 'react-hot-toast'
import AppLayout from '@/components/layout/AppLayout'
import CurrencyInput from '@/components/shared/CurrencyInput'
import DataTable from '@/components/shared/DataTable'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import { Manutencao, Veiculo, PaginatedResponse, PaginationParams } from '@/types'
import { cn, formatCurrency, formatDate } from '@/lib/utils'

type MaintenanceStatus = 'pendente' | 'agendada' | 'em_andamento' | 'concluida' | 'cancelada'
type MaintenanceUrgencyTone = 'critica' | 'atencao' | 'info' | 'ok'

interface MaintenanceSummary {
  total_manutencoes: number
  manutencoes_abertas: number
  manutencoes_pendentes: number
  manutencoes_agendadas: number
  manutencoes_em_andamento: number
  total_custo: number
  vencendo_em_30_dias: number
  vencidas_por_data: number
  vencidas_por_km: number
  criticas: number
  alertas: Array<{
    id: string
    titulo: string
    descricao: string
    urgencia: 'critica' | 'atencao' | 'info'
    placa?: string
    data_proxima?: string | null
    km_proxima?: number | null
  }>
}

interface MaintenanceFormData {
  veiculo_id: string
  data_realizada: string
  data_proxima: string
  tipo: 'preventiva' | 'corretiva'
  descricao: string
  custo: number
  oficina: string
  km_realizada: number
  km_proxima: number
  status: MaintenanceStatus
}

type VehicleOption = Veiculo & {
  quilometragem: number
}

const today = () => new Date().toISOString().split('T')[0]
const formatKm = (value?: number | null) =>
  `${new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(Number(value || 0))} km`
const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const defaultFormData = (): MaintenanceFormData => ({
  veiculo_id: '',
  data_realizada: today(),
  data_proxima: today(),
  tipo: 'preventiva',
  descricao: '',
  custo: '' as any,
  oficina: '',
  km_realizada: '' as any,
  km_proxima: '' as any,
  status: 'agendada',
})

const normalizeMaintenanceStatus = (status?: string): MaintenanceStatus => {
  if (status === 'em_progresso') return 'em_andamento'
  if (status === 'agendada') return 'agendada'
  if (status === 'concluida') return 'concluida'
  if (status === 'cancelada') return 'cancelada'
  return 'pendente'
}

const isOpenStatus = (status?: string) =>
  ['pendente', 'agendada', 'em_andamento', 'em_progresso'].includes(status || '')

const statusLabel = (status?: string) => {
  switch (normalizeMaintenanceStatus(status)) {
    case 'agendada':
      return 'Agendada'
    case 'em_andamento':
      return 'Em andamento'
    case 'concluida':
      return 'Concluida'
    case 'cancelada':
      return 'Cancelada'
    default:
      return 'Pendente'
  }
}

const statusClass = (status?: string) => {
  switch (normalizeMaintenanceStatus(status)) {
    case 'agendada':
      return 'bg-blue-50 text-blue-700 border border-blue-200'
    case 'em_andamento':
      return 'bg-amber-50 text-amber-700 border border-amber-200'
    case 'concluida':
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
    case 'cancelada':
      return 'bg-rose-50 text-rose-700 border border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border border-slate-200'
  }
}

const urgencyClass = (tone: MaintenanceUrgencyTone) => {
  switch (tone) {
    case 'critica':
      return 'bg-red-50 text-red-700 border border-red-200'
    case 'atencao':
      return 'bg-amber-50 text-amber-700 border border-amber-200'
    case 'ok':
      return 'bg-emerald-50 text-emerald-700 border border-emerald-200'
    default:
      return 'bg-blue-50 text-blue-700 border border-blue-200'
  }
}

const CountUpValue: React.FC<{
  value: number
  formatter?: (value: number) => string
  className?: string
}> = ({ value, formatter = (current) => Math.round(current).toLocaleString('pt-BR'), className }) => {
  const [displayValue, setDisplayValue] = useState(value)

  useEffect(() => {
    if (typeof window === 'undefined') {
      setDisplayValue(value)
      return
    }

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      setDisplayValue(value)
      return
    }

    const startValue = displayValue
    const delta = value - startValue
    const duration = 650
    const startedAt = performance.now()
    let frameId = 0

    const step = (now: number) => {
      const progress = clamp((now - startedAt) / duration, 0, 1)
      const eased = 1 - (1 - progress) ** 3
      setDisplayValue(startValue + delta * eased)
      if (progress < 1) {
        frameId = window.requestAnimationFrame(step)
      }
    }

    frameId = window.requestAnimationFrame(step)
    return () => window.cancelAnimationFrame(frameId)
  }, [displayValue, value])

  return <span className={className}>{formatter(displayValue)}</span>
}

const getMaintenanceUrgency = (maintenance: Manutencao) => {
  const status = maintenance.status_original || maintenance.status
  if (!isOpenStatus(status)) {
    return {
      tone: 'ok' as MaintenanceUrgencyTone,
      label: 'Controlada',
      detail: status === 'cancelada' ? 'Ordem cancelada' : 'Sem pressao operacional',
    }
  }

  const kmAtual = Number(maintenance.veiculo?.km_atual || 0)
  const kmProxima = maintenance.km_proxima ?? maintenance.quilometragem
  const kmRestante = kmProxima !== undefined && kmProxima !== null ? Number(kmProxima) - kmAtual : null
  const dataProxima = maintenance.data_proxima || maintenance.data_manutencao
  const diasRestantes = dataProxima
    ? Math.ceil((new Date(dataProxima).getTime() - new Date(today()).getTime()) / 86400000)
    : null

  if ((kmRestante !== null && kmRestante <= 0) || (diasRestantes !== null && diasRestantes < 0)) {
    return {
      tone: 'critica' as MaintenanceUrgencyTone,
      label: 'Critica',
      detail:
        kmRestante !== null && kmRestante <= 0
          ? `KM estourado em ${formatKm(Math.abs(kmRestante))}`
          : `Atrasada ha ${Math.abs(diasRestantes || 0)} dia(s)`,
    }
  }

  if ((kmRestante !== null && kmRestante <= 500) || (diasRestantes !== null && diasRestantes <= 7)) {
    return {
      tone: 'atencao' as MaintenanceUrgencyTone,
      label: 'Atencao',
      detail:
        kmRestante !== null && kmRestante <= 500
          ? `Faltam ${formatKm(kmRestante)}`
          : `Vence em ${diasRestantes || 0} dia(s)`,
    }
  }

  return {
    tone: 'info' as MaintenanceUrgencyTone,
    label: 'Planejada',
    detail:
      kmRestante !== null
        ? `Janela em ${formatKm(kmRestante)}`
        : dataProxima
          ? `Programada para ${formatDate(dataProxima)}`
          : 'Aguardando janela',
  }
}

const Manutencoes: React.FC = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingMaintenance, setEditingMaintenance] = useState<Manutencao | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [statusFilter, setStatusFilter] = useState<string>('todos')
  const [typeFilter, setTypeFilter] = useState<string>('todos')
  const [search, setSearch] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState<any>(defaultFormData)

  const { data, isLoading } = useQuery({
    queryKey: ['manutencoes', pagination, statusFilter, typeFilter, search],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/manutencoes', {
        params: {
          page: pagination.page,
          limit: pagination.limit,
          search: search || undefined,
          status: statusFilter !== 'todos' ? statusFilter : undefined,
          tipo: typeFilter !== 'todos' ? typeFilter : undefined,
        },
      })
      return data
    },
  })

  const { data: resumoData } = useQuery({
    queryKey: ['manutencoes-resumo'],
    queryFn: async () => {
      const { data } = await api.get<MaintenanceSummary>('/manutencoes/resumo')
      return data
    },
  })

  const { data: veiculos } = useQuery({
    queryKey: ['veiculos-select'],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/veiculos', { params: { limit: 1000 } })
      return data
    },
  })

  const vehicleOptions = useMemo<VehicleOption[]>(
    () =>
      (veiculos?.data || []).map((vehicle: any) => ({
        ...vehicle,
        quilometragem: Number(vehicle.km_atual || 0),
      })),
    [veiculos?.data],
  )

  const maintenanceRows = useMemo<Manutencao[]>(
    () =>
      (data?.data || []).map((maintenance: any) => ({
        ...maintenance,
        id: String(maintenance.id),
        veiculo_id: String(maintenance.veiculo_id),
      })),
    [data?.data],
  )

  const selectedVehicle = vehicleOptions.find((vehicle) => String(vehicle.id) === formData.veiculo_id)

  useEffect(() => {
    if (!isModalOpen || editingMaintenance || !selectedVehicle) return

    setFormData((current) => {
      const next = { ...current }
      let changed = false

      if (!current.km_realizada) {
        next.km_realizada = Number(selectedVehicle.km_atual || 0)
        changed = true
      }

      if (current.tipo === 'preventiva' && !current.km_proxima) {
        next.km_proxima = Number(selectedVehicle.km_atual || 0) + 10000
        changed = true
      }

      return changed ? next : current
    })
  }, [editingMaintenance, formData.tipo, isModalOpen, selectedVehicle])

  const invalidateMaintenanceViews = () => {
    queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
    queryClient.invalidateQueries({ queryKey: ['manutencoes-resumo'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    queryClient.invalidateQueries({ queryKey: ['veiculos'] })
    queryClient.invalidateQueries({ queryKey: ['veiculos-select'] })
  }

  const _legacyCreateMutation = useMutation({
    mutationFn: (payload: any) => api.post('/manutencoes', payload),
    onSuccess: () => {
      invalidateMaintenanceViews()
      setIsModalOpen(false)
      resetForm()
      toast.success('Manutenção criada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao criar manutenção')
    },
  })

  const _legacyUpdateMutation = useMutation({
    mutationFn: (formData: any) => api.patch(`/manutencoes/${editingMaintenance?.id}`, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
      setIsModalOpen(false)
      resetForm()
      toast.success('Manutenção atualizada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao atualizar manutenção')
    },
  })

  const _legacyDeleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/manutencoes/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
      setDeleteConfirm({ isOpen: false })
      toast.success('Manutenção deletada com sucesso!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.message || 'Erro ao deletar manutenção')
    },
  })

  const _legacyResetForm = () => {
    setFormData({
      veiculo_id: '',
      data_manutencao: new Date().toISOString().split('T')[0],
      tipo: 'preventiva',
      descricao: '',
      valor: '' as any,
      oficina: '',
      quilometragem: 0,
      status: 'pendente',
    })
    setEditingMaintenance(null)
  }

  const _legacyHandleOpenModal = (maintenance?: Manutencao) => {
    if (maintenance) {
      setEditingMaintenance(maintenance)
      setFormData(maintenance)
    } else {
      resetForm()
    }
    setIsModalOpen(true)
  }

  const _legacyHandleSubmit = (e: React.FormEvent) => {
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

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/manutencoes', payload),
    onSuccess: () => {
      invalidateMaintenanceViews()
      setIsModalOpen(false)
      resetForm()
      toast.success('Manutencao criada com sucesso')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.detail || error.response?.data?.message || 'Erro ao criar manutencao')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (payload: any) => api.patch(`/manutencoes/${editingMaintenance?.id}`, payload),
    onSuccess: () => {
      invalidateMaintenanceViews()
      setIsModalOpen(false)
      resetForm()
      toast.success('Manutencao atualizada com sucesso')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.detail || error.response?.data?.message || 'Erro ao atualizar manutencao')
    },
  })

  const completeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/manutencoes/${id}/completar`),
    onSuccess: () => {
      invalidateMaintenanceViews()
      toast.success('Ordem concluida e frota sincronizada')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.detail || error.response?.data?.message || 'Erro ao concluir manutencao')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/manutencoes/${id}`),
    onSuccess: () => {
      invalidateMaintenanceViews()
      setDeleteConfirm({ isOpen: false })
      toast.success('Manutencao excluida com sucesso')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.detail || error.response?.data?.message || 'Erro ao excluir manutencao')
    },
  })

  const resetForm = () => {
    setFormData(defaultFormData())
    setEditingMaintenance(null)
  }

  const handleOpenModal = (maintenance?: Manutencao) => {
    if (maintenance) {
      setEditingMaintenance(maintenance)
      setFormData({
        veiculo_id: String(maintenance.veiculo_id),
        data_realizada: (maintenance.data_realizada || maintenance.data_manutencao || today()).slice(0, 10),
        data_proxima: (maintenance.data_proxima || maintenance.data_manutencao || today()).slice(0, 10),
        tipo: maintenance.tipo,
        descricao: maintenance.descricao || '',
        custo: Number(maintenance.custo ?? maintenance.valor ?? 0),
        oficina: maintenance.oficina || '',
        km_realizada: Number(maintenance.km_realizada ?? maintenance.quilometragem ?? maintenance.veiculo?.km_atual ?? 0),
        km_proxima: Number(maintenance.km_proxima ?? maintenance.quilometragem ?? 0),
        status: normalizeMaintenanceStatus(maintenance.status_original || maintenance.status),
      })
    } else {
      resetForm()
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.veiculo_id || !formData.descricao.trim()) {
      toast.error('Selecione o veiculo e descreva a manutencao')
      return
    }

    if (formData.custo < 0) {
      toast.error('O custo nao pode ser negativo')
      return
    }

    if (isOpenStatus(formData.status) && !formData.data_proxima && formData.km_proxima <= 0) {
      toast.error('Informe a proxima data ou a proxima quilometragem')
      return
    }

    const payload = {
      veiculo_id: Number(formData.veiculo_id),
      data_realizada: formData.data_realizada || undefined,
      data_proxima: formData.data_proxima || undefined,
      tipo: formData.tipo,
      descricao: formData.descricao.trim(),
      custo: formData.custo || 0,
      oficina: formData.oficina.trim() || undefined,
      km_realizada: formData.km_realizada > 0 ? formData.km_realizada : Number(selectedVehicle?.km_atual || 0) || undefined,
      km_proxima: formData.km_proxima > 0 ? formData.km_proxima : undefined,
      status: normalizeMaintenanceStatus(formData.status),
    }

    if (editingMaintenance) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
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

  const heroBadges = [
    { label: 'Ordens abertas', value: resumoData?.manutencoes_abertas || 0, tone: 'slate' },
    { label: 'Criticas', value: resumoData?.criticas || 0, tone: (resumoData?.criticas || 0) > 0 ? 'red' : 'emerald' },
    {
      label: 'Bloqueios na frota',
      value: maintenanceRows.filter((maintenance) => maintenance.veiculo?.status === 'manutencao').length,
      tone: 'amber',
    },
  ]

  const summaryCards = [
    {
      label: 'Ordens abertas',
      value: resumoData?.manutencoes_abertas || 0,
      helper: `${resumoData?.manutencoes_agendadas || 0} agendadas`,
      icon: Wrench,
      tone: 'slate',
      currency: false,
    },
    {
      label: 'Criticas por KM',
      value: resumoData?.vencidas_por_km || 0,
      helper: 'Revisoes estouradas pela quilometragem',
      icon: Gauge,
      tone: 'amber',
      currency: false,
    },
    {
      label: 'Criticas por data',
      value: resumoData?.vencidas_por_data || 0,
      helper: 'Ordens vencidas ou atrasadas',
      icon: CalendarClock,
      tone: 'red',
      currency: false,
    },
    {
      label: 'Custo planejado',
      value: resumoData?.total_custo || 0,
      helper: `${resumoData?.vencendo_em_30_dias || 0} revisoes nos proximos 30 dias`,
      icon: CheckCircle2,
      tone: 'emerald',
      currency: true,
    },
  ]

  const columns = [
    {
      key: 'veiculo_id' as const,
      label: 'Veículo',
      render: (_: any, row: any) => <span className="text-slate-900">{row.veiculo?.placa || '-'}</span>,
    },
    {
      key: 'tipo' as const,
      label: 'Tipo',
      render: (tipo: string) =>
        tipo === 'preventiva' ? (
          <span className="badge-info text-xs px-2 py-1">Preventiva</span>
        ) : (
          <span className="badge-danger text-xs px-2 py-1">Corretiva</span>
        ),
    },
    {
      key: 'data_realizada' as const,
      label: 'Data',
      render: (_: string, row: any) => <span className="text-slate-700">{formatDate(row.data_realizada || row.data_proxima)}</span>,
    },
    {
      key: 'oficina' as const,
      label: 'Oficina',
      render: (oficina: string) => <span className="text-slate-700">{oficina || '-'}</span>,
    },
    {
      key: 'custo' as const,
      label: 'Custo',
      render: (value: number, row: any) => <span className="font-semibold text-slate-900">{formatCurrency(value ?? row.valor ?? 0)}</span>,
    },
        {
      key: 'status' as const,
      label: 'Status',
      render: (status: string) => <span className={cn('inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold', statusClass(status))}>{statusLabel(status)}</span>,
    },
    {
      key: 'id' as const,
      label: 'Ações',
      render: (_: any, row: Manutencao) => (
        <div className="flex items-center gap-2">
          {isOpenStatus(row.status_original || row.status) && (
            <button
              onClick={() => completeMutation.mutate(row.id)}
              className="btn-icon p-2 text-emerald-600 hover:bg-emerald-50 rounded transition-colors"
              title="Concluir manutencao"
              disabled={completeMutation.isPending}
            >
              <CheckCircle2 size={16} />
            </button>
          )}
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
        <section className="dashboard-hero animate-fade-in-up">
          <div className="dashboard-hero-glow" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="dashboard-hero-pill">
                  <Wrench size={16} />
                  Oficina operacional
                </span>
                <span className="dashboard-hero-pill dashboard-hero-pill-muted">
                  Bloqueio automatico, fila por KM e calendario da frota
                </span>
              </div>
              <h1 className="mt-4 text-4xl font-display font-bold text-slate-950">Manutencoes da frota</h1>
              <p className="mt-3 max-w-2xl text-base text-slate-600">
                Bem-vindo, {user?.nome || 'Operador'}. Agora voce enxerga risco por quilometragem e por data,
                acompanha bloqueios automaticos e libera a frota assim que a ordem for concluida.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {heroBadges.map((badge) => (
                <div
                  key={badge.label}
                  className={cn(
                    'dashboard-hero-chip',
                    badge.tone === 'red' && 'dashboard-hero-chip-red',
                    badge.tone === 'emerald' && 'dashboard-hero-chip-emerald',
                    badge.tone === 'amber' && 'dashboard-hero-chip-amber',
                  )}
                >
                  <p className="text-xs uppercase tracking-[0.18em] text-current/70">{badge.label}</p>
                  <CountUpValue value={badge.value} className="mt-2 block text-2xl font-display font-bold text-slate-950" />
                </div>
              ))}
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4 stagger-children">
          {summaryCards.map((card) => {
            const Icon = card.icon
            return (
              <div key={card.label} className="card animate-fade-in-up overflow-hidden">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-500">{card.label}</p>
                    {card.currency ? (
                      <CountUpValue
                        value={card.value}
                        formatter={(value) => formatCurrency(value)}
                        className="mt-3 block text-3xl font-display font-bold text-slate-950"
                      />
                    ) : (
                      <CountUpValue value={card.value} className="mt-3 block text-3xl font-display font-bold text-slate-950" />
                    )}
                  </div>
                  <div
                    className={cn(
                      'rounded-2xl p-3',
                      card.tone === 'slate' && 'bg-slate-100 text-slate-700',
                      card.tone === 'amber' && 'bg-amber-100 text-amber-700',
                      card.tone === 'red' && 'bg-red-100 text-red-700',
                      card.tone === 'emerald' && 'bg-emerald-100 text-emerald-700',
                    )}
                  >
                    <Icon size={20} />
                  </div>
                </div>
                <p className="mt-3 text-sm text-slate-500">{card.helper}</p>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all duration-700',
                      card.tone === 'slate' && 'bg-slate-700',
                      card.tone === 'amber' && 'bg-amber-500',
                      card.tone === 'red' && 'bg-red-500',
                      card.tone === 'emerald' && 'bg-emerald-500',
                    )}
                    style={{ width: `${Math.min(card.currency ? Number(card.value) / 50 : Number(card.value) * 18, 100)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)] animate-fade-in-up" style={{ animationDelay: '80ms' }}>
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-red-50 p-3 text-red-600">
                <AlertTriangle size={22} className={cn((resumoData?.criticas || 0) > 0 && 'animate-pulse')} />
              </div>
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.18em] text-slate-400">Alertas operacionais</p>
                <h2 className="mt-1 text-2xl font-display font-bold text-slate-950">Fila inteligente da oficina</h2>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {(resumoData?.alertas || []).length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-center">
                  <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600">
                    <CheckCircle2 size={26} />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold text-slate-900">Nenhuma manutencao critica agora</h3>
                  <p className="mt-2 text-sm text-slate-500">A frota esta dentro da janela de revisao planejada.</p>
                </div>
              ) : (
                (resumoData?.alertas || []).map((alerta, index) => (
                  <div
                    key={alerta.id}
                    className={cn(
                      'rounded-3xl border px-5 py-4 animate-fade-in-up',
                      alerta.urgencia === 'critica' && 'border-red-200 bg-red-50/80',
                      alerta.urgencia === 'atencao' && 'border-amber-200 bg-amber-50/80',
                      alerta.urgencia === 'info' && 'border-blue-200 bg-blue-50/80',
                    )}
                    style={{ animationDelay: `${index * 60}ms` }}
                  >
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={cn('inline-flex rounded-full px-3 py-1 text-xs font-semibold', urgencyClass(alerta.urgencia))}>
                            {alerta.urgencia === 'critica' ? 'Critica' : alerta.urgencia === 'atencao' ? 'Atencao' : 'Info'}
                          </span>
                          {alerta.placa && <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{alerta.placa}</span>}
                        </div>
                        <h3 className="mt-3 text-lg font-semibold text-slate-950">{alerta.titulo}</h3>
                        <p className="mt-1 text-sm text-slate-600">{alerta.descricao}</p>
                      </div>
                      <div className="rounded-2xl bg-white/80 px-3 py-3 text-sm text-slate-600">
                        <p>Data alvo: <strong className="text-slate-900">{formatDate(alerta.data_proxima || null)}</strong></p>
                        <p className="mt-1">KM alvo: <strong className="text-slate-900">{alerta.km_proxima ? formatKm(alerta.km_proxima) : 'Sem alvo'}</strong></p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card border-primary-100 bg-[linear-gradient(180deg,rgba(240,248,255,0.98),rgba(255,255,255,0.98))]">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-primary-100 p-3 text-primary-dark">
                <Sparkles size={22} />
              </div>
              <div>
                <p className="text-sm uppercase tracking-[0.18em] text-primary-dark/70">Fluxo melhorado</p>
                <h2 className="mt-1 text-2xl font-display font-bold text-slate-950">Operacao mais segura</h2>
              </div>
            </div>

            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              <li className="rounded-2xl border border-primary-100 bg-white/92 px-4 py-3">Ordens abertas podem colocar o carro em manutencao automaticamente.</li>
              <li className="rounded-2xl border border-primary-100 bg-white/92 px-4 py-3">Concluir a manutencao devolve o veiculo para disponibilidade quando nao ha outro bloqueio.</li>
              <li className="rounded-2xl border border-primary-100 bg-white/92 px-4 py-3">A tela agora mostra risco por data e quilometragem sem depender de memoria operacional.</li>
            </ul>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="page-title flex items-center gap-2">
              <Wrench className="text-primary" size={32} />
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
            {['todos', 'pendente', 'agendada', 'em_andamento', 'concluida', 'cancelada'].map((status) => (
              <button
                key={status}
                onClick={() => handleStatusFilter(status)}
                className={`filter-tab text-sm ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos'
                  ? 'Todos'
                  : status === 'em_andamento'
                    ? 'Em Andamento'
                    : status === 'agendada'
                      ? 'Agendadas'
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
              <div className="empty-state-icon bg-primary-50 mb-4">
                <Wrench className="text-primary" size={40} />
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
              data={maintenanceRows}
              isLoading={isLoading}
              searchPlaceholder="Buscar por descricao ou oficina..."
              onSearch={(value) => {
                setSearch(value)
                setPagination({ ...pagination, page: 1 })
              }}
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
          <div className="modal-content max-w-4xl w-full flex flex-col max-h-[92vh]" onClick={(e) => e.stopPropagation()}>
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

            <form
              id="manutencao-form"
              onSubmit={handleSubmit}
              className="px-6 py-5 overflow-y-auto max-h-[calc(92vh-130px)] space-y-4"
            >
              <div>
                <label className="input-label">Veículo *</label>
                <select
                  value={formData.veiculo_id}
                  onChange={(e) => setFormData({ ...formData, veiculo_id: e.target.value })}
                  className="input-field"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  <option value="">Selecione um veículo</option>
                  {vehicleOptions.map((v) => (
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
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="input-label">Data da execucao</label>
                  <input
                    type="date"
                    value={formData.data_realizada}
                    onChange={(e) => setFormData({ ...formData, data_realizada: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
                <div>
                  <label className="input-label">Proxima data</label>
                  <input
                    type="date"
                    value={formData.data_proxima}
                    onChange={(e) => setFormData({ ...formData, data_proxima: e.target.value })}
                    className="input-field"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
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
              <CurrencyInput
                label="Custo da manutencao"
                value={formData.custo}
                onChange={(custo) => setFormData({ ...formData, custo })}
                disabled={createMutation.isPending || updateMutation.isPending}
              />

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
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="input-label">KM da execucao</label>
                  <input
                    type="number"
                    value={formData.km_realizada}
                    onChange={(e) => setFormData({ ...formData, km_realizada: Number(e.target.value) || 0 })}
                    min="0"
                    className="input-field"
                    placeholder="KM atual do veiculo"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
                <div>
                  <label className="input-label">Proxima revisao por KM</label>
                  <input
                    type="number"
                    value={formData.km_proxima}
                    onChange={(e) => setFormData({ ...formData, km_proxima: Number(e.target.value) || 0 })}
                    min="0"
                    className="input-field"
                    placeholder="Ex.: 35000"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  />
                </div>
              </div>

              <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-blue-700/70">Planejamento rapido</p>
                    <p className="mt-1 text-sm text-slate-700">
                      KM atual do veiculo: <strong className="text-slate-900">{formatKm(selectedVehicle?.km_atual)}</strong>
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => setFormData({ ...formData, km_realizada: Number(selectedVehicle?.km_atual || 0) })}
                      disabled={!selectedVehicle}
                    >
                      Usar KM atual
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      onClick={() => setFormData({ ...formData, km_proxima: Number(selectedVehicle?.km_atual || formData.km_realizada || 0) + 10000 })}
                      disabled={!selectedVehicle}
                    >
                      Sugerir +10.000 km
                    </button>
                  </div>
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
                  <option value="agendada">Agendada</option>
                  <option value="em_andamento">Em andamento</option>
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
                form="manutencao-form"
                className="btn-primary"
                disabled={createMutation.isPending || updateMutation.isPending}
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


