import React, { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Building2,
  Car,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  FileText,
  Receipt,
  Sparkles,
  Users,
} from 'lucide-react'
import toast from 'react-hot-toast'

import AppLayout from '@/components/layout/AppLayout'
import { formatCurrency } from '@/lib/utils'
import api from '@/services/api'

interface VeiculoUso {
  id: number
  veiculo_id: number
  placa: string
  modelo: string
  marca: string
  km_inicial: number
  km_final: number | null
  km_percorrido: number | null
  km_referencia: number | null
  valor_km_extra: number | null
  valor_diaria_empresa: number | null
  data_inicio: string | null
  data_fim: string | null
  status: string
  medicoes_salvas?: number
  total_km_faturada?: number
  total_km_excedente?: number
  total_valor_extra?: number
  ultimo_periodo_inicio?: string | null
  ultimo_periodo_fim?: string | null
  selected: boolean
  km_input: string
  km_permitido_input: string
  valor_km_extra_input: string
}

const exportCards = [
  {
    key: 'clientes',
    icon: Users,
    label: 'Clientes',
    description: 'Cadastros, contatos, documentos e relacionamento.',
    accentClass: 'bg-cyan-100 text-cyan-700',
    badgeClass: 'bg-cyan-50 text-cyan-700',
  },
  {
    key: 'veiculos',
    icon: Car,
    label: 'Veiculos',
    description: 'Frota, status, quilometragem e disponibilidade.',
    accentClass: 'bg-emerald-100 text-emerald-700',
    badgeClass: 'bg-emerald-50 text-emerald-700',
  },
  {
    key: 'contratos',
    icon: FileText,
    label: 'Contratos',
    description: 'Periodos, valores, clientes e movimentacao da operacao.',
    accentClass: 'bg-blue-100 text-blue-700',
    badgeClass: 'bg-blue-50 text-blue-700',
  },
  {
    key: 'financeiro',
    icon: BarChart3,
    label: 'Financeiro',
    description: 'Receitas, despesas e consolidado para fechamento.',
    accentClass: 'bg-amber-100 text-amber-700',
    badgeClass: 'bg-amber-50 text-amber-700',
  },
] as const

const extractErrorMessage = async (error: any, fallback: string) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  const blob = error?.response?.data
  if (blob instanceof Blob) {
    try {
      const text = await blob.text()
      if (!text) return fallback

      try {
        const parsed = JSON.parse(text)
        if (typeof parsed?.detail === 'string' && parsed.detail.trim()) {
          return parsed.detail
        }
      } catch {
        return text
      }
    } catch {
      return fallback
    }
  }

  return fallback
}

