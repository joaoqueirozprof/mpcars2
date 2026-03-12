import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '@/services/api'
import { User } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User | null) => void
  canAccess: (page: string) => boolean
  isAdmin: boolean
  isBackupOperator: boolean
  getHomeRoute: () => string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token')
      const storedUser = localStorage.getItem('user')

      if (token && storedUser) {
        try {
          const parsed = JSON.parse(storedUser)
          setUser(parsed)
        } catch {
          // If stored user is corrupted, try fetching from API
          try {
            const { data } = await api.get('/auth/me')
            setUser(data)
            localStorage.setItem('user', JSON.stringify(data))
          } catch {
            localStorage.removeItem('user')
            localStorage.removeItem('access_token')
          }
        }
      } else if (token && !storedUser) {
        // Token exists but no user stored - fetch user
        try {
          const { data } = await api.get('/auth/me')
          setUser(data)
          localStorage.setItem('user', JSON.stringify(data))
        } catch {
          localStorage.removeItem('access_token')
        }
      }
      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password })

    localStorage.setItem('access_token', data.access_token)

    // Backend returns user object in login response
    if (data.user) {
      localStorage.setItem('user', JSON.stringify(data.user))
      setUser(data.user)
    } else {
      // Fallback: fetch user from /auth/me
      const meResponse = await api.get('/auth/me')
      const userData = meResponse.data
      localStorage.setItem('user', JSON.stringify(userData))
      setUser(userData)
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setUser(null)
  }

  const isAdmin = user?.perfil === 'admin'
  const isBackupOperator = user?.perfil === 'admin' || user?.perfil === 'owner'

  const canAccess = useCallback((page: string): boolean => {
    if (!user) return false
    if (user.perfil === 'admin') return true
    if (user.perfil === 'owner') return page === 'governanca'
    const pages = user.permitted_pages || []
    return pages.includes(page)
  }, [user])

  const getHomeRoute = useCallback(() => {
    if (!user) return '/login'
    if (user.perfil === 'owner') return '/backups'
    if (canAccess('dashboard')) return '/dashboard'

    const fallbackPages = [
      'contratos',
      'reservas',
      'clientes',
      'veiculos',
      'financeiro',
      'relatorios',
      'configuracoes',
      'governanca',
    ]
    const firstAllowedPage = fallbackPages.find((page) => canAccess(page))

    if (!firstAllowedPage || firstAllowedPage === 'dashboard') {
      return '/dashboard'
    }

    return firstAllowedPage === 'governanca' ? '/backups' : `/${firstAllowedPage}`
  }, [canAccess, user])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        setUser,
        canAccess,
        isAdmin,
        isBackupOperator,
        getHomeRoute,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
