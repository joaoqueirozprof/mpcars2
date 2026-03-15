import React, { useMemo, useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  Car,
  CheckCircle,
  ChevronDown,
  Download,
  Edit,
  FileText,
  Loader2,
  MoreHorizontal,
  Plus,
  Printer,
  Search,
  Trash2,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

import AppLayout from '@/components/layout/AppLayout'
import CurrencyInput from '@/components/shared/CurrencyInput'
import { useConfig } from '@/contexts/ConfigContext'
import { calculateDays, formatCurrency, formatDate } from '@/lib/utils'
import api from '@/services/api'
import { Contrato, EmpresaUso, PaginatedResponse, PaginationParams, Veiculo } from '@/types'

type StatusFilter = 'todos' | 'ativo' | 'finalizado' | 'cancelado' | 'atraso'

type ContractForm = {
  cliente_id: string
  veiculo_id: string
  tipo: 'cliente' | 'empresa'
  data_inicio: string
  data_fim: string
  vigencia_indeterminada: boolean
  empresa_uso_id: string
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
  { key: 'chave_de_roda', label: 'Chave de roda', hint: 'Ferramenta de troca de pne' },
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

// Tipo para agrupar contratos de empresa por cliente/empresa
type ContratoAgrupado = {
  tipo: 'empresa' | 'cliente'
  contratos: Contrato[]
  empresaId?: number
  empresaNome?: string
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
    vigencia_indeterminada: false,
    empresa_uso_id: '',
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [formData, setFormData] = useState<ContractForm>(buildForm())
  
  // Modal para detalhes do contrato de empresa
  const [companyContractDetails, setCompanyContractDetails] = useState<{
    isOpen: boolean;
    contrato: Contrato | null;
    empresaUsos: EmpresaUso[];
    loading: boolean;
  }>({ isOpen: false, contrato: null, empresaUsos: [], loading: false })
  
  // Modal para selecionar veículo ao gerar PDF de contrato de empresa
  const [pdfVehicleSelector, setPdfVehicleSelector] = useState<{
    isOpen: boolean;
    contrato: Contrato | null;
    empresaUsos: EmpresaUso[];
    loading: boolean;
  }>({ isOpen: false, contrato: null, empresaUsos: [], loading: false })
  
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

  // Agrupar contratos de empresa por cliente (uma linha por empresa)
  const contratosAgrupados = useMemo(() => {
    if (!contratos?.data) return []
    
    const grouped = new Map<string, ContratoAgrupado>()
    
    contratos.data.forEach(contrato => {
      const key = contrato.tipo === 'empresa' 
        ? `empresa_${contrato.cliente?.empresa_id || contrato.cliente_id}`
        : `cliente_${contrato.cliente_id}`
      
      if (!grouped.has(key)) {
        grouped.set(key, {
          tipo: contrato.tipo as 'empresa' | 'cliente',
          contratos: [],
          empresaId: contrato.cliente?.empresa_id,
          empresaNome: contrato.cliente?.nome,
        })
      }
      grouped.get(key)!.contratos.push(contrato)
    })
    
    return Array.from(grouped.values())
  }, [contratos])

  const { data: clientes } = useQuery({
    queryKey: ['clientes-select', formData.tipo],
    enabled: formData.tipo === 'cliente',
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/clientes', {
        params: {
          limit: 1000,
          tipo: 'pf',
        },
      })
      return data.data || []
    },
  })

  const { data: empresas } = useQuery({
    queryKey: ['empresas-select'],
    enabled: formData.tipo === 'empresa',
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<any>>('/empresas', {
        params: { limit: 1000 },
      })
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

  const selectedCliente = formData.tipo === 'cliente'
    ? clientes?.find((cliente: any) => String(cliente.id) === String(formData.cliente_id))
    : null
  const selectedEmpresa = formData.tipo === 'empresa'
    ? empresas?.find((empresa: any) => String(empresa.id) === String(formData.cliente_id))
    : null
  const selectedVeiculo = (veiculos || []).find((veiculo: any) => String(veiculo.id) === String(formData.veiculo_id))
  const selectedEmpresaId = formData.tipo === 'empresa'
    ? (selectedEmpresa ? String(selectedEmpresa.id) : '')
    : (selectedCliente?.empresa_id ? String(selectedCliente.empresa_id) : '')
  const contractPartyOptions = formData.tipo === 'empresa' ? (empresas || []) : (clientes || [])
  const selectedPartyName = formData.tipo === 'empresa' ? selectedEmpresa?.nome : selectedCliente?.nome

  const { data: empresaUsos } = useQuery({
    queryKey: ['empresa-usos-select', selectedEmpresaId, editingContract?.id || 'novo'],
    enabled: Boolean(selectedEmpresaId && formData.tipo === 'empresa'),
    queryFn: async () => {
      const { data } = await api.get(`/empresas/${selectedEmpresaId}/usos`, {
        params: { status_filter: editingContract ? undefined : 'ativo' },
      })
      return data || []
    },
  })

  const selectedEmpresaUso = useMemo(
    () =>
      (empresaUsos || []).find(
        (uso: any) =>
          String(uso.veiculo_id) === String(formData.veiculo_id) ||
          String(uso.id) === String(formData.empresa_uso_id)
      ),
    [empresaUsos, formData.veiculo_id, formData.empresa_uso_id]
  )

  const availableVehicles = useMemo(() => {
    if (formData.tipo !== 'empresa') {
      return (veiculos || []).filter(
        (veiculo: any) =>
          veiculo.status === 'disponivel' ||
          String(veiculo.id) === String(formData.veiculo_id) ||
          String(veiculo.id) === String(editingContract?.veiculo_id)
      )
    }

    if (!empresaUsos || empresaUsos.length === 0) {
      return (veiculos || []).filter(
        (veiculo: any) =>
          veiculo.status === 'disponivel' ||
          String(veiculo.id) === String(formData.veiculo_id) ||
          String(veiculo.id) === String(editingContract?.veiculo_id)
      )
    }

    return empresaUsos.map((uso: any) => {
      const veiculoRelacionado = (veiculos || []).find(
        (veiculo: any) => String(veiculo.id) === String(uso.veiculo_id)
      )

      return {
        ...veiculoRelacionado,
        id: uso.veiculo_id,
        placa: uso.placa || veiculoRelacionado?.placa || 'Sem placa',
        marca: uso.marca || veiculoRelacionado?.marca || '',
        modelo: uso.modelo || veiculoRelacionado?.modelo || '',
        km_atual: veiculoRelacionado?.km_atual ?? uso.km_inicial ?? 0,
      }
    })
  }, [veiculos, formData.veiculo_id, editingContract, formData.tipo, empresaUsos])

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

  const [downloadingPdf, setDownloadingPdf] = useState<string | null>(null)

  // Função para gerar PDF - agora suporta veículo específico
  const handlePdf = async (contratoId: string, numero: string, veiculoId?: number, print = false) => {
    setDownloadingPdf(contratoId)
    try {
      const params: any = { responseType: 'blob' }
      // Se for contrato de empresa e tem veículo específico, passar o veiculo_id
      if (veiculoId) {
        params.params = { veiculo_id: veiculoId }
      } else {
        // Fallback para o endpoint do router de contratos se o de relatórios falhar ou for diferente
        const response = await api.get(`/contratos/${contratoId}/pdf`, params)
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
        return
      }
      const response = await api.get(`/relatorios/contrato/${contratoId}/pdf`, params)
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

  // Abrir seletor de veículo para gerar PDF de contrato de empresa
  const openPdfVehicleSelector = async (contrato: Contrato) => {
    setPdfVehicleSelector({ isOpen: true, contrato, empresaUsos: [], loading: true })
    try {
      const { data } = await api.get(`/contratos/${contrato.id}`)
      setPdfVehicleSelector(prev => ({
        ...prev,
        empresaUsos: data.empresa_usos || [],
        loading: false,
      }))
    } catch {
      toast.error('Erro ao carregar veículos')
      setPdfVehicleSelector({ isOpen: false, contrato: null, empresaUsos: [], loading: false })
    }
  }

  // Gerar PDF para veículo específico selecionado
  const handlePdfForVehicle = async (uso: any) => {
    if (!pdfVehicleSelector.contrato) return
    setPdfVehicleSelector({ isOpen: false, contrato: null, empresaUsos: [], loading: false })
    await handlePdf(pdfVehicleSelector.contrato.id, pdfVehicleSelector.contrato.numero, uso.veiculo_id)
  }
  
  // Open company contract details modal
  const openCompanyContractDetails = async (contrato: Contrato) => {
    setCompanyContractDetails({ isOpen: true, contrato, empresaUsos: [], loading: true })
    try {
      const { data } = await api.get(`/contratos/${contrato.id}`)
      setCompanyContractDetails(prev => ({
        ...prev,
        empresaUsos: data.empresa_usos || [],
        loading: false,
      }))
    } catch {
      toast.error('Erro ao carregar detalhes do contrato')
      setCompanyContractDetails({ isOpen: false, contrato: null, empresaUsos: [], loading: false })
    }
  }

  // Download NF report for company contract
  const downloadNfReport = async (contrato: Contrato, empresaId?: number) => {
    if (!empresaId) {
      toast.error('Empresa não encontrada')
      return
    }
    setDownloadingPdf(contrato.id)
    try {
      const { data } = await api.get(`/contratos/${contrato.id}`)
      const empresaUsos = data.empresa_usos || []
      
      if (empresaUsos.length === 0) {
        toast.error('Nenhum veículo encontrado no contrato')
        return
      }
      
      const veiculos = empresaUsos.map((uso: any) => ({
        uso_id: uso.id,
        km_percorrido: uso.km_percorrido || 0,
        km_referencia: uso.km_referencia || 0,
        valor_km_extra: uso.valor_km_extra || 0,
      }))
      
      const response = await api.post('/relatorios/nf/empresa/pdf', {
        empresa_id: empresaId,
        periodo_inicio: new Date().toISOString().slice(0, 10),
        periodo_fim: new Date().toISOString().slice(0, 10),
        veiculos,
      }, { responseType: 'blob' })
      
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `notas_fiscais_${contrato.numero}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      toast.success('Relatório de notas fiscais baixado!')
    } catch (error) {
      console.error('Error downloading NF report:', error)
      toast.error('Erro ao baixar relatório de notas fiscais')
    } finally {
      setDownloadingPdf(null)
    }
  }

  const openCreate = () => {
    setEditingContract(null)
    setFormData(buildForm())
    setIsModalOpen(true)
  }

  useEffect(() => {
    if (searchParams.get('quick') !== 'create') return

    openCreate()
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete('quick')
    setSearchParams(nextParams, { replace: true })
  }, [searchParams, setSearchParams])

  const openEdit = (contrato: Contrato) => {
    setEditingContract(contrato)
    setFormData({
      cliente_id:
        (contrato.tipo || 'cliente') === 'empresa' && contrato.cliente?.empresa_id
          ? String(contrato.cliente.empresa_id)
          : String(contrato.cliente_id),
      veiculo_id: contrato.veiculo_id,
      tipo: contrato.tipo || 'cliente',
      data_inicio: toDateInput(contrato.data_inicio),
      data_fim: toDateInput(contrato.data_fim),
      vigencia_indeterminada:
        (contrato.tipo || 'cliente') === 'empresa' &&
        getRoundedDaysBetween(contrato.data_inicio, contrato.data_fim) >= 3650,
      empresa_uso_id: '',
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
    const veiculo: any = availableVehicles.find((item: any) => String(item.id) === String(veiculoId))
    const usoEmpresa = (empresaUsos || []).find((uso: any) => String(uso.veiculo_id) === String(veiculoId))
    setFormData((current) => ({
      ...current,
      veiculo_id: veiculoId,
      empresa_uso_id: current.tipo === 'empresa' ? String(usoEmpresa?.id || '') : '',
      km_atual_veiculo: veiculo?.km_atual ?? usoEmpresa?.km_inicial ?? 0,
      valor_diaria:
        current.tipo === 'empresa'
          ? Number(usoEmpresa?.valor_diaria_empresa || veiculo?.valor_diaria || 0)
          : current.valor_diaria || veiculo?.valor_diaria || config.valor_diaria_padrao || 0,
    }))
  }

  useEffect(() => {
    if (formData.tipo !== 'empresa' || !selectedEmpresaId || !(empresaUsos || []).length) return

    const selectedStillExists = (empresaUsos || []).some(
      (uso: any) => String(uso.veiculo_id) === String(formData.veiculo_id)
    )

    if (!selectedStillExists) {
      handleVehicleChange(String(empresaUsos?.[0]?.veiculo_id || ''))
    }
  }, [formData.tipo, selectedEmpresaId, empresaUsos])

  useEffect(() => {
    if (formData.tipo !== 'empresa' || !selectedEmpresaUso) return

    setFormData((current) => ({
      ...current,
      empresa_uso_id: String(selectedEmpresaUso.id),
      km_atual_veiculo: selectedVeiculo?.km_atual ?? Number(selectedEmpresaUso.km_inicial || 0),
      km_livres: Number(selectedEmpresaUso.km_referencia || 0),
      valor_km_excedente: Number(selectedEmpresaUso.valor_km_extra || 0),
      valor_diaria: Number(selectedEmpresaUso.valor_diaria_empresa || 0),
      data_inicio: current.data_inicio || toDateInput(selectedEmpresaUso.data_inicio),
      data_fim:
        current.vigencia_indeterminada
          ? ''
          : (current.data_fim || toDateInput(selectedEmpresaUso.data_fim)),
    }))
  }, [formData.tipo, selectedEmpresaUso, selectedVeiculo])

  const dias = formData.data_inicio && formData.data_fim ? calculateDays(formData.data_inicio, formData.data_fim) : 0
  const diasPreview = formData.tipo === 'empresa' || formData.vigencia_indeterminada ? 1 : dias
  const valorPreview = Math.max(
    (formData.tipo === 'empresa' ? formData.valor_diaria : diasPreview * formData.valor_diaria) - formData.desconto,
    0
  )

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
    ? String(closingContract.tipo || '').toLowerCase() === 'empresa'
      ? 1
      : Math.max(closingContract.qtd_diarias || getRoundedDaysBetween(closingContract.data_inicio, closingContract.data_fim), 1)
    : 0
  const closeoutDiasFaturados = closingContract && closeoutBillingEnd
    ? String(closingContract.tipo || '').toLowerCase() === 'empresa'
      ? 1
      : getRoundedDaysBetween(closingContract.data_inicio, closeoutBillingEnd)
    : 0
  const closeoutValorBaseContratado = closingContract
    ? String(closingContract.tipo || '').toLowerCase() === 'empresa'
      ? closingContract.valor_diaria || 0
      : closeoutDiasContratados * (closingContract.valor_diaria || 0)
    : 0
  const closeoutValorBaseAtualizado = closingContract
    ? String(closingContract.tipo || '').toLowerCase() === 'empresa'
      ? closingContract.valor_diaria || 0
      : closeoutDiasFaturados * (closingContract.valor_diaria || 0)
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
    if (!formData.cliente_id || !formData.veiculo_id || !formData.data_inicio) {
      toast.error('Preencha cliente, veiculo e a data inicial.')
      return
    }
    if (!formData.vigencia_indeterminada && !formData.data_fim) {
      toast.error('Informe a data final ou marque a vigencia indeterminada.')
      return
    }
    if (!formData.vigencia_indeterminada && new Date(formData.data_fim) <= new Date(formData.data_inicio)) {
      toast.error('A data final precisa ser maior que a inicial.')
      return
    }
    if (formData.tipo === 'empresa' && !selectedEmpresaId) {
      toast.error('Escolha um cliente vinculado a uma empresa para criar contrato corporativo.')
      return
    }

    const payload = {
      ...formData,
      empresa_id: formData.tipo === 'empresa' ? Number(formData.cliente_id) || undefined : undefined,
      data_fim: formData.vigencia_indeterminada ? undefined : formData.data_fim,
      qtd_diarias: diasPreview,
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
            <h1 className="page-title">Contratos (V2)</h1>
            <p className="page-subtitle">Locacao com retirada, acompanhamento e encerramento.</p>
          </div>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2">
            <Plus size={18} />
            Novo Contrato
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                <FileText size={20} />
              </div>
              <p className="text-sm font-medium text-slate-500">Total</p>
            </div>
            <p className="text-2xl font-bold text-slate-900">{summary.total}</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-green-50 rounded-lg text-green-600">
                <CheckCircle size={20} />
              </div>
              <p className="text-sm font-medium text-slate-500">Ativos</p>
            </div>
            <p className="text-2xl font-bold text-green-600">{summary.ativos}</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-red-50 rounded-lg text-red-600">
                <AlertCircle size={20} />
              </div>
              <p className="text-sm font-medium text-slate-500">Atrasados</p>
            </div>
            <p className="text-2xl font-bold text-red-600">{summary.atrasados}</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-amber-50 rounded-lg text-amber-600">
                <div className="relative">
                  <FileText size={20} />
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-amber-500 rounded-full"></div>
                </div>
              </div>
              <p className="text-sm font-medium text-slate-500">Financeiro Pendente</p>
            </div>
            <p className="text-2xl font-bold text-amber-600">{summary.pendentesFinanceiro}</p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-50 rounded-lg text-purple-600">
                <div className="font-bold text-xs">R$</div>
              </div>
              <p className="text-sm font-medium text-slate-500">Valor em Tela</p>
            </div>
            <p className="text-2xl font-bold text-purple-600 leading-tight">
              <span className="text-sm font-normal mr-1">R$</span>
              {formatCurrency(summary.valor).replace('R$', '').trim()}
            </p>
          </div>
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
          ) : contratosAgrupados.length ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50/50">
                    <th className="px-4 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Número</th>
                    <th className="px-4 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Cliente</th>
                    <th className="px-4 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Veículo(s)</th>
                    <th className="px-4 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Período</th>
                    <th className="px-4 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Valor Total</th>
                    <th className="px-4 py-4 text-center text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-4 text-center text-xs font-bold text-slate-500 uppercase tracking-wider">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {contratosAgrupados.map((grupo) => {
                    const contrato = grupo.contratos[0]
                    const status = displayStatus(contrato)
                    const ehEmpresa = grupo.tipo === 'empresa'
                    
                    return (
                      <tr key={grupo.tipo === 'empresa' ? `empresa_${grupo.empresaId}` : `cliente_${contrato.cliente_id}`} className="hover:bg-blue-50/30 transition-colors group">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span className={`text-xs font-mono font-bold px-2 py-1 rounded-md ${ehEmpresa ? 'bg-blue-50 text-blue-700 border border-blue-100' : 'bg-slate-100 text-slate-700 border border-slate-200'}`}>
                            {contrato.numero}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex flex-col">
                            <span className="text-sm font-bold text-slate-900">{contrato.cliente?.nome || '-'}</span>
                            {ehEmpresa && (
                              <span className="inline-flex items-center gap-1 mt-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded w-fit">
                                Empresarial
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          {ehEmpresa ? (
                            <div className="flex flex-col gap-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-slate-600 font-medium">
                                  {grupo.contratos.length} veículos na frota
                                </span>
                                <button
                                  onClick={() => openCompanyContractDetails(contrato)}
                                  className="p-1 text-blue-600 hover:bg-blue-100 rounded-full transition-colors"
                                  title="Ver todos os veículos da empresa"
                                >
                                  <Car size={14} />
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-col">
                              <span className="text-sm font-medium text-slate-800">
                                {contrato.veiculo ? `${contrato.veiculo.marca} ${contrato.veiculo.modelo}` : '-'}
                              </span>
                              <span className="text-xs text-slate-500 font-mono">{contrato.veiculo?.placa || '-'}</span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="flex flex-col gap-1 text-xs text-slate-600">
                            <div className="flex items-center gap-1.5 font-medium">
                              <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
                              {formatDate(contrato.data_inicio)}
                            </div>
                            <div className="flex items-center gap-1.5 font-medium">
                              <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
                              {formatDate(contrato.data_fim)}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right whitespace-nowrap">
                          <div className="flex flex-col">
                            <span className="text-sm font-bold text-slate-900">{formatCurrency(contrato.valor_total)}</span>
                            <span className="text-[10px] text-slate-500">
                              Recebido: <span className="font-semibold text-slate-700">{formatCurrency(contrato.valor_recebido || 0)}</span>
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center">
                          <div className="flex flex-col items-center gap-1.5">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              status === 'ativo' ? 'bg-green-100 text-green-700' :
                              status === 'finalizado' ? 'bg-blue-100 text-blue-700' :
                              status === 'cancelado' ? 'bg-red-100 text-red-700' :
                              'bg-amber-100 text-amber-700'
                            }`}>
                              {statusLabel(status)}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              contrato.status_pagamento === 'pago' ? 'bg-emerald-100 text-emerald-700' :
                              contrato.status_pagamento === 'pendente' ? 'bg-amber-100 text-amber-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {paymentStatusLabel(contrato.status_pagamento)}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-center whitespace-nowrap">
                          <div className="flex items-center justify-center gap-0.5 opacity-60 group-hover:opacity-100 transition-opacity">
                            {/* PDF e Impressão agrupados em um dropdown para Empresas */}
                            {ehEmpresa ? (
                              <div className="dropdown dropdown-left">
                                <label 
                                  tabIndex={0} 
                                  className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg cursor-pointer transition-all flex items-center gap-1 group/btn"
                                >
                                  <FileText size={18} className="group-hover/btn:scale-110 transition-transform" />
                                  <ChevronDown size={14} className="group-hover/btn:translate-y-0.5 transition-transform" />
                                </label>
                                <div tabIndex={0} className="dropdown-content z-[30] p-0 shadow-2xl bg-white border border-slate-100 rounded-2xl w-80 mt-2 animate-in fade-in zoom-in duration-200 origin-top-right">
                                  <div className="p-4 bg-slate-50/50 border-b border-slate-100 rounded-t-2xl">
                                    <div className="flex items-center justify-between mb-1">
                                      <div className="flex items-center gap-2">
                                        <div className="w-6 h-6 rounded-md bg-blue-100 flex items-center justify-center text-blue-600">
                                          <FileText size={14} />
                                        </div>
                                        <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-600">Documentos da Frota</h4>
                                      </div>
                                      <button 
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          // Find the dropdown content and blur it, or blur active element
                                          if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
                                        }}
                                        className="text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full p-1 transition-colors"
                                        title="Fechar menu"
                                      >
                                        <X size={14} />
                                      </button>
                                    </div>
                                    <p className="text-[10px] text-slate-400 font-medium ml-8">Selecione o veículo para gerar o PDF ou imprimir</p>
                                  </div>
                                  
                                  <div className="max-h-[350px] overflow-y-auto custom-scrollbar">
                                    {grupo.contratos.map((c, idx) => (
                                      <div 
                                        key={c.id} 
                                        className={`p-4 hover:bg-blue-50/30 transition-colors border-b border-slate-50 last:border-0 group/item ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50/20'}`}
                                      >
                                        <div className="flex items-center justify-between mb-3">
                                          <div className="flex items-center gap-2">
                                            <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 group-hover/item:bg-blue-100 group-hover/item:text-blue-600 transition-colors">
                                              <Car size={16} />
                                            </div>
                                            <div>
                                              <p className="text-[10px] font-mono font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full w-fit mb-0.5">{c.veiculo?.placa}</p>
                                              <p className="text-xs font-bold text-slate-700 truncate max-w-[150px]">{c.veiculo?.modelo}</p>
                                            </div>
                                          </div>
                                        </div>
                                        
                                        <div className="flex gap-2">
                                          <button 
                                            onClick={() => {
                                              handlePdf(c.id, c.numero, c.veiculo_id);
                                              if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
                                            }}
                                            className="flex-1 flex items-center justify-center gap-2 text-[10px] font-bold py-2.5 bg-white border border-slate-200 text-slate-600 rounded-xl hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all shadow-sm active:scale-95"
                                          >
                                            <Download size={12} /> PDF
                                          </button>
                                          <button 
                                            onClick={() => {
                                              handlePdf(c.id, c.numero, c.veiculo_id, true);
                                              if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
                                            }}
                                            className="flex-1 flex items-center justify-center gap-2 text-[10px] font-bold py-2.5 bg-white border border-slate-200 text-slate-600 rounded-xl hover:bg-purple-600 hover:text-white hover:border-purple-600 transition-all shadow-sm active:scale-95"
                                          >
                                            <Printer size={12} /> IMPRIMIR
                                          </button>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                  
                                  <div className="p-3 bg-slate-50/80 rounded-b-2xl">
                                    <button 
                                      onClick={() => {
                                        openPdfVehicleSelector(contrato);
                                        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
                                      }}
                                      className="w-full flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-widest py-3 text-blue-600 bg-white border border-blue-100 rounded-xl hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all shadow-sm active:scale-[0.98]"
                                    >
                                      <Search size={14} />
                                      Buscar na Frota Completa
                                    </button>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <>
                                <button onClick={() => handlePdf(contrato.id, contrato.numero)} className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Download PDF">
                                  {downloadingPdf === contrato.id ? <Loader2 size={18} className="animate-spin" /> : <Download size={18} />}
                                </button>
                                <button onClick={() => handlePdf(contrato.id, contrato.numero, undefined, true)} className="p-2 text-slate-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors" title="Imprimir">
                                  <Printer size={18} />
                                </button>
                              </>
                            )}
                            
                            <div className="w-px h-4 bg-slate-200 mx-1"></div>

                            {contrato.status === 'ativo' && (
                              <button onClick={() => openCloseout(contrato)} className="p-2 text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" title="Encerrar Contrato">
                                <CheckCircle size={18} />
                              </button>
                            )}
                            <button onClick={() => openEdit(contrato)} className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Editar">
                              <Edit size={18} />
                            </button>
                            <button onClick={() => setDeleteConfirm({ isOpen: true, id: contrato.id })} className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Excluir">
                              <Trash2 size={18} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div className="flex items-center justify-between pt-4 border-t border-slate-200">
                <p className="text-sm text-slate-600">Mostrando {contratosAgrupados.length} de {contratos?.total || 0} contratos</p>
                <div className="flex gap-2">
                  <button onClick={() => setPagination({ ...pagination, page: Math.max(1, pagination.page - 1) })} disabled={pagination.page === 1} className="btn-secondary btn-sm">Anterior</button>
                  <button onClick={() => setPagination({ ...pagination, page: pagination.page + 1 })} disabled={pagination.page * pagination.limit >= (contratos?.total || 0)} className="btn-secondary btn-sm">Proximo</button>
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

      {/* Modal para selecionar veículo ao gerar PDF */}
      {pdfVehicleSelector.isOpen && pdfVehicleSelector.contrato && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setPdfVehicleSelector({ isOpen: false, contrato: null, empresaUsos: [], loading: false })}>
          <div className="modal-content max-w-md w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                Selecionar Veículo para PDF
              </h3>
              <button onClick={() => setPdfVehicleSelector({ isOpen: false, contrato: null, empresaUsos: [], loading: false })} className="btn-icon">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6">
              {pdfVehicleSelector.loading ? (
                <div className="flex justify-center p-4">
                  <Loader2 className="animate-spin text-blue-600" size={32} />
                </div>
              ) : pdfVehicleSelector.empresaUsos.length > 0 ? (
                <div className="space-y-3">
                  <p className="text-sm text-slate-600 mb-4">
                    Selecione qual veículo deseja gerar o contrato:
                  </p>
                  {pdfVehicleSelector.empresaUsos.map((uso) => (
                    <button
                      key={uso.id}
                      onClick={() => handlePdfForVehicle(uso)}
                      className="w-full text-left p-4 border border-slate-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-slate-900">
                            {uso.placa || 'Sem placa'} - {uso.marca} {uso.modelo}
                          </p>
                          <p className="text-sm text-slate-500">
                            {uso.status === 'ativo' ? 'Ativo' : uso.status}
                          </p>
                        </div>
                        <Download size={20} className="text-blue-600" />
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-center text-slate-500">Nenhum veículo encontrado.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Company Contract Details Modal - permanece igual */}
      {companyContractDetails.isOpen && companyContractDetails.contrato && (
        <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && setCompanyContractDetails({ isOpen: false, contrato: null, empresaUsos: [], loading: false })}>
          <div className="modal-content max-w-4xl w-full" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h3 className="text-lg font-display font-bold text-slate-900">
                Contrato Empresa - {companyContractDetails.contrato.numero}
              </h3>
              <button onClick={() => setCompanyContractDetails({ isOpen: false, contrato: null, empresaUsos: [], loading: false })} className="btn-icon">
                <X size={20} />
              </button>
            </div>
            
            <div className="modal-scroll-body">
              {companyContractDetails.loading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="animate-spin text-blue-600" size={32} />
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
                      <p className="text-xs uppercase tracking-wide text-slate-500">Veículos</p>
                      <p className="text-2xl font-bold text-slate-900">{companyContractDetails.empresaUsos.length}</p>
                    </div>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                      <p className="text-xs uppercase tracking-wide text-blue-600">Valor Mensal Total</p>
                      <p className="text-2xl font-bold text-blue-900">
                        {formatCurrency(companyContractDetails.empresaUsos.reduce((sum, uso) => sum + (uso.valor_diaria_empresa || 0), 0))}
                      </p>
                    </div>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
                      <p className="text-xs uppercase tracking-wide text-amber-600">Total KM Extra</p>
                      <p className="text-2xl font-bold text-amber-900">
                        {formatCurrency(companyContractDetails.empresaUsos.reduce((sum, uso) => {
                          const kmPercorrido = uso.km_percorrido || 0
                          const kmReferencia = uso.km_referencia || 0
                          const kmExtra = Math.max(kmPercorrido - kmReferencia, 0)
                          return sum + (kmExtra * (uso.valor_km_extra || 0))
                        }, 0))}
                      </p>
                    </div>
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                      <p className="text-xs uppercase tracking-wide text-green-600">Valor Total Geral</p>
                      <p className="text-2xl font-bold text-green-900">
                        {formatCurrency(companyContractDetails.contrato.valor_total || 0)}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {companyContractDetails.empresaUsos.map((uso) => {
                      const kmPercorrido = uso.km_percorrido || 0
                      const kmReferencia = uso.km_referencia || 0
                      const kmExtra = Math.max(kmPercorrido - kmReferencia, 0)
                      const valorKmExtra = kmExtra * (uso.valor_km_extra || 0)
                      
                      return (
                        <div key={uso.id} className="border border-slate-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-semibold text-slate-900">
                              {uso.placa || 'Sem placa'} - {uso.marca} {uso.modelo}
                            </h4>
                            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${uso.status === 'ativo' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-600'}`}>
                              {uso.status === 'ativo' ? 'Ativo' : uso.status}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <p className="text-slate-500">Período</p>
                              <p className="font-medium text-slate-900">
                                {uso.data_inicio ? formatDate(uso.data_inicio) : '-'} a {uso.data_fim ? formatDate(uso.data_fim) : 'Em andamento'}
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-500">KM Percorrida</p>
                              <p className="font-medium text-slate-900">{kmPercorrido.toLocaleString('pt-BR')} km</p>
                            </div>
                            <div>
                              <p className="text-slate-500">KM Excedente</p>
                              <p className={`font-medium ${kmExtra > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                                {kmExtra.toLocaleString('pt-BR')} km
                              </p>
                            </div>
                            <div>
                              <p className="text-slate-500">Valor KM Extra</p>
                              <p className="font-medium text-slate-900">{formatCurrency(valorKmExtra)}</p>
                            </div>
                          </div>
                          
                          <div className="mt-4 pt-4 border-t border-slate-200 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-slate-500">Valor Mensal</p>
                              <p className="font-semibold text-slate-900">{formatCurrency(uso.valor_diaria_empresa || 0)}</p>
                            </div>
                            <div>
                              <p className="text-slate-500">KM Referência</p>
                              <p className="font-medium text-slate-900">{kmReferencia.toLocaleString('pt-BR')} km</p>
                            </div>
                            <div>
                              <p className="text-slate-500">Valor Total</p>
                              <p className="font-semibold text-slate-900">
                                {formatCurrency((uso.valor_diaria_empresa || 0) + valorKmExtra)}
                              </p>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {companyContractDetails.empresaUsos.length === 0 && (
                    <div className="text-center py-8 text-slate-500">
                      Nenhum veículo encontrado neste contrato.
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="modal-footer">
              <button 
                onClick={() => setCompanyContractDetails({ isOpen: false, contrato: null, empresaUsos: [], loading: false })} 
                className="btn-secondary"
              >
                Fechar
              </button>
              {companyContractDetails.contrato.cliente?.empresa_id && (
                <button 
                  onClick={() => downloadNfReport(companyContractDetails.contrato!, companyContractDetails.contrato.cliente?.empresa_id)} 
                  className="btn-primary flex items-center gap-2"
                  disabled={downloadingPdf === companyContractDetails.contrato.id}
                >
                  {downloadingPdf === companyContractDetails.contrato.id ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Download size={16} />
                  )}
                  Baixar Relatório de Notas Fiscais
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Form Modal - similar ao original, apenas ajustando key */}
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
                    <label className="input-label">{formData.tipo === 'empresa' ? 'Empresa cliente *' : 'Cliente *'}</label>
                    <select
                      value={formData.cliente_id}
                      onChange={(event) =>
                        setFormData({
                          ...formData,
                          cliente_id: event.target.value,
                          veiculo_id: '',
                          empresa_uso_id: '',
                        })
                      }
                      className="input-field"
                    >
                      <option value="">Selecione</option>
                      {contractPartyOptions.map((item: any) => <option key={item.id} value={item.id}>{item.nome}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="input-label">Tipo</label>
                    <select
                      value={formData.tipo}
                      onChange={(event) =>
                        setFormData({
                          ...buildForm(),
                          tipo: event.target.value as 'cliente' | 'empresa',
                          valor_diaria: config.valor_diaria_padrao || 0,
                        })
                      }
                      className="input-field"
                    >
                      <option value="cliente">Cliente</option>
                      <option value="empresa">Empresa</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="input-label">{formData.tipo === 'empresa' ? 'Veiculo vinculado a empresa *' : 'Veiculo *'}</label>
                  <select value={formData.veiculo_id} onChange={(event) => handleVehicleChange(event.target.value)} className="input-field">
                    <option value="">Selecione</option>
                    {availableVehicles.map((veiculo: any) => <option key={veiculo.id} value={veiculo.id}>{veiculo.placa} - {veiculo.marca} {veiculo.modelo}</option>)}
                  </select>
                </div>
                {selectedPartyName && selectedVeiculo && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm text-slate-700">
                    {selectedPartyName} | {selectedVeiculo.marca} {selectedVeiculo.modelo} | KM atual {selectedVeiculo.km_atual || 0}
                  </div>
                )}
                {formData.tipo === 'empresa' && (
                  <div className="space-y-3 rounded-2xl border border-blue-200 bg-blue-50/80 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-blue-950">Fluxo corporativo</p>
                        <p className="mt-1 text-sm text-blue-900/80">
                          Contratos de empresa podem operar com vigencia indeterminada e usar a parametrizacao mensal do veiculo associado.
                        </p>
                      </div>
                      <label className="flex items-center gap-2 text-sm font-medium text-blue-950">
                        <input
                          type="checkbox"
                          checked={formData.vigencia_indeterminada}
                          onChange={(event) =>
                            setFormData({
                              ...formData,
                              vigencia_indeterminada: event.target.checked,
                              data_fim: event.target.checked ? '' : formData.data_fim,
                            })
                          }
                          className="h-4 w-4 rounded border-blue-300"
                        />
                        Vigencia indeterminada
                      </label>
                    </div>
                    {!selectedEmpresaId && (
                      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                        Escolha uma empresa para habilitar a parametrizacao corporativa.
                      </div>
                    )}
                    {selectedEmpresaId && (empresaUsos || []).length === 0 && (
                      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                        Essa empresa ainda nao possui veiculos vinculados. Abra o cadastro da empresa e use o botao <strong>Frota</strong> para associar os carros.
                      </div>
                    )}
                    {selectedEmpresaUso && (
                      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 text-sm">
                        <div className="rounded-xl bg-white/90 px-4 py-3 border border-blue-100">
                          <p className="text-xs uppercase tracking-[0.18em] text-blue-700/70">Veiculo associado</p>
                          <p className="mt-2 font-semibold text-slate-900">{selectedEmpresaUso.placa} - {selectedEmpresaUso.modelo}</p>
                        </div>
                        <div className="rounded-xl bg-white/90 px-4 py-3 border border-blue-100">
                          <p className="text-xs uppercase tracking-[0.18em] text-blue-700/70">KM permitida no periodo</p>
                          <p className="mt-2 font-semibold text-slate-900">{Number(selectedEmpresaUso.km_referencia || 0).toLocaleString('pt-BR')} km</p>
                        </div>
                        <div className="rounded-xl bg-white/90 px-4 py-3 border border-blue-100">
                          <p className="text-xs uppercase tracking-[0.18em] text-blue-700/70">Valor mensal / periodo</p>
                          <p className="mt-2 font-semibold text-slate-900">{formatCurrency(Number(selectedEmpresaUso.valor_diaria_empresa || 0))}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div><label className="input-label">Data Inicio *</label><input type="date" value={formData.data_inicio} onChange={(event) => setFormData({ ...formData, data_inicio: event.target.value })} className="input-field" /></div>
                  <div>
                    <label className="input-label">{formData.vigencia_indeterminada ? 'Data base de revisao' : 'Data Fim *'}</label>
                    <input
                      type="date"
                      value={formData.data_fim}
                      onChange={(event) => setFormData({ ...formData, data_fim: event.target.value })}
                      className="input-field"
                      disabled={formData.vigencia_indeterminada}
                    />
                  </div>
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
                  <CurrencyInput
                    label={formData.tipo === 'empresa' ? 'Valor mensal / periodo *' : 'Valor Diaria *'}
                    value={formData.valor_diaria}
                    onChange={(valor_diaria) => setFormData({ ...formData, valor_diaria })}
                  />
                  <CurrencyInput
                    label="Valor KM Excedente"
                    value={formData.valor_km_excedente}
                    onChange={(valor_km_excedente) => setFormData({ ...formData, valor_km_excedente })}
                  />
                  <CurrencyInput
                    label="Desconto"
                    value={formData.desconto}
                    onChange={(desconto) => setFormData({ ...formData, desconto })}
                  />
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-sm space-y-2">
                  <div className="flex justify-between"><span>Periodo</span><strong>{formData.vigencia_indeterminada ? 'Indeterminado' : `${dias} dia(s)`}</strong></div>
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
                        <CurrencyInput
                          value={closeoutData.desconto}
                          onChange={(desconto) => setCloseoutData({ ...closeoutData, desconto })}
                        />
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
                            <CurrencyInput
                              value={closeoutData[field.key]}
                              onChange={(nextValue) => setCloseoutData({ ...closeoutData, [field.key]: nextValue })}
                              className="bg-white"
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
                          <CurrencyInput
                            value={closeoutData.valor_recebido}
                            onChange={(valor_recebido) => setCloseoutData({ ...closeoutData, valor_recebido })}
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
