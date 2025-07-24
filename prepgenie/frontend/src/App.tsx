import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import {
  LoginPage,
  RegisterPage,
  DashboardPage,
  SyllabusPage,
  PYQSearchPage,
  AnswersPage,
  StudyPlanPage,
  ProgressPage,
  ChatPage,
} from './pages';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary-50 via-secondary-50 to-accent-50">
        <div className="relative">
          <div className="animate-spin rounded-full h-32 w-32 border-4 border-transparent bg-gradient-to-r from-ai-blue via-ai-purple to-ai-cyan rounded-full animate-spin-slow"></div>
          <div className="absolute inset-0 rounded-full h-32 w-32 border-4 border-transparent bg-gradient-to-r from-ai-cyan via-ai-emerald to-ai-blue rounded-full animate-spin-slow animation-delay-75"></div>
          <div className="absolute inset-4 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center">
            <div className="text-ai-blue font-bold text-lg animate-pulse-ai">PrepGenie</div>
          </div>
        </div>
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary-50 via-secondary-50 to-accent-50">
        <div className="relative">
          <div className="animate-spin rounded-full h-32 w-32 border-4 border-transparent bg-gradient-to-r from-ai-blue via-ai-purple to-ai-cyan rounded-full animate-spin-slow"></div>
          <div className="absolute inset-0 rounded-full h-32 w-32 border-4 border-transparent bg-gradient-to-r from-ai-cyan via-ai-emerald to-ai-blue rounded-full animate-spin-slow animation-delay-75"></div>
          <div className="absolute inset-4 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center">
            <div className="text-ai-blue font-bold text-lg animate-pulse-ai">PrepGenie</div>
          </div>
        </div>
      </div>
    );
  }

  return !isAuthenticated ? <>{children}</> : <Navigate to="/dashboard" replace />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Public Routes */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <RegisterPage />
                </PublicRoute>
              }
            />

            {/* Protected Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="syllabus" element={<SyllabusPage />} />
              <Route path="pyq-search" element={<PYQSearchPage />} />
              <Route path="answers" element={<AnswersPage />} />
              <Route path="study-plan" element={<StudyPlanPage />} />
              <Route path="progress" element={<ProgressPage />} />
              <Route path="chat" element={<ChatPage />} />
            </Route>

            {/* Catch-all route */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
