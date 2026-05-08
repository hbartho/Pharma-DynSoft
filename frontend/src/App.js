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
import PriceManagement from './pages/PriceManagement';
import PaymentMethods from './pages/PaymentMethods';
import Debts from './pages/Debts';
import SupplierDebts from './pages/SupplierDebts';
import ShiftsHistory from './pages/ShiftsHistory';
import ShiftSchedules from './pages/ShiftSchedules';
import StockLosses from './pages/StockLosses';
import Inventory from './pages/Inventory';
import StockMovements from './pages/StockMovements';
import PromoCodes from './pages/PromoCodes';
import DiscountRules from './pages/DiscountRules';
import DiscountHistory from './pages/DiscountHistory';
import PWAInstallPrompt from './components/PWAInstallPrompt';

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
      <Route
        path="/price-management"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <PriceManagement />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/payment-methods"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <PaymentMethods />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/debts"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <Debts />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/supplier-debts"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <SupplierDebts />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/shifts"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <ShiftsHistory />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/shift-schedules"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <ShiftSchedules />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/stock-losses"
        element={
          <ProtectedRoute>
            <StockLosses />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inventory"
        element={
          <ProtectedRoute>
            <Inventory />
          </ProtectedRoute>
        }
      />
      <Route
        path="/stock-movements"
        element={
          <ProtectedRoute>
            <StockMovements />
          </ProtectedRoute>
        }
      />
      <Route
        path="/promo-codes"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <PromoCodes />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/discount-rules"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <DiscountRules />
          </RoleProtectedRoute>
        }
      />
      <Route
        path="/discount-history"
        element={
          <RoleProtectedRoute allowedRoles={['admin']}>
            <DiscountHistory />
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
              <PWAInstallPrompt />
            </BrowserRouter>
          </OfflineProvider>
        </SettingsProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;