import React, { useState, useEffect } from 'react';
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
  PanelLeftClose,
  PanelLeft,
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
  
  // État pour la sidebar - récupérer depuis localStorage
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved === 'true';
  });

  // Sauvegarder l'état dans localStorage
  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
  }, [sidebarCollapsed]);
  
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
    { path: '/settings', icon: Settings, label: 'Paramètres', roles: ['admin'] },
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

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside 
        className={`${
          sidebarCollapsed ? 'w-20' : 'w-64'
        } bg-white border-r border-slate-200 flex flex-col transition-all duration-300 ease-in-out`}
      >
        {/* Header */}
        <div className={`p-4 border-b border-slate-200 ${sidebarCollapsed ? 'px-2' : 'px-6'}`}>
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold text-teal-700 truncate" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  DynSoft Pharma
                </h1>
                <p className="text-sm text-slate-500 mt-1 truncate" style={{ fontFamily: 'Inter, sans-serif' }}>
                  {user?.name}
                </p>
                <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${getRoleColor(user?.role)}`}>
                  {getRoleLabel(user?.role)}
                </span>
              </div>
            )}
            
            {/* Toggle Button */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={toggleSidebar}
                    className={`p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-teal-700 transition-colors ${
                      sidebarCollapsed ? 'mx-auto' : ''
                    }`}
                  >
                    {sidebarCollapsed ? (
                      <PanelLeft className="w-5 h-5" strokeWidth={1.5} />
                    ) : (
                      <PanelLeftClose className="w-5 h-5" strokeWidth={1.5} />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  {sidebarCollapsed ? 'Afficher le menu' : 'Masquer le menu'}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {/* Collapsed: Show avatar/initials */}
          {sidebarCollapsed && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="mt-3 mx-auto w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                    <span className="text-teal-700 font-semibold text-sm">
                      {user?.name?.charAt(0)?.toUpperCase() || 'U'}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <div>
                    <p className="font-medium">{user?.name}</p>
                    <p className={`text-xs ${getRoleColor(user?.role)} px-1 rounded inline-block mt-1`}>
                      {getRoleLabel(user?.role)}
                    </p>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Navigation */}
        <nav className={`flex-1 p-2 space-y-1 ${sidebarCollapsed ? 'px-2' : 'px-4'}`}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            if (sidebarCollapsed) {
              return (
                <TooltipProvider key={item.path}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link
                        to={item.path}
                        data-testid={`nav-${item.path.substring(1)}`}
                        className={`flex items-center justify-center p-3 rounded-lg transition-all ${
                          isActive
                            ? 'bg-teal-50 text-teal-700'
                            : 'text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <Icon className="w-5 h-5" strokeWidth={1.5} />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      {item.label}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              );
            }
            
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

        {/* Footer */}
        <div className={`p-2 border-t border-slate-200 space-y-2 ${sidebarCollapsed ? 'px-2' : 'px-4'}`}>
          {/* Sync Status */}
          {sidebarCollapsed ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => isOnline && performSync()}
                    disabled={isSyncing || !isOnline}
                    className={`w-full flex items-center justify-center p-3 rounded-lg transition-colors ${
                      isOnline 
                        ? pendingChangesCount > 0 
                          ? 'bg-amber-50 text-amber-600 hover:bg-amber-100' 
                          : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
                        : 'bg-red-50 text-red-500'
                    }`}
                  >
                    {isSyncing ? (
                      <RefreshCw className="w-5 h-5 animate-spin" strokeWidth={1.5} />
                    ) : isOnline ? (
                      pendingChangesCount > 0 ? (
                        <div className="relative">
                          <Cloud className="w-5 h-5" strokeWidth={1.5} />
                          <span className="absolute -top-1 -right-1 w-2 h-2 bg-amber-500 rounded-full"></span>
                        </div>
                      ) : (
                        <Cloud className="w-5 h-5" strokeWidth={1.5} />
                      )
                    ) : (
                      <CloudOff className="w-5 h-5" strokeWidth={1.5} />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <div className="text-sm">
                    {isOnline ? (
                      pendingChangesCount > 0 ? (
                        <p>{pendingChangesCount} modification(s) en attente</p>
                      ) : (
                        <p>Synchronisé</p>
                      )
                    ) : (
                      <p>Hors ligne</p>
                    )}
                    {timeSinceSync && <p className="text-xs text-slate-400 mt-1">Dernière sync: {timeSinceSync}</p>}
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <>
              {/* Full Sync Status */}
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
            </>
          )}

          {/* Logout Button */}
          {sidebarCollapsed ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleLogout}
                    data-testid="logout-button"
                    className="w-full flex items-center justify-center p-3 rounded-lg text-slate-600 hover:bg-red-50 hover:text-red-600 transition-colors"
                  >
                    <LogOut className="w-5 h-5" strokeWidth={1.5} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  Déconnexion
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <Button
              onClick={handleLogout}
              data-testid="logout-button"
              variant="outline"
              className="w-full flex items-center gap-2 justify-center"
            >
              <LogOut className="w-4 h-4" strokeWidth={1.5} />
              Déconnexion
            </Button>
          )}
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
