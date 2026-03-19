import React, { Suspense, lazy } from "react"
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider, useAuth } from "@/contexts/AuthContext"
import { ConfigProvider } from "@/contexts/ConfigContext"
import ErrorBoundary from "@/components/shared/ErrorBoundary"
import RouteLoader from "@/components/shared/RouteLoader"
import PWAInstallPrompt from "@/components/shared/PWAInstallPrompt"

const Login = lazy(() => import("@/pages/Login"))
const Dashboard = lazy(() => import("@/pages/Dashboard"))
const Clientes = lazy(() => import("@/pages/Clientes"))
const Veiculos = lazy(() => import("@/pages/Veiculos"))
const Contratos = lazy(() => import("@/pages/Contratos"))
const Empresas = lazy(() => import("@/pages/Empresas"))
const Financeiro = lazy(() => import("@/pages/Financeiro"))
const Seguros = lazy(() => import("@/pages/Seguros"))
const Ipva = lazy(() => import("@/pages/Ipva"))
const Multas = lazy(() => import("@/pages/Multas"))
const Manutencoes = lazy(() => import("@/pages/Manutencoes"))
const Reservas = lazy(() => import("@/pages/Reservas"))
const Relatorios = lazy(() => import("@/pages/Relatorios"))
const Configuracoes = lazy(() => import("@/pages/Configuracoes"))
const DespesasLoja = lazy(() => import("@/pages/DespesasLoja"))
const Usuarios = lazy(() => import("@/pages/Usuarios"))
const Governanca = lazy(() => import("@/pages/Governanca"))
const ResetPassword = lazy(() => import("@/pages/ResetPassword"))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <RouteLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

const PermissionRoute: React.FC<{
  children: React.ReactNode
  page: string
}> = ({ children, page }) => {
  const { isAuthenticated, isLoading, canAccess, getHomeRoute } = useAuth()

  if (isLoading) {
    return <RouteLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!canAccess(page)) {
    return <Navigate to={getHomeRoute()} replace />
  }

  return <>{children}</>
}

const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading, isAdmin } = useAuth()

  if (isLoading) {
    return <RouteLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

const AppRoutes: React.FC = () => {
  const { isAuthenticated, getHomeRoute } = useAuth()
  const homeRoute = getHomeRoute()

  return (
    <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? <Navigate to={homeRoute} replace /> : <Login />
          }
        />
        <Route path="/redefinir-senha" element={<ResetPassword />} />
        <Route
          path="/dashboard"
          element={
            <PermissionRoute page="dashboard">
              <Dashboard />
            </PermissionRoute>
          }
        />
        <Route
          path="/clientes"
          element={
            <PermissionRoute page="clientes">
              <Clientes />
            </PermissionRoute>
          }
        />
        <Route
          path="/veiculos"
          element={
            <PermissionRoute page="veiculos">
              <Veiculos />
            </PermissionRoute>
          }
        />
        <Route
          path="/contratos"
          element={
            <PermissionRoute page="contratos">
              <Contratos />
            </PermissionRoute>
          }
        />
        <Route
          path="/empresas"
          element={
            <PermissionRoute page="empresas">
              <Empresas />
            </PermissionRoute>
          }
        />
        <Route
          path="/financeiro"
          element={
            <PermissionRoute page="financeiro">
              <Financeiro />
            </PermissionRoute>
          }
        />
        <Route
          path="/seguros"
          element={
            <PermissionRoute page="seguros">
              <Seguros />
            </PermissionRoute>
          }
        />
        <Route
          path="/ipva"
          element={
            <PermissionRoute page="ipva">
              <Ipva />
            </PermissionRoute>
          }
        />
        <Route
          path="/multas"
          element={
            <PermissionRoute page="multas">
              <Multas />
            </PermissionRoute>
          }
        />
        <Route
          path="/manutencoes"
          element={
            <PermissionRoute page="manutencoes">
              <Manutencoes />
            </PermissionRoute>
          }
        />
        <Route
          path="/reservas"
          element={
            <PermissionRoute page="reservas">
              <Reservas />
            </PermissionRoute>
          }
        />
        <Route
          path="/relatorios"
          element={
            <PermissionRoute page="relatorios">
              <Relatorios />
            </PermissionRoute>
          }
        />
        <Route
          path="/despesas-loja"
          element={
            <PermissionRoute page="despesas-loja">
              <DespesasLoja />
            </PermissionRoute>
          }
        />
        <Route
          path="/configuracoes"
          element={
            <PermissionRoute page="configuracoes">
              <Configuracoes />
            </PermissionRoute>
          }
        />
        <Route
          path="/usuarios"
          element={
            <AdminRoute>
              <Usuarios />
            </AdminRoute>
          }
        />
        <Route
          path="/backups"
          element={
            <PermissionRoute page="governanca">
              <Governanca />
            </PermissionRoute>
          }
        />
        <Route
          path="/"
          element={
            <Navigate to={isAuthenticated ? homeRoute : "/login"} replace />
          }
        />
        <Route
          path="*"
          element={
            <Navigate to={isAuthenticated ? homeRoute : "/login"} replace />
          }
        />
      </Routes>
    </Suspense>
  )
}

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <ErrorBoundary>
          <AuthProvider>
            <ConfigProvider>
              <AppRoutes />
              <PWAInstallPrompt />
            </ConfigProvider>
          </AuthProvider>
        </ErrorBoundary>
      </Router>
    </QueryClientProvider>
  )
}

export default App
