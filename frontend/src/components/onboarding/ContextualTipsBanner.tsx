import React, { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  CalendarClock,
  CarFront,
  DollarSign,
  FileText,
  LifeBuoy,
  Settings2,
  ShieldAlert,
  Sparkles,
  Users,
  Wrench,
  X,
} from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'

interface ContextualTipsBannerProps {
  onOpenGuide: () => void
}

interface TipAction {
  label: string
  href?: string
  variant?: 'primary' | 'secondary'
  openGuide?: boolean
}

interface TipDefinition {
  id: string
  match: (pathname: string) => boolean
  eyebrow: string
  title: string
  description: string
  icon: React.ElementType
  tone: 'blue' | 'emerald' | 'amber' | 'slate'
  bullets: string[]
  actions: TipAction[]
}

const tipDefinitions: TipDefinition[] = [
  {
    id: 'dashboard',
    match: (pathname) => pathname.startsWith('/dashboard'),
    eyebrow: 'Comece por aqui',
    title: 'O Dashboard mostra o que precisa da sua atencao hoje',
    description: 'Antes de cadastrar ou editar qualquer coisa, confira retiradas, devolucoes, alertas e manutencoes do dia.',
    icon: Sparkles,
    tone: 'blue',
    bullets: [
      'Veja os cards de fila rapida para entender onde agir primeiro.',
      'Abra a agenda do dia para acompanhar entregas, reservas e devolucoes.',
      'Use a central de alertas para resolver o que esta vencendo ou atrasado.',
    ],
    actions: [
      { label: 'Abrir contratos', href: '/contratos', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'clientes',
    match: (pathname) => pathname.startsWith('/clientes'),
    eyebrow: 'Cadastro base',
    title: 'Clientes sao usados em reservas, contratos e financeiro',
    description: 'Aqui voce registra quem vai alugar o carro e garante que os dados fiquem prontos para o contrato.',
    icon: Users,
    tone: 'emerald',
    bullets: [
      'Cadastre nome, telefone e documento corretamente para evitar retrabalho.',
      'Se o contrato for corporativo, relacione o cliente com a empresa antes.',
      'Sempre confira se o cliente esta ativo antes de abrir a locacao.',
    ],
    actions: [
      { label: 'Abrir reservas', href: '/reservas', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'empresas',
    match: (pathname) => pathname.startsWith('/empresas'),
    eyebrow: 'Cadastro corporativo',
    title: 'Empresas organizam locacoes por cliente corporativo',
    description: 'Use esta area para manter os dados da empresa responsavel e dar contexto aos contratos PJ.',
    icon: Users,
    tone: 'emerald',
    bullets: [
      'Cadastre razao social, contato e CNPJ corretamente.',
      'Relacione clientes e motoristas com a empresa quando for locacao corporativa.',
      'Antes de excluir uma empresa, confira se ainda existem clientes vinculados.',
    ],
    actions: [
      { label: 'Abrir clientes', href: '/clientes', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'veiculos',
    match: (pathname) => pathname.startsWith('/veiculos'),
    eyebrow: 'Controle da frota',
    title: 'Mantenha KM, status e documentacao da frota sempre atualizados',
    description: 'O veiculo precisa estar com status correto para aparecer de forma confiavel em reserva, contrato e manutencao.',
    icon: CarFront,
    tone: 'amber',
    bullets: [
      'Revise o KM atual antes de liberar uma nova locacao.',
      'Nao deixe carro indisponivel marcado como disponivel.',
      'Use manutencao, seguro e IPVA para manter a operacao protegida.',
    ],
    actions: [
      { label: 'Abrir manutencoes', href: '/manutencoes', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'reservas',
    match: (pathname) => pathname.startsWith('/reservas'),
    eyebrow: 'Antes da retirada',
    title: 'Reserva serve para organizar locacoes futuras',
    description: 'Quando o cliente ainda nao vai sair com o carro agora, comece por aqui e converta para contrato na retirada.',
    icon: CalendarClock,
    tone: 'blue',
    bullets: [
      'Use pendente para reserva nova e confirme quando estiver validada.',
      'Converta em contrato no momento da retirada para travar o veiculo.',
      'Evite deixar reservas antigas sem decisao para nao poluir a agenda.',
    ],
    actions: [
      { label: 'Abrir contratos', href: '/contratos', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'contratos',
    match: (pathname) => pathname.startsWith('/contratos'),
    eyebrow: 'Locacao em andamento',
    title: 'Contrato e o coracao da locacao',
    description: 'Aqui nasce a retirada e aqui tambem acontece o encerramento com KM, checklist, taxas e pagamento.',
    icon: FileText,
    tone: 'blue',
    bullets: [
      'Confirme cliente, veiculo, diaria e KM atual antes de salvar.',
      'No encerramento, revise combustivel, checklist e avarias com calma.',
      'Use os valores extras apenas quando houver ocorrencia real na devolucao.',
    ],
    actions: [
      { label: 'Abrir financeiro', href: '/financeiro', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'seguros',
    match: (pathname) => pathname.startsWith('/seguros'),
    eyebrow: 'Protecao da frota',
    title: 'Seguros evitam surpresa com cobertura vencida',
    description: 'Acompanhe apolices, parcelas e vencimentos para nao deixar veiculo exposto.',
    icon: ShieldAlert,
    tone: 'amber',
    bullets: [
      'Cadastre seguradora, apolice e datas de vigencia.',
      'Marque o pagamento das parcelas para refletir o status correto.',
      'Use o dashboard e proximos vencimentos para agir antes do atraso.',
    ],
    actions: [
      { label: 'Abrir IPVA', href: '/ipva', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'ipva',
    match: (pathname) => pathname.startsWith('/ipva'),
    eyebrow: 'Regularizacao',
    title: 'IPVA ajuda a manter a frota em dia para rodar sem bloqueio',
    description: 'Registre parcelas, vencimentos e pagamentos para nao perder controle fiscal dos veiculos.',
    icon: ShieldAlert,
    tone: 'amber',
    bullets: [
      'Confirme o ano do tributo e o vencimento correto.',
      'Ao pagar, atualize a parcela para limpar o alerta no sistema.',
      'Junte IPVA, seguro e multa para ter visao completa da documentacao do carro.',
    ],
    actions: [
      { label: 'Abrir multas', href: '/multas', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'multas',
    match: (pathname) => pathname.startsWith('/multas'),
    eyebrow: 'Risco operacional',
    title: 'Multas precisam de controle rapido para nao virar bola de neve',
    description: 'Registre a infracao, acompanhe vencimento e defina pagamento para reduzir risco financeiro e documental.',
    icon: ShieldAlert,
    tone: 'amber',
    bullets: [
      'Cadastre descricao e vencimento assim que a notificacao chegar.',
      'Priorize as vencidas e proximas do prazo de pagamento.',
      'Mantenha o veiculo vinculado corretamente para saber onde agir.',
    ],
    actions: [
      { label: 'Abrir relatorios', href: '/relatorios', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'financeiro',
    match: (pathname) => pathname.startsWith('/financeiro'),
    eyebrow: 'Fechamento',
    title: 'O financeiro confirma o que entrou, saiu e ficou pendente',
    description: 'Use esta tela para acompanhar recebimentos de contratos, despesas e pendencias de caixa.',
    icon: DollarSign,
    tone: 'emerald',
    bullets: [
      'Conferir status de pagamento evita contrato fechado sem recebimento.',
      'Separe receitas e despesas com categorias claras para facilitar relatorio.',
      'Use o dashboard e os relatorios para comparar receita e gasto do mes.',
    ],
    actions: [
      { label: 'Abrir relatorios', href: '/relatorios', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'despesas-loja',
    match: (pathname) => pathname.startsWith('/despesas-loja'),
    eyebrow: 'Custos da operacao',
    title: 'Despesas da loja mostram quanto custa manter a locadora rodando',
    description: 'Use este modulo para separar gastos internos das despesas ligadas diretamente a contratos.',
    icon: DollarSign,
    tone: 'slate',
    bullets: [
      'Lance alugueis, internet, agua, luz e outros custos administrativos aqui.',
      'Mantenha categorias consistentes para os relatorios fazerem sentido.',
      'Nao misture custo fixo da loja com recebimento de contrato.',
    ],
    actions: [
      { label: 'Abrir financeiro', href: '/financeiro', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'manutencoes',
    match: (pathname) => pathname.startsWith('/manutencoes'),
    eyebrow: 'Saude da frota',
    title: 'Manutencao ajuda a prevenir carro parado e problema com cliente',
    description: 'Planeje revisoes por data ou KM e conclua as ordens para liberar a frota com seguranca.',
    icon: Wrench,
    tone: 'slate',
    bullets: [
      'Abra ordem preventiva antes do problema virar corretiva.',
      'Ao concluir a manutencao, confirme custo, oficina e KM realizado.',
      'Se o carro ainda nao puder voltar, mantenha o bloqueio operacional.',
    ],
    actions: [
      { label: 'Abrir veiculos', href: '/veiculos', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'relatorios',
    match: (pathname) => pathname.startsWith('/relatorios'),
    eyebrow: 'Visao de gestao',
    title: 'Relatorios ajudam a enxergar resultado e gargalos da locadora',
    description: 'Use esta area para acompanhar desempenho financeiro, frota, contratos e operacao por periodo.',
    icon: Sparkles,
    tone: 'blue',
    bullets: [
      'Compare receita e despesa antes de tomar decisao comercial.',
      'Olhe veiculos e clientes com mais giro para entender sua operacao.',
      'Use filtros por periodo para nao tirar conclusao em cima de dado misturado.',
    ],
    actions: [
      { label: 'Abrir dashboard', href: '/dashboard', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'configuracoes',
    match: (pathname) => pathname.startsWith('/configuracoes'),
    eyebrow: 'Ajustes da operacao',
    title: 'Aqui ficam os parametros da locadora e a checagem de producao',
    description: 'Antes de operar com dados reais, revise empresa, usuario, sistema e o painel de backups e governanca.',
    icon: Settings2,
    tone: 'slate',
    bullets: [
      'Confira nome da empresa, e-mail e dados operacionais basicos.',
      'Troque senha fraca antes de usar o sistema em producao real.',
      'No painel de backups e governanca voce encontra checklist de producao, backup e seguranca.',
    ],
    actions: [
      { label: 'Abrir backups', href: '/backups', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
  {
    id: 'usuarios',
    match: (pathname) => pathname.startsWith('/usuarios'),
    eyebrow: 'Controle de acesso',
    title: 'Usuarios e permissoes definem quem pode fazer o que no sistema',
    description: 'Antes de liberar o uso para a equipe, revise perfis, paginas permitidas e senhas fortes.',
    icon: Settings2,
    tone: 'slate',
    bullets: [
      'Crie acessos separados para evitar senha compartilhada.',
      'De permissao apenas para os modulos que cada funcao precisa usar.',
      'Desative usuarios antigos quando alguem sair da operacao.',
    ],
    actions: [
      { label: 'Abrir backups', href: '/backups', variant: 'primary' },
      { label: 'Guia completo', openGuide: true, variant: 'secondary' },
    ],
  },
]

const toneStyles = {
  blue: {
    shell: 'from-primary-50 via-white to-cyan-50 border-primary-100',
    icon: 'bg-primary text-white shadow-[0_16px_34px_rgba(74,168,255,0.22)]',
    chip: 'bg-primary-50 text-primary-dark ring-primary-100',
  },
  emerald: {
    shell: 'from-emerald-50 via-white to-teal-50 border-emerald-100',
    icon: 'bg-emerald-600 text-white shadow-[0_16px_34px_rgba(5,150,105,0.22)]',
    chip: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  },
  amber: {
    shell: 'from-amber-50 via-white to-orange-50 border-amber-100',
    icon: 'bg-amber-500 text-white shadow-[0_16px_34px_rgba(245,158,11,0.22)]',
    chip: 'bg-amber-50 text-amber-700 ring-amber-100',
  },
  slate: {
    shell: 'from-slate-100 via-white to-primary-50 border-slate-200',
    icon: 'bg-primary text-white shadow-[0_16px_34px_rgba(74,168,255,0.18)]',
    chip: 'bg-slate-100 text-slate-700 ring-slate-200',
  },
}

const ContextualTipsBanner: React.FC<ContextualTipsBannerProps> = ({ onOpenGuide }) => {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [isTipDismissed, setIsTipDismissed] = useState(false)

  const currentTip = useMemo(
    () => {
      if (!location.pathname.startsWith('/dashboard')) {
        return undefined
      }
      return tipDefinitions.find((definition) => definition.id === 'dashboard')
    },
    [location.pathname],
  )

  const dismissKey = currentTip
    ? `mpcars2_context_tip_hidden_${user?.id || 'guest'}_${currentTip.id}`
    : ''

  useEffect(() => {
    if (!currentTip || typeof window === 'undefined') {
      setIsTipDismissed(false)
      return
    }

    setIsTipDismissed(window.sessionStorage.getItem(dismissKey) === '1')
  }, [currentTip, dismissKey])

  const handleDismiss = () => {
    if (typeof window !== 'undefined' && dismissKey) {
      window.sessionStorage.setItem(dismissKey, '1')
    }
    setIsTipDismissed(true)
  }

  const runAction = (action: TipAction) => {
    if (action.openGuide) {
      onOpenGuide()
      return
    }

    if (action.href) {
      navigate(action.href)
    }
  }

  if (!currentTip) {
    return null
  }

  return (
    <div className="mb-6 space-y-4">
      {currentTip && !isTipDismissed && (
        <section
          className={cn(
            'animate-fade-in-up overflow-hidden rounded-[30px] border bg-gradient-to-br shadow-[0_20px_54px_rgba(15,23,42,0.08)]',
            toneStyles[currentTip.tone].shell,
          )}
        >
          <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1.45fr)_320px] lg:p-6">
            <div className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'flex h-14 w-14 items-center justify-center rounded-[22px]',
                      toneStyles[currentTip.tone].icon,
                    )}
                  >
                    <currentTip.icon size={24} />
                  </div>
                  <div>
                    <div
                      className={cn(
                        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ring-1',
                        toneStyles[currentTip.tone].chip,
                      )}
                    >
                      <LifeBuoy size={13} />
                      {currentTip.eyebrow}
                    </div>
                    <h2 className="mt-3 text-xl font-display font-bold text-slate-950">{currentTip.title}</h2>
                    <p className="mt-2 max-w-3xl text-sm text-slate-600">{currentTip.description}</p>
                  </div>
                </div>

                <button onClick={handleDismiss} className="btn-icon" title="Fechar ajuda desta tela">
                  <X size={18} />
                </button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {currentTip.bullets.map((bullet, index) => (
                  <div
                    key={bullet}
                    className="rounded-[22px] border border-white/70 bg-white/85 p-4 shadow-sm animate-fade-in-up"
                    style={{ animationDelay: `${index * 70}ms` }}
                  >
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                      Dica {index + 1}
                    </p>
                    <p className="mt-2 text-sm text-slate-600">{bullet}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-white/70 bg-white/92 p-5 shadow-sm">
              <p className="text-sm font-semibold text-slate-900">Proximo passo sugerido</p>
              <p className="mt-2 text-sm text-slate-500">
                Se voce esta usando esta tela pela primeira vez, siga uma acao simples e depois volte para o fluxo completo quando precisar.
              </p>

              <div className="mt-5 space-y-3">
                {currentTip.actions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => runAction(action)}
                    className={cn(
                      'flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition-all duration-200',
                      action.variant === 'primary'
                        ? 'border-primary bg-primary text-white hover:bg-primary-dark'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-white',
                    )}
                  >
                    <span className="text-sm font-semibold">{action.label}</span>
                    <ArrowRight size={16} />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default ContextualTipsBanner
