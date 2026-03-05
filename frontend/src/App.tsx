import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Clientes from '@/pages/Clientes'
import Veiculos from '@/pages/Veiculos'
import Contratos from '@/pages/Contratos'
import Empresas from '@/pages/Empresas'
import Financeiro from '@/pages/Financeiro'
import Seguros from '@/pages/Seguros'
import Ipva from '@/pages/Ipva'
import Multas from '@/pages/Multas'
import Manutencoes from '@/pages/Manutencoes'
import Reservas from '@/pages/Reservas'
import Relatorios from '@/pages/Relatorios'
import Configuracoes from '@/pages/Configuracoes'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-surface">
        <div className="text-center">
          <h1 className="text-2xl font-display font-bold text-slate-900">MPCARS</h1>
          <p className="text-slate-600 mt-2">Carregando...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

const AppRoutes: React.FC = () => {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/clientes" element={<ProtectedRoute><Clientes /></ProtectedRoute>} />
      <Route path="/veiculos" element={<ProtectedRoute><Veiculos /></ProtectedRoute>} />
      <Route path="/contratos" element={<ProtectedRoute><Contratos /></ProtectedRoute>} />
      <Route path="/empresas" element={<ProtectedRoute><Empresas /></ProtectedRoute>} />
      <Route path="/financeiro" element={<ProtectedRoute><Financeiro /></ProtectedRoute>} />
      <Route path="/seguros" element={<ProtectedRoute><Seguros /></ProtectedRoute>} />
      <Route path="/ipva" element={<ProtectedRoute><Ipva /></ProtectedRoute>} />
      <Route path="/multas" element={<ProtectedRoute><Multas /></ProtectedRoute>} />
      <Route path="/manutencoes" element={<ProtectedRoute><Manutencoes /></ProtectedRoute>} />
      <Route path="/reservas" element={<ProtectedRoute><Reservas /></ProtectedRoute>} />
      <Route path="/relatorios" element={<ProtectedRoute><Relatorios /></ProtectedRoute>} />
      <Route path="/configuracoes" element={<ProtectedRoute><Configuracoes /></ProtectedRoute>} />
      <Route path="/" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
      <Route path="*" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
    </Routes>
  )
}

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  )
}

export default App
