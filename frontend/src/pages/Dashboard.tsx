import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import {
  Car,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  DollarSign,
  FileText,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Users,
  Zap,
  Calendar,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import { formatCurrency, formatDate } from '@/lib/utils'
import { DashboardStats } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const Dashboard: React.FC = () => {
  const { user } = useAuth()
  const [alertFilter, setAlertFilter] = useState<'critica' | 'atencao' | 'info'>('critica')

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('/dashboard')
      return data
    },
  })

  const getAlertIcon = (urgencia: string) => {
    switch (urgencia) {
      case 'critica':
        return AlertTriangle
      case 'atencao':
        return Clock
      case 'info':
        return Zap
      default:
        return AlertCircle
    }
  }

  const getAlertBadgeClass = (urgencia: string) => {
    switch (urgencia) {
      case 'critica':
        return 'badge-danger'
      case 'atencao':
        return 'badge-warning'
      case 'info':
        return 'badge-info'
      default:
        return 'badge-neutral'
    }
  }

  const getAlertBorderClass = (urgencia: string) => {
    switch (urgencia) {
      case 'critica':
        return 'border-l-red-500 bg-red-50/50'
      case 'atencao':
        return 'border-l-amber-500 bg-amber-50/50'
      case 'info':
        return 'border-l-blue-500 bg-blue-50/50'
      default:
        return 'border-l-slate-500 bg-slate-50/50'
    }
  }

  const KPICard = ({
    icon: Icon,
    label,
    value,
    color,
    trend,
  }: {
    icon: React.ElementType
    label: string
    value: string | number
    color: 'blue' | 'green' | 'orange' | 'emerald'
    trend?: number
  }) => {
    const colorClasses = {
      blue: 'bg-blue-100 text-blue-600',
      green: 'bg-emerald-100 text-emerald-600',
      orange: 'bg-orange-100 text-orange-600',
      emerald: 'bg-emerald-100 text-emerald-600',
    }

    return (
      <div className="kpi-card group">
        <div className={`kpi-icon ${colorClasses[color]}`}>
          {isLoading ? (
            <div className="w-6 h-6 bg-slate-300 rounded animate-pulse" />
          ) : (
            <Icon size={24} />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="kpi-label">{label}</p>
          {isLoading ? (
            <div className="h-8 w-24 bg-slate-200 rounded animate-pulse mt-1" />
          ) : (
            <h3 className="kpi-value">{value}</h3>
          )}
          {trend !== undefined && !isLoading && (
            <div className="flex items-center gap-1 mt-2 text-xs">
              {trend > 0 ? (
                <>
                  <TrendingUp size={14} className="text-emerald-600" />
                  <span className="text-emerald-600 font-medium">+{trend}%</span>
                </>
              ) : trend < 0 ? (
                <>
                  <TrendingDown size={14} className="text-red-600" />
                  <span className="text-red-600 font-medium">{trend}%</span>
                </>
              ) : null}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-8 pb-8">
        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">
              Bem-vindo, {user?.nome || 'Usuário'}. Aqui está um resumo do seu negócio.
            </p>
          </div>
        </div>

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 stagger-children animate-fade-in-up">
          <KPICard
            icon={Car}
            label="Total de Veículos"
            value={isLoading ? '-' : stats?.total_veiculos || 0}
            color="blue"
          />
          <KPICard
            icon={Zap}
            label="Veículos Alugados"
            value={isLoading ? '-' : stats?.veiculos_alugados || 0}
            color="green"
          />
          <KPICard
            icon={FileText}
            label="Contratos Ativos"
            value={isLoading ? '-' : stats?.contratos_ativos || 0}
            color="orange"
          />
          <KPICard
            icon={DollarSign}
            label="Receita Mês"
            value={isLoading ? '-' : formatCurrency(stats?.receita_mensal || 0)}
            color="emerald"
            trend={stats?.variacao_receita_mensal}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 animate-fade-in-up" style={{ animationDelay: '60ms' }}>
          <div className="card bg-slate-50 border border-slate-200">
            <p className="text-xs uppercase tracking-wide text-slate-500">Veiculos Disponiveis</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">{isLoading ? '-' : stats?.veiculos_disponiveis || 0}</p>
          </div>
          <div className="card bg-slate-50 border border-slate-200">
            <p className="text-xs uppercase tracking-wide text-slate-500">Taxa de Ocupacao</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">{isLoading ? '-' : `${stats?.taxa_ocupacao || 0}%`}</p>
          </div>
          <div className="card bg-slate-50 border border-slate-200">
            <p className="text-xs uppercase tracking-wide text-slate-500">Ticket Medio</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">{isLoading ? '-' : formatCurrency(stats?.ticket_medio || 0)}</p>
          </div>
          <div className="card bg-slate-50 border border-slate-200">
            <p className="text-xs uppercase tracking-wide text-slate-500">Clientes Ativos</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">{isLoading ? '-' : stats?.total_clientes || 0}</p>
          </div>
        </div>

        {/* Revenue Chart and Alerts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-up" style={{ animationDelay: '120ms' }}>
          {/* Revenue Chart */}
          <div className="lg:col-span-2 card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900">Receita vs Despesas</h2>
              <p className="text-sm text-slate-500 mt-1">Comparação mensal de receitas e despesas</p>
            </div>

            {isLoading ? (
              <div className="h-80 bg-slate-100 rounded-xl animate-pulse" />
            ) : stats?.receita_vs_despesas && stats.receita_vs_despesas.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart
                  data={stats.receita_vs_despesas}
                  margin={{ top: 20, right: 30, left: 0, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="mes" stroke="#94a3b8" style={{ fontSize: '12px' }} />
                  <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                    cursor={{ fill: 'rgba(37, 99, 235, 0.1)' }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: '20px' }}
                    iconType="circle"
                    formatter={(value) => (
                      <span style={{ color: '#64748b', fontSize: '13px', fontWeight: '500' }}>
                        {value === 'receita' ? 'Receita' : 'Despesa'}
                      </span>
                    )}
                  />
                  <Bar
                    dataKey="receita"
                    fill="#3b82f6"
                    radius={[8, 8, 0, 0]}
                    isAnimationActive={true}
                  />
                  <Bar
                    dataKey="despesa"
                    fill="#ef4444"
                    radius={[8, 8, 0, 0]}
                    isAnimationActive={true}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state min-h-80">
                <div className="empty-state-icon">
                  <BarChart size={32} className="text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium">Sem dados disponíveis</p>
              </div>
            )}
          </div>

          {/* Alerts Section */}
          <div className="card">
            <div className="mb-5">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <AlertCircle size={20} className="text-orange-600" />
                Alertas
              </h2>
              <p className="text-sm text-slate-500 mt-1">Ações requeridas</p>
            </div>

            {/* Alert Filter Tabs */}
            <div className="flex gap-2 mb-4 pb-4 border-b border-slate-200">
              {['critica', 'atencao', 'info'].map((urgency) => {
                const isActive = alertFilter === urgency
                const labels = {
                  critica: 'Crítica',
                  atencao: 'Atenção',
                  info: 'Info',
                }

                return (
                  <button
                    key={urgency}
                    onClick={() => setAlertFilter(urgency as any)}
                    className={`filter-tab ${isActive ? 'filter-tab-active' : 'filter-tab-inactive'}`}
                  >
                    {labels[urgency as keyof typeof labels]}
                  </button>
                )
              })}
            </div>

            {/* Alerts List */}
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {isLoading ? (
                <>
                  <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                  <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                  <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                </>
              ) : stats?.alertas && stats.alertas.length > 0 ? (
                stats.alertas
                  .filter((a) => a.urgencia === alertFilter)
                  .map((alert) => {
                    const AlertIcon = getAlertIcon(alert.urgencia)
                    const badgeClass = getAlertBadgeClass(alert.urgencia)
                    const borderClass = getAlertBorderClass(alert.urgencia)

                    return (
                      <div
                        key={alert.id}
                        className={`p-4 rounded-lg border-l-4 transition-all duration-200 hover:shadow-sm ${borderClass}`}
                      >
                        <div className="flex items-start gap-3">
                          <AlertIcon size={16} className="mt-0.5 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="font-semibold text-sm text-slate-900">{alert.titulo}</p>
                              <span className={`badge text-xs ${badgeClass}`}>
                                {alert.urgencia === 'critica'
                                  ? 'Crítica'
                                  : alert.urgencia === 'atencao'
                                    ? 'Atenção'
                                    : 'Info'}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 mt-1 line-clamp-2">
                              {alert.descricao}
                            </p>
                          </div>
                        </div>
                      </div>
                    )
                  })
              ) : (
                <div className="empty-state py-8">
                  <div className="empty-state-icon">
                    <CheckCircle2 size={24} className="text-emerald-600" />
                  </div>
                  <p className="text-slate-500 font-medium text-sm">Sem alertas</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Top Clients and Vehicles */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: '240ms' }}>
          {/* Top Clients */}
          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <Users size={20} className="text-blue-600" />
                Top 5 Clientes
              </h2>
              <p className="text-sm text-slate-500 mt-1">Clientes com maior volume de contrato</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.top_clientes && stats.top_clientes.length > 0 ? (
              <div className="space-y-3">
                {stats.top_clientes.map((cliente, idx) => {
                  const initials = cliente.nome
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .toUpperCase()
                    .slice(0, 2)

                  return (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors duration-200 group"
                    >
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center flex-shrink-0 text-white font-semibold text-sm">
                          {initials}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-slate-900 truncate">{cliente.nome}</p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {cliente.contratos} contrato{cliente.contratos !== 1 ? 's' : ''}
                          </p>
                        </div>
                      </div>
                      <p className="font-semibold text-emerald-600 flex-shrink-0 ml-3">
                        {formatCurrency(cliente.valor_total)}
                      </p>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="empty-state py-8">
                <div className="empty-state-icon">
                  <Users size={24} className="text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium text-sm">Sem dados</p>
              </div>
            )}
          </div>

          {/* Top Vehicles */}
          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <Car size={20} className="text-orange-600" />
                Top 5 Veículos
              </h2>
              <p className="text-sm text-slate-500 mt-1">Veículos mais alugados</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.top_veiculos && stats.top_veiculos.length > 0 ? (
              <div className="space-y-3">
                {stats.top_veiculos.map((veiculo, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors duration-200 group"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-400 to-orange-600 flex items-center justify-center flex-shrink-0 text-white font-semibold text-sm">
                        <Car size={18} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 truncate">{veiculo.placa}</p>
                        <p className="text-xs text-slate-500 mt-0.5 truncate">{veiculo.modelo}</p>
                      </div>
                    </div>
                    <div className="badge badge-info flex-shrink-0 ml-3">
                      {veiculo.alugadas}x
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state py-8">
                <div className="empty-state-icon">
                  <Car size={24} className="text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium text-sm">Sem dados</p>
              </div>
            )}
          </div>
        </div>

        {/* Late Contracts and Upcoming Expirations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: '360ms' }}>
          {/* Overdue Contracts */}
          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <AlertTriangle size={20} className="text-red-600" />
                Contratos em Atraso
              </h2>
              <p className="text-sm text-slate-500 mt-1">Ação necessária imediata</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.contratos_atrasados && stats.contratos_atrasados.length > 0 ? (
              <div className="space-y-3">
                {stats.contratos_atrasados.map((contrato) => (
                  <div
                    key={contrato.id}
                    className="p-4 rounded-lg border-l-4 border-l-red-500 bg-red-50/50 hover:shadow-sm transition-all duration-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-900 text-sm">{contrato.numero}</p>
                        <p className="text-xs text-slate-600 mt-1">
                          Vencimento: {formatDate(contrato.data_fim)}
                        </p>
                      </div>
                      <span className="badge badge-danger flex-shrink-0">Atraso</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state py-8">
                <div className="empty-state-icon">
                  <CheckCircle2 size={24} className="text-emerald-600" />
                </div>
                <p className="text-slate-500 font-medium text-sm">Nenhum atraso</p>
              </div>
            )}
          </div>

          {/* Upcoming Expirations */}
          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <Calendar size={20} className="text-amber-600" />
                Próximos Vencimentos
              </h2>
              <p className="text-sm text-slate-500 mt-1">Próximos 30 dias</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.proximos_vencimentos && stats.proximos_vencimentos.length > 0 ? (
              <div className="space-y-3">
                {stats.proximos_vencimentos.map((item, idx) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-lg border-l-4 border-l-amber-500 bg-amber-50/50 hover:shadow-sm transition-all duration-200"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0 text-amber-600 font-semibold text-sm">
                        {idx + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-900 text-sm line-clamp-1">
                          {item.titulo}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-slate-500">
                            {item.tipo}
                          </span>
                          <span className="text-xs text-slate-400">•</span>
                          <span className="text-xs text-slate-500">
                            {formatDate(item.data_vencimento)}
                          </span>
                        </div>
                      </div>
                      <Clock size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state py-8">
                <div className="empty-state-icon">
                  <Calendar size={24} className="text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium text-sm">Nada pendente</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

export default Dashboard
