import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bell, CheckCheck, ChevronDown, Command, Menu, Search, Sparkles, X } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { findNavigationItem, inferAlertRoute } from '@/config/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useSidebar } from '@/contexts/SidebarContext'
import { getInitials } from '@/lib/utils'
import api from '@/services/api'
import { DashboardStats } from '@/types'

interface HeaderProps {
  onOpenCommandPalette: () => void
}

interface HeaderNotification {
  id: string
  title: string
  message: string
  type: 'info' | 'warning' | 'danger'
  href: string
  scope: 'alerta' | 'agenda'
}

const Header: React.FC<HeaderProps> = ({ onOpenCommandPalette }) => {
  const { user, logout } = useAuth()
  const { toggleMobile, isMobileOpen } = useSidebar()
  const navigate = useNavigate()
  const location = useLocation()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [readNotificationIds, setReadNotificationIds] = useState<string[]>([])

  const notifRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  const activePage = findNavigationItem(location.pathname)

  const { data: dashboardData } = useQuery({
    queryKey: ['header-dashboard'],
    queryFn: async () => {
      const { data } = await api.get<DashboardStats>('/dashboard')
      return data
    },
    staleTime: 60 * 1000,
  })

  const notifications = useMemo<HeaderNotification[]>(() => {
    const alerts = (dashboardData?.alertas || []).slice(0, 4).map((alerta) => ({
      id: `alert-${alerta.id}`,
      title: alerta.titulo,
      message: alerta.descricao,
      type:
        alerta.urgencia === 'critica'
          ? 'danger'
          : alerta.urgencia === 'atencao'
            ? 'warning'
            : 'info',
      href: inferAlertRoute(alerta.tipo),
      scope: 'alerta' as const,
    }))

    const agenda = (dashboardData?.agenda_hoje || []).slice(0, 3).map((item) => ({
      id: `agenda-${item.id}`,
      title: item.titulo,
      message: item.descricao,
      type:
        item.urgencia === 'critica'
          ? 'danger'
          : item.urgencia === 'atencao'
            ? 'warning'
            : 'info',
      href: item.rota || '/dashboard',
      scope: 'agenda' as const,
    }))

    return [...alerts, ...agenda]
  }, [dashboardData])

  const unreadCount = notifications.filter((notification) => !readNotificationIds.includes(notification.id)).length

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const markAllAsRead = () => {
    setReadNotificationIds((current) => [
      ...new Set([...current, ...notifications.map((notification) => notification.id)]),
    ])
  }

  const openNotification = (notification: HeaderNotification) => {
    setReadNotificationIds((current) => Array.from(new Set([...current, notification.id])))
    setShowNotifications(false)
    navigate(notification.href)
  }

  const getTypeColor = (type: HeaderNotification['type']) => {
    switch (type) {
      case 'danger':
        return 'bg-red-500'
      case 'warning':
        return 'bg-amber-500'
      default:
        return 'bg-blue-500'
    }
  }

  return (
    <header className="sticky top-0 z-30 border-b border-white/70 bg-white/80 shadow-[0_10px_35px_rgba(15,23,42,0.07)] backdrop-blur-xl">
      <div className="flex min-h-[76px] items-center justify-between gap-3 px-4 py-3 md:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button
            onClick={toggleMobile}
            className="rounded-2xl border border-slate-200 bg-white/80 p-2.5 text-slate-600 transition-colors hover:border-primary/30 hover:text-primary md:hidden"
          >
            {isMobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>

          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="hidden min-w-0 flex-1 items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/90 px-4 py-3 text-left transition-all duration-200 hover:border-primary/30 hover:bg-white md:flex"
          >
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <Search size={18} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">
                  Buscar pagina, cliente, fluxo ou atalho
                </p>
                <p className="truncate text-xs text-slate-500">
                  Pule entre contratos, reservas, frota, financeiro e criacao rapida
                </p>
              </div>
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-500 lg:flex">
              <Command size={13} />
              Ctrl K
            </div>
          </button>

          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 transition-colors hover:border-primary/30 hover:text-primary md:hidden"
          >
            <Search size={18} />
          </button>

          <div className="hidden min-w-0 xl:block">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-700">
                <Sparkles size={12} />
                UX fluida
              </span>
              <p className="truncate text-sm font-semibold text-slate-900">{activePage.label}</p>
            </div>
            <p className="truncate text-xs text-slate-500">{activePage.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div ref={notifRef} className="relative">
            <button
              onClick={() => {
                setShowNotifications((current) => !current)
                setShowUserMenu(false)
              }}
              className="relative rounded-2xl border border-slate-200 bg-white p-2.5 text-slate-600 transition-colors hover:border-primary/30 hover:text-primary"
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-[19px] min-w-[19px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-3 w-[360px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-2xl animate-in">
                <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/80 px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Central de alertas</p>
                    <p className="text-xs text-slate-500">Agenda do dia e riscos operacionais</p>
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-primary transition-colors hover:text-primary/80"
                    >
                      <CheckCheck size={14} />
                      Marcar tudo
                    </button>
                  )}
                </div>

                <div className="max-h-[420px] space-y-2 overflow-y-auto px-3 py-3">
                  {notifications.length === 0 ? (
                    <div className="flex flex-col items-center justify-center gap-2 px-4 py-10 text-center">
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                        <CheckCheck size={24} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-900">Operacao sob controle</p>
                        <p className="text-xs text-slate-500">Nenhum alerta critico no momento.</p>
                      </div>
                    </div>
                  ) : (
                    notifications.map((notification) => {
                      const isUnread = !readNotificationIds.includes(notification.id)

                      return (
                        <button
                          key={notification.id}
                          onClick={() => openNotification(notification)}
                          className={`flex w-full items-start gap-3 rounded-2xl border px-3 py-3 text-left transition-all duration-200 ${
                            isUnread
                              ? 'border-blue-100 bg-blue-50/70 hover:bg-blue-50'
                              : 'border-slate-100 bg-white hover:bg-slate-50'
                          }`}
                        >
                          <div className={`mt-1 h-2.5 w-2.5 rounded-full ${getTypeColor(notification.type)}`} />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <p className={`truncate text-sm ${isUnread ? 'font-semibold text-slate-900' : 'font-medium text-slate-700'}`}>
                                {notification.title}
                              </p>
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                                {notification.scope}
                              </span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-xs text-slate-500">{notification.message}</p>
                          </div>
                        </button>
                      )
                    })
                  )}
                </div>

                <div className="border-t border-slate-100 bg-slate-50/70 px-4 py-3">
                  <button
                    onClick={() => {
                      setShowNotifications(false)
                      navigate('/dashboard')
                    }}
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:border-primary/30 hover:text-primary"
                  >
                    Abrir painel operacional
                  </button>
                </div>
              </div>
            )}
          </div>

          <div ref={userMenuRef} className="relative">
            <button
              onClick={() => {
                setShowUserMenu((current) => !current)
                setShowNotifications(false)
              }}
              className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-2.5 py-2 transition-colors hover:border-primary/30 hover:bg-slate-50"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-white shadow-lg shadow-primary/20">
                {user ? getInitials(user.nome) : '?'}
              </div>
              <div className="hidden text-left md:block">
                <p className="max-w-[160px] truncate text-sm font-semibold text-slate-900">
                  {user?.nome || 'Usuario'}
                </p>
                <p className="text-[11px] capitalize text-slate-500">
                  {user?.perfil || user?.role || 'Admin'}
                </p>
              </div>
              <ChevronDown size={14} className="hidden text-slate-400 md:block" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-3 w-56 overflow-hidden rounded-[22px] border border-slate-200 bg-white py-2 shadow-2xl animate-in">
                <div className="border-b border-slate-100 px-4 py-3 md:hidden">
                  <p className="text-sm font-semibold text-slate-900">{user?.nome}</p>
                  <p className="text-xs capitalize text-slate-500">{user?.perfil || user?.role}</p>
                </div>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    navigate('/configuracoes')
                  }}
                  className="w-full px-4 py-2.5 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Configuracoes
                </button>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    onOpenCommandPalette()
                  }}
                  className="w-full px-4 py-2.5 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Abrir central de comandos
                </button>
                <hr className="my-1 border-slate-100" />
                <button
                  onClick={() => {
                    logout()
                    setShowUserMenu(false)
                  }}
                  className="w-full px-4 py-2.5 text-left text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
                >
                  Sair
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
