import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../contexts/OfflineContext';
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Users,
  Truck,
  FileText,
  BarChart3,
  Settings,
  LogOut,
  Wifi,
  WifiOff,
  RefreshCw,
} from 'lucide-react';
import { Button } from './ui/button';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isOnline, isSyncing, performSync, lastSyncTime } = useOffline();

  const menuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord' },
    { path: '/products', icon: Package, label: 'Produits' },
    { path: '/sales', icon: ShoppingCart, label: 'Ventes' },
    { path: '/customers', icon: Users, label: 'Clients' },
    { path: '/suppliers', icon: Truck, label: 'Fournisseurs' },
    { path: '/prescriptions', icon: FileText, label: 'Ordonnances' },
    { path: '/reports', icon: BarChart3, label: 'Rapports' },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-2xl font-bold text-teal-700" style={{ fontFamily: 'Manrope, sans-serif' }}>
            PharmaFlow
          </h1>
          <p className="text-sm text-slate-500 mt-1" style={{ fontFamily: 'Inter, sans-serif' }}>
            {user?.name} ({user?.role})
          </p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.path.substring(1)}`}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  isActive
                    ? 'bg-teal-50 text-teal-700 font-medium'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <Icon className="w-5 h-5" strokeWidth={1.5} />
                <span style={{ fontFamily: 'Inter, sans-serif' }}>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200 space-y-3">
          {/* Sync Status */}
          <div className="flex items-center justify-between px-4 py-2 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2">
              {isOnline ? (
                <Wifi className="w-4 h-4 text-emerald-600" strokeWidth={1.5} />
              ) : (
                <WifiOff className="w-4 h-4 text-red-500" strokeWidth={1.5} />
              )}
              <span className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                {isOnline ? 'En ligne' : 'Hors ligne'}
              </span>
            </div>
            {isOnline && (
              <button
                onClick={performSync}
                disabled={isSyncing}
                data-testid="sync-button"
                className="text-teal-600 hover:text-teal-700 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} strokeWidth={1.5} />
              </button>
            )}
          </div>

          {lastSyncTime && (
            <p className="text-xs text-slate-500 px-4" style={{ fontFamily: 'Inter, sans-serif' }}>
              Dernière sync: {lastSyncTime.toLocaleTimeString()}
            </p>
          )}

          <Button
            onClick={handleLogout}
            data-testid="logout-button"
            variant="outline"
            className="w-full flex items-center gap-2 justify-center"
          >
            <LogOut className="w-4 h-4" strokeWidth={1.5} />
            Déconnexion
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
};

export default Layout;