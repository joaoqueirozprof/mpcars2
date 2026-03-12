import {
  AlertCircle,
  BarChart3,
  Building2,
  Calendar,
  Car,
  DollarSign,
  FileCheck,
  FileText,
  LayoutDashboard,
  LucideIcon,
  PlusCircle,
  Settings,
  ShieldAlert,
  Store,
  UserCog,
  Users,
  Wrench,
} from 'lucide-react'

export interface NavigationItem {
  id: string
  label: string
  href: string
  icon: LucideIcon
  description: string
  keywords: string[]
  slug?: string
  adminOnly?: boolean
}

export interface NavigationSection {
  id: string
  label: string
  tone: 'blue' | 'emerald' | 'amber' | 'slate'
  items: NavigationItem[]
}

export interface QuickAction {
  id: string
  label: string
  description: string
  href: string
  icon: LucideIcon
  keywords: string[]
  search?: string
  slug?: string
  adminOnly?: boolean
}

interface VisibilityOptions {
  canAccess: (page: string) => boolean
  isAdmin: boolean
}

export const navigationSections: NavigationSection[] = [
  {
    id: 'operacao',
    label: 'Operacao',
    tone: 'blue',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        href: '/dashboard',
        icon: LayoutDashboard,
        description: 'Visao geral da locadora, alertas e agenda operacional.',
        keywords: ['inicio', 'painel', 'alertas', 'agenda', 'indicadores'],
      },
      {
        id: 'contratos',
        label: 'Contratos',
        href: '/contratos',
        icon: FileText,
        slug: 'contratos',
        description: 'Locacoes ativas, encerramentos, recebimentos e historico.',
        keywords: ['locacao', 'fechamento', 'retirada', 'devolucao', 'aluguel'],
      },
      {
        id: 'reservas',
        label: 'Reservas',
        href: '/reservas',
        icon: Calendar,
        slug: 'reservas',
        description: 'Reservas pendentes, confirmacoes e conversao em contrato.',
        keywords: ['agenda', 'agendamento', 'confirmar', 'converter'],
      },
      {
        id: 'clientes',
        label: 'Clientes',
        href: '/clientes',
        icon: Users,
        slug: 'clientes',
        description: 'Cadastro e relacionamento com pessoas fisicas e juridicas.',
        keywords: ['cadastro', 'contato', 'cpf', 'cnpj'],
      },
      {
        id: 'empresas',
        label: 'Empresas',
        href: '/empresas',
        icon: Building2,
        slug: 'empresas',
        description: 'Empresas vinculadas, filiais e dados cadastrais.',
        keywords: ['filial', 'cnpj', 'responsavel', 'corporativo'],
      },
    ],
  },
  {
    id: 'frota',
    label: 'Frota',
    tone: 'emerald',
    items: [
      {
        id: 'veiculos',
        label: 'Veiculos',
        href: '/veiculos',
        icon: Car,
        slug: 'veiculos',
        description: 'Frota, fotos, status atual, disponibilidade e KM.',
        keywords: ['frota', 'placa', 'modelo', 'km', 'status'],
      },
      {
        id: 'manutencoes',
        label: 'Manutencoes',
        href: '/manutencoes',
        icon: Wrench,
        slug: 'manutencoes',
        description: 'Preventivas, corretivas, alertas por data e quilometragem.',
        keywords: ['revisao', 'oficina', 'preventiva', 'corretiva'],
      },
      {
        id: 'seguros',
        label: 'Seguros',
        href: '/seguros',
        icon: ShieldAlert,
        slug: 'seguros',
        description: 'Apolices, franquias, parcelas e vencimentos.',
        keywords: ['apolice', 'franquia', 'seguradora'],
      },
      {
        id: 'ipva',
        label: 'Licenciamento',
        href: '/ipva',
        icon: FileCheck,
        slug: 'ipva',
        description: 'IPVA, licenciamento e parcelas por veiculo.',
        keywords: ['ipva', 'licenciamento', 'taxa', 'vencimento'],
      },
      {
        id: 'multas',
        label: 'Multas',
        href: '/multas',
        icon: AlertCircle,
        slug: 'multas',
        description: 'Controle de infracoes, vencimentos e pagamento.',
        keywords: ['infracao', 'vencimento', 'pagamento', 'transito'],
      },
    ],
  },
  {
    id: 'financeiro',
    label: 'Financeiro',
    tone: 'amber',
    items: [
      {
        id: 'financeiro',
        label: 'Financeiro',
        href: '/financeiro',
        icon: DollarSign,
        slug: 'financeiro',
        description: 'Receitas, despesas, recebimentos e conciliacao dos contratos.',
        keywords: ['receita', 'despesa', 'pix', 'pagamento', 'caixa'],
      },
      {
        id: 'despesas-loja',
        label: 'Despesas Loja',
        href: '/despesas-loja',
        icon: Store,
        slug: 'despesas-loja',
        description: 'Custos fixos e operacionais fora dos contratos.',
        keywords: ['loja', 'aluguel', 'energia', 'custos'],
      },
      {
        id: 'relatorios',
        label: 'Relatorios',
        href: '/relatorios',
        icon: BarChart3,
        slug: 'relatorios',
        description: 'Analises da operacao, desempenho da frota e resultados.',
        keywords: ['analise', 'desempenho', 'graficos', 'exportar'],
      },
    ],
  },
  {
    id: 'administracao',
    label: 'Administracao',
    tone: 'slate',
    items: [
      {
        id: 'configuracoes',
        label: 'Configuracoes',
        href: '/configuracoes',
        icon: Settings,
        slug: 'configuracoes',
        description: 'Regras da locadora, valores padrao e preferencias.',
        keywords: ['preferencias', 'sistema', 'parametros', 'empresa'],
      },
      {
        id: 'usuarios',
        label: 'Usuarios',
        href: '/usuarios',
        icon: UserCog,
        slug: 'usuarios',
        adminOnly: true,
        description: 'Perfis, permissoes e acessos do time.',
        keywords: ['permissao', 'equipe', 'acesso', 'perfil'],
      },
    ],
  },
]