const Relatorios: React.FC = () => {
  const [loading, setLoading] = useState<string | null>(null)
  const [contratoId, setContratoId] = useState('')
  const [financeiroDates, setFinanceiroDates] = useState({ start: '', end: '' })
  const [contratos, setContratos] = useState<any[]>([])
  const [empresas, setEmpresas] = useState<any[]>([])
  const [selectedEmpresa, setSelectedEmpresa] = useState('')
  const [veiculosUso, setVeiculosUso] = useState<VeiculoUso[]>([])
  const [loadingUsos, setLoadingUsos] = useState(false)
  const [nfPeriod, setNfPeriod] = useState({ start: '', end: '' })
  const [exportDates, setExportDates] = useState({ start: '', end: '' })
  const [exportStatus, setExportStatus] = useState('')

  useEffect(() => {
    loadContratos()
    loadEmpresas()
  }, [])

  useEffect(() => {
    if (selectedEmpresa) {
      loadVeiculosEmpresa(parseInt(selectedEmpresa, 10))
    } else {
      setVeiculosUso([])
    }
  }, [selectedEmpresa])

  const loadContratos = async () => {
    try {
      const res = await api.get('/contratos/?limit=100')
      setContratos(res.data?.data || res.data || [])
    } catch {
      setContratos([])
    }
  }

  const loadEmpresas = async () => {
    try {
      const res = await api.get('/empresas/?limit=100')
      setEmpresas(res.data?.data || res.data || [])
    } catch {
      setEmpresas([])
    }
  }

  const loadVeiculosEmpresa = async (empresaId: number) => {
    setLoadingUsos(true)
    try {
      const res = await api.get(`/empresas/${empresaId}/usos`)
      const data = (res.data || []).map((uso: any) => ({
        ...uso,
        selected: false,
        km_input: '',
        km_permitido_input: uso.km_referencia ? String(uso.km_referencia) : '',
        valor_km_extra_input: uso.valor_km_extra ? String(uso.valor_km_extra) : '',
      }))
      setVeiculosUso(data)
    } catch {
      setVeiculosUso([])
    } finally {
      setLoadingUsos(false)
    }
  }

  const downloadFile = async (url: string, filename: string, method = 'GET', body?: any) => {
    const response =
      method === 'POST'
        ? await api.post(url, body, { responseType: 'blob' })
        : await api.get(url, { responseType: 'blob' })

    const blob = new Blob([response.data], { type: response.headers['content-type'] })
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  }

  const handlePdfContrato = async () => {
    if (!contratoId) {
      toast.error('Selecione um contrato')
      return
    }

    setLoading('contrato-pdf')
    const tid = toast.loading('Gerando PDF do contrato...')
    try {
      await downloadFile(`/relatorios/contrato/${contratoId}/pdf`, `contrato_${contratoId}.pdf`)
      toast.dismiss(tid)
      toast.success('PDF do contrato gerado!')
    } catch (error: any) {
      toast.dismiss(tid)
      toast.error(error?.response?.status === 404 ? 'Contrato nao encontrado' : await extractErrorMessage(error, 'Erro ao gerar PDF'))
    } finally {
      setLoading(null)
    }
  }

  const handlePdfFinanceiro = async () => {
    if (!financeiroDates.start || !financeiroDates.end) {
      toast.error('Selecione o periodo')
      return
    }

    setLoading('financeiro-pdf')
    const tid = toast.loading('Gerando relatorio financeiro...')
    try {
      await downloadFile(
        `/relatorios/financeiro/pdf?data_inicio=${financeiroDates.start}&data_fim=${financeiroDates.end}`,
        `financeiro_${financeiroDates.start}_${financeiroDates.end}.pdf`
      )
      toast.dismiss(tid)
      toast.success('Relatorio financeiro gerado!')
    } catch (error: any) {
      toast.dismiss(tid)
      toast.error(await extractErrorMessage(error, 'Erro ao gerar relatorio financeiro'))
    } finally {
      setLoading(null)
    }
  }

  const handleNfSingle = async (uso: VeiculoUso) => {
    const km = parseFloat(uso.km_input)
    if (!km || km <= 0) {
      toast.error(`Informe o KM percorrido para ${uso.placa}`)
      return
    }

    setLoading(`nf-single-${uso.id}`)
    const tid = toast.loading(`Gerando NF para ${uso.placa}...`)
    try {
      let url = `/relatorios/nf/${uso.id}/pdf?km_percorrido=${km}`
      const kmPermitido = parseFloat(uso.km_permitido_input)
      const valorExtra = parseFloat(uso.valor_km_extra_input)
      if (kmPermitido >= 0 && uso.km_permitido_input) url += `&km_referencia=${kmPermitido}`
      if (valorExtra >= 0 && uso.valor_km_extra_input) url += `&valor_km_extra=${valorExtra}`
      if (nfPeriod.start) url += `&periodo_inicio=${nfPeriod.start}`
      if (nfPeriod.end) url += `&periodo_fim=${nfPeriod.end}`
      await downloadFile(url, `nf_${uso.placa}.pdf`)
      toast.dismiss(tid)
      toast.success(`NF gerada para ${uso.placa}!`)
    } catch (error: any) {
      toast.dismiss(tid)
      toast.error(await extractErrorMessage(error, 'Erro ao gerar NF'))
    } finally {
      setLoading(null)
    }
  }

  const handleNfConsolidada = async () => {
    const selecionados = veiculosUso.filter((veiculo) => veiculo.selected)
    if (selecionados.length === 0) {
      toast.error('Selecione ao menos um veiculo')
      return
    }

    for (const veiculo of selecionados) {
      const km = parseFloat(veiculo.km_input)
      if (!km || km <= 0) {
        toast.error(`Informe o KM percorrido para ${veiculo.placa}`)
        return
      }
    }

    setLoading('nf-consolidada')
    const tid = toast.loading(`Gerando NF consolidada (${selecionados.length} veiculos)...`)
    try {
      const body = {
        empresa_id: parseInt(selectedEmpresa, 10),
        periodo_inicio: nfPeriod.start || undefined,
        periodo_fim: nfPeriod.end || undefined,
        veiculos: selecionados.map((veiculo) => {
          const item: any = {
            uso_id: veiculo.id,
            km_percorrido: parseFloat(veiculo.km_input),
          }
          const kmPerm = parseFloat(veiculo.km_permitido_input)
          const valorExtra = parseFloat(veiculo.valor_km_extra_input)
          if (kmPerm >= 0 && veiculo.km_permitido_input) item.km_referencia = kmPerm
          if (valorExtra >= 0 && veiculo.valor_km_extra_input) item.valor_km_extra = valorExtra
          return item
        }),
      }

      await downloadFile('/relatorios/nf/empresa/pdf', 'nf_consolidada_empresa.pdf', 'POST', body)
      toast.dismiss(tid)
      toast.success('NF consolidada gerada com sucesso!')
    } catch (error: any) {
      toast.dismiss(tid)
      toast.error(await extractErrorMessage(error, 'Erro ao gerar NF consolidada'))
    } finally {
      setLoading(null)
    }
  }

  const handleExport = async (entity: string, formato: string) => {
    const key = `${entity}-${formato}`
    setLoading(key)
    const tid = toast.loading(`Exportando ${entity}...`)

    try {
      let url = `/relatorios/exportar/${entity}?formato=${formato}`
      if (exportDates.start && exportDates.end) {
        url += `&data_inicio=${exportDates.start}&data_fim=${exportDates.end}`
      }
      if (exportStatus && (entity === 'veiculos' || entity === 'contratos')) {
        url += `&status=${exportStatus}`
      }

      await downloadFile(url, `${entity}_${exportDates.start || 'geral'}.${formato}`)
      toast.dismiss(tid)
      toast.success(`${entity} exportado!`)
    } catch (error: any) {
      toast.dismiss(tid)
      toast.error(await extractErrorMessage(error, `Erro ao exportar ${entity}`))
    } finally {
      setLoading(null)
    }
  }

  const toggleVeiculoSelection = (id: number) => {
    setVeiculosUso((current) => current.map((veiculo) => (veiculo.id === id ? { ...veiculo, selected: !veiculo.selected } : veiculo)))
  }

  const selectAll = () => {
    const allSelected = veiculosUso.length > 0 && veiculosUso.every((veiculo) => veiculo.selected)
    setVeiculosUso((current) => current.map((veiculo) => ({ ...veiculo, selected: !allSelected })))
  }

  const updateKmInput = (id: number, value: string) => {
    setVeiculosUso((current) => current.map((veiculo) => (veiculo.id === id ? { ...veiculo, km_input: value } : veiculo)))
  }

  const updateKmPermitido = (id: number, value: string) => {
    setVeiculosUso((current) => current.map((veiculo) => (veiculo.id === id ? { ...veiculo, km_permitido_input: value } : veiculo)))
  }

  const updateValorKmExtra = (id: number, value: string) => {
    setVeiculosUso((current) => current.map((veiculo) => (veiculo.id === id ? { ...veiculo, valor_km_extra_input: value } : veiculo)))
  }

  const selectedCount = veiculosUso.filter((veiculo) => veiculo.selected).length

  const overviewCards = useMemo(
    () => [
      {
        label: 'Contratos disponiveis',
        value: contratos.length,
        detail: `${contratos.filter((contrato) => contrato.status === 'ativo').length} ativos no seletor`,
      },
      {
        label: 'Empresas elegiveis',
        value: empresas.length,
        detail: 'Com NF e consolidado prontos para emissao',
      },
      {
        label: 'Veiculos no fluxo NF',
        value: veiculosUso.length,
        detail: selectedEmpresa ? 'Empresa carregada para conferencia' : 'Escolha uma empresa para visualizar',
      },
      {
        label: 'Itens selecionados',
        value: selectedCount,
        detail: selectedCount > 0 ? 'Prontos para NF consolidada' : 'Nenhum item marcado ainda',
      },
    ],
    [contratos, empresas, selectedCount, selectedEmpresa, veiculosUso.length]
  )

  const nfSummary = useMemo(() => {
    return veiculosUso.reduce(
      (acc, veiculo) => {
        const kmInput = parseFloat(veiculo.km_input) || 0
        const kmPermitido = parseFloat(veiculo.km_permitido_input) || 0
        const valorKmExtra = parseFloat(veiculo.valor_km_extra_input) || 0
        const excedente = kmPermitido > 0 && kmInput > kmPermitido ? kmInput - kmPermitido : 0

        if (kmInput > 0) acc.preenchidos += 1
        if (excedente > 0) {
          acc.comExcedente += 1
          acc.valorExtra += excedente * valorKmExtra
        }

        return acc
      },
      { preenchidos: 0, comExcedente: 0, valorExtra: 0 }
    )
  }, [veiculosUso])

  const loadingSpinner = (
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
  )

  return (
    <AppLayout>
      <div className="space-y-8 stagger-children">
        <section className="reports-hero">
          <div className="relative z-10">
            <div className="dashboard-hero-pill">
              <Sparkles size={14} />
              Central de relatorios
            </div>
            <h1 className="mt-5 text-3xl font-display font-bold text-slate-950 md:text-4xl">
              Gere PDFs, NFs e exportacoes sem perder contexto
            </h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-600 md:text-base">
              A area de relatorios agora organiza emissao de documentos, exportacao e fechamento por empresa em um fluxo mais claro para a equipe.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <div className="dashboard-hero-chip dashboard-hero-chip-emerald">
                <span className="text-xs uppercase tracking-wide text-emerald-700/80">PDFs</span>
                <strong className="text-2xl">{contratos.length > 0 ? 'Prontos' : 'Aguardando'}</strong>
              </div>
              <div className="dashboard-hero-chip dashboard-hero-chip-amber">
                <span className="text-xs uppercase tracking-wide text-amber-700/80">NFs selecionadas</span>
                <strong className="text-2xl">{selectedCount}</strong>
              </div>
              <div className="dashboard-hero-chip">
                <span className="text-xs uppercase tracking-wide text-sky-700/80">Potencial extra</span>
                <strong className="text-2xl">{formatCurrency(nfSummary.valorExtra)}</strong>
              </div>
            </div>
          </div>
          <div className="dashboard-hero-glow" />
        </section>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {overviewCards.map((card) => (
            <div key={card.label} className="report-kpi-card">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{card.label}</p>
              <p className="mt-3 text-3xl font-display font-bold text-slate-950">{card.value}</p>
              <p className="mt-2 text-sm text-slate-500">{card.detail}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
          <section className="report-panel">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-600">PDFs operacionais</p>
                <h2 className="mt-2 text-2xl font-display font-bold text-slate-950">Documentos da locadora</h2>
                <p className="mt-1 text-sm text-slate-500">Emita contrato de locacao e relatorio financeiro em poucos cliques.</p>
              </div>
              <div className="rounded-2xl bg-blue-50 p-3 text-blue-600">
                <FileText size={24} />
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-start justify-between">
                  <div className="rounded-2xl bg-blue-100 p-3 text-blue-700">
                    <FileText size={22} />
                  </div>
                  <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-700">
                    PDF
                  </span>
                </div>
                <h3 className="text-lg font-display font-bold text-slate-900">Contrato de locacao</h3>
                <p className="mt-2 text-sm text-slate-500">Contrato completo com clausulas, valores e dados do fechamento.</p>
                <div className="mt-5 space-y-3">
                  <div>
                    <label className="input-label">Contrato</label>
                    <select value={contratoId} onChange={(event) => setContratoId(event.target.value)} className="input-field">
                      <option value="">Selecione um contrato...</option>
                      {contratos.map((contrato: any) => (
                        <option key={contrato.id} value={contrato.id}>
                          #{contrato.id} - {contrato.numero} ({contrato.status})
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={handlePdfContrato}
                    className="btn-primary flex w-full items-center justify-center gap-2"
                    disabled={loading === 'contrato-pdf' || !contratoId}
                  >
                    {loading === 'contrato-pdf' ? loadingSpinner : <Download size={16} />}
                    Gerar PDF do contrato
                  </button>
                </div>
              </div>

              <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-start justify-between">
                  <div className="rounded-2xl bg-emerald-100 p-3 text-emerald-700">
                    <BarChart3 size={22} />
                  </div>
                  <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">
                    Financeiro
                  </span>
                </div>
                <h3 className="text-lg font-display font-bold text-slate-900">Relatorio financeiro</h3>
                <p className="mt-2 text-sm text-slate-500">Receitas, despesas e consolidado do periodo escolhido.</p>
                <div className="mt-5 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="input-label">Data inicio</label>
                      <input
                        type="date"
                        value={financeiroDates.start}
                        onChange={(event) => setFinanceiroDates({ ...financeiroDates, start: event.target.value })}
                        className="input-field"
                      />
                    </div>
                    <div>
                      <label className="input-label">Data fim</label>
                      <input
                        type="date"
                        value={financeiroDates.end}
                        onChange={(event) => setFinanceiroDates({ ...financeiroDates, end: event.target.value })}
                        className="input-field"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handlePdfFinanceiro}
                    className="btn-primary flex w-full items-center justify-center gap-2"
                    disabled={loading === 'financeiro-pdf' || !financeiroDates.start || !financeiroDates.end}
                  >
                    {loading === 'financeiro-pdf' ? loadingSpinner : <Download size={16} />}
                    Gerar PDF financeiro
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section className="report-panel">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-600">Saida de dados</p>
                <h2 className="mt-2 text-2xl font-display font-bold text-slate-950">Exportacao inteligente</h2>
                <p className="mt-1 text-sm text-slate-500">Filtre o periodo e leve os dados para planilhas e contador.</p>
              </div>
              <div className="rounded-2xl bg-amber-50 p-3 text-amber-600">
                <FileSpreadsheet size={24} />
              </div>
            </div>

            <div className="mt-6 rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
              <h3 className="text-sm font-display font-bold text-slate-800">Filtros da exportacao</h3>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                <div>
                  <label className="input-label">Data inicio</label>
                  <input
                    type="date"
                    value={exportDates.start}
                    onChange={(event) => setExportDates({ ...exportDates, start: event.target.value })}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Data fim</label>
                  <input
                    type="date"
                    value={exportDates.end}
                    onChange={(event) => setExportDates({ ...exportDates, end: event.target.value })}
                    className="input-field"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="input-label">Status</label>
                  <select value={exportStatus} onChange={(event) => setExportStatus(event.target.value)} className="input-field">
                    <option value="">Todos</option>
                    <option value="ativo">Ativo</option>
                    <option value="finalizado">Finalizado</option>
                    <option value="disponivel">Disponivel</option>
                    <option value="alugado">Alugado</option>
                  </select>
                </div>
              </div>

              <button
                className="btn-secondary mt-4 w-full"
                onClick={() => {
                  setExportDates({ start: '', end: '' })
                  setExportStatus('')
                }}
              >
                Limpar filtros
              </button>
            </div>

            <div className="mt-5 space-y-3">
              {exportCards.map((card) => {
                const Icon = card.icon
                return (
                  <div key={card.key} className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex items-start gap-3">
                      <div className={`rounded-2xl p-3 ${card.accentClass}`}>
                        <Icon size={20} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-display font-bold text-slate-900">{card.label}</h3>
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${card.badgeClass}`}>
                            Dados
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-slate-500">{card.description}</p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <button
                        onClick={() => handleExport(card.key, 'xlsx')}
                        className="btn-primary flex items-center justify-center gap-2 py-2 text-xs"
                        disabled={loading === `${card.key}-xlsx`}
                      >
                        {loading === `${card.key}-xlsx` ? loadingSpinner : <FileSpreadsheet size={14} />}
                        XLSX
                      </button>
                      <button
                        onClick={() => handleExport(card.key, 'csv')}
                        className="btn-secondary flex items-center justify-center gap-2 py-2 text-xs"
                        disabled={loading === `${card.key}-csv`}
                      >
                        {loading === `${card.key}-csv` ? loadingSpinner : <Download size={14} />}
                        CSV
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        </div>

        <section className="report-panel">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-600">Faturamento por empresa</p>
              <h2 className="mt-2 text-2xl font-display font-bold text-slate-950">Nota fiscal por uso de veiculo</h2>
              <p className="mt-1 max-w-3xl text-sm text-slate-500">
                Selecione a empresa, ajuste KM percorrido, limite e valor por KM extra para gerar NF individual ou consolidada.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Preenchidos</p>
                <p className="mt-2 text-xl font-display font-bold text-slate-900">{nfSummary.preenchidos}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Com excedente</p>
                <p className="mt-2 text-xl font-display font-bold text-slate-900">{nfSummary.comExcedente}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Valor extra</p>
                <p className="mt-2 text-xl font-display font-bold text-slate-900">{formatCurrency(nfSummary.valorExtra)}</p>
              </div>
            </div>
          </div>

          <div className="mt-6 rounded-[24px] border border-slate-200 bg-slate-50/80 p-4">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end">
              <div className="min-w-0 flex-1">
                <label className="input-label">Empresa</label>
                <select value={selectedEmpresa} onChange={(event) => setSelectedEmpresa(event.target.value)} className="input-field">
                  <option value="">Selecione uma empresa...</option>
                  {empresas.map((empresa: any) => (
                    <option key={empresa.id} value={empresa.id}>
                      {empresa.nome} - CNPJ: {empresa.cnpj}
                    </option>
                  ))}
                </select>
              </div>

              {veiculosUso.length > 0 && (
                <div className="grid gap-2 sm:grid-cols-2">
                  <button onClick={selectAll} className="btn-secondary px-4 py-3 text-sm">
                    {veiculosUso.every((veiculo) => veiculo.selected) ? 'Desmarcar todos' : 'Selecionar todos'}
                  </button>
                  <button
                    onClick={handleNfConsolidada}
                    className="btn-primary flex items-center justify-center gap-2 px-4 py-3 text-sm"
                    disabled={loading === 'nf-consolidada' || selectedCount === 0}
                  >
                    {loading === 'nf-consolidada' ? loadingSpinner : <Receipt size={15} />}
                    NF consolidada ({selectedCount})
                  </button>
                </div>
              )}
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div>
                <label className="input-label">Periodo inicial da medicao</label>
                <input
                  type="date"
                  value={nfPeriod.start}
                  onChange={(event) => setNfPeriod((current) => ({ ...current, start: event.target.value }))}
                  className="input-field"
                />
              </div>
              <div>
                <label className="input-label">Periodo final da medicao</label>
                <input
                  type="date"
                  value={nfPeriod.end}
                  onChange={(event) => setNfPeriod((current) => ({ ...current, end: event.target.value }))}
                  className="input-field"
                />
              </div>
            </div>
          </div>

          <div className="mt-6">
            {loadingUsos ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="report-skeleton-card" />
                ))}
              </div>
            ) : selectedEmpresa && veiculosUso.length === 0 ? (
              <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
                <Car size={42} className="mx-auto text-slate-300" />
                <h3 className="mt-4 text-lg font-display font-bold text-slate-900">Nenhum veiculo para essa empresa</h3>
                <p className="mt-2 text-sm text-slate-500">Cadastre ou vincule veiculos antes de gerar as notas fiscais.</p>
              </div>
            ) : veiculosUso.length > 0 ? (
              <div className="space-y-4">
                {veiculosUso.map((veiculo) => {
                  const kmInput = parseFloat(veiculo.km_input) || 0
                  const kmPermitido = parseFloat(veiculo.km_permitido_input) || 0
                  const valorKmExtra = parseFloat(veiculo.valor_km_extra_input) || 0
                  const excedeu = kmPermitido > 0 && kmInput > kmPermitido
                  const kmExcedente = excedeu ? kmInput - kmPermitido : 0
                  const valorExtra = kmExcedente * valorKmExtra

                  return (
                    <div
                      key={veiculo.id}
                      className={`rounded-[28px] border bg-white p-5 shadow-sm transition-all duration-200 ${
                        veiculo.selected
                          ? 'border-blue-200 shadow-[0_16px_34px_rgba(59,130,246,0.12)]'
                          : 'border-slate-200'
                      }`}
                    >
                      <div className="flex flex-col gap-4 xl:flex-row xl:items-start">
                        <div className="flex min-w-0 flex-1 items-start gap-4">
                          <input
                            type="checkbox"
                            checked={veiculo.selected}
                            onChange={() => toggleVeiculoSelection(veiculo.id)}
                            className="mt-1 h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-lg font-display font-bold text-slate-950">{veiculo.placa}</span>
                              <span className="text-sm text-slate-500">{veiculo.marca} {veiculo.modelo}</span>
                              <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${veiculo.status === 'ativo' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                                {veiculo.status}
                              </span>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-400">
                              {veiculo.data_inicio && <span>Inicio: {new Date(veiculo.data_inicio).toLocaleDateString('pt-BR')}</span>}
                              {veiculo.data_fim && <span>Fim: {new Date(veiculo.data_fim).toLocaleDateString('pt-BR')}</span>}
                              {veiculo.valor_diaria_empresa && <span>Valor base: {formatCurrency(Number(veiculo.valor_diaria_empresa))}</span>}
                              {veiculo.medicoes_salvas ? <span>{veiculo.medicoes_salvas} medicoes salvas</span> : null}
                              {veiculo.ultimo_periodo_inicio ? <span>Ultimo periodo: {new Date(veiculo.ultimo_periodo_inicio).toLocaleDateString('pt-BR')} a {new Date(veiculo.ultimo_periodo_fim || veiculo.ultimo_periodo_inicio).toLocaleDateString('pt-BR')}</span> : null}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          <div className={`rounded-2xl px-3 py-2 text-xs font-semibold ${excedeu ? 'bg-red-50 text-red-700' : kmInput > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                            {excedeu
                              ? `+${kmExcedente.toFixed(0)} km | ${formatCurrency(valorExtra)}`
                              : kmInput > 0
                                ? 'Dentro do limite'
                                : 'Aguardando conferencia'}
                          </div>
                          <button
                            onClick={() => handleNfSingle(veiculo)}
                            className="btn-secondary flex items-center gap-2 px-4 py-2.5 text-xs"
                            disabled={loading === `nf-single-${veiculo.id}` || !veiculo.km_input}
                          >
                            {loading === `nf-single-${veiculo.id}` ? loadingSpinner : <Download size={14} />}
                            NF individual
                          </button>
                        </div>
                      </div>

                      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-4">
                        <div>
                          <label className="input-label">KM percorrido *</label>
                          <input
                            type="number"
                            value={veiculo.km_input}
                            onChange={(event) => updateKmInput(veiculo.id, event.target.value)}
                            className="input-field"
                            placeholder="Digite o KM"
                            min="0"
                            step="0.1"
                          />
                        </div>
                        <div>
                          <label className="input-label">KM permitido</label>
                          <input
                            type="number"
                            value={veiculo.km_permitido_input}
                            onChange={(event) => updateKmPermitido(veiculo.id, event.target.value)}
                            className="input-field"
                            placeholder="Limite contratual"
                            min="0"
                            step="0.1"
                          />
                        </div>
                        <div>
                          <label className="input-label">Valor por KM extra</label>
                          <input
                            type="number"
                            value={veiculo.valor_km_extra_input}
                            onChange={(event) => updateValorKmExtra(veiculo.id, event.target.value)}
                            className="input-field"
                            placeholder="R$/km"
                            min="0"
                            step="0.01"
                          />
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Fechamento</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">
                            {excedeu ? `${kmExcedente.toFixed(0)} km extra` : 'Sem excedente'}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {excedeu ? formatCurrency(valorExtra) : 'Sem cobranca adicional'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-[28px] border border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center">
                <Building2 size={42} className="mx-auto text-slate-300" />
                <h3 className="mt-4 text-lg font-display font-bold text-slate-900">Escolha uma empresa para comecar</h3>
                <p className="mt-2 text-sm text-slate-500">Quando voce selecionar a empresa, liberamos o fluxo completo de NF individual e consolidada.</p>
              </div>
            )}
          </div>
        </section>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-blue-50 p-3 text-blue-600">
                <CheckCircle2 size={20} />
              </div>
              <div>
                <h3 className="text-base font-display font-bold text-slate-900">Fluxo mais claro</h3>
                <p className="mt-1 text-sm text-slate-500">PDF, NF e exportacao agora estao organizados por objetivo, nao por tipo tecnico.</p>
              </div>
            </div>
          </div>
          <div className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-amber-50 p-3 text-amber-600">
                <AlertTriangle size={20} />
              </div>
              <div>
                <h3 className="text-base font-display font-bold text-slate-900">Conferencia de KM</h3>
                <p className="mt-1 text-sm text-slate-500">O painel mostra rapidamente onde ha excedente e qual valor pode ser repassado.</p>
              </div>
            </div>
          </div>
          <div className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-600">
                <ArrowRight size={20} />
              </div>
              <div>
                <h3 className="text-base font-display font-bold text-slate-900">Menos atrito</h3>
                <p className="mt-1 text-sm text-slate-500">Tudo ficou mais rapido para operador, financeiro e contador trabalharem no mesmo fluxo.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

export default Relatorios
