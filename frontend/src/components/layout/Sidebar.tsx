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
  blue: 'text-blue-300',
  emerald: 'text-emerald-300',
  amber: 'text-amber-300',
  slate: 'text-slate-300',
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
        'fixed inset-y-0 left-0 z-50 hidden flex-col overflow-hidden border-r border-sky-700/20 bg-sidebar text-white transition-all duration-300 ease-in-out md:flex',
        isCollapsed ? 'md:w-24' : 'md:w-[292px]'
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(186,230,253,0.32),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.16),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(12,74,110,0.18))]" />

      <div
        className={cn(
          'relative flex h-20 items-center border-b border-slate-800/80',
          isCollapsed ? 'justify-center px-3' : 'px-6'
        )}
      >
        {isCollapsed ? (
          <span className="text-2xl font-display font-bold">M</span>
        ) : (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-sky-100">MPCARS</p>
            <h1 className="mt-1 text-2xl font-display font-bold text-white">Painel da Locadora</h1>
            <p className="text-xs text-sky-100/75">Fluxo simples para operar no dia a dia</p>
          </div>
        )}
      </div>

      <div className="relative flex-1 overflow-y-auto px-3 py-5">
        <button
          onClick={onOpenCommandPalette}
          className={cn(
            'flex w-full items-center rounded-2xl border border-white/20 bg-white/12 text-left transition-all duration-200 hover:bg-white/18',
            isCollapsed ? 'justify-center px-3 py-3' : 'gap-3 px-4 py-3.5'
          )}
          title={isCollapsed ? 'Busca rapida' : undefined}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/20 text-white">
            <Search size={18} />
          </div>
          {!isCollapsed && (
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white">Busca rapida</p>
              <p className="text-xs text-sky-100/80">Encontre paginas e atalhos sem abrir mais menus</p>
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
                          ? 'bg-white text-slate-950 shadow-[0_16px_34px_rgba(15,23,42,0.18)]'
                          : 'text-sky-50/90 hover:bg-white/12 hover:text-white'
                      )}
                    >
                      <div
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-2xl transition-colors',
                          active ? 'bg-sky-500 text-white' : 'bg-white/12 text-sky-50 group-hover:bg-white/18'
                        )}
                      >
                        <Icon size={18} />
                      </div>
                      {!isCollapsed && (
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{item.label}</p>
                          <p className={cn('truncate text-xs', active ? 'text-slate-500' : 'text-sky-100/70')}>
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

      <div className="relative space-y-1 border-t border-slate-800/80 p-3">
        <button
          onClick={logout}
          title={isCollapsed ? 'Sair' : undefined}
          className={cn(
            'flex w-full items-center rounded-2xl text-sky-50/90 transition-colors hover:bg-white/10 hover:text-white',
            isCollapsed ? 'justify-center px-2 py-3' : 'gap-3 px-3.5 py-3'
          )}
        >
          <LogOut size={18} />
          {!isCollapsed && <span className="text-sm font-medium">Sair</span>}
        </button>

        <button
          onClick={toggleCollapse}
          className={cn(
            'flex w-full items-center rounded-2xl text-sky-100/70 transition-colors hover:bg-white/10 hover:text-white',
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
          'fixed inset-y-0 left-0 z-50 flex w-[86vw] max-w-[340px] flex-col overflow-hidden border-r border-sky-700/20 bg-sidebar text-white transition-transform duration-300 ease-in-out md:hidden',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(186,230,253,0.28),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.14),transparent_28%)]" />

        <div className="relative border-b border-slate-800/80 px-5 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-sky-100">MPCARS</p>
          <h1 className="mt-1 text-2xl font-display font-bold text-white">Painel da Locadora</h1>
          <p className="text-xs text-sky-100/75">Fluxo simples para o uso diario</p>
        </div>

        <div className="relative flex-1 overflow-y-auto px-4 py-4">
          <button
            onClick={() => {
              closeMobile()
              onOpenCommandPalette()
            }}
            className="flex w-full items-center gap-3 rounded-2xl border border-white/20 bg-white/12 px-4 py-3.5 text-left transition-colors hover:bg-white/18"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/20 text-white">
              <Search size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Busca rapida</p>
              <p className="text-xs text-sky-100/80">Encontre paginas sem navegar em excesso</p>
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
                            ? 'bg-white text-slate-950 shadow-[0_12px_28px_rgba(15,23,42,0.18)]'
                            : 'text-sky-50/90 hover:bg-white/10 hover:text-white'
                        )}
                      >
                        <div
                          className={cn(
                            'flex h-10 w-10 items-center justify-center rounded-2xl',
                            active ? 'bg-sky-500 text-white' : 'bg-white/12 text-sky-50'
                          )}
                        >
                          <Icon size={18} />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{item.label}</p>
                          <p className={cn('truncate text-xs', active ? 'text-slate-500' : 'text-sky-100/70')}>
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

        <div className="relative border-t border-slate-800/80 p-4">
          <button
            onClick={() => {
              logout()
              closeMobile()
            }}
            className="flex w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
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
