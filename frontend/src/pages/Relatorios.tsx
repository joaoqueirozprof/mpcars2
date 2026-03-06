import React, { useState } from 'react'
import { Download, FileText, BarChart3, TrendingUp, Users, Zap, Calendar, Printer, Eye, Trash2, FileSpreadsheet } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import AppLayout from '@/components/layout/AppLayout'
import toast from 'react-hot-toast'
import api from '@/services/api'

interface GeneratedReport {
  id: string
  name: string
  type: string
  date: string
  url: string
  status: 'gerando' | 'completo' | 'erro'
}

const Relatorios: React.FC = () => {
  const { user } = useAuth()
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const [generatedReports, setGeneratedReports] = useState<GeneratedReport[]>([])
  const [loading, setLoading] = useState<string | null>(null)

  const reports = [
    { id: 'contratos', name: 'Relatorio de Contratos', description: 'Lista completa de contratos com detalhes de clientes e valores', icon: FileText, color: 'blue', needsDate: true, pdfEndpoint: '/relatorios/contratos/pdf', xlsxEndpoint: '/relatorios/contratos/xlsx' },
    { id: 'receitas', name: 'Relatorio de Receitas', description: 'Resumo de receitas por periodo, cliente e tipo de servico', icon: TrendingUp, color: 'green', needsDate: true, pdfEndpoint: '/relatorios/receitas/pdf', xlsxEndpoint: null },
    { id: 'despesas', name: 'Relatorio de Despesas', description: 'Detalhamento de despesas por categoria e veiculo', icon: BarChart3, color: 'orange', needsDate: true, pdfEndpoint: '/relatorios/despesas/pdf', xlsxEndpoint: '/relatorios/despesas/xlsx' },
    { id: 'frota', name: 'Relatorio de Frota', description: 'Status atual da frota, manutencao e disponibilidade', icon: Zap, color: 'purple', needsDate: false, pdfEndpoint: '/relatorios/frota/pdf', xlsxEndpoint: '/relatorios/veiculos/xlsx' },
    { id: 'clientes', name: 'Relatorio de Clientes', description: 'Analise de clientes, historico de contratos e pagamentos', icon: Users, color: 'cyan', needsDate: false, pdfEndpoint: '/relatorios/clientes/pdf', xlsxEndpoint: '/relatorios/clientes/xlsx' },
    { id: 'ipva', name: 'Relatorio de IPVA', description: 'Pendencias, pagamentos e historico de IPVA por veiculo', icon: Calendar, color: 'red', needsDate: false, pdfEndpoint: '/relatorios/ipva/pdf', xlsxEndpoint: null },
  ]

  const downloadFile = async (url: string, filename: string) => {
    try {
      const response = await api.get(url, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: response.headers['content-type'] })
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
      return downloadUrl
    } catch (error: any) {
      console.error('Download error:', error)
      throw error
    }
  }

  const handleGenerateReport = async (report: typeof reports[0], format: 'pdf' | 'xlsx' | 'print') => {
    if (report.needsDate && (!dateRange.start || !dateRange.end)) {
      toast.error('Selecione o periodo do relatorio')
      return
    }

    const endpoint = format === 'xlsx' ? report.xlsxEndpoint : report.pdfEndpoint
    if (!endpoint) {
      toast.error('Formato nao disponivel para este relatorio')
      return
    }

    const loadingId = `${report.id}-${format}`
    setLoading(loadingId)
    const toastId = toast.loading(`Gerando ${report.name}...`)

    try {
      let url = endpoint
      if (report.needsDate) {
        url += `?data_inicio=${dateRange.start}&data_fim=${dateRange.end}`
      }

      const ext = format === 'xlsx' ? 'xlsx' : 'pdf'
      const filename = `${report.id}_${dateRange.start || 'geral'}_${dateRange.end || new Date().toISOString().split('T')[0]}.${ext}`

      if (format === 'print') {
        // For print: open PDF in new tab
        const response = await api.get(url, { responseType: 'blob' })
        const blob = new Blob([response.data], { type: 'application/pdf' })
        const pdfUrl = window.URL.createObjectURL(blob)
        const printWindow = window.open(pdfUrl, '_blank')
        if (printWindow) {
          printWindow.onload = () => {
            printWindow.print()
          }
        }
        toast.dismiss(toastId)
        toast.success('PDF aberto para impressao!')
      } else {
        await downloadFile(url, filename)
        toast.dismiss(toastId)
        toast.success(`${report.name} gerado com sucesso!`)
      }

      // Add to generated reports list
      const newReport: GeneratedReport = {
        id: `${Date.now()}`,
        name: `${report.name} - ${format.toUpperCase()}`,
        type: format,
        date: new Date().toLocaleString('pt-BR'),
        url: endpoint,
        status: 'completo',
      }
      setGeneratedReports(prev => [newReport, ...prev].slice(0, 10))

    } catch (error: any) {
      toast.dismiss(toastId)
      const msg = error?.response?.data?.detail || 'Erro ao gerar relatorio'
      toast.error(msg)
    } finally {
      setLoading(null)
    }
  }

  const handleDeleteReport = (reportId: string) => {
    setGeneratedReports(prev => prev.filter(r => r.id !== reportId))
    toast.success('Relatorio removido da lista')
  }

  const getColorClasses = (color: string) => {
    const colors: Record<string, string> = {
      blue: 'bg-blue-50 text-blue-600 border-blue-200',
      green: 'bg-green-50 text-green-600 border-green-200',
      orange: 'bg-orange-50 text-orange-600 border-orange-200',
      purple: 'bg-purple-50 text-purple-600 border-purple-200',
      cyan: 'bg-cyan-50 text-cyan-600 border-cyan-200',
      red: 'bg-red-50 text-red-600 border-red-200',
    }
    return colors[color] || colors.blue
  }

  const getIconColorClasses = (color: string) => {
    const colors: Record<string, string> = {
      blue: 'bg-blue-100 text-blue-700',
      green: 'bg-green-100 text-green-700',
      orange: 'bg-orange-100 text-orange-700',
      purple: 'bg-purple-100 text-purple-700',
      cyan: 'bg-cyan-100 text-cyan-700',
      red: 'bg-red-100 text-red-700',
    }
    return colors[color] || colors.blue
  }

  return (
    <AppLayout>
      <div className="space-y-8 stagger-children">
        <div>
          <h1 className="page-title">Relatorios</h1>
          <p className="page-subtitle">Geracao e exportacao de relatorios do sistema com filtros por periodo</p>
        </div>

        <div className="card">
          <h2 className="text-lg font-display font-bold text-slate-900 mb-6">Filtro de Periodo</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="input-label">Data Inicio</label>
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="input-field"
              />
            </div>
            <div>
              <label className="input-label">Data Fim</label>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="input-field"
              />
            </div>
            <div className="flex items-end">
              <button
                className="btn-primary w-full"
                onClick={() => {
                  if (dateRange.start && dateRange.end) {
                    toast.success('Periodo atualizado')
                  } else {
                    toast.error('Selecione ambas as datas')
                  }
                }}
              >
                Aplicar Filtro
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {reports.map((report) => {
            const IconComponent = report.icon
            const colorClasses = getColorClasses(report.color)
            const iconColorClasses = getIconColorClasses(report.color)
            const isDisabled = report.needsDate && (!dateRange.start || !dateRange.end)

            return (
              <div key={report.id} className="card card-hover transition-all duration-200">
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-xl ${iconColorClasses}`}>
                    <IconComponent size={24} />
                  </div>
                  {!report.needsDate && (
                    <span className="badge badge-info text-xs">Sem periodo</span>
                  )}
                </div>

                <h3 className="text-lg font-display font-bold text-slate-900 mb-2">{report.name}</h3>
                <p className="text-sm text-slate-600 mb-6 line-clamp-2">{report.description}</p>

                <div className="space-y-2">
                  <button
                    onClick={() => handleGenerateReport(report, 'pdf')}
                    className="btn-primary w-full flex items-center justify-center gap-2 py-2 text-sm"
                    disabled={isDisabled || loading === `${report.id}-pdf`}
                  >
                    {loading === `${report.id}-pdf` ? (
                      <span className="animate-spin inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full"></span>
                    ) : (
                      <Download size={16} />
                    )}
                    Gerar PDF
                  </button>

                  <div className="grid grid-cols-3 gap-2">
                    <button
                      onClick={() => handleGenerateReport(report, 'print')}
                      className="btn-secondary py-2 text-xs flex items-center justify-center gap-1"
                      disabled={isDisabled || loading === `${report.id}-print`}
                      title="Imprimir"
                    >
                      <Printer size={14} />
                      Imprimir
                    </button>
                    <button
                      onClick={() => handleGenerateReport(report, 'xlsx')}
                      className="btn-secondary py-2 text-xs flex items-center justify-center gap-1"
                      disabled={isDisabled || !report.xlsxEndpoint || loading === `${report.id}-xlsx`}
                      title="Exportar Excel"
                    >
                      <FileSpreadsheet size={14} />
                      Excel
                    </button>
                    <button
                      onClick={() => {
                        handleGenerateReport(report, 'pdf').then(() => {})
                      }}
                      className="btn-secondary py-2 text-xs flex items-center justify-center gap-1"
                      disabled={isDisabled}
                      title="Visualizar"
                    >
                      <Eye size={14} />
                      Ver
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {generatedReports.length > 0 && (
          <div className="card">
            <h2 className="text-lg font-display font-bold text-slate-900 mb-6">Relatorios Gerados</h2>
            <div className="space-y-3">
              {generatedReports.map((report) => (
                <div
                  key={report.id}
                  className="flex items-center justify-between p-4 border border-slate-200 rounded-xl hover:border-slate-300 transition-colors animate-fade-in"
                >
                  <div className="flex-1">
                    <p className="font-medium text-slate-900">{report.name}</p>
                    <p className="text-sm text-slate-500">{report.date}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`badge ${report.status === 'completo' ? 'badge-success' : report.status === 'erro' ? 'badge-danger' : 'badge-warning'} text-xs`}>
                      {report.status === 'completo' ? 'Completo' : report.status === 'erro' ? 'Erro' : 'Gerando...'}
                    </span>
                    <button
                      onClick={() => handleDeleteReport(report.id)}
                      className="btn-icon p-1.5"
                      title="Remover"
                    >
                      <Trash2 size={16} className="text-red-400 hover:text-red-600" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}

export default Relatorios
