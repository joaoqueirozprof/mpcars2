import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Search, ChevronDown, Menu, X, CheckCheck } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useSidebar } from '@/contexts/SidebarContext'
import { getInitials } from '@/lib/utils'

interface Notification {
  id: string
  title: string
  message: string
  time: string
  read: boolean
  type: 'info' | 'warning' | 'danger'
}

const mockNotifications: Notification[] = [
  {
    id: '1',
    title: 'Contrato Vencendo',
    message: 'O contrato #0042 vence em 3 dias. Verifique com o cliente.',
    time: 'Agora',
    read: false,
    type: 'warning',
  },
  {
    id: '2',
    title: 'Manutencao Pendente',
    message: 'Veiculo ABC-1234 precisa de revisao programada.',
    time: '2h atras',
    read: false,
    type: 'danger',
  },
  {
    id: '3',
    title: 'IPVA Proximo do Vencimento',
    message: 'IPVA de 5 veiculos vence nos proximos 30 dias.',
    time: '5h atras',
    read: false,
    type: 'warning',
  },
  {
    id: '4',
    title: 'Novo Cliente Cadastrado',
    message: 'Maria Silva foi cadastrada com sucesso.',
    time: '1 dia atras',
    read: true,
    type: 'info',
  },
]

const Header: React.FC = () => {
  const { user, logout } = useAuth()
  const { toggleMobile, isMobileOpen, isCollapsed } = useSidebar()
  const navigate = useNavigate()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications)

  const notifRef = useRef<HTMLDivElement>(null)
  const userMenuRef = useRef<HTMLDivElement>(null)

  const unreadCount = notifications.filter(n => !n.read).length

  // Close dropdowns on outside click
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
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  }

  const markAsRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'danger': return 'bg-red-500'
      case 'warning': return 'bg-amber-500'
      default: return 'bg-blue-500'
    }
  }

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 shadow-sm">
      <div className={`flex items-center justify-between h-16 px-4 md:px-6 transition-all duration-300`}>
        {/* Left: mobile menu + search */}
        <div className="flex items-center gap-3 flex-1">
          {/* Mobile hamburger */}
          <button
            onClick={toggleMobile}
            className="md:hidden p-2 text-slate-600 hover:text-primary hover:bg-slate-100 rounded-lg transition-colors"
          >
            {isMobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>

          {/* Search */}
          <div className="hidden md:block max-w-md flex-1">
            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus-within:outline-none focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all">
              <Search size={16} className="text-slate-400 flex-shrink-0" />
              <input
                type="text"
                placeholder="Buscar..."
                className="flex-1 bg-transparent outline-none placeholder:text-slate-400 text-sm"
              />
            </div>
          </div>
        </div>

        {/* Right: notifications + user */}
        <div className="flex items-center gap-2">
          {/* Notifications */}
          <div ref={notifRef} className="relative">
            <button
              onClick={() => { setShowNotifications(!showNotifications); setShowUserMenu(false) }}
              className="relative p-2 text-slate-600 hover:text-primary hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-red-500 text-white text-[10px] font-bold rounded-full px-1">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notifications dropdown */}
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200">
                  <h3 className="text-sm font-semibold text-slate-900">Notificacoes</h3>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 font-medium transition-colors"
                    >
                      <CheckCheck size={14} />
                      Marcar todas como lidas
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                  {notifications.length === 0 ? (
                    <div className="px-4 py-8 text-center text-sm text-slate-400">
                      Nenhuma notificacao
                    </div>
                  ) : (
                    notifications.map((notif) => (
                      <button
                        key={notif.id}
                        onClick={() => markAsRead(notif.id)}
                        className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${!notif.read ? 'bg-blue-50/50' : ''}`}
                      >
                        <div className="flex gap-3">
                          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${getTypeColor(notif.type)}`} />
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm ${!notif.read ? 'font-semibold text-slate-900' : 'font-medium text-slate-700'}`}>
                              {notif.title}
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{notif.message}</p>
                            <p className="text-[10px] text-slate-400 mt-1">{notif.time}</p>
                          </div>
                        </div>
                      </button>
                    ))
                  )}
                </div>

                <div className="px-4 py-2.5 border-t border-slate-200 bg-slate-50">
                  <button
                    onClick={() => { setShowNotifications(false); navigate('/dashboard') }}
                    className="w-full text-center text-xs font-medium text-primary hover:text-primary/80 transition-colors"
                  >
                    Ver todas no Dashboard
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* User menu */}
          <div ref={userMenuRef} className="relative">
            <button
              onClick={() => { setShowUserMenu(!showUserMenu); setShowNotifications(false) }}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold">
                {user ? getInitials(user.nome) : '?'}
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-slate-900">{user?.nome || 'Usuario'}</p>
                <p className="text-[10px] text-slate-500 capitalize">{user?.perfil || user?.role || 'Admin'}</p>
              </div>
              <ChevronDown size={14} className="text-slate-400 hidden md:block" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-2xl border border-slate-200 py-1 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="px-4 py-2 border-b border-slate-100 md:hidden">
                  <p className="text-sm font-medium text-slate-900">{user?.nome}</p>
                  <p className="text-xs text-slate-500 capitalize">{user?.perfil || user?.role}</p>
                </div>
                <button
                  onClick={() => { setShowUserMenu(false); navigate('/configuracoes') }}
                  className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Configuracoes
                </button>
                <hr className="my-1 border-slate-100" />
                <button
                  onClick={() => { logout(); setShowUserMenu(false) }}
                  className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 transition-colors"
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
