import React, { startTransition, useDeferredValue, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Calendar,
  Car,
  CheckCircle2,
  ChevronRight,
  Clock,
  DollarSign,
  FileText,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Users,
  Wrench,
  Zap,
} from 'lucide-react'
import api from '@/services/api'
import AppLayout from '@/components/layout/AppLayout'
import { cn, formatCurrency, formatDate, formatDateTime } from '@/lib/utils'
import { DashboardStats } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

const formatInteger = (value: number) =>
  new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(Math.round(value))

const formatPercent = (value: number) =>
  new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: value % 1 === 0 ? 0 : 1,
    maximumFractionDigits: 1,
  }).format(value)

const formatAgendaTime = (value?: string | null) => {
  if (!value) return 'Hoje'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Hoje'
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

const CountUpValue: React.FC<{
  value: number
  formatter?: (value: number) => string
  className?: string
}> = ({ value, formatter = formatInteger, className }) => {
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
    const duration = 700
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
  }, [value])

  return <span className={className}>{formatter(displayValue)}</span>
}

const Dashboard: React.FC = () => {
  const { user, canAccess } = useAuth()
  const [alertFilter, setAlertFilter] = useState<'critica' | 'atencao' | 'info'>('critica')
  const deferredAlertFilter = useDeferredValue(alertFilter)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('/dashboard')
      return data
    },
  })

  const alerts = stats?.alertas || []
  const alertCounts = {
    critica: alerts.filter((alert) => alert.urgencia === 'critica').length,
    atencao: alerts.filter((alert) => alert.urgencia === 'atencao').length,
    info: alerts.filter((alert) => alert.urgencia === 'info').length,
  }
  const filteredAlerts = alerts.filter((alert) => alert.urgencia === deferredAlertFilter)
  const agendaHoje = stats?.agenda_hoje || []
  const criticalAlerts = alertCounts.critica

  const operationScore = stats
    ? clamp(
        100
          - criticalAlerts * 12
          - (stats.contratos_atrasados.length * 10)
          - (stats.veiculos_manutencao * 5)
          - (stats.reservas_pendentes > 5 ? 6 : 0)
          + (stats.taxa_ocupacao >= 55 && stats.taxa_ocupacao <= 88 ? 4 : 0),
        34,
        100,
      )
    : 0

  const scoreLabel =
    operationScore >= 85
      ? 'Operacao saudavel'
      : operationScore >= 68
        ? 'Operacao sob observacao'
        : 'Operacao pede acao imediata'

  const scoreTone =
    operationScore >= 85 ? 'emerald' : operationScore >= 68 ? 'amber' : 'red'

  const actionCards = [
    {
      title: 'Reservas pendentes',
      description: 'Confirmar ou converter antes da retirada.',
      value: stats?.reservas_pendentes || 0,
      href: '/reservas',
      slug: 'reservas',
      icon: Calendar,
      tone: 'amber',
      pulse: (stats?.reservas_pendentes || 0) > 0,
      progress: Math.min((stats?.reservas_pendentes || 0) * 18, 100),
    },
    {
      title: 'Retiradas de hoje',
      description: 'Contratos com entrega para liberar ainda hoje.',
      value: stats?.retiradas_hoje || 0,
      href: '/contratos',
      slug: 'contratos',
      icon: FileText,
      tone: 'blue',
      pulse: (stats?.retiradas_hoje || 0) > 0,
      progress: Math.min((stats?.retiradas_hoje || 0) * 28, 100),
    },
    {
      title: 'Devolucoes de hoje',
      description: 'Encerramentos e vistoria que precisam entrar na fila.',
      value: stats?.devolucoes_hoje || 0,
      href: '/contratos',
      slug: 'contratos',
      icon: Car,
      tone: 'rose',
      pulse: (stats?.devolucoes_hoje || 0) > 0,
      progress: Math.min((stats?.devolucoes_hoje || 0) * 30, 100),
    },
    {
      title: 'Frota em manutencao',
      description: 'Carros parados e ordens abertas para acompanhar.',
      value: stats?.veiculos_manutencao || 0,
      extra: `${stats?.manutencoes_abertas || 0} ordem(ns)`,
      href: '/manutencoes',
      slug: 'manutencoes',
      icon: Wrench,
      tone: 'slate',
      pulse: (stats?.veiculos_manutencao || 0) > 0,
      progress: Math.min((stats?.veiculos_manutencao || 0) * 22, 100),
    },
  ].filter((item) => canAccess(item.slug))

  const heroBadges = [
    {
      label: 'Ocupacao',
      value: stats ? `${formatPercent(stats.taxa_ocupacao)}%` : '-',
      tone: 'blue',
    },
    {
      label: 'Alertas criticos',
      value: isLoading ? '-' : String(criticalAlerts),
      tone: criticalAlerts > 0 ? 'red' : 'emerald',
    },
    {
      label: 'Agenda de hoje',
      value: isLoading ? '-' : String(agendaHoje.length),
      tone: 'amber',
    },
  ]

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
        return 'border-l-red-500 bg-red-50/70'
      case 'atencao':
        return 'border-l-amber-500 bg-amber-50/70'
      case 'info':
        return 'border-l-blue-500 bg-blue-50/70'
      default:
        return 'border-l-slate-400 bg-slate-50'
    }
  }

  const getAgendaCardClass = (urgencia: string) => {
    switch (urgencia) {
      case 'critica':
        return 'border-red-200 bg-red-50/80'
      case 'atencao':
        return 'border-amber-200 bg-amber-50/80'
      case 'info':
        return 'border-blue-200 bg-blue-50/80'
      default:
        return 'border-slate-200 bg-slate-50'
    }
  }

  const KPIBaseCard = ({
    icon: Icon,
    label,
    value,
    color,
    trend,
    formatter = formatInteger,
  }: {
    icon: React.ElementType
    label: string
    value: number
    color: 'blue' | 'green' | 'orange' | 'emerald'
    trend?: number
    formatter?: (value: number) => string
  }) => {
    const colorClasses = {
      blue: 'bg-blue-100 text-blue-600',
      green: 'bg-emerald-100 text-emerald-600',
      orange: 'bg-orange-100 text-orange-600',
      emerald: 'bg-emerald-100 text-emerald-600',
    }

    return (
      <div className="kpi-card group dashboard-lift">
        <div className={cn('kpi-icon shadow-sm', colorClasses[color])}>
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
            <CountUpValue value={value} formatter={formatter} className="kpi-value" />
          )}
          {trend !== undefined && !isLoading && (
            <div className="flex items-center gap-1 mt-2 text-xs">
              {trend > 0 ? (
                <>
                  <TrendingUp size={14} className="text-emerald-600" />
                  <span className="text-emerald-600 font-medium">+{formatPercent(trend)}%</span>
                </>
              ) : trend < 0 ? (
                <>
                  <TrendingDown size={14} className="text-red-600" />
                  <span className="text-red-600 font-medium">{formatPercent(trend)}%</span>
                </>
              ) : (
                <span className="text-slate-500 font-medium">Sem variacao relevante</span>
              )}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-8 pb-8">
        <section className="dashboard-hero animate-fade-in-up">
          <div className="dashboard-hero-glow" />
          <div className="relative grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.62fr)_420px]">
            <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="dashboard-hero-pill">
                  <Sparkles size={14} />
                  Radar da operacao
                </span>
                <span className="dashboard-hero-pill dashboard-hero-pill-muted">
                  Atualizado com contratos, reservas, manutencoes e alertas
                </span>
              </div>

              <div>
                <h1 className="page-title text-slate-950">Dashboard</h1>
                <p className="mt-2 max-w-2xl text-sm text-slate-600">
                  Bem-vindo, {user?.nome || 'Usuario'}. Este painel agora mostra a fila operacional da locadora e ajuda a priorizar retirada, devolucao, reservas e manutencao sem sair da tela inicial.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
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
                    <span className="text-xs uppercase tracking-[0.2em] text-current/70">{badge.label}</span>
                    <strong className="text-sm font-semibold">{badge.value}</strong>
                  </div>
                ))}
              </div>

              {actionCards.length > 0 && (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {actionCards.map((item) => {
                    const Icon = item.icon
                    return (
                      <Link
                        key={item.title}
                        to={item.href}
                        className={cn(
                          'dashboard-action-card',
                          item.tone === 'amber' && 'dashboard-action-card-amber',
                          item.tone === 'blue' && 'dashboard-action-card-blue',
                          item.tone === 'rose' && 'dashboard-action-card-rose',
                          item.tone === 'slate' && 'dashboard-action-card-slate',
                          item.pulse && 'dashboard-action-card-pulse',
                        )}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <div className="dashboard-action-icon">
                                <Icon size={18} />
                              </div>
                              <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                            </div>
                            <p className="text-xs text-slate-500">{item.description}</p>
                          </div>
                          <ChevronRight size={18} className="text-slate-400" />
                        </div>

                        <div className="mt-5 flex items-end justify-between gap-3">
                          <div>
                            <CountUpValue value={item.value} className="text-3xl font-display font-bold text-slate-950" />
                            {item.extra && <p className="mt-1 text-xs font-medium text-slate-500">{item.extra}</p>}
                          </div>
                          <span className="badge badge-neutral bg-white/80 text-slate-700">
                            abrir fila
                            <ArrowRight size={12} className="ml-1" />
                          </span>
                        </div>

                        <div className="metric-progress-track mt-4">
                          <div
                            className="metric-progress-fill"
                            style={{ width: `${item.progress}%` }}
                          />
                        </div>
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>

            <div className="dashboard-score-card">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-primary-dark/75">Saude da operacao</p>
                  <h2 className="mt-1 text-xl font-display font-bold text-slate-950">{scoreLabel}</h2>
                </div>
                <ShieldCheck size={22} className="text-primary" />
              </div>

              <div className="mt-6 flex items-end justify-between gap-4">
                <div>
                  <CountUpValue value={operationScore} className="text-5xl font-display font-bold text-slate-950" />
                  <p className="mt-2 text-sm text-slate-600">Score operacional calculado sobre alertas, atrasos, manutencoes e ocupacao.</p>
                </div>
                <div className={cn('dashboard-score-badge', `dashboard-score-badge-${scoreTone}`)}>
                  {operationScore >= 85 ? 'Estavel' : operationScore >= 68 ? 'Atencao' : 'Critico'}
                </div>
              </div>

              <div className="metric-progress-track mt-6 bg-primary-100">
                <div
                  className={cn(
                    'metric-progress-fill',
                    scoreTone === 'emerald' && 'bg-emerald-400',
                    scoreTone === 'amber' && 'bg-amber-400',
                    scoreTone === 'red' && 'bg-red-400',
                  )}
                  style={{ width: `${operationScore}%` }}
                />
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <div className="dashboard-mini-card flex flex-col gap-2">
                  <span className="text-xs uppercase tracking-wide text-slate-500">Disponiveis</span>
                  <CountUpValue value={stats?.veiculos_disponiveis || 0} className="mt-2 text-2xl font-display font-bold text-slate-950" />
                </div>
                <div className="dashboard-mini-card flex flex-col gap-2">
                  <span className="text-xs uppercase tracking-wide text-slate-500">Reservas confirmadas</span>
                  <CountUpValue value={stats?.reservas_confirmadas || 0} className="mt-2 text-2xl font-display font-bold text-slate-950" />
                </div>
                <div className="dashboard-mini-card flex flex-col gap-2">
                  <span className="text-xs uppercase tracking-wide text-slate-500">Atrasos</span>
                  <CountUpValue value={stats?.contratos_atrasados.length || 0} className="mt-2 text-2xl font-display font-bold text-slate-950" />
                </div>
                <div className="dashboard-mini-card col-span-2 flex min-w-0 items-end justify-between gap-3">
                  <div className="min-w-0">
                    <span className="text-xs uppercase tracking-wide text-slate-500">Ticket medio</span>
                    <p className="mt-2 text-xs text-slate-500">Media por contrato encerrado</p>
                  </div>
                  <CountUpValue
                    value={stats?.ticket_medio || 0}
                    formatter={formatCurrency}
                    className="block max-w-full text-right text-[clamp(1.05rem,1.35vw,1.5rem)] font-display font-bold leading-tight tracking-[-0.02em] text-slate-950"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 stagger-children">
          <KPIBaseCard
            icon={Car}
            label="Total de Veiculos"
            value={stats?.total_veiculos || 0}
            color="blue"
          />
          <KPIBaseCard
            icon={Zap}
            label="Veiculos Alugados"
            value={stats?.veiculos_alugados || 0}
            color="green"
          />
          <KPIBaseCard
            icon={FileText}
            label="Contratos Ativos"
            value={stats?.contratos_ativos || 0}
            color="orange"
          />
          <KPIBaseCard
            icon={DollarSign}
            label="Receita Mes"
            value={stats?.receita_mensal || 0}
            color="emerald"
            trend={stats?.variacao_receita_mensal}
            formatter={formatCurrency}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 animate-fade-in-up" style={{ animationDelay: '70ms' }}>
          <div className="card bg-slate-50 border border-slate-200 dashboard-lift">
            <p className="text-xs uppercase tracking-wide text-slate-500">Veiculos Disponiveis</p>
            {isLoading ? (
              <div className="h-8 w-20 bg-slate-200 rounded animate-pulse mt-2" />
            ) : (
              <CountUpValue value={stats?.veiculos_disponiveis || 0} className="mt-2 text-2xl font-bold text-slate-900" />
            )}
          </div>
          <div className="card bg-slate-50 border border-slate-200 dashboard-lift">
            <p className="text-xs uppercase tracking-wide text-slate-500">Taxa de Ocupacao</p>
            {isLoading ? (
              <div className="h-8 w-24 bg-slate-200 rounded animate-pulse mt-2" />
            ) : (
              <>
                <CountUpValue value={stats?.taxa_ocupacao || 0} formatter={(value) => `${formatPercent(value)}%`} className="mt-2 text-2xl font-bold text-slate-900" />
                <div className="metric-progress-track mt-3">
                  <div className="metric-progress-fill bg-blue-500" style={{ width: `${stats?.taxa_ocupacao || 0}%` }} />
                </div>
              </>
            )}
          </div>
          <div className="card bg-slate-50 border border-slate-200 dashboard-lift">
            <p className="text-xs uppercase tracking-wide text-slate-500">Veiculos em Manutencao</p>
            {isLoading ? (
              <div className="h-8 w-20 bg-slate-200 rounded animate-pulse mt-2" />
            ) : (
              <>
                <CountUpValue value={stats?.veiculos_manutencao || 0} className="mt-2 text-2xl font-bold text-slate-900" />
                <p className="mt-2 text-xs text-slate-500">{stats?.manutencoes_abertas || 0} ordem(ns) aberta(s)</p>
              </>
            )}
          </div>
          <div className="card bg-slate-50 border border-slate-200 dashboard-lift">
            <p className="text-xs uppercase tracking-wide text-slate-500">Clientes Ativos</p>
            {isLoading ? (
              <div className="h-8 w-20 bg-slate-200 rounded animate-pulse mt-2" />
            ) : (
              <CountUpValue value={stats?.total_clientes || 0} className="mt-2 text-2xl font-bold text-slate-900" />
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] animate-fade-in-up" style={{ animationDelay: '120ms' }}>
          <div className="card">
            <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                  <Calendar size={20} className="text-blue-600" />
                  Agenda da Operacao
                </h2>
                <p className="text-sm text-slate-500 mt-1">Retiradas, devolucoes, reservas e manutencoes previstas para hoje.</p>
              </div>
              <span className="badge badge-info">{agendaHoje.length} item(ns)</span>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, index) => (
                  <div key={index} className="h-20 bg-slate-100 rounded-2xl animate-pulse" />
                ))}
              </div>
            ) : agendaHoje.length > 0 ? (
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                {agendaHoje.map((item) => (
                  <Link
                    key={item.id}
                    to={item.rota}
                    className={cn('dashboard-agenda-card dashboard-lift', getAgendaCardClass(item.urgencia))}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={cn('badge text-[11px]', getAlertBadgeClass(item.urgencia))}>{item.tipo}</span>
                          <span className="text-xs font-medium text-slate-500">{formatAgendaTime(item.horario)}</span>
                        </div>
                        <p className="mt-3 font-semibold text-slate-900">{item.titulo}</p>
                        <p className="mt-1 text-sm text-slate-600 line-clamp-2">{item.descricao}</p>
                      </div>
                      <ChevronRight size={18} className="text-slate-400 mt-1 flex-shrink-0" />
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="empty-state py-10">
                <div className="empty-state-icon">
                  <CheckCircle2 size={24} className="text-emerald-600" />
                </div>
                <p className="text-slate-500 font-medium text-sm">Sem eventos criticos para hoje</p>
              </div>
            )}
          </div>

          <div className="card">
            <div className="mb-5">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <AlertCircle size={20} className="text-orange-600" />
                Central de Alertas
              </h2>
              <p className="text-sm text-slate-500 mt-1">Use os filtros para focar no que precisa de acao imediata.</p>
            </div>

            <div className="flex gap-2 mb-4 pb-4 border-b border-slate-200 flex-wrap">
              {(['critica', 'atencao', 'info'] as const).map((urgency) => {
                const labels = {
                  critica: 'Critica',
                  atencao: 'Atencao',
                  info: 'Info',
                }
                const isActive = alertFilter === urgency
                return (
                  <button
                    key={urgency}
                    onClick={() => startTransition(() => setAlertFilter(urgency))}
                    className={`filter-tab ${isActive ? 'filter-tab-active' : 'filter-tab-inactive'}`}
                  >
                    {labels[urgency]}
                    <span className="ml-2 rounded-full bg-white/70 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                      {alertCounts[urgency]}
                    </span>
                  </button>
                )
              })}
            </div>

            <div key={deferredAlertFilter} className="space-y-3 max-h-[29rem] overflow-y-auto pr-1 alert-stack">
              {isLoading ? (
                <>
                  <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                  <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                  <div className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                </>
              ) : filteredAlerts.length > 0 ? (
                filteredAlerts.map((alert) => {
                  const AlertIcon = getAlertIcon(alert.urgencia)
                  const badgeClass = getAlertBadgeClass(alert.urgencia)
                  const borderClass = getAlertBorderClass(alert.urgencia)

                  return (
                    <div
                      key={alert.id}
                      className={cn(
                        'p-4 rounded-lg border-l-4 transition-all duration-200 hover:shadow-sm',
                        borderClass,
                        alert.urgencia === 'critica' && 'alert-critical',
                      )}
                    >
                      <div className="flex items-start gap-3">
                        <div className={cn('status-beacon', alert.urgencia === 'critica' && 'status-beacon-critical')} />
                        <AlertIcon size={16} className="mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-semibold text-sm text-slate-900">{alert.titulo}</p>
                            <span className={`badge text-xs ${badgeClass}`}>
                              {alert.urgencia === 'critica'
                                ? 'Critica'
                                : alert.urgencia === 'atencao'
                                  ? 'Atencao'
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
                  <p className="text-slate-500 font-medium text-sm">Sem alertas nesse filtro</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-up" style={{ animationDelay: '200ms' }}>
          <div className="lg:col-span-2 card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900">Receita vs Despesas</h2>
              <p className="text-sm text-slate-500 mt-1">Comparacao mensal de receitas e despesas para acompanhar caixa e margem.</p>
            </div>

            {isLoading ? (
              <div className="h-80 bg-slate-100 rounded-xl animate-pulse" />
            ) : stats?.receita_vs_despesas && stats.receita_vs_despesas.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart
                  data={stats.receita_vs_despesas}
                  margin={{ top: 20, right: 30, left: 0, bottom: 40 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis dataKey="mes" stroke="#94a3b8" style={{ fontSize: '12px' }} />
                  <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #dbeafe',
                      borderRadius: '12px',
                      color: '#0f172a',
                      boxShadow: '0 18px 44px rgba(15, 23, 42, 0.12)',
                    }}
                    formatter={(value: number) => formatCurrency(Number(value || 0))}
                    cursor={{ fill: 'rgba(37, 99, 235, 0.08)' }}
                  />
                  <Legend
                    wrapperStyle={{ paddingTop: '16px' }}
                    iconType="circle"
                    formatter={(value) => (
                      <span style={{ color: '#64748b', fontSize: '13px', fontWeight: '500' }}>
                        {value === 'receita' ? 'Receita' : 'Despesa'}
                      </span>
                    )}
                  />
                  <Bar dataKey="receita" fill="#2563eb" radius={[10, 10, 0, 0]} isAnimationActive />
                  <Bar dataKey="despesa" fill="#f97316" radius={[10, 10, 0, 0]} isAnimationActive />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state min-h-80">
                <div className="empty-state-icon">
                  <DollarSign size={32} className="text-slate-400" />
                </div>
                <p className="text-slate-500 font-medium">Sem dados disponiveis</p>
              </div>
            )}
          </div>

          <div className="card overflow-hidden relative border-primary-200/80 bg-[linear-gradient(180deg,#edf7ff_0%,#ffffff_42%,#ffffff_100%)] shadow-[0_18px_36px_rgba(74,168,255,0.08)]">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(74,168,255,0.12),_transparent_48%)]" />
            <div className="relative">
              <div className="mb-6">
                <h2 className="text-lg font-display font-bold flex items-center gap-2">
                  <Sparkles size={20} className="text-primary" />
                  Leitura Rapida
                </h2>
                <p className="mt-1 text-sm text-slate-600">Resumo para decidir sua proxima acao em poucos segundos.</p>
              </div>

              <div className="space-y-4">
                <div className="dashboard-insight-card">
                  <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Receita do mes</span>
                  <CountUpValue value={stats?.receita_mensal || 0} formatter={formatCurrency} className="mt-2 block text-2xl font-display font-bold text-slate-950" />
                  <p className="mt-2 text-xs text-slate-600">Variacao frente ao mes anterior: {stats ? `${formatPercent(stats.variacao_receita_mensal)}%` : '-'}</p>
                </div>
                <div className="dashboard-insight-card">
                  <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Fila do dia</span>
                  <p className="mt-2 text-2xl font-display font-bold text-slate-950">{(stats?.retiradas_hoje || 0) + (stats?.devolucoes_hoje || 0)}</p>
                  <p className="mt-2 text-xs text-slate-600">Somando retiradas previstas, devolucoes e reservas que precisam de decisao.</p>
                </div>
                <div className="dashboard-insight-card">
                  <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Atencao imediata</span>
                  <p className="mt-2 text-2xl font-display font-bold text-slate-950">{criticalAlerts}</p>
                  <p className="mt-2 text-xs text-slate-600">Alertas criticos ainda nao resolvidos no sistema.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: '260ms' }}>
          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <Users size={20} className="text-blue-600" />
                Top 5 Clientes
              </h2>
              <p className="text-sm text-slate-500 mt-1">Clientes com maior volume financeiro em contratos.</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, index) => (
                  <div key={index} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.top_clientes && stats.top_clientes.length > 0 ? (
              <div className="space-y-3">
                {stats.top_clientes.map((cliente, index) => {
                  const initials = cliente.nome
                    .split(' ')
                    .map((part) => part[0])
                    .join('')
                    .toUpperCase()
                    .slice(0, 2)

                  return (
                    <div
                      key={`${cliente.nome}-${index}`}
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

          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <Car size={20} className="text-orange-600" />
                Top 5 Veiculos
              </h2>
              <p className="text-sm text-slate-500 mt-1">Veiculos mais usados para ajudar a enxergar giro de frota.</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, index) => (
                  <div key={index} className="h-12 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.top_veiculos && stats.top_veiculos.length > 0 ? (
              <div className="space-y-3">
                {stats.top_veiculos.map((veiculo, index) => (
                  <div
                    key={`${veiculo.placa}-${index}`}
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
                    <div className="text-right flex-shrink-0 ml-3">
                      <div className="badge badge-info">{veiculo.alugadas}x</div>
                      {veiculo.receita !== undefined && (
                        <p className="mt-2 text-xs font-medium text-slate-500">{formatCurrency(veiculo.receita)}</p>
                      )}
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up" style={{ animationDelay: '320ms' }}>
          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <AlertTriangle size={20} className="text-red-600" />
                Contratos em Atraso
              </h2>
              <p className="text-sm text-slate-500 mt-1">Casos que pedem contato ou fechamento imediato.</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, index) => (
                  <div key={index} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.contratos_atrasados && stats.contratos_atrasados.length > 0 ? (
              <div className="space-y-3">
                {stats.contratos_atrasados.map((contrato) => (
                  <div
                    key={contrato.id}
                    className="p-4 rounded-lg border-l-4 border-l-red-500 bg-red-50/60 hover:shadow-sm transition-all duration-200"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-900 text-sm">{contrato.numero}</p>
                        <p className="text-xs text-slate-600 mt-1">
                          Cliente: {contrato.cliente?.nome || 'Nao informado'}
                        </p>
                        <p className="text-xs text-slate-600 mt-1">
                          Vencimento: {formatDateTime(contrato.data_fim)}
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

          <div className="card">
            <div className="mb-6">
              <h2 className="text-lg font-display font-bold text-slate-900 flex items-center gap-2">
                <Calendar size={20} className="text-amber-600" />
                Proximos Vencimentos
              </h2>
              <p className="text-sm text-slate-500 mt-1">Contratos, seguro, IPVA e manutencoes nos proximos 30 dias.</p>
            </div>

            {isLoading ? (
              <div className="space-y-3">
                {[...Array(3)].map((_, index) => (
                  <div key={index} className="h-16 bg-slate-100 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : stats?.proximos_vencimentos && stats.proximos_vencimentos.length > 0 ? (
              <div className="space-y-3">
                {stats.proximos_vencimentos.map((item, index) => (
                  <div
                    key={item.id}
                    className="p-4 rounded-lg border-l-4 border-l-amber-500 bg-amber-50/50 hover:shadow-sm transition-all duration-200"
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0 text-amber-600 font-semibold text-sm">
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-900 text-sm line-clamp-1">{item.titulo}</p>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="text-xs text-slate-500">{item.tipo}</span>
                          <span className="text-xs text-slate-400">•</span>
                          <span className="text-xs text-slate-500">{formatDate(item.data_vencimento)}</span>
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
