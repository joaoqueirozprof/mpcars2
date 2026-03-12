import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronLeft, ChevronRight, LogOut, Search } from 'lucide-react'

import { getVisibleNavigationSections } from '@/config/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useSidebar } from '@/contexts/SidebarContext'
import { cn } from '@/lib/utils'

interface SidebarProps {
  onOpenCommandPalette: () => void
}

const sectionToneStyles = {
  blue: 'text-sky-700',
  emerald: 'text-emerald-700',
  amber: 'text-amber-700',
  slate: 'text-slate-600',
}

const Sidebar: React.FC<SidebarProps> = ({ onOpenCommandPalette }) => {
  const location = useLocation()
  const { logout, canAccess, isAdmin } = useAuth()
  const { isCollapsed, isMobileOpen, toggleCollapse, closeMobile } = useSidebar()

  const sections = getVisibleNavigationSections({ canAccess, isAdmin })

  const isActive = (href: string) =>
    location.pathname === href || (href !== '/dashboard' && location.pathname.startsWith(`${href}/`))

  const renderDesktop = () => (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 hidden flex-col overflow-hidden border-r border-primary-200/80 bg-sidebar text-slate-900 transition-all duration-300 ease-in-out md:flex',
        isCollapsed ? 'md:w-24' : 'md:w-[292px]'
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(74,168,255,0.18),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(74,168,255,0.08),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(245,250,255,0.98))]" />

      <div
        className={cn(
          'relative flex h-20 items-center border-b border-primary-200/80',
          isCollapsed ? 'justify-center px-3' : 'px-6'
        )}
      >
        {isCollapsed ? (
          <span className="text-2xl font-display font-bold text-primary-dark">M</span>
        ) : (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-primary-dark">MPCARS</p>
            <h1 className="mt-1 text-2xl font-display font-bold text-slate-900">Painel da Locadora</h1>
            <p className="text-xs text-slate-500">Fluxo simples para operar no dia a dia</p>
          </div>
        )}
      </div>

      <div className="relative flex-1 overflow-y-auto px-3 py-5">
        <button
          onClick={onOpenCommandPalette}
          className={cn(
            'flex w-full items-center rounded-2xl border border-primary-200 bg-white/92 text-left transition-all duration-200 shadow-[0_10px_22px_rgba(74,168,255,0.08)] hover:border-primary/40 hover:bg-white',
            isCollapsed ? 'justify-center px-3 py-3' : 'gap-3 px-4 py-3.5'
          )}
          title={isCollapsed ? 'Busca rapida' : undefined}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary-100 text-primary-dark">
            <Search size={18} />
          </div>
          {!isCollapsed && (
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900">Busca rapida</p>
              <p className="text-xs text-slate-500">Encontre paginas e atalhos sem abrir mais menus</p>
            </div>
          )}
        </button>

        <div className="mt-5 space-y-5">
          {sections.map((section) => (
            <div key={section.id}>
              {!isCollapsed && (
                <p className={cn('mb-2 px-3 text-[11px] font-semibold uppercase tracking-[0.22em]', sectionToneStyles[section.tone])}>
                  {section.label}
                </p>
              )}
              <div className="space-y-1.5">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const active = isActive(item.href)

                  return (
                    <Link
                      key={item.href}
                      to={item.href}
                      title={isCollapsed ? item.label : undefined}
                        className={cn(
                          'group relative flex rounded-2xl transition-all duration-200',
                          isCollapsed ? 'justify-center px-2 py-3' : 'items-center gap-3 px-3.5 py-3',
                          active
                          ? 'bg-primary text-white shadow-[0_16px_34px_rgba(74,168,255,0.24)]'
                          : 'text-slate-700 hover:bg-white/80 hover:text-slate-950'
                      )}
                    >
                      <div
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-2xl transition-colors',
                          active ? 'bg-white/20 text-white' : 'bg-primary-100 text-primary-dark group-hover:bg-primary-200'
                        )}
                      >
                        <Icon size={18} />
                      </div>
                      {!isCollapsed && (
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{item.label}</p>
                          <p className={cn('truncate text-xs', active ? 'text-white/80' : 'text-slate-500')}>
                            {item.description}
                          </p>
                        </div>
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="relative space-y-1 border-t border-primary-200/80 p-3">
        <button
          onClick={logout}
          title={isCollapsed ? 'Sair' : undefined}
          className={cn(
            'flex w-full items-center rounded-2xl text-slate-700 transition-colors hover:bg-white/80 hover:text-slate-950',
            isCollapsed ? 'justify-center px-2 py-3' : 'gap-3 px-3.5 py-3'
          )}
        >
          <LogOut size={18} />
          {!isCollapsed && <span className="text-sm font-medium">Sair</span>}
        </button>

        <button
          onClick={toggleCollapse}
          className={cn(
            'flex w-full items-center rounded-2xl text-slate-500 transition-colors hover:bg-white/80 hover:text-slate-900',
            isCollapsed ? 'justify-center px-2 py-3' : 'gap-3 px-3.5 py-3'
          )}
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!isCollapsed && <span className="text-sm font-medium">Recolher menu</span>}
        </button>
      </div>
    </aside>
  )

  const renderMobile = () => (
    <>
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/55 backdrop-blur-sm md:hidden"
          onClick={closeMobile}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-[86vw] max-w-[340px] flex-col overflow-hidden border-r border-primary-200/80 bg-sidebar text-slate-900 transition-transform duration-300 ease-in-out md:hidden',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(74,168,255,0.18),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(74,168,255,0.08),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(245,250,255,0.98))]" />

        <div className="relative border-b border-primary-200/80 px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-primary-dark">MPCARS</p>
          <h1 className="mt-1 text-2xl font-display font-bold text-slate-900">Painel da Locadora</h1>
          <p className="text-xs text-slate-500">Fluxo simples para o uso diario</p>
        </div>

        <div className="relative flex-1 overflow-y-auto px-4 py-4">
          <button
            onClick={() => {
              closeMobile()
              onOpenCommandPalette()
            }}
            className="flex w-full items-center gap-3 rounded-2xl border border-primary-200 bg-white/92 px-4 py-3.5 text-left shadow-[0_10px_22px_rgba(74,168,255,0.08)] transition-colors hover:border-primary/40 hover:bg-white"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary-100 text-primary-dark">
              <Search size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Busca rapida</p>
              <p className="text-xs text-slate-500">Encontre paginas sem navegar em excesso</p>
            </div>
          </button>

          <div className="mt-5 space-y-5">
            {sections.map((section) => (
              <div key={section.id}>
                <p className={cn('mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.22em]', sectionToneStyles[section.tone])}>
                  {section.label}
                </p>
                <div className="space-y-1.5">
                  {section.items.map((item) => {
                    const Icon = item.icon
                    const active = isActive(item.href)

                    return (
                      <Link
                        key={item.href}
                        to={item.href}
                        onClick={closeMobile}
                        className={cn(
                          'flex items-center gap-3 rounded-2xl px-3.5 py-3 transition-colors',
                          active
                            ? 'bg-primary text-white shadow-[0_12px_28px_rgba(74,168,255,0.24)]'
                            : 'text-slate-700 hover:bg-white/80 hover:text-slate-950'
                        )}
                      >
                        <div
                          className={cn(
                            'flex h-10 w-10 items-center justify-center rounded-2xl',
                            active ? 'bg-white/20 text-white' : 'bg-primary-100 text-primary-dark'
                          )}
                        >
                          <Icon size={18} />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{item.label}</p>
                          <p className={cn('truncate text-xs', active ? 'text-white/80' : 'text-slate-500')}>
                            {item.description}
                          </p>
                        </div>
                      </Link>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative border-t border-primary-200/80 p-4">
          <button
            onClick={() => {
              logout()
              closeMobile()
            }}
            className="flex w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-slate-700 transition-colors hover:bg-white/80 hover:text-slate-950"
          >
            <LogOut size={18} />
            <span className="text-sm font-medium">Sair</span>
          </button>
        </div>
      </aside>
    </>
  )

  return (
    <>
      {renderDesktop()}
      {renderMobile()}
    </>
  )
}

export default Sidebar