export const quickActions: QuickAction[] = [
  {
    id: 'quick-contrato',
    label: 'Novo contrato',
    description: 'Abrir o fluxo de locacao sem procurar o modulo.',
    href: '/contratos',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'contratos',
    keywords: ['criar contrato', 'locacao', 'retirada'],
  },
  {
    id: 'quick-reserva',
    label: 'Nova reserva',
    description: 'Agendar uma nova retirada rapidamente.',
    href: '/reservas',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'reservas',
    keywords: ['agendar', 'reserva', 'cliente'],
  },
  {
    id: 'quick-cliente',
    label: 'Novo cliente',
    description: 'Cadastrar cliente sem sair do contexto atual.',
    href: '/clientes',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'clientes',
    keywords: ['cadastro cliente', 'pessoa fisica', 'pessoa juridica'],
  },
  {
    id: 'quick-veiculo',
    label: 'Novo veiculo',
    description: 'Adicionar um carro novo na frota.',
    href: '/veiculos',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'veiculos',
    keywords: ['frota', 'placa', 'carro'],
  },
  {
    id: 'quick-manutencao',
    label: 'Nova manutencao',
    description: 'Abrir uma ordem de manutencao rapidamente.',
    href: '/manutencoes',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'manutencoes',
    keywords: ['revisao', 'oficina', 'preventiva'],
  },
  {
    id: 'quick-financeiro',
    label: 'Novo lancamento',
    description: 'Criar uma receita ou despesa manual no financeiro.',
    href: '/financeiro',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'financeiro',
    keywords: ['caixa', 'receita', 'despesa', 'lancamento'],
  },
  {
    id: 'quick-empresa',
    label: 'Nova empresa',
    description: 'Cadastrar uma nova empresa ou filial.',
    href: '/empresas',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'empresas',
    keywords: ['empresa', 'cnpj', 'filial'],
  },
  {
    id: 'quick-despesa-loja',
    label: 'Nova despesa da loja',
    description: 'Registrar um custo operacional geral.',
    href: '/despesas-loja',
    search: '?quick=create',
    icon: PlusCircle,
    slug: 'despesas-loja',
    keywords: ['despesa loja', 'custo', 'operacional'],
  },
]

const canSeeEntry = (
  entry: { adminOnly?: boolean; slug?: string },
  { canAccess, isAdmin }: VisibilityOptions
) => {
  if (entry.adminOnly) return isAdmin
  if (!entry.slug) return true
  return canAccess(entry.slug)
}

export const getVisibleNavigationSections = (options: VisibilityOptions) =>
  navigationSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => canSeeEntry(item, options)),
    }))
    .filter((section) => section.items.length > 0)

export const getVisibleQuickActions = (options: VisibilityOptions) =>
  quickActions.filter((item) => canSeeEntry(item, options))

export const flattenNavigationItems = () => navigationSections.flatMap((section) => section.items)

export const findNavigationItem = (pathname: string) =>
  flattenNavigationItems().find(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  ) || navigationSections[0].items[0]

export const inferAlertRoute = (tipo?: string) => {
  const value = (tipo || '').toLowerCase()

  if (value.includes('manut')) return '/manutencoes'
  if (value.includes('seguro')) return '/seguros'
  if (value.includes('ipva') || value.includes('licenciamento')) return '/ipva'
  if (value.includes('multa')) return '/multas'
  if (value.includes('reserva')) return '/reservas'
  if (value.includes('contrato')) return '/contratos'
  if (value.includes('financ')) return '/financeiro'
  if (value.includes('veiculo')) return '/veiculos'

  return '/dashboard'
}
