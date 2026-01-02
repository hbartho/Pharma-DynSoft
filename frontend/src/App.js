import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OfflineProvider } from './contexts/OfflineContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { Toaster } from './components/ui/sonner';
import { initDB } from './services/indexedDB';
import { autoSync } from './services/syncService';

import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Sales from './pages/Sales';
import Customers from './pages/Customers';
import Suppliers from './pages/Suppliers';
import Supplies from './pages/Supplies';
import Prescriptions from './pages/Prescriptions';
import Reports from './pages/Reports';
import Users from './pages/Users';
import Settings from './pages/Settings';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700 mx-auto mb-4"></div>
          <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
            Chargement...
          </p>
        </div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
};

// Role-based protected route
const RoleProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700 mx-auto mb-4"></div>
          <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
            Chargement...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <Navigate to="/dashboard" />;
  }

  return children;
};

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={
          <RoleProtectedRoute allowedRoles={['admin', 'pharmacien']}>
            <Products />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/sales"
        element={
          <ProtectedRoute>
            <Sales />
          </ProtectedRoute>
        }
      />
      <Route
        path="/customers"
        element={
          <ProtectedRoute>
            <Customers />
          </ProtectedRoute>
        }
      />
      <Route
        path="/suppliers"
        element={
          <RoleProtectedRoute allowedRoles={['admin', 'pharmacien']}>
            <Suppliers />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/supplies"
        element={
          <RoleProtectedRoute allowedRoles={['admin', 'pharmacien', 'caissier']}>
            <Supplies />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/prescriptions"
        element={
          <RoleProtectedRoute allowedRoles={['admin', 'pharmacien']}>
            <Prescriptions />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <RoleProtectedRoute allowedRoles={['admin', 'pharmacien']}>
            <Reports />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <Users />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <Settings />
          </RoleProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
};

function App() {
  useEffect(() => {
    // Initialize IndexedDB
    initDB();
    
    // Start auto-sync
    autoSync();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <SettingsProvider>
          <OfflineProvider>
            <BrowserRouter>
              <AppRoutes />
              <Toaster position="top-right" richColors />
            </BrowserRouter>
          </OfflineProvider>
        </SettingsProvider>
      </AuthProvider>
      {/* DevTools uniquement en développement */}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
      )}
    </QueryClientProvider>
  );
}

export default App;