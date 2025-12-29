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
  UserCog,
  Cloud,
  CloudOff,
  AlertCircle,
} from 'lucide-react';
import { Button } from './ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isOnline, isSyncing, performSync, lastSyncTime, pendingChangesCount, getTimeSinceLastSync } = useOffline();
  
  const timeSinceSync = getTimeSinceLastSync();

  // Define menu items with role restrictions
  const allMenuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord', roles: ['admin', 'pharmacien', 'caissier'] },
    { path: '/products', icon: Package, label: 'Produits', roles: ['admin', 'pharmacien'] },
    { path: '/sales', icon: ShoppingCart, label: 'Ventes', roles: ['admin', 'pharmacien', 'caissier'] },
    { path: '/customers', icon: Users, label: 'Clients', roles: ['admin', 'pharmacien', 'caissier'] },
    { path: '/suppliers', icon: Truck, label: 'Fournisseurs', roles: ['admin', 'pharmacien'] },
    { path: '/prescriptions', icon: FileText, label: 'Ordonnances', roles: ['admin', 'pharmacien'] },
    { path: '/reports', icon: BarChart3, label: 'Rapports', roles: ['admin', 'pharmacien'] },
    { path: '/users', icon: UserCog, label: 'Utilisateurs', roles: ['admin'] },
  ];

  // Filter menu items based on user role
  const menuItems = allMenuItems.filter(item => 
    item.roles.includes(user?.role || 'caissier')
  );

  // Get role display info
  const getRoleLabel = (role) => {
    switch (role) {
      case 'admin': return 'Administrateur';
      case 'pharmacien': return 'Pharmacien';
      case 'caissier': return 'Caissier';
      default: return role;
    }
  };

  const getRoleColor = (role) => {
    switch (role) {
      case 'admin': return 'text-red-600 bg-red-50';
      case 'pharmacien': return 'text-blue-600 bg-blue-50';
      case 'caissier': return 'text-green-600 bg-green-50';
      default: return 'text-slate-600 bg-slate-50';
    }
  };

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
            DynSoft Pharma
          </h1>
          <p className="text-sm text-slate-500 mt-1" style={{ fontFamily: 'Inter, sans-serif' }}>
            {user?.name}
          </p>
          <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${getRoleColor(user?.role)}`}>
            {getRoleLabel(user?.role)}
          </span>
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
          {/* Sync Status - Enhanced */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className={`flex items-center justify-between px-4 py-3 rounded-lg ${
                  isOnline 
                    ? pendingChangesCount > 0 
                      ? 'bg-amber-50 border border-amber-100' 
                      : 'bg-emerald-50 border border-emerald-100'
                    : 'bg-red-50 border border-red-100'
                }`}>
                  <div className="flex items-center gap-2">
                    {isOnline ? (
                      pendingChangesCount > 0 ? (
                        <Cloud className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
                      ) : (
                        <Cloud className="w-4 h-4 text-emerald-600" strokeWidth={1.5} />
                      )
                    ) : (
                      <CloudOff className="w-4 h-4 text-red-500" strokeWidth={1.5} />
                    )}
                    <div>
                      <span className={`text-sm font-medium ${
                        isOnline 
                          ? pendingChangesCount > 0 ? 'text-amber-700' : 'text-emerald-700'
                          : 'text-red-600'
                      }`} style={{ fontFamily: 'Inter, sans-serif' }}>
                        {isOnline ? (pendingChangesCount > 0 ? 'Modifications en attente' : 'Synchronisé') : 'Hors ligne'}
                      </span>
                      {pendingChangesCount > 0 && (
                        <span className="ml-2 text-xs bg-amber-200 text-amber-800 px-1.5 py-0.5 rounded-full font-medium">
                          {pendingChangesCount}
                        </span>
                      )}
                    </div>
                  </div>
                  {isOnline && (
                    <button
                      onClick={() => performSync()}
                      disabled={isSyncing}
                      data-testid="sync-button"
                      className={`p-1.5 rounded-md transition-colors ${
                        pendingChangesCount > 0 
                          ? 'text-amber-600 hover:bg-amber-100' 
                          : 'text-emerald-600 hover:bg-emerald-100'
                      } disabled:opacity-50`}
                    >
                      <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} strokeWidth={1.5} />
                    </button>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <div className="text-sm">
                  {isOnline ? (
                    <>
                      <p className="font-medium text-emerald-700">Connecté au serveur</p>
                      {pendingChangesCount > 0 && (
                        <p className="text-amber-600 mt-1">
                          {pendingChangesCount} modification(s) à synchroniser
                        </p>
                      )}
                      {timeSinceSync && (
                        <p className="text-slate-500 mt-1">Dernière sync: {timeSinceSync}</p>
                      )}
                      <p className="text-slate-400 text-xs mt-1">Sync automatique toutes les 15 min</p>
                    </>
                  ) : (
                    <>
                      <p className="font-medium text-red-600">Mode hors ligne actif</p>
                      <p className="text-slate-500 mt-1">
                        Vos modifications sont sauvegardées localement et seront synchronisées au retour en ligne.
                      </p>
                    </>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Offline indicator badge */}
          {!isOnline && (
            <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 rounded-lg border border-amber-100">
              <AlertCircle className="w-4 h-4 text-amber-600" strokeWidth={1.5} />
              <p className="text-xs text-amber-700" style={{ fontFamily: 'Inter, sans-serif' }}>
                Les données seront synchronisées au retour en ligne
              </p>
            </div>
          )}

          {lastSyncTime && isOnline && (
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
      <main className="flex-1 overflow-auto flex flex-col">
        <div className="flex-1 p-8">{children}</div>
        <footer className="py-4 px-8 border-t border-slate-200 bg-white">
          <p className="text-center text-sm text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
            Made by <span className="font-medium text-teal-700">DynSoftware</span>
          </p>
        </footer>
      </main>
    </div>
  );
};

export default Layout;