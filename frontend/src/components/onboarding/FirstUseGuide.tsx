import React from 'react'
import { ArrowRight, BookOpenCheck, Car, DollarSign, FileText, Settings, ShieldCheck, Users, Wrench, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface FirstUseGuideProps {
  isOpen: boolean
  onClose: () => void
  onDismissPermanently: () => void
}

const steps = [
  {
    title: '1. Ajuste a locadora',
    description: 'Comece em Configuracoes para conferir nome da empresa, valor da diaria, tema e parametros principais.',
    href: '/configuracoes',
    icon: Settings,
    cta: 'Abrir configuracoes',
  },
  {
    title: '2. Cadastre a frota',
    description: 'Entre em Veiculos e registre placa, modelo, KM atual, foto e status do carro.',
    href: '/veiculos?quick=create',
    icon: Car,
    cta: 'Cadastrar veiculo',
  },
  {
    title: '3. Cadastre clientes e empresas',
    description: 'Registre quem vai alugar o carro. Se a locacao for corporativa, use Empresas tambem.',
    href: '/clientes?quick=create',
    icon: Users,
    cta: 'Cadastrar cliente',
  },
  {
    title: '4. Reserve ou abra o contrato',
    description: 'Se a retirada for futura, comece por Reservas. Se o cliente ja vai sair com o carro, abra o Contrato.',
    href: '/contratos?quick=create',
    icon: FileText,
    cta: 'Novo contrato',
  },
  {
    title: '5. Encerramento e financeiro',
    description: 'Na devolucao, encerre o contrato, confira checklist, taxas e confirme como ficou o pagamento.',
    href: '/financeiro',
    icon: DollarSign,
    cta: 'Abrir financeiro',
  },
  {
    title: '6. Manutencao e rotina',
    description: 'Use Manutencoes, Seguros, IPVA e Multas para manter a frota regular e segura.',
    href: '/manutencoes',
    icon: Wrench,
    cta: 'Ver manutencoes',
  },
]

const moduleCards = [
  { label: 'Dashboard', description: 'Mostra o que precisa ser feito hoje.', icon: ShieldCheck },
  { label: 'Contratos', description: 'Onde a locacao nasce e termina.', icon: FileText },
  { label: 'Financeiro', description: 'Controla o que entrou, saiu e ficou pendente.', icon: DollarSign },
  { label: 'Veiculos', description: 'Guarda toda a situacao atual da frota.', icon: Car },
]

const FirstUseGuide: React.FC<FirstUseGuideProps> = ({
  isOpen,
  onClose,
  onDismissPermanently,
}) => {
  const navigate = useNavigate()

  const openPath = (href: string) => {
    const [pathname, search = ''] = href.split('?')
    navigate({ pathname, search: search ? `?${search}` : '' })
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={(event) => event.target === event.currentTarget && onClose()}>
      <div className="modal-content max-w-6xl w-full" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">Primeiro uso</p>
            <h2 className="mt-1 text-2xl font-display font-bold text-slate-950">Guia rapido da locadora</h2>
            <p className="mt-1 text-sm text-slate-500">
              Um roteiro simples para quem nunca usou o sistema e precisa operar sem complicacao.
            </p>
          </div>
          <button onClick={onClose} className="btn-icon" title="Fechar guia">
            <X size={20} />
          </button>
        </div>

        <div className="modal-scroll-body space-y-6">
          <section className="rounded-[28px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,rgba(191,219,254,0.8),transparent_28%),linear-gradient(135deg,#eff6ff_0%,#ffffff_60%,#f8fafc_100%)] p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-blue-700 ring-1 ring-blue-100">
                  <BookOpenCheck size={13} />
                  Fluxo recomendado
                </div>
                <h3 className="mt-4 text-3xl font-display font-bold text-slate-950">
                  Pense no sistema como o dia a dia da locadora
                </h3>
                <p className="mt-3 text-sm text-slate-600">
                  Primeiro voce configura a empresa, depois cadastra frota e clientes, abre reservas ou contratos, encerra a locacao e acompanha financeiro e manutencao.
                </p>
              </div>

              <div className="grid min-w-[280px] gap-3 sm:grid-cols-2 lg:w-[360px]">
                {moduleCards.map((item) => {
                  const Icon = item.icon
                  return (
                    <div key={item.label} className="rounded-[22px] border border-white/70 bg-white/95 p-4 shadow-sm">
                      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-950 text-white">
                        <Icon size={18} />
                      </div>
                      <p className="mt-3 text-sm font-semibold text-slate-900">{item.label}</p>
                      <p className="mt-1 text-xs text-slate-500">{item.description}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            {steps.map((step) => {
              const Icon = step.icon
              return (
                <div key={step.title} className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-start gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                      <Icon size={22} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-lg font-display font-bold text-slate-900">{step.title}</h3>
                      <p className="mt-2 text-sm text-slate-500">{step.description}</p>
                      <button
                        onClick={() => openPath(step.href)}
                        className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary transition-colors hover:text-primary/80"
                      >
                        {step.cta}
                        <ArrowRight size={15} />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </section>

          <section className="rounded-[26px] border border-slate-200 bg-slate-50/80 p-5">
            <h3 className="text-lg font-display font-bold text-slate-900">Dicas para quem esta começando</h3>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Use sempre o Dashboard primeiro</p>
                <p className="mt-1 text-xs text-slate-500">Ele mostra reservas, retiradas, devolucoes, manutencoes e alertas do dia.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Reserva nao e contrato</p>
                <p className="mt-1 text-xs text-slate-500">Reserve antes quando a retirada for futura; converta para contrato no momento da locacao.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Fechamento exige conferencia</p>
                <p className="mt-1 text-xs text-slate-500">Ao encerrar contrato, confira KM, checklist, combustivel, avarias e pagamento.</p>
              </div>
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button onClick={onDismissPermanently} className="btn-secondary">
            Nao mostrar automaticamente
          </button>
          <button onClick={() => openPath('/dashboard')} className="btn-primary">
            Ir para o Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

export default FirstUseGuide
