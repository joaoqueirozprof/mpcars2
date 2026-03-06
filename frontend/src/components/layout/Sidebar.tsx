import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { LogOut, ChevronLeft, ChevronRight } from 'lucide-react'
import {
  LayoutDashboard, Users, Car, FileText, Building2, DollarSign,
  ShieldAlert, FileCheck, AlertCircle, Wrench, Calendar, BarChart3, Settings, Store
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useSidebar } from '@/contexts/SidebarContext'
import { cn } from '@/lib/utils'

const Sidebar: React.FC = () => {
  const location = useLocation()
  const { logout } = useAuth()
  const { isCollapsed, isMobileOpen, toggleCollapse, closeMobile } = useSidebar()

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
    { icon: Users, label: 'Clientes', href: '/clientes' },
    { icon: Car, label: 'Veiculos', href: '/veiculos' },
    { icon: FileText, label: 'Contratos', href: '/contratos' },
    { icon: Building2, label: 'Empresas', href: '/empresas' },
    { icon: DollarSign, label: 'Financeiro', href: '/financeiro' },
    { icon: ShieldAlert, label: 'Seguros', href: '/seguros' },
    { icon: FileCheck, label: 'Licenciamento', href: '/ipva' },
    { icon: AlertCircle, label: 'Multas', href: '/multas' },
    { icon: Wrench, label: 'Manutencoes', href: '/manutencoes' },
    { icon: Calendar, label: 'Reservas', href: '/reservas' },
    { icon: Store, label: 'Despesas Loja', href: '/despesas-loja' },
    { icon: BarChart3, label: 'Relatorios', href: '/relatorios' },
    { icon: Settings, label: 'Configuracoes', href: '/configuracoes' },
  ]

  const isActive = (href: string) => location.pathname === href

  return (
    <>
      {/* Overlay mobile */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden transition-opacity duration-300"
          onClick={closeMobile}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 bg-sidebar text-white flex flex-col',
          'transition-all duration-300 ease-in-out',
          // Desktop
          'hidden md:flex',
          isCollapsed ? 'md:w-20' : 'md:w-64',
        )}
      >
        {/* Logo area */}
        <div className={cn(
          'flex items-center border-b border-slate-700 h-16 flex-shrink-0',
          isCollapsed ? 'justify-center px-2' : 'px-6'
        )}>
          {isCollapsed ? (
            <span className="text-xl font-display font-bold">M</span>
          ) : (
            <div>
              <h1 className="text-xl font-display font-bold text-white">MPCARS</h1>
              <p className="text-[10px] text-slate-400">Sistema de Aluguel</p>
            </div>
          )}
        </div>

        {/* Menu */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.href)
            return (
              <Link
                key={item.href}
                to={item.href}
                title={isCollapsed ? item.label : undefined}
                className={cn(
                  'flex items-center gap-3 rounded-lg transition-all duration-200',
                  isCollapsed ? 'justify-center px-2 py-3' : 'px-4 py-2.5',
                  active
                    ? 'bg-primary text-white shadow-lg shadow-primary/30'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                )}
              >
                <Icon size={20} className="flex-shrink-0" />
                {!isCollapsed && (
                  <span className="text-sm font-medium whitespace-nowrap">{item.label}</span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Collapse toggle + Logout */}
        <div className="border-t border-slate-700 p-3 space-y-1 flex-shrink-0">
          <button
            onClick={() => { logout() }}
            title={isCollapsed ? 'Sair' : undefined}
            className={cn(
              'flex items-center gap-3 w-full rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-all duration-200',
              isCollapsed ? 'justify-center px-2 py-3' : 'px-4 py-2.5'
            )}
          >
            <LogOut size={20} className="flex-shrink-0" />
            {!isCollapsed && <span className="text-sm font-medium">Sair</span>}
          </button>

          <button
            onClick={toggleCollapse}
            className={cn(
              'flex items-center gap-3 w-full rounded-lg text-slate-400 hover:bg-white/10 hover:text-white transition-all duration-200',
              isCollapsed ? 'justify-center px-2 py-3' : 'px-4 py-2.5'
            )}
          >
            {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
            {!isCollapsed && <span className="text-sm font-medium">Recolher menu</span>}
          </button>
        </div>
      </aside>

      {/* Mobile sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-sidebar text-white flex flex-col md:hidden',
          'transition-transform duration-300 ease-in-out',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex items-center justify-between px-6 h-16 border-b border-slate-700 flex-shrink-0">
          <div>
            <h1 className="text-xl font-display font-bold text-white">MPCARS</h1>
            <p className="text-[10px] text-slate-400">Sistema de Aluguel</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.href)
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={closeMobile}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200',
                  active
                    ? 'bg-primary text-white shadow-lg shadow-primary/30'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                )}
              >
                <Icon size={20} />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            )
          })}
        </nav>

        <div className="border-t border-slate-700 p-3 flex-shrink-0">
          <button
            onClick={() => { logout(); closeMobile() }}
            className="flex items-center gap-3 w-full px-4 py-2.5 rounded-lg text-slate-300 hover:bg-white/10 hover:text-white transition-all duration-200"
          >
            <LogOut size={20} />
            <span className="text-sm font-medium">Sair</span>
          </button>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
