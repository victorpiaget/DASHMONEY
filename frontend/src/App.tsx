import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider, useAuth } from './context/AuthContext'
import { CurrencyProvider } from './context/CurrencyContext'
import { ProfileProvider, useProfile } from './context/ProfileContext'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import WorkspaceSelectorPage from './pages/WorkspaceSelectorPage'
import ProfileSelectorPage from './pages/ProfileSelectorPage'
import DashboardPage from './pages/DashboardPage'
import AccountsPage from './pages/AccountsPage'
import AccountDetailPage from './pages/AccountDetailPage'
import TransfersPage from './pages/TransfersPage'
import CategoriesPage from './pages/CategoriesPage'
import AccountAnalysisPage from './pages/AccountAnalysisPage'
import PortfoliosPage from './pages/PortfoliosPage'
import PortfolioDetailPage from './pages/PortfolioDetailPage'
import PortfolioAnalysisPage from './pages/PortfolioAnalysisPage'
import InstrumentsPage from './pages/InstrumentsPage'
import TransactionsPage from './pages/TransactionsPage'
import PortfoliosComparePage from './pages/PortfoliosComparePage'
import WorkspaceOverviewPage from './pages/WorkspaceOverviewPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

// Route protégée : doit être authentifié ET avoir sélectionné un profil
function PrivateRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth()
  const { profileId } = useProfile()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!profileId) return <Navigate to="/select-workspace" replace />
  return children
}

// Route accessible si authentifié, indépendamment du profil
function WorkspaceAuthRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

// Route accessible uniquement si authentifié mais sans profil sélectionné
function AuthOnlyRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth()
  const { profileId } = useProfile()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (profileId) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <ThemeProvider>
    <QueryClientProvider client={queryClient}>
      <ProfileProvider>
        <AuthProvider>
          <CurrencyProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />

                {/* Vue d'ensemble workspace (accessible avec ou sans profil sélectionné) */}
                <Route path="/workspaces/:workspaceId/overview" element={
                  <WorkspaceAuthRoute><WorkspaceOverviewPage /></WorkspaceAuthRoute>
                } />

                {/* Sélection workspace / profil */}
                <Route path="/select-workspace" element={
                  <AuthOnlyRoute><WorkspaceSelectorPage /></AuthOnlyRoute>
                } />
                <Route path="/select-profile" element={
                  <AuthOnlyRoute><ProfileSelectorPage /></AuthOnlyRoute>
                } />

                {/* App principale */}
                <Route
                  path="/"
                  element={
                    <PrivateRoute>
                      <AppLayout />
                    </PrivateRoute>
                  }
                >
                  <Route index element={<DashboardPage />} />
                  <Route path="accounts" element={<AccountsPage />} />
                  <Route path="accounts/:id" element={<AccountDetailPage />} />
                  <Route path="accounts/:id/analyse" element={<AccountAnalysisPage />} />
                  <Route path="transfers" element={<TransfersPage />} />
                  <Route path="categories" element={<CategoriesPage />} />
                  <Route path="portfolios" element={<PortfoliosPage />} />
                  <Route path="portfolios/:id" element={<PortfolioDetailPage />} />
                  <Route path="portfolios/:id/analyse" element={<PortfolioAnalysisPage />} />
                  <Route path="portfolios/compare" element={<PortfoliosComparePage />} />
                  <Route path="instruments" element={<InstrumentsPage />} />
                  <Route path="transactions" element={<TransactionsPage />} />
                </Route>

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </CurrencyProvider>
        </AuthProvider>
      </ProfileProvider>
    </QueryClientProvider>
    </ThemeProvider>
  )
}
