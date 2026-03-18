import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import { CurrencyProvider } from './context/CurrencyContext'
import AppLayout from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
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
import WorkspacePage from './pages/WorkspacePage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

function PrivateRoute({ children }: { children: React.ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    )
  }
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <CurrencyProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
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
              <Route path="instruments" element={<InstrumentsPage />} />
              <Route path="workspace" element={<WorkspacePage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        </CurrencyProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
