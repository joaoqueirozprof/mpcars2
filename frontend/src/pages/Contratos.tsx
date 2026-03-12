import React, { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  CheckCircle,
  Download,
  Edit,
  FileText,
  Loader2,
  Plus,
  Printer,
  Search,
  Trash2,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import { useConfig } from '@/contexts/ConfigContext'
import { calculateDays, formatCurrency, formatDate } from '@/lib/utils'
import api from '@/services/api'
import { Contrato, PaginatedResponse, PaginationParams, Veiculo } from '@/types'

type StatusFilter = 'todos' | 'ativo' | 'finalizado' | 'cancelado' | 'atraso'

type ContractForm = {
  cliente_id: string
  veiculo_id: string
  tipo: 'cliente' | 'empresa'
  data_inicio: string
  data_fim: string
  km_atual_veiculo: number
  hora_saida: string
  combustivel_saida: string
  km_livres: number
  valor_diaria: number
  valor_km_excedente: number
  desconto: number
  observacoes: string
}

type CloseoutForm = {
  km_atual_veiculo: number
  combustivel_retorno: string
  itens_checklist: CloseoutChecklist
  valor_avarias: number
  taxa_combustivel: number
  taxa_limpeza: number
  taxa_higienizacao: number
  taxa_pneus: number
  taxa_acessorios: number
  valor_franquia_seguro: number
  taxa_administrativa: number
  desconto: number
  status_pagamento: PaymentStatus
  forma_pagamento: string
  data_vencimento_pagamento: string
  data_pagamento: string
  valor_recebido: number
  observacoes: string
}

type PaymentStatus = 'pendente' | 'pago' | 'cancelado'

type CloseoutChecklistKey =
  | 'macaco'
  | 'estepe'
  | 'chave_de_roda'
  | 'triangulo'
  | 'documento'
  | 'chave_reserva'
  | 'tapetes'
  | 'multimidia'
  | 'limpeza_ok'

type CloseoutChecklist = Record<CloseoutChecklistKey, boolean>

type CloseoutFeeFieldKey =
  | 'valor_avarias'
  | 'taxa_combustivel'
  | 'taxa_limpeza'
  | 'taxa_higienizacao'
  | 'taxa_pneus'
  | 'taxa_acessorios'
  | 'valor_franquia_seguro'
  | 'taxa_administrativa'

const fuelOptions = ['1/4', '1/2', '3/4', 'Cheio']
const paymentStatusOptions: Array<{ value: PaymentStatus; label: string }> = [
  { value: 'pago', label: 'Pago agora' },
  { value: 'pendente', label: 'Ficou pendente' },
  { value: 'cancelado', label: 'Cancelado' },
]
const paymentMethodOptions = ['Pix', 'Cartao', 'Dinheiro', 'Transferencia', 'Boleto', 'Faturado']

const closeoutChecklistFields: Array<{ key: CloseoutChecklistKey; label: string; hint: string }> = [
  { key: 'macaco', label: 'Macaco', hint: 'Equipamento presente no carro' },
  { key: 'estepe', label: 'Estepe', hint: 'Roda reserva devolvida' },
  { key: 'chave_de_roda', label: 'Chave de roda', hint: 'Ferramenta de troca de pneu' },
  { key: 'triangulo', label: 'Triangulo', hint: 'Item de seguranca obrigatorio' },
  { key: 'documento', label: 'Documento', hint: 'CRLV ou documento liberado' },
  { key: 'chave_reserva', label: 'Chave reserva', hint: 'Chave extra ou chaveiro devolvido' },
  { key: 'tapetes', label: 'Tapetes', hint: 'Jogo de tapetes conferido' },
  { key: 'multimidia', label: 'Multimidia / som', hint: 'Som, tela ou acessorio eletronico' },
  { key: 'limpeza_ok', label: 'Limpeza geral', hint: 'Veiculo voltou limpo e organizado' },
]

const closeoutFeeFields: Array<{ key: CloseoutFeeFieldKey; label: string; hint: string }> = [
  { key: 'valor_avarias', label: 'Avarias / funilaria', hint: 'Batidas, riscos, lanternas, para-choque' },
  { key: 'taxa_combustivel', label: 'Taxa de combustivel', hint: 'Retorno abaixo do nivel combinado' },
  { key: 'taxa_limpeza', label: 'Limpeza simples', hint: 'Sujeira interna ou externa fora do normal' },
  { key: 'taxa_higienizacao', label: 'Higienizacao / odor', hint: 'Fumaca, mau cheiro ou sujeira pesada' },
  { key: 'taxa_pneus', label: 'Pneus / rodas', hint: 'Pneu furado, roda riscada, calibragem extrema' },
  { key: 'taxa_acessorios', label: 'Acessorios / documentos', hint: 'Chave, estepe, triangulo, documentos, tapetes' },
  { key: 'valor_franquia_seguro', label: 'Franquia de seguro', hint: 'Quando houver sinistro com coparticipacao' },
  { key: 'taxa_administrativa', label: 'Taxa administrativa', hint: 'Custos operacionais extras na devolucao' },
]

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail || error?.response?.data?.message || fallback

const displayStatus = (contrato: Contrato) => {
  if (contrato.status === 'ativo' && new Date(contrato.data_fim) < new Date()) {
    return 'atraso'
  }
  return contrato.status
}

const statusLabel = (status: string) =>
  ({
    ativo: 'Ativo',
    finalizado: 'Finalizado',
    cancelado: 'Cancelado',
    atraso: 'Atraso',
  }[status] || status)

const statusClass = (status: string) =>
  ({
    ativo: 'badge-success',
    finalizado: 'badge-info',
    cancelado: 'badge-danger',
    atraso: 'badge-warning',
  }[status] || 'badge-info')

const paymentStatusLabel = (status?: string) =>
  ({
    pago: 'Pago',
    pendente: 'Pendente',
    cancelado: 'Cancelado',
  }[status || 'pendente'] || 'Pendente')

const paymentStatusClass = (status?: string) =>
  ({
    pago: 'badge-success',
    pendente: 'badge-warning',
    cancelado: 'badge-danger',
  }[status || 'pendente'] || 'badge-warning')

const toDateInput = (value?: string) => (value ? value.slice(0, 10) : '')

const getRoundedDaysBetween = (start?: string, end?: string | Date) => {
  if (!start || !end) return 0

  const startDate = new Date(start)
  const endDate = end instanceof Date ? end : new Date(end)
  const diffMs = Math.max(endDate.getTime() - startDate.getTime(), 0)
  return Math.max(1, Math.ceil(diffMs / (1000 * 60 * 60 * 24)))
}

const buildCloseoutChecklist = (veiculo?: any): CloseoutChecklist => {
  const source = veiculo?.checklist || {}
  const resolve = (keys: string[]) => {
    for (const key of keys) {
      if (source[key] !== undefined) return Boolean(source[key])
      if (veiculo?.[key] !== undefined) return Boolean(veiculo[key])
    }
    return true
  }

  return {
    macaco: resolve(['macaco', 'checklist_item_1']),
    estepe: resolve(['estepe', 'checklist_item_2']),
    chave_de_roda: resolve(['chave_de_roda', 'ferramentas', 'checklist_item_3']),
    triangulo: resolve(['triangulo', 'checklist_item_4']),
    documento: resolve(['documento', 'documentos', 'checklist_item_5']),
    chave_reserva: resolve(['chave_reserva', 'chave_extra']),
    tapetes: resolve(['tapetes', 'checklist_item_8']),
    multimidia: resolve(['multimidia', 'som', 'cd_player', 'checklist_item_9', 'checklist_item_10']),
    limpeza_ok: resolve(['limpeza_ok', 'limpo']),
  }
}

const Contratos: React.FC = () => {
  const queryClient = useQueryClient()
  const config = useConfig()

  const buildForm = (): ContractForm => ({
    cliente_id: '',
    veiculo_id: '',
    tipo: 'cliente',
    data_inicio: '',
    data_fim: '',
    km_atual_veiculo: 0,
    hora_saida: '',
    combustivel_saida: '',
    km_livres: 0,
    valor_diaria: config.valor_diaria_padrao || 0,
    valor_km_excedente: 0,
    desconto: 0,
    observacoes: '',
  })

  const [pagination, setPagination] = useState<PaginationParams>({ page: 1, limit: 10 })
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('todos')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingContract, setEditingContract] = useState<Contrato | null>(null)
  const [closingContract, setClosingContract] = useState<Contrato | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; id?: string }>({ isOpen: false })
  const [formData, setFormData] = useState<ContractForm>(buildForm())
  const [closeoutData, setCloseoutData] = useState<CloseoutForm>({
    km_atual_veiculo: 0,
    combustivel_retorno: '',
    itens_checklist: buildCloseoutChecklist(),
    valor_avarias: 0,
    taxa_combustivel: 0,
    taxa_limpeza: 0,
    taxa_higienizacao: 0,
    taxa_pneus: 0,
    taxa_acessorios: 0,
    valor_franquia_seguro: 0,
    taxa_administrativa: 0,
    desconto: 0,
    status_pagamento: 'pago',
    forma_pagamento: '',
    data_vencimento_pagamento: '',
    data_pagamento: new Date().toISOString().split('T')[0],
    valor_recebido: 0,
    observacoes: '',
  })

  const { data: contratos, isLoading } = useQuery({
    queryKey: ['contratos', pagination, statusFilter, searchTerm],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Contrato>>('/contratos', {
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
      const { data } = await api.get<PaginatedResponse<Veiculo>>('/veiculos', { params: { limit: 1000 } })
      return (data.data || []).map((veiculo: any) => ({
        ...veiculo,
        km_atual: veiculo.km_atual ?? veiculo.quilometragem ?? 0,
        quilometragem: veiculo.quilometragem ?? veiculo.km_atual ?? 0,
      }))
    },
  })

  const availableVehicles = useMemo(
    () =>
      (veiculos || []).filter(
        (veiculo: any) =>
          veiculo.status === 'disponivel' ||
          String(veiculo.id) === String(formData.veiculo_id) ||
          String(veiculo.id) === String(editingContract?.veiculo_id)
      ),
    [veiculos, formData.veiculo_id, editingContract]
  )

  const selectedCliente = clientes?.find((cliente: any) => String(cliente.id) === String(formData.cliente_id))
  const selectedVeiculo = (veiculos || []).find((veiculo: any) => String(veiculo.id) === String(formData.veiculo_id))

  const invalidateCoreQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['contratos'] })
    queryClient.invalidateQueries({ queryKey: ['veiculos-select'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post('/contratos', payload),
    onSuccess: () => {
      invalidateCoreQueries()
      setIsModalOpen(false)
      setEditingContract(null)
      setFormData(buildForm())
      toast.success('Contrato salvo com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao salvar contrato')),
  })

  const updateMutation = useMutation({
    mutationFn: (payload: any) => api.patch(`/contratos/${editingContract?.id}`, payload),
    onSuccess: () => {
      invalidateCoreQueries()
      setIsModalOpen(false)
      setEditingContract(null)
      setFormData(buildForm())
      toast.success('Contrato atualizado com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao atualizar contrato')),
  })

  const closeMutation = useMutation({
    mutationFn: (payload: any) => api.post(`/contratos/${closingContract?.id}/encerrar`, payload),
    onSuccess: () => {
      invalidateCoreQueries()
      setClosingContract(null)
      toast.success('Contrato encerrado com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao encerrar contrato')),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/contratos/${id}`),
    onSuccess: () => {
      invalidateCoreQueries()
      setDeleteConfirm({ isOpen: false })
      toast.success('Contrato deletado com sucesso!')
    },
    onError: (error: any) => toast.error(getErrorMessage(error, 'Erro ao deletar contrato')),
  })

  const handlePdf = async (contratoId: string, numero: string, print = false) => {
    setDownloadingPdf(contratoId)
    try {
      const response = await api.get(`/relatorios/contrato/${contratoId}/pdf`, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      if (print) {
        const printWindow = window.open(url, '_blank')
        if (printWindow) printWindow.onload = () => printWindow.print()
      } else {
        const link = document.createElement('a')
        link.href = url
        link.download = `contrato_${numero}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      }
      window.URL.revokeObjectURL(url)
    } catch {
      toast.error('Erro ao gerar PDF do contrato')
    } finally {
      setDownloadingPdf(null)
    }
  }

  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null)

  const openCreate = () => {
    setEditingContract(null)
    setFormData(buildForm())
    setIsModalOpen(true)
  }

  const openEdit = (contrato: Contrato) => {
    setEditingContract(contrato)
    setFormData({
      cliente_id: contrato.cliente_id,
      veiculo_id: contrato.veiculo_id,
      tipo: contrato.tipo || 'cliente',
      data_inicio: toDateInput(contrato.data_inicio),
      data_fim: toDateInput(contrato.data_fim),
      km_atual_veiculo: contrato.veiculo?.km_atual ?? contrato.quilometragem_inicial ?? 0,
      hora_saida: contrato.hora_saida || '',
      combustivel_saida: contrato.combustivel_saida || '',
      km_livres: contrato.km_livres || 0,
      valor_diaria: contrato.valor_diaria || 0,
      valor_km_excedente: contrato.valor_km_excedente || 0,
      desconto: contrato.desconto || 0,
      observacoes: contrato.observacoes || '',
    })
    setIsModalOpen(true)
  }

  const openCloseout = (contrato: Contrato) => {
    setClosingContract(contrato)
    setCloseoutData({
      km_atual_veiculo: contrato.veiculo?.km_atual ?? contrato.quilometragem_inicial ?? 0,
      combustivel_retorno: contrato.combustivel_retorno || '',
      itens_checklist: buildCloseoutChecklist(contrato.veiculo),
      valor_avarias: contrato.valor_avarias || 0,
      taxa_combustivel: contrato.taxa_combustivel || 0,
      taxa_limpeza: contrato.taxa_limpeza || 0,
      taxa_higienizacao: contrato.taxa_higienizacao || 0,
      taxa_pneus: contrato.taxa_pneus || 0,
      taxa_acessorios: contrato.taxa_acessorios || 0,
      valor_franquia_seguro: contrato.valor_franquia_seguro || 0,
      taxa_administrativa: contrato.taxa_administrativa || 0,
      desconto: contrato.desconto || 0,
      status_pagamento: contrato.status_pagamento || 'pago',
      forma_pagamento: contrato.forma_pagamento || '',
      data_vencimento_pagamento: contrato.data_vencimento_pagamento ? contrato.data_vencimento_pagamento.slice(0, 10) : new Date().toISOString().split('T')[0],
      data_pagamento: contrato.data_pagamento ? contrato.data_pagamento.slice(0, 10) : new Date().toISOString().split('T')[0],
      valor_recebido: contrato.valor_recebido || contrato.valor_total || 0,
      observacoes: '',
    })
  }

  const handleVehicleChange = (veiculoId: string) => {
    const veiculo: any = (veiculos || []).find((item: any) => String(item.id) === String(veiculoId))
    setFormData((current) => ({
      ...current,
      veiculo_id: veiculoId,
      km_atual_veiculo: veiculo?.km_atual || 0,
      valor_diaria: current.valor_diaria || veiculo?.valor_diaria || config.valor_diaria_padrao || 0,
    }))
  }

  const dias = formData.data_inicio && formData.data_fim ? calculateDays(formData.data_inicio, formData.data_fim) : 0
  const valorPreview = Math.max(dias * formData.valor_diaria - formData.desconto, 0)

  const closeoutKmRodado = closingContract
    ? Math.max(closeoutData.km_atual_veiculo - (closingContract.quilometragem_inicial || 0), 0)
    : 0
  const closeoutKmExcedente = closingContract
    ? Math.max(closeoutKmRodado - (closingContract.km_livres || 0), 0)
    : 0
  const closeoutValorKmExcedente = closingContract
    ? closeoutKmExcedente * (closingContract.valor_km_excedente || 0)
    : 0
  const closeoutBillingEnd = closingContract ? new Date(Math.max(new Date(closingContract.data_fim).getTime(), Date.now())) : null
  const closeoutDiasContratados = closingContract
    ? Math.max(closingContract.qtd_diarias || getRoundedDaysBetween(closingContract.data_inicio, closingContract.data_fim), 1)
    : 0
  const closeoutDiasFaturados = closingContract && closeoutBillingEnd
    ? getRoundedDaysBetween(closingContract.data_inicio, closeoutBillingEnd)
    : 0
  const closeoutValorBaseContratado = closingContract
    ? closeoutDiasContratados * (closingContract.valor_diaria || 0)
    : 0
  const closeoutValorBaseAtualizado = closingContract
    ? closeoutDiasFaturados * (closingContract.valor_diaria || 0)
    : 0
  const closeoutValorAtraso = Math.max(closeoutValorBaseAtualizado - closeoutValorBaseContratado, 0)
  const closeoutTaxasOperacionais = closeoutFeeFields.reduce(
    (total, field) => total + Number(closeoutData[field.key] || 0),
    0
  )
  const closeoutChecklistPendencias = closeoutChecklistFields.filter(
    (field) => !closeoutData.itens_checklist[field.key]
  )
  const closeoutFeeBreakdown = closeoutFeeFields
    .map((field) => ({ ...field, value: Number(closeoutData[field.key] || 0) }))
    .filter((field) => field.value > 0)
  const closeoutEstimativa = closingContract
    ? Math.max(closeoutValorBaseAtualizado + closeoutValorKmExcedente + closeoutTaxasOperacionais - closeoutData.desconto, 0)
    : 0

  const summary = useMemo(() => {
    const list = contratos?.data || []
    return {
      total: contratos?.total || 0,
      ativos: list.filter((contrato) => displayStatus(contrato) === 'ativo').length,
      atrasados: list.filter((contrato) => displayStatus(contrato) === 'atraso').length,
      valor: list.reduce((total, contrato) => total + (contrato.valor_total || 0), 0),
      pendentesFinanceiro: list.filter((contrato) => (contrato.status_pagamento || 'pendente') === 'pendente').length,
    }
  }, [contratos])

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!formData.cliente_id || !formData.veiculo_id || !formData.data_inicio || !formData.data_fim) {
      toast.error('Preencha cliente, veiculo e datas.')
      return
    }
    if (new Date(formData.data_fim) <= new Date(formData.data_inicio)) {
      toast.error('A data final precisa ser maior que a inicial.')
      return
    }

    const payload = {
      ...formData,
      qtd_diarias: dias,
      valor_total: valorPreview,
    }
    if (editingContract) updateMutation.mutate(payload)
    else createMutation.mutate(payload)
  }

  const handleCloseout = () => {
    if (!closingContract) return
    if (closeoutData.km_atual_veiculo <= 0) {
      toast.error('Informe o KM atual do veiculo.')
      return
    }
    if (closeoutData.km_atual_veiculo < (closingContract.quilometragem_inicial || 0)) {
      toast.error('O KM atual nao pode ser menor que o KM de retirada.')
      return
    }
    const payload = {
      ...closeoutData,
      data_pagamento:
        closeoutData.status_pagamento === 'pago'
          ? closeoutData.data_pagamento
          : '',
      valor_recebido:
        closeoutData.status_pagamento === 'pago' && closeoutData.valor_recebido <= 0
          ? closeoutEstimativa
          : closeoutData.status_pagamento === 'cancelado'
            ? 0
            : closeoutData.valor_recebido,
    }
    closeMutation.mutate(payload)
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="page-header">
          <div>
            <h1 className="page-title">Contratos</h1>
            <p className="page-subtitle">Locacao com retirada, acompanhamento e encerramento.</p>
          </div>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2">
            <Plus size={18} />
            Novo Contrato
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="kpi-card"><p className="kpi-label">Total</p><p className="kpi-value">{summary.total}</p></div>
          <div className="kpi-card"><p className="kpi-label">Ativos</p><p className="kpi-value text-green-600">{summary.ativos}</p></div>
          <div className="kpi-card"><p className="kpi-label">Atrasados</p><p className="kpi-value text-red-600">{summary.atrasados}</p></div>
          <div className="kpi-card"><p className="kpi-label">Financeiro Pendente</p><p className="kpi-value text-amber-600">{summary.pendentesFinanceiro}</p></div>
          <div className="kpi-card"><p className="kpi-label">Valor em Tela</p><p className="kpi-value text-purple-600">{formatCurrency(summary.valor)}</p></div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-4 py-2.5">
            <Search size={18} className="text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(event.target.value)
                setPagination({ ...pagination, page: 1 })
              }}
              className="flex-1 bg-transparent text-sm outline-none"
              placeholder="Buscar por numero, cliente, placa ou modelo..."
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {(['todos', 'ativo', 'finalizado', 'cancelado', 'atraso'] as StatusFilter[]).map((status) => (
              <button
                key={status}
                onClick={() => {
                  setStatusFilter(status)
                  setPagination({ ...pagination, page: 1 })
                }}
                className={`filter-tab ${statusFilter === status ? 'filter-tab-active' : 'filter-tab-inactive'}`}
              >
                {status === 'todos' ? 'Todos' : statusLabel(status)}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          {isLoading ? (
            <div className="space-y-3">{[...Array(5)].map((_, index) => <div key={index} className="h-12 bg-slate-100 rounded animate-pulse" />)}</div>
          ) : contratos?.data?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="table-header border-b border-slate-200">
                    <th className="table-cell text-left">Numero</th>
                    <th className="table-cell text-left">Cliente</th>
                    <th className="table-cell text-left">Veiculo</th>
                    <th className="table-cell text-left">Periodo</th>
                    <th className="table-cell text-right">Valor</th>
                    <th className="table-cell text-center">Status</th>
                    <th className="table-cell text-center">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {contratos.data.map((contrato) => {
                    const status = displayStatus(contrato)
                    return (
                      <tr key={contrato.id} className="table-row hover:bg-slate-50">
                        <td className="table-cell font-semibold text-slate-900">{contrato.numero}</td>
                        <td className="table-cell text-slate-700">{contrato.cliente?.nome || '-'}</td>
                        <td className="table-cell text-slate-700">
                          {contrato.veiculo ? `${contrato.veiculo.marca} ${contrato.veiculo.modelo}` : '-'}
                          <div className="text-xs text-slate-500">{contrato.veiculo?.placa || '-'}</div>
                        </td>
                        <td className="table-cell text-slate-600 text-sm">
                          {formatDate(contrato.data_inicio)} a {formatDate(contrato.data_fim)}
                        </td>
                        <td className="table-cell text-right font-semibold text-slate-900">
                          <div>{formatCurrency(contrato.valor_total)}</div>
                          <div className="mt-1 text-xs font-medium text-slate-500">
                            Recebido: {formatCurrency(contrato.valor_recebido || 0)}
                          </div>
                        </td>
                        <td className="table-cell text-center">
                          <div className="flex flex-col items-center gap-2">
                            <span className={`inline-block ${statusClass(status)}`}>{statusLabel(status)}</span>
                            <span className={`inline-block ${paymentStatusClass(contrato.status_pagamento)}`}>
                              {paymentStatusLabel(contrato.status_pagamento)}
                            </span>
                          </div>
                        </td>
                        <td className="table-cell text-center">
                          <div className="flex items-center justify-center gap-1">
                            <button onClick={() => handlePdf(contrato.id, contrato.numero)} className="p-1.5 hover:text-green-600" disabled={downloadingPdf === contrato.id}>
                              {downloadingPdf === contrato.id ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                            </button>
                            <button onClick={() => handlePdf(contrato.id, contrato.numero, true)} className="p-1.5 hover:text-purple-600"><Printer size={16} /></button>
                            {contrato.status === 'ativo' && <button onClick={() => openCloseout(contrato)} className="p-1.5 hover:text-emerald-600"><CheckCircle size={16} /></button>}
                            <button onClick={() => openEdit(contrato)} className="p-1.5 hover:text-blue-600"><Edit size={16} /></button>
                            <button onClick={() => setDeleteConfirm({ isOpen: true, id: contrato.id })} className="p-1.5 hover:text-red-600"><Trash2 size={16} /></button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-600">Mostrando {contratos.data.length} de {contratos.total} contratos</p>
                <div className="flex gap-2">
                  <button onClick={() => setPagination({ ...pagination, page: Math.max(1, pagination.page - 1) })} disabled={pagination.page === 1} className="btn-secondary btn-sm">Anterior</button>
                  <button onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })} disabled={pagination.page * pagination.limit >= (contratos.total || 0)} className="btn-secondary btn-sm">Proximo</button>
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon bg-slate-100"><FileText className="text-slate-400" size={48} /></div>
              <h3 className="mt-4 font-semibold text-slate-900">Nenhum contrato encontrado</h3>
            </div>
          )}
        </div>
      </div>

      {isModalOpen && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setIsModalOpen(false)}>
          <div className="modal-content max-w-2xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">{editingContract ? 'Editar Contrato' : 'Novo Contrato'}</h3>
              <button onClick={() => setIsModalOpen(false)} className="btn-icon"><X size={20} /></button>
            </div>
            <form onSubmit={handleSubmit} className="flex flex-1 min-h-0 flex-col overflow-hidden">
              <div className="modal-scroll-body space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Cliente *</label>
                    <select value={formData.cliente_id} onChange={(event) => setFormData({ ...formData, cliente_id: event.target.value })} className="input-field">
                      <option value="">Selecione</option>
                      {clientes?.map((cliente: any) => <option key={cliente.id} value={cliente.id}>{cliente.nome}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="input-label">Tipo</label>
                    <select value={formData.tipo} onChange={(event) => setFormData({ ...formData, tipo: event.target.value as 'cliente' | 'empresa' })} className="input-field">
                      <option value="cliente">Cliente</option>
                      <option value="empresa">Empresa</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="input-label">Veiculo *</label>
                  <select value={formData.veiculo_id} onChange={(event) => handleVehicleChange(event.target.value)} className="input-field">
                    <option value="">Selecione</option>
                    {availableVehicles.map((veiculo: any) => <option key={veiculo.id} value={veiculo.id}>{veiculo.placa} - {veiculo.marca} {veiculo.modelo}</option>)}
                  </select>
                </div>
                {selectedCliente && selectedVeiculo && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm text-slate-700">
                    {selectedCliente.nome} | {selectedVeiculo.marca} {selectedVeiculo.modelo} | KM atual {selectedVeiculo.km_atual || 0}
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div><label className="input-label">Data Inicio *</label><input type="date" value={formData.data_inicio} onChange={(event) => setFormData({ ...formData, data_inicio: event.target.value })} className="input-field" /></div>
                  <div><label className="input-label">Data Fim *</label><input type="date" value={formData.data_fim} onChange={(event) => setFormData({ ...formData, data_fim: event.target.value })} className="input-field" /></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-xs uppercase tracking-wide text-blue-700">KM Atual do Veiculo</p>
                    <p className="text-2xl font-bold text-blue-950 mt-2">{formData.km_atual_veiculo.toLocaleString('pt-BR')}</p>
                  </div>
                  <div><label className="input-label">Hora de Saida</label><input type="time" value={formData.hora_saida} onChange={(event) => setFormData({ ...formData, hora_saida: event.target.value })} className="input-field" /></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="input-label">Combustivel na Saida</label>
                    <select value={formData.combustivel_saida} onChange={(event) => setFormData({ ...formData, combustivel_saida: event.target.value })} className="input-field">
                      <option value="">Selecione</option>
                      {fuelOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </div>
                  <div><label className="input-label">KM Livres</label><input type="number" value={formData.km_livres} onChange={(event) => setFormData({ ...formData, km_livres: Number(event.target.value) || 0 })} className="input-field" /></div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div><label className="input-label">Valor Diaria *</label><input type="number" step="0.01" value={formData.valor_diaria} onChange={(event) => setFormData({ ...formData, valor_diaria: Number(event.target.value) || 0 })} className="input-field" /></div>
                  <div><label className="input-label">Valor KM Excedente</label><input type="number" step="0.01" value={formData.valor_km_excedente} onChange={(event) => setFormData({ ...formData, valor_km_excedente: Number(event.target.value) || 0 })} className="input-field" /></div>
                  <div><label className="input-label">Desconto</label><input type="number" step="0.01" value={formData.desconto} onChange={(event) => setFormData({ ...formData, desconto: Number(event.target.value) || 0 })} className="input-field" /></div>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm space-y-2">
                  <div className="flex justify-between"><span>Periodo</span><strong>{dias} dia(s)</strong></div>
                  <div className="flex justify-between"><span>Valor previsto</span><strong>{formatCurrency(valorPreview)}</strong></div>
                </div>
                <div><label className="input-label">Observacoes</label><textarea value={formData.observacoes} onChange={(event) => setFormData({ ...formData, observacoes: event.target.value })} rows={3} className="input-field" /></div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>{createMutation.isPending || updateMutation.isPending ? 'Salvando...' : 'Salvar Contrato'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {closingContract && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && !closeMutation.isPending && setClosingContract(null)}>
          <div className="modal-content max-w-6xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Encerrar Contrato</h3>
              <button onClick={() => setClosingContract(null)} className="btn-icon" disabled={closeMutation.isPending}><X size={20} /></button>
            </div>
            <div className="flex flex-1 min-h-0 flex-col overflow-hidden">
              <div className="modal-scroll-body space-y-6">
                <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-950">
                  <p className="font-semibold">Fechamento completo da devolucao</p>
                  <p className="mt-1 text-blue-900/80">
                    KM excedente e atraso entram automaticamente pelo contrato. Use as taxas abaixo para combustivel, limpeza, danos,
                    pneus, acessorios, franquia e outras ocorrencias da devolucao.
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.9fr)_minmax(320px,0.95fr)]">
                  <div className="space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                        <p className="text-xs uppercase tracking-wide text-slate-500">KM de Retirada</p>
                        <p className="text-2xl font-bold text-slate-900 mt-2">{(closingContract.quilometragem_inicial || 0).toLocaleString('pt-BR')}</p>
                      </div>
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Diarias Faturadas</p>
                        <p className="text-2xl font-bold text-slate-900 mt-2">{closeoutDiasFaturados}</p>
                        <p className="mt-2 text-sm text-slate-600">
                          Contratadas: {closeoutDiasContratados} | Base atualizada: {formatCurrency(closeoutValorBaseAtualizado)}
                        </p>
                      </div>
                      <div>
                        <label className="input-label">KM Atual do Veiculo *</label>
                        <input
                          type="number"
                          min={closingContract.quilometragem_inicial || 0}
                          value={closeoutData.km_atual_veiculo}
                          onChange={(event) => setCloseoutData({ ...closeoutData, km_atual_veiculo: Number(event.target.value) || 0 })}
                          className="input-field"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="input-label">Combustivel Retorno</label>
                        <select value={closeoutData.combustivel_retorno} onChange={(event) => setCloseoutData({ ...closeoutData, combustivel_retorno: event.target.value })} className="input-field">
                          <option value="">Selecione</option>
                          {fuelOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="input-label">Desconto Final</label>
                        <input type="number" step="0.01" value={closeoutData.desconto} onChange={(event) => setCloseoutData({ ...closeoutData, desconto: Number(event.target.value) || 0 })} className="input-field" />
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
                        <div>
                          <h4 className="text-base font-semibold text-slate-900">Checklist de devolucao</h4>
                          <p className="text-sm text-slate-500">Desmarque o que faltou ou voltou com problema na vistoria.</p>
                        </div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Conferencia fisica do veiculo</p>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {closeoutChecklistFields.map((field) => {
                          const checked = closeoutData.itens_checklist[field.key]
                          return (
                            <label
                              key={field.key}
                              className={`flex items-start gap-3 rounded-xl border p-4 cursor-pointer transition-colors ${
                                checked ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(event) =>
                                  setCloseoutData({
                                    ...closeoutData,
                                    itens_checklist: {
                                      ...closeoutData.itens_checklist,
                                      [field.key]: event.target.checked,
                                    },
                                  })
                                }
                                className="mt-1 h-4 w-4 rounded border-slate-300"
                              />
                              <div>
                                <p className="text-sm font-semibold text-slate-900">{field.label}</p>
                                <p className="mt-1 text-xs text-slate-500">{field.hint}</p>
                              </div>
                            </label>
                          )
                        })}
                      </div>
                      {closeoutChecklistPendencias.length > 0 && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                          Itens pendentes: {closeoutChecklistPendencias.map((field) => field.label).join(', ')}
                        </div>
                      )}
                    </div>

                    <div className="space-y-3">
                      <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
                        <div>
                          <h4 className="text-base font-semibold text-slate-900">Taxas de devolucao</h4>
                          <p className="text-sm text-slate-500">Preencha apenas as situacoes que realmente aconteceram com o veiculo.</p>
                        </div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Campos adicionais de cobranca</p>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {closeoutFeeFields.map((field) => (
                          <div key={field.key} className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                            <label className="input-label">{field.label}</label>
                            <p className="mb-3 text-xs text-slate-500">{field.hint}</p>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={closeoutData[field.key]}
                              onChange={(event) => setCloseoutData({ ...closeoutData, [field.key]: Number(event.target.value) || 0 })}
                              className="input-field bg-white"
                            />
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between">
                        <div>
                          <h4 className="text-base font-semibold text-slate-900">Recebimento financeiro</h4>
                          <p className="text-sm text-slate-500">Defina se este encerramento foi pago agora ou vai para contas a receber.</p>
                        </div>
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Financeiro integrado ao contrato</p>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="input-label">Status do recebimento</label>
                          <select
                            value={closeoutData.status_pagamento}
                            onChange={(event) =>
                              setCloseoutData({
                                ...closeoutData,
                                status_pagamento: event.target.value as PaymentStatus,
                                valor_recebido:
                                  event.target.value === 'pago' && closeoutData.valor_recebido <= 0
                                    ? closeoutEstimativa
                                    : event.target.value === 'cancelado'
                                      ? 0
                                      : closeoutData.valor_recebido,
                              })
                            }
                            className="input-field"
                          >
                            {paymentStatusOptions.map((option) => (
                              <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="input-label">Forma de pagamento</label>
                          <select
                            value={closeoutData.forma_pagamento}
                            onChange={(event) => setCloseoutData({ ...closeoutData, forma_pagamento: event.target.value })}
                            className="input-field"
                          >
                            <option value="">Selecione</option>
                            {paymentMethodOptions.map((option) => (
                              <option key={option} value={option}>{option}</option>
                            ))}
                          </select>
                        </div>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <label className="input-label">Vencimento</label>
                          <input
                            type="date"
                            value={closeoutData.data_vencimento_pagamento}
                            onChange={(event) => setCloseoutData({ ...closeoutData, data_vencimento_pagamento: event.target.value })}
                            className="input-field"
                          />
                        </div>
                        <div>
                          <label className="input-label">Data do pagamento</label>
                          <input
                            type="date"
                            value={closeoutData.data_pagamento}
                            onChange={(event) => setCloseoutData({ ...closeoutData, data_pagamento: event.target.value })}
                            className="input-field"
                            disabled={closeoutData.status_pagamento !== 'pago'}
                          />
                        </div>
                        <div>
                          <label className="input-label">Valor recebido</label>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={closeoutData.valor_recebido}
                            onChange={(event) => setCloseoutData({ ...closeoutData, valor_recebido: Number(event.target.value) || 0 })}
                            className="input-field"
                          />
                        </div>
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <span>
                          Total do encerramento: <strong className="text-slate-900">{formatCurrency(closeoutEstimativa)}</strong>
                        </span>
                        <button
                          type="button"
                          onClick={() => setCloseoutData({ ...closeoutData, valor_recebido: closeoutEstimativa, status_pagamento: 'pago' })}
                          className="btn-secondary btn-sm"
                        >
                          Usar total como recebido
                        </button>
                      </div>
                    </div>

                    <div>
                      <label className="input-label">Observacoes</label>
                      <textarea rows={4} value={closeoutData.observacoes} onChange={(event) => setCloseoutData({ ...closeoutData, observacoes: event.target.value })} className="input-field" />
                    </div>
                  </div>

                  <div className="xl:sticky xl:top-0">
                    <div className="space-y-4">
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm space-y-2">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-xs uppercase tracking-wide text-blue-700">Resumo Financeiro</p>
                            <h4 className="text-base font-semibold text-slate-900">Fechamento da devolucao</h4>
                          </div>
                          <div className="rounded-full bg-white/80 px-3 py-1 text-xs font-semibold text-blue-700">
                            {closeoutChecklistPendencias.length} pendencia(s)
                          </div>
                        </div>
                        <div className="flex justify-between"><span>Valor base contratado</span><strong>{formatCurrency(closeoutValorBaseContratado)}</strong></div>
                        <div className="flex justify-between"><span>Valor base atualizado</span><strong>{formatCurrency(closeoutValorBaseAtualizado)}</strong></div>
                        {closeoutValorAtraso > 0 && <div className="flex justify-between text-amber-700"><span>Acrescimo por atraso</span><strong>{formatCurrency(closeoutValorAtraso)}</strong></div>}
                        <div className="flex justify-between"><span>KM rodado</span><strong>{closeoutKmRodado.toLocaleString('pt-BR')}</strong></div>
                        <div className="flex justify-between"><span>KM excedente</span><strong>{closeoutKmExcedente.toLocaleString('pt-BR')}</strong></div>
                        <div className="flex justify-between"><span>Cobranca KM excedente</span><strong>{formatCurrency(closeoutValorKmExcedente)}</strong></div>
                        <div className="flex justify-between"><span>Itens pendentes no checklist</span><strong>{closeoutChecklistPendencias.length}</strong></div>
                        <div className="flex justify-between"><span>Taxas operacionais</span><strong>{formatCurrency(closeoutTaxasOperacionais)}</strong></div>
                        {closeoutFeeBreakdown.length > 0 && (
                          <div className="pt-2 border-t border-blue-200 space-y-1">
                            {closeoutFeeBreakdown.map((field) => (
                              <div key={field.key} className="flex justify-between text-slate-600">
                                <span>{field.label}</span>
                                <strong>{formatCurrency(field.value)}</strong>
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="flex justify-between text-red-600"><span>Desconto final</span><strong>- {formatCurrency(closeoutData.desconto)}</strong></div>
                        <div className="flex justify-between"><span>Status financeiro</span><strong>{paymentStatusLabel(closeoutData.status_pagamento)}</strong></div>
                        <div className="flex justify-between"><span>Valor recebido</span><strong>{formatCurrency(closeoutData.valor_recebido)}</strong></div>
                        <div className="flex justify-between pt-2 border-t border-blue-200 text-base"><span>Total estimado</span><strong>{formatCurrency(closeoutEstimativa)}</strong></div>
                      </div>

                      {closeoutChecklistPendencias.length > 0 && (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                          <p className="font-semibold">Checklist com pendencias</p>
                          <p className="mt-1">
                            Revise os itens faltantes antes de concluir: {closeoutChecklistPendencias.map((field) => field.label).join(', ')}.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button onClick={() => setClosingContract(null)} className="btn-secondary" disabled={closeMutation.isPending}>Cancelar</button>
                <button onClick={handleCloseout} className="btn-primary" disabled={closeMutation.isPending}>{closeMutation.isPending ? 'Encerrando...' : 'Encerrar Contrato'}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm.isOpen && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && !deleteMutation.isPending && setDeleteConfirm({ isOpen: false })}>
          <div className="modal-content max-w-sm w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">Deletar Contrato</h3>
              <button onClick={() => setDeleteConfirm({ isOpen: false })} className="btn-icon" disabled={deleteMutation.isPending}><X size={20} /></button>
            </div>
            <div className="px-6 py-5 flex items-start gap-4">
              <div className="bg-red-100 rounded-lg p-3"><AlertCircle className="text-red-600" size={24} /></div>
              <p className="text-sm text-slate-600">Esta acao nao pode ser desfeita.</p>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
              <button onClick={() => setDeleteConfirm({ isOpen: false })} className="btn-secondary" disabled={deleteMutation.isPending}>Cancelar</button>
              <button onClick={() => deleteConfirm.id && deleteMutation.mutate(deleteConfirm.id)} className="btn-danger" disabled={deleteMutation.isPending}>{deleteMutation.isPending ? 'Deletando...' : 'Deletar'}</button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}

export default Contratos
