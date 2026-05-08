import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../contexts/OfflineContext';
import { useCurrentShift, useMarkShiftAlert } from '../hooks/useShifts';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { ShiftAlertModal, CloseShiftModal, OpenShiftModal } from './ShiftModals';
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
  PackagePlus,
  DollarSign,
  CreditCard,
  Wallet,
  Clock,
  Calculator,
  PackageX,
  ClipboardList,
  History,
  Building2,
  Tag,
  Zap,
  ChevronUp,
  ChevronDown,
  Boxes,
  Receipt,
  Menu,
  X,
} from 'lucide-react';
import { Button } from './ui/button';
import Footer from './Footer';
import SyncStatusIndicator from './SyncStatusIndicator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import logoImage from '../images/logo.jpg';
import logoSidebar from '../images/logo-sidebar.png';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isSyncing: isLoginSyncing, syncProgress } = useAuth();
  const { isOnline, isSyncing, performSync, lastSyncTime, pendingChangesCount, getTimeSinceLastSync } = useOffline();
  const { data: currentShift, isLoading: shiftLoading, refetch: refetchShift } = useCurrentShift();
  
  // État pour la modal de blocage de déconnexion
  const [showLogoutBlockedModal, setShowLogoutBlockedModal] = useState(false);
  
  // États pour les modales de shift (globales sur toutes les pages)
  const [showOpenShiftModal, setShowOpenShiftModal] = useState(false);
  const [shiftAlert, setShiftAlert] = useState({ show: false, type: null });
  const [showCloseShiftModal, setShowCloseShiftModal] = useState(false);
  
  // État pour shift expiré - bloque les opérations pour caissier/pharmacien
  const [shiftExpired, setShiftExpired] = useState(false);
  const [showShiftExpiredModal, setShowShiftExpiredModal] = useState(false);
  
  // Afficher la modal d'ouverture de shift si aucun shift n'est ouvert
  // Pour les admins: optionnel (ils peuvent fermer le modal et continuer sans shift)
  // Pour les autres: requis pour effectuer des opérations
  useEffect(() => {
    if (!shiftLoading && !currentShift && isOnline && user) {
      setShowOpenShiftModal(true);
    }
  }, [currentShift, shiftLoading, isOnline, user]);
  
  // Timer pour les alertes de fin de shift - GLOBAL sur toutes les pages
  useEffect(() => {
    if (!currentShift?.expected_end_time) {
      setShiftExpired(false);
      return;
    }
    
    const checkAlerts = () => {
      const now = new Date();
      const endTime = new Date(currentShift.expected_end_time);
      const diffMs = endTime - now;
      const diffMinutes = diffMs / (1000 * 60);
      
      // Alerte fin de shift (priorité la plus haute)
      if (diffMinutes <= 0) {
        // Shift expiré - bloquer les opérations pour caissier/pharmacien
        if (user?.role === 'caissier' || user?.role === 'pharmacien') {
          setShiftExpired(true);
          if (!showShiftExpiredModal && !showCloseShiftModal) {
            setShowShiftExpiredModal(true);
          }
        }
        if (!currentShift.alert_end_shown) {
          setShiftAlert({ show: true, type: 'end' });
        }
      } else {
        setShiftExpired(false);
        // Alerte 5 minutes avant
        if (diffMinutes <= 5 && diffMinutes > 0 && !currentShift.alert_5min_shown) {
          setShiftAlert({ show: true, type: '5min' });
        }
        // Alerte 30 minutes avant
        else if (diffMinutes <= 30 && diffMinutes > 5 && !currentShift.alert_30min_shown) {
          setShiftAlert({ show: true, type: '30min' });
        }
      }
    };
    
    // Vérifier immédiatement
    checkAlerts();
    
    // Vérifier toutes les 10 secondes
    const interval = setInterval(checkAlerts, 10000);
    
    return () => clearInterval(interval);
  }, [currentShift?.expected_end_time, currentShift?.alert_30min_shown, currentShift?.alert_5min_shown, currentShift?.alert_end_shown, user?.role, showShiftExpiredModal, showCloseShiftModal]);
  
  // État pour la sidebar - récupérer depuis localStorage
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved === 'true';
  });
  
  // État pour la sidebar mobile (ouverte/fermée)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Détecter la taille de l'écran
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 768); // < md
      setIsTablet(window.innerWidth >= 768 && window.innerWidth < 1024); // md to lg
    };
    
    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);
  
  // Fermer le menu mobile quand on change de page
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Sauvegarder l'état dans localStorage
  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
  }, [sidebarCollapsed]);
  
  const timeSinceSync = getTimeSinceLastSync();

  // État pour les sections dépliées du menu
  const [expandedSections, setExpandedSections] = useState(() => {
    const saved = localStorage.getItem('menuExpandedSections');
    return saved ? JSON.parse(saved) : { operations: true, stocks: true, finances: true, discounts: true, admin: true };
  });

  // Sauvegarder l'état des sections dans localStorage
  useEffect(() => {
    localStorage.setItem('menuExpandedSections', JSON.stringify(expandedSections));
  }, [expandedSections]);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Structure du menu groupé avec catégories
  const menuStructure = [
    {
      type: 'item',
      path: '/dashboard',
      icon: LayoutDashboard,
      label: 'Tableau de bord',
      roles: ['admin', 'pharmacien', 'caissier'],
    },
    {
      type: 'group',
      id: 'operations',
      icon: Receipt,
      label: 'Opérations',
      roles: ['admin', 'pharmacien', 'caissier'],
      items: [
        { path: '/sales', icon: ShoppingCart, label: 'Ventes', roles: ['admin', 'pharmacien', 'caissier'] },
        { path: '/supplies', icon: PackagePlus, label: 'Approvisionnements', roles: ['admin', 'pharmacien', 'caissier'] },
        { path: '/customers', icon: Users, label: 'Clients', roles: ['admin', 'pharmacien', 'caissier'] },
        { path: '/suppliers', icon: Truck, label: 'Fournisseurs', roles: ['admin', 'pharmacien'] },
        { path: '/prescriptions', icon: FileText, label: 'Ordonnances', roles: ['admin', 'pharmacien'] },
      ],
    },
    {
      type: 'group',
      id: 'stocks',
      icon: Boxes,
      label: 'Stocks',
      roles: ['admin', 'pharmacien', 'caissier'],
      items: [
        { path: '/products', icon: Package, label: 'Produits', roles: ['admin', 'pharmacien'] },
        { path: '/stock-movements', icon: History, label: 'Mouvements', roles: ['admin', 'pharmacien'] },
        { path: '/inventory', icon: ClipboardList, label: 'Inventaire', roles: ['admin'] },
        { path: '/stock-losses', icon: PackageX, label: 'Pertes', roles: ['admin', 'pharmacien', 'caissier'] },
      ],
    },
    {
      type: 'group',
      id: 'finances',
      icon: Wallet,
      label: 'Finances',
      roles: ['admin', 'pharmacien'],
      items: [
        { path: '/reports', icon: BarChart3, label: 'Rapports', roles: ['admin', 'pharmacien'] },
        { path: '/debts', icon: Wallet, label: 'Dettes Clients', roles: ['admin'] },
        { path: '/supplier-debts', icon: Building2, label: 'Dettes Fournisseurs', roles: ['admin'] },
      ],
    },
    {
      type: 'group',
      id: 'discounts',
      icon: Tag,
      label: 'Rabais',
      roles: ['admin'],
      items: [
        { path: '/promo-codes', icon: Tag, label: 'Codes Promo', roles: ['admin'] },
        { path: '/discount-rules', icon: Zap, label: 'Règles', roles: ['admin'] },
        { path: '/discount-history', icon: History, label: 'Historique', roles: ['admin'] },
      ],
    },
    {
      type: 'group',
      id: 'admin',
      icon: Settings,
      label: 'Administration',
      roles: ['admin'],
      items: [
        { path: '/shift-schedules', icon: Calculator, label: 'Planification Shifts', roles: ['admin'] },
        { path: '/shifts', icon: Clock, label: 'Historique Shifts', roles: ['admin'] },
        { path: '/price-management', icon: DollarSign, label: 'Gestion des Prix', roles: ['admin'] },
        { path: '/payment-methods', icon: CreditCard, label: 'Modes de paiement', roles: ['admin'] },
        { path: '/users', icon: UserCog, label: 'Utilisateurs', roles: ['admin'] },
        { path: '/settings', icon: Settings, label: 'Paramètres', roles: ['admin'] },
      ],
    },
  ];

  // Filtrer le menu selon le rôle de l'utilisateur
  const filteredMenu = menuStructure
    .filter(item => item.roles.includes(user?.role || 'caissier'))
    .map(item => {
      if (item.type === 'group') {
        const filteredItems = item.items.filter(subItem => 
          subItem.roles.includes(user?.role || 'caissier')
        );
        return filteredItems.length > 0 ? { ...item, items: filteredItems } : null;
      }
      return item;
    })
    .filter(Boolean);

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
    // Vérifier si un shift est ouvert
    if (currentShift && currentShift.status === 'open') {
      setShowLogoutBlockedModal(true);
      return;
    }
    
    await logout();
    navigate('/login');
  };
  
  const handleGoToSales = () => {
    setShowLogoutBlockedModal(false);
    navigate('/sales');
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Mobile Header avec bouton hamburger - visible uniquement sur mobile */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <button
          onClick={() => setMobileMenuOpen(true)}
          className="p-2 rounded-lg hover:bg-slate-100 text-slate-600"
          data-testid="mobile-menu-button"
        >
          <Menu className="w-6 h-6" />
        </button>
        
        <div className="flex items-center gap-2">
          <img src={logoSidebar} alt="Logo" className="h-8 w-auto" />
        </div>
        
        <div className="flex items-center gap-2">
          {isOnline ? (
            <Wifi className="w-5 h-5 text-green-500" />
          ) : (
            <WifiOff className="w-5 h-5 text-red-500" />
          )}
        </div>
      </div>
      
      {/* Overlay pour fermer le menu mobile */}
      {mobileMenuOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      
      {/* Sidebar Mobile - Drawer qui slide */}
      <aside 
        className={`md:hidden fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-slate-200 flex flex-col transform transition-transform duration-300 ease-in-out ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header de la Sidebar Mobile */}
        <div className="p-4 border-b border-slate-200">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="p-2 rounded-lg hover:bg-slate-100 text-slate-500"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex-1 ml-3">
              <img 
                src={logoSidebar} 
                alt="Logo" 
                className="w-full h-auto object-contain max-w-[120px]"
              />
            </div>
          </div>
          <div className="mt-3">
            <p className="text-sm text-slate-500 truncate">{user?.name}</p>
            <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${getRoleColor(user?.role)}`}>
              {getRoleLabel(user?.role)}
            </span>
          </div>
        </div>

        {/* Navigation Mobile */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {filteredMenu.map((menuItem) => {
            if (menuItem.type === 'item') {
              const Icon = menuItem.icon;
              const isActive = location.pathname === menuItem.path;
              return (
                <Link
                  key={menuItem.path}
                  to={menuItem.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                    isActive ? 'bg-teal-50 text-teal-700 font-medium' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-5 h-5" strokeWidth={1.5} />
                  <span>{menuItem.label}</span>
                </Link>
              );
            }
            if (menuItem.type === 'group') {
              const GroupIcon = menuItem.icon;
              const isExpanded = expandedSections[menuItem.id];
              const hasActiveChild = menuItem.items.some(item => location.pathname === item.path);
              return (
                <div key={menuItem.id} className="space-y-0.5">
                  <button
                    onClick={() => toggleSection(menuItem.id)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg ${
                      hasActiveChild ? 'text-teal-700' : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <GroupIcon className="w-5 h-5" strokeWidth={1.5} />
                      <span className="font-medium">{menuItem.label}</span>
                    </div>
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {isExpanded && (
                    <div className="ml-3 pl-3 border-l-2 border-slate-100 space-y-0.5">
                      {menuItem.items.map(subItem => {
                        const SubIcon = subItem.icon;
                        const isActive = location.pathname === subItem.path;
                        return (
                          <Link
                            key={subItem.path}
                            to={subItem.path}
                            onClick={() => setMobileMenuOpen(false)}
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg ${
                              isActive ? 'bg-teal-50 text-teal-700 font-medium' : 'text-slate-600 hover:bg-slate-50'
                            }`}
                          >
                            <SubIcon className="w-4 h-4" strokeWidth={1.5} />
                            <span className="text-sm">{subItem.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }
            return null;
          })}
        </nav>

        {/* Footer Mobile */}
        <div className="p-4 border-t border-slate-200">
          <Button onClick={handleLogout} variant="outline" className="w-full flex items-center gap-2 justify-center">
            <LogOut className="w-4 h-4" strokeWidth={1.5} />
            Déconnexion
          </Button>
        </div>
      </aside>
      
      {/* Sidebar Desktop - hidden on mobile */}
      <aside 
        className={`hidden md:flex ${
          sidebarCollapsed ? 'w-20' : 'w-64 lg:w-72'
        } bg-white border-r border-slate-200 flex-col transition-all duration-300 ease-in-out`}
      >
        {/* Header de la Sidebar Desktop */}
        <div className={`p-4 border-b border-slate-200 ${sidebarCollapsed ? 'px-2' : 'px-4'}`}>
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <div className="mb-3">
                  <img 
                    src={logoSidebar} 
                    alt="Logo" 
                    className="w-full h-auto object-contain max-w-[130px]"
                  />
                </div>
                <p className="text-sm text-slate-500 truncate">{user?.name}</p>
                <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${getRoleColor(user?.role)}`}>
                  {getRoleLabel(user?.role)}
                </span>
              </div>
            )}
            
            {/* Toggle Button Desktop */}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={toggleSidebar}
                    className={`p-2 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-teal-700 ${sidebarCollapsed ? 'mx-auto' : ''}`}
                  >
                    {sidebarCollapsed ? <PanelLeft className="w-5 h-5" /> : <PanelLeftClose className="w-5 h-5" />}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  {sidebarCollapsed ? 'Afficher le menu' : 'Masquer le menu'}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {/* Collapsed: Show mini logo */}
          {sidebarCollapsed && (
            <div className="mt-3 mx-auto px-1">
              <img src={logoSidebar} alt="Logo" className="w-full h-auto object-contain" />
            </div>
          )}
        </div>

        {/* Navigation Desktop */}
        <nav className={`flex-1 p-2 space-y-1 overflow-y-auto ${sidebarCollapsed ? 'px-2' : 'px-3'}`}>
          {filteredMenu.map((menuItem) => {
            if (menuItem.type === 'item') {
              const Icon = menuItem.icon;
              const isActive = location.pathname === menuItem.path;
              
              if (sidebarCollapsed) {
                return (
                  <TooltipProvider key={menuItem.path}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Link
                          to={menuItem.path}
                          data-testid={`nav-${menuItem.path.substring(1)}`}
                          className={`flex items-center justify-center p-3 rounded-lg ${
                            isActive ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:bg-slate-50'
                          }`}
                        >
                          <Icon className="w-5 h-5" strokeWidth={1.5} />
                        </Link>
                      </TooltipTrigger>
                      <TooltipContent side="right">{menuItem.label}</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                );
              }
              
              return (
                <Link
                  key={menuItem.path}
                  to={menuItem.path}
                  data-testid={`nav-${menuItem.path.substring(1)}`}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg ${
                    isActive ? 'bg-teal-50 text-teal-700 font-medium' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-5 h-5" strokeWidth={1.5} />
                  <span>{menuItem.label}</span>
                </Link>
              );
            }
            
            if (menuItem.type === 'group') {
              const GroupIcon = menuItem.icon;
              const isExpanded = expandedSections[menuItem.id];
              const hasActiveChild = menuItem.items.some(item => location.pathname === item.path);
              
              if (sidebarCollapsed) {
                return (
                  <div key={menuItem.id} className="space-y-1">
                    {menuItem.items.map(subItem => {
                      const SubIcon = subItem.icon;
                      const isActive = location.pathname === subItem.path;
                      return (
                        <TooltipProvider key={subItem.path}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Link
                                to={subItem.path}
                                data-testid={`nav-${subItem.path.substring(1)}`}
                                className={`flex items-center justify-center p-3 rounded-lg ${
                                  isActive ? 'bg-teal-50 text-teal-700' : 'text-slate-600 hover:bg-slate-50'
                                }`}
                              >
                                <SubIcon className="w-5 h-5" strokeWidth={1.5} />
                              </Link>
                            </TooltipTrigger>
                            <TooltipContent side="right">{subItem.label}</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      );
                    })}
                  </div>
                );
              }
              
              return (
                <div key={menuItem.id} className="space-y-0.5">
                  <button
                    onClick={() => toggleSection(menuItem.id)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg ${
                      hasActiveChild ? 'text-teal-700' : 'text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <GroupIcon className="w-5 h-5" strokeWidth={1.5} />
                      <span className="font-medium">{menuItem.label}</span>
                    </div>
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                  {isExpanded && (
                    <div className="ml-3 pl-3 border-l-2 border-slate-100 space-y-0.5">
                      {menuItem.items.map(subItem => {
                        const SubIcon = subItem.icon;
                        const isActive = location.pathname === subItem.path;
                        return (
                          <Link
                            key={subItem.path}
                            to={subItem.path}
                            data-testid={`nav-${subItem.path.substring(1)}`}
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                              isActive ? 'bg-teal-50 text-teal-700 font-medium' : 'text-slate-600 hover:bg-slate-50'
                            }`}
                          >
                            <SubIcon className="w-4 h-4" strokeWidth={1.5} />
                            <span>{subItem.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            }
            return null;
          })}
        </nav>

        {/* Footer Desktop */}
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
          {(sidebarCollapsed && !isMobile) ? (
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
      <main className={`flex-1 overflow-y-auto overflow-x-hidden flex flex-col relative ${isMobile ? 'pt-16' : ''}`}>
        {/* Indicateur de synchronisation non-bloquant - en bas sur mobile, en haut sur desktop */}
        {isLoginSyncing && syncProgress && (
          <div className="fixed bottom-20 md:bottom-auto md:top-4 left-1/2 transform -translate-x-1/2 z-40 animate-in slide-in-from-bottom md:slide-in-from-top duration-300">
            <div className="bg-white px-4 md:px-6 py-2 md:py-3 rounded-full shadow-lg border border-teal-200 flex items-center gap-2 md:gap-3">
              <RefreshCw className="w-4 h-4 md:w-5 md:h-5 text-teal-600 animate-spin" strokeWidth={1.5} />
              <span className="text-xs md:text-sm font-medium text-teal-700" style={{ fontFamily: 'Inter, sans-serif' }}>
                {syncProgress.message || 'Sync...'}
              </span>
            </div>
          </div>
        )}
        
        {/* Overlay de blocage quand shift expiré (caissier/pharmacien) */}
        {shiftExpired && (user?.role === 'caissier' || user?.role === 'pharmacien') && (
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm z-40 flex items-center justify-center">
            <div className="bg-white p-6 rounded-xl shadow-2xl text-center max-w-md mx-4">
              <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-slate-800 mb-2">Shift Expiré</h3>
              <p className="text-slate-600 mb-4">
                Veuillez clôturer votre caisse pour continuer.
              </p>
              <Button
                onClick={() => setShowCloseShiftModal(true)}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                <Calculator className="w-4 h-4 mr-2" />
                Clôturer ma caisse
              </Button>
            </div>
          </div>
        )}
        <div className="flex-1 p-8">{children}</div>
        <Footer />
      </main>

      {/* Indicateur de Shift flottant fixe - Global (centré en haut, sous header mobile) */}
      <div className="fixed top-16 md:top-4 left-1/2 transform -translate-x-1/2 z-40">
        {currentShift ? (
          <div className="flex items-center gap-1 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 bg-green-50 border border-green-200 rounded-full shadow-md">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-xs md:text-sm text-green-700 font-medium">
              {new Date(currentShift.opened_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
              {currentShift.expected_end_time && (
                <span className="text-green-600 hidden sm:inline"> → {new Date(currentShift.expected_end_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>
              )}
            </span>
            <button
              onClick={() => setShowCloseShiftModal(true)}
              className="ml-1 p-1 rounded-full text-amber-700 hover:bg-amber-100 transition-colors"
              title="Clôturer le shift"
            >
              <LogOut className="w-3 h-3 md:w-4 md:h-4" />
            </button>
          </div>
        ) : (
          !shiftLoading && user && user.role !== 'admin' && (
            <div className="flex items-center gap-1 md:gap-2 px-3 md:px-4 py-1.5 md:py-2 bg-amber-50 border border-amber-200 rounded-full shadow-md">
              <AlertCircle className="w-3 h-3 md:w-4 md:h-4 text-amber-600" />
              <span className="text-xs md:text-sm text-amber-700 font-medium">Aucun shift</span>
              <button
                onClick={() => setShowOpenShiftModal(true)}
                className="ml-1 px-2 py-0.5 rounded-full text-xs bg-amber-600 text-white hover:bg-amber-700 transition-colors"
              >
                Ouvrir
              </button>
            </div>
          )
        )}
      </div>
      
      {/* Modal de blocage de déconnexion - Shift ouvert */}
      <Dialog open={showLogoutBlockedModal} onOpenChange={setShowLogoutBlockedModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-700">
              <AlertCircle className="w-5 h-5" />
              Déconnexion impossible
            </DialogTitle>
            <DialogDescription>
              Vous ne pouvez pas vous déconnecter tant que votre shift est ouvert.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
              <div className="flex items-start gap-3">
                <Clock className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">Shift en cours</p>
                  <p className="text-sm text-amber-700 mt-1">
                    Veuillez clôturer votre caisse avant de vous déconnecter. 
                    Cela garantit un suivi correct des transactions.
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setShowLogoutBlockedModal(false)}
            >
              Annuler
            </Button>
            <Button
              onClick={handleGoToSales}
              className="bg-teal-600 hover:bg-teal-700"
              data-testid="go-to-close-shift-btn"
            >
              <Calculator className="w-4 h-4 mr-2" />
              Aller clôturer ma caisse
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Modal de blocage - Shift expiré (caissier/pharmacien uniquement) */}
      <Dialog open={showShiftExpiredModal} onOpenChange={() => {}}>
        <DialogContent className="max-w-md bg-red-50 border-red-400 border-2">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-red-800">
              <AlertCircle className="w-6 h-6 text-red-600 animate-pulse" />
              Shift Expiré - Action Requise
            </DialogTitle>
          </DialogHeader>
          
          <div className="py-4 space-y-4">
            <p className="text-red-700 font-medium">
              Votre shift est terminé. Vous devez clôturer votre caisse avant de pouvoir continuer à utiliser l'application.
            </p>
            <div className="p-3 bg-red-100 rounded-lg border border-red-200">
              <p className="text-red-800 text-sm">
                <strong>Toutes les opérations sont bloquées</strong> jusqu'à la clôture de votre shift.
              </p>
            </div>
            {currentShift?.expected_end_time && (
              <div className="flex items-center gap-2 text-slate-600 text-sm">
                <Clock className="w-4 h-4" />
                <span>
                  Heure de fin prévue: <strong>
                    {new Date(currentShift.expected_end_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                  </strong>
                </span>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button
              onClick={() => {
                setShowShiftExpiredModal(false);
                setShowCloseShiftModal(true);
              }}
              className="w-full bg-red-600 hover:bg-red-700 text-white"
              data-testid="close-expired-shift-btn"
            >
              <Calculator className="w-4 h-4 mr-2" />
              Clôturer ma caisse maintenant
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Modal d'alerte de fin de shift - GLOBAL sur toutes les pages */}
      <ShiftAlertModal
        isOpen={shiftAlert.show}
        alertType={shiftAlert.type}
        expectedEndTime={currentShift?.expected_end_time}
        onClose={() => {
          setShiftAlert({ show: false, type: null });
          refetchShift();
        }}
        onCloseShift={() => {
          setShiftAlert({ show: false, type: null });
          setShowCloseShiftModal(true);
        }}
      />
      
      {/* Modal d'ouverture de shift - GLOBAL sur toutes les pages */}
      <OpenShiftModal
        isOpen={showOpenShiftModal}
        onClose={() => setShowOpenShiftModal(false)}
        onSuccess={() => refetchShift()}
      />
      
      {/* Modal de clôture de shift (depuis alerte) */}
      <CloseShiftModal
        isOpen={showCloseShiftModal}
        onClose={() => {
          setShowCloseShiftModal(false);
          // Réafficher le modal de blocage si le shift est toujours expiré et non clôturé
          if (shiftExpired && currentShift) {
            setTimeout(() => setShowShiftExpiredModal(true), 500);
          }
        }}
        onSuccess={() => {
          setShiftExpired(false);
          setShowShiftExpiredModal(false);
          refetchShift();
        }}
      />
    </div>
  );
};

export default Layout;
