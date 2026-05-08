import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Settings as SettingsIcon, Save, Package, Calculator, Building2, Coins, RotateCcw, Clock, Calendar, AlertTriangle, Wifi, WifiOff, Cloud, CloudOff, RefreshCw, Download, Database, CheckCircle, Loader2, Users, Smartphone, Timer, Bell } from 'lucide-react';
import { useSettingsQuery, useUpdateSettings, useStockValuation } from '../hooks';
import { useSettings } from '../contexts/SettingsContext';
import { useOffline } from '../contexts/OfflineContext';
import { formatCurrency } from '../services/currencyService';
import { preloadDataForOffline, getOfflineStats } from '../services/offlineOperations';
import { getStoreCounts, clearLocalChanges } from '../services/indexedDB';
import { toast } from 'sonner';
import OfflineIndicator from '../components/OfflineIndicator';
import SyncQueuePanel from '../components/SyncQueuePanel';

const Settings = () => {
  const { refreshSettings } = useSettings();
  const { isOnline, isSyncing, performSync, forceFullSync, pendingChangesCount, lastSyncTime, getTimeSinceLastSync } = useOffline();
  
  // React Query hooks
  const { data: settingsData, isLoading, isError } = useSettingsQuery();
  const { data: stockValuation } = useStockValuation();
  const updateSettings = useUpdateSettings();
  
  // Local state for form
  const [localSettings, setLocalSettings] = useState({
    stock_valuation_method: 'fefo',
    currency: 'GNF',
    pharmacy_name: '',
    low_stock_threshold: 10,
    default_min_stock: 10,
    return_delay_days: 3,
    expiration_alert_days: 30,
    top_debt_customers_count: 10,
    debt_overdue_days: 90,
    orange_money_default_phone: '',
    mtn_money_default_phone: '',
    default_shift_duration_hours: 8,
    timezone: 'Africa/Conakry',
  });
  
  const [offlineStats, setOfflineStats] = useState(null);
  const [storeCounts, setStoreCounts] = useState(null);
  const [preloading, setPreloading] = useState(false);
  const [preloadProgress, setPreloadProgress] = useState(null);

  // Sync local state when settings data loads
  useEffect(() => {
    if (settingsData) {
      setLocalSettings({
        stock_valuation_method: settingsData.stock_valuation_method || 'fefo',
        currency: settingsData.currency || 'GNF',
        pharmacy_name: settingsData.pharmacy_name || '',
        low_stock_threshold: settingsData.low_stock_threshold || 10,
        default_min_stock: settingsData.default_min_stock || 10,
        return_delay_days: settingsData.return_delay_days || 3,
        expiration_alert_days: settingsData.expiration_alert_days || 30,
        top_debt_customers_count: settingsData.top_debt_customers_count || 10,
        debt_overdue_days: settingsData.debt_overdue_days || 90,
        orange_money_default_phone: settingsData.orange_money_default_phone || '',
        mtn_money_default_phone: settingsData.mtn_money_default_phone || '',
        default_shift_duration_hours: settingsData.default_shift_duration_hours || 8,
        timezone: settingsData.timezone || 'Africa/Conakry',
      });
    }
  }, [settingsData]);

  useEffect(() => {
    loadOfflineStats();
  }, []);

  const loadOfflineStats = async () => {
    try {
      const stats = await getOfflineStats();
      const counts = await getStoreCounts();
      setOfflineStats(stats);
      setStoreCounts(counts);
    } catch (error) {
      console.error('Error loading offline stats:', error);
    }
  };

  const handlePreloadData = async () => {
    setPreloading(true);
    setPreloadProgress({ current: 0, total: 5, store: 'Initialisation...' });
    
    try {
      const results = await preloadDataForOffline((progress) => {
        setPreloadProgress(progress);
      });
      
      let totalItems = 0;
      let failedStores = [];
      
      for (const [store, result] of Object.entries(results)) {
        if (result.success) {
          totalItems += result.count;
        } else {
          failedStores.push(store);
        }
      }
      
      if (failedStores.length === 0) {
        toast.success('Données préchargées avec succès', {
          description: `${totalItems} éléments mis en cache pour le mode hors ligne`
        });
      } else {
        toast.warning('Préchargement partiel', {
          description: `Échec pour: ${failedStores.join(', ')}`
        });
      }
      
      await loadOfflineStats();
    } catch (error) {
      toast.error('Erreur de préchargement', {
        description: error.message
      });
    } finally {
      setPreloading(false);
      setPreloadProgress(null);
    }
  };

  const handleClearPendingChanges = async () => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer toutes les modifications en attente ? Cette action est irréversible.')) {
      try {
        await clearLocalChanges();
        toast.success('Modifications en attente supprimées');
        await loadOfflineStats();
      } catch (error) {
        toast.error('Erreur lors de la suppression');
      }
    }
  };

  const handleSave = () => {
    updateSettings.mutate(localSettings, {
      onSuccess: () => {
        refreshSettings();
      },
    });
  };

  const getMethodLabel = (method) => {
    switch (method) {
      case 'fifo': return 'FIFO (Premier Entré, Premier Sorti)';
      case 'lifo': return 'LIFO (Dernier Entré, Premier Sorti)';
      case 'fefo': return 'FEFO (Premier Périmé, Premier Sorti)';
      case 'weighted_average': return 'CMP (Coût Moyen Pondéré)';
      default: return method;
    }
  };

  const getMethodDescription = (method) => {
    switch (method) {
      case 'fifo':
        return 'Les premiers articles achetés sont considérés comme les premiers vendus. Prix = lot le plus ancien.';
      case 'lifo':
        return 'Les derniers articles achetés sont considérés comme les premiers vendus. Prix = lot le plus récent.';
      case 'fefo':
        return 'Les articles avec la date de péremption la plus proche sont vendus en premier. Recommandé pour les pharmacies.';
      case 'weighted_average':
        return 'Le coût moyen pondéré de tous les lots en stock est calculé. Méthode comptable standard.';
      default:
        return '';
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
        </div>
      </Layout>
    );
  }

  if (isError) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <p className="text-red-500">Erreur lors du chargement des paramètres</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="settings-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Paramètres
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Configuration de la pharmacie
            </p>
          </div>
          <Button 
            onClick={handleSave} 
            disabled={updateSettings.isPending} 
            className="bg-teal-600 hover:bg-teal-700"
          >
            {updateSettings.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Save className="w-4 h-4 mr-2" strokeWidth={1.5} />
            )}
            {updateSettings.isPending ? 'Enregistrement...' : 'Enregistrer'}
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Paramètres généraux */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-teal-50 rounded-lg">
                <Building2 className="w-5 h-5 text-teal-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Informations générales
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="pharmacy_name">Nom de la pharmacie</Label>
                <Input
                  id="pharmacy_name"
                  value={localSettings.pharmacy_name}
                  onChange={(e) => setLocalSettings({ ...localSettings, pharmacy_name: e.target.value })}
                  placeholder="Ma Pharmacie"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="currency">Devise</Label>
                <Select 
                  value={localSettings.currency} 
                  onValueChange={(value) => setLocalSettings({ ...localSettings, currency: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">Dollar US ($)</SelectItem>
                    <SelectItem value="CAD">Dollar CAD ($ CAD)</SelectItem>
                    <SelectItem value="EUR">Euro (€)</SelectItem>
                    <SelectItem value="XOF">Franc CFA (FCFA)</SelectItem>
                    <SelectItem value="GNF">Franc Guinéen (GNF)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="low_stock_threshold">Seuil d'alerte stock bas</Label>
                <Input
                  id="low_stock_threshold"
                  type="number"
                  min="1"
                  value={localSettings.low_stock_threshold}
                  onChange={(e) => setLocalSettings({ ...localSettings, low_stock_threshold: parseInt(e.target.value) || 10 })}
                  className="mt-1"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Alerte affichée quand le stock d'un produit est en dessous de ce seuil
                </p>
              </div>

              <div>
                <Label htmlFor="default_min_stock">Stock minimum par défaut</Label>
                <Input
                  id="default_min_stock"
                  type="number"
                  min="0"
                  value={localSettings.default_min_stock}
                  onChange={(e) => setLocalSettings({ ...localSettings, default_min_stock: parseInt(e.target.value) || 10 })}
                  className="mt-1"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Stock minimum appliqué aux nouveaux produits (peut être surchargé par catégorie)
                </p>
              </div>
            </div>
          </div>

          {/* Politique de retours */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-amber-50 rounded-lg">
                <RotateCcw className="w-5 h-5 text-amber-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Politique de retours
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="return_delay_days">Délai maximum pour les retours (jours)</Label>
                <div className="flex items-center gap-3 mt-1">
                  <Input
                    id="return_delay_days"
                    type="number"
                    min="0"
                    max="365"
                    value={localSettings.return_delay_days}
                    onChange={(e) => setLocalSettings({ ...localSettings, return_delay_days: parseInt(e.target.value) || 3 })}
                    className="w-24"
                  />
                  <span className="text-slate-600">jour(s)</span>
                </div>
              </div>

              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-start gap-3">
                  <Clock className="w-5 h-5 text-amber-600 mt-0.5" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      Règle actuelle
                    </p>
                    <p className="text-sm text-amber-700 mt-1">
                      {localSettings.return_delay_days === 0 
                        ? "Les retours sont désactivés (délai de 0 jour)."
                        : localSettings.return_delay_days === 1
                          ? "Les retours sont autorisés uniquement le jour même de la vente."
                          : `Les retours sont autorisés jusqu'à ${localSettings.return_delay_days} jours après la vente.`
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Alertes de péremption */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-red-50 rounded-lg">
                <Calendar className="w-5 h-5 text-red-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Alertes de péremption
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="expiration_alert_days">Délai d'alerte avant péremption (jours)</Label>
                <div className="flex items-center gap-3 mt-1">
                  <Input
                    id="expiration_alert_days"
                    type="number"
                    min="1"
                    max="365"
                    value={localSettings.expiration_alert_days}
                    onChange={(e) => setLocalSettings({ ...localSettings, expiration_alert_days: parseInt(e.target.value) || 30 })}
                    className="w-24"
                  />
                  <span className="text-slate-600">jour(s) avant la date de péremption</span>
                </div>
              </div>

              <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium text-red-800">
                      Notification active
                    </p>
                    <p className="text-sm text-red-700 mt-1">
                      Les produits dont la date de péremption est dans les <strong>{localSettings.expiration_alert_days} prochains jours</strong> seront mis en évidence dans la liste des produits et le tableau de bord.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Paramètres de gestion des dettes */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-red-50 rounded-lg">
                <Users className="w-5 h-5 text-red-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Gestion des dettes
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="top_debt_customers_count">Nombre de clients dans "Top Clients Endettés"</Label>
                <div className="flex items-center gap-3 mt-1">
                  <Input
                    id="top_debt_customers_count"
                    type="number"
                    min="1"
                    max="50"
                    value={localSettings.top_debt_customers_count}
                    onChange={(e) => setLocalSettings({ ...localSettings, top_debt_customers_count: parseInt(e.target.value) || 10 })}
                    className="w-24"
                  />
                  <span className="text-sm text-slate-600">clients</span>
                </div>
                <p className="text-sm text-slate-500 mt-2">
                  Définit le nombre maximum de clients affichés dans la section "Top Clients Endettés" du tableau de bord des dettes.
                </p>
              </div>

              <div>
                <Label htmlFor="debt_overdue_days">Délai avant qu'une dette soit considérée en retard</Label>
                <div className="flex items-center gap-3 mt-1">
                  <Input
                    id="debt_overdue_days"
                    type="number"
                    min="1"
                    max="365"
                    value={localSettings.debt_overdue_days}
                    onChange={(e) => setLocalSettings({ ...localSettings, debt_overdue_days: parseInt(e.target.value) || 90 })}
                    className="w-24"
                  />
                  <span className="text-sm text-slate-600">jours</span>
                </div>
                <p className="text-sm text-slate-500 mt-2">
                  Si une dette n'a pas de date d'échéance définie, elle sera automatiquement considérée "en retard" après ce délai.
                </p>
              </div>

              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      Règle de calcul des dettes en retard
                    </p>
                    <p className="text-sm text-amber-700 mt-1">
                      Une dette est considérée "en retard" si :<br/>
                      • Elle a une date d'échéance définie ET cette date est dépassée, OU<br/>
                      • Elle n'a pas de date d'échéance ET a été créée il y a plus de <strong>{localSettings.debt_overdue_days} jours</strong>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Paramètres Gestion des Shifts */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-teal-50 rounded-lg">
                <Clock className="w-5 h-5 text-teal-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Gestion des Shifts de Caisse
              </h2>
            </div>

            <div className="space-y-4">
              <p className="text-sm text-slate-600">
                Configurez la durée par défaut des shifts de caisse. Cette durée sera utilisée si le caissier ne spécifie pas d'heure de fin lors de l'ouverture.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="default_shift_duration_hours" className="flex items-center gap-2">
                    <Timer className="w-4 h-4 text-teal-600" />
                    Durée par défaut du shift (heures)
                  </Label>
                  <Input
                    id="default_shift_duration_hours"
                    type="number"
                    min="1"
                    max="24"
                    value={localSettings.default_shift_duration_hours}
                    onChange={(e) => setLocalSettings({ ...localSettings, default_shift_duration_hours: parseInt(e.target.value) || 8 })}
                    className="mt-1 w-32"
                  />
                </div>
                
                <div>
                  <Label htmlFor="timezone" className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-teal-600" />
                    Fuseau horaire
                  </Label>
                  <Select
                    value={localSettings.timezone}
                    onValueChange={(value) => setLocalSettings({ ...localSettings, timezone: value })}
                  >
                    <SelectTrigger className="mt-1 w-full" id="timezone">
                      <SelectValue placeholder="Sélectionner le fuseau horaire" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Africa/Conakry">Guinée (GMT+0)</SelectItem>
                      <SelectItem value="Africa/Dakar">Sénégal (GMT+0)</SelectItem>
                      <SelectItem value="Africa/Abidjan">Côte d'Ivoire (GMT+0)</SelectItem>
                      <SelectItem value="Africa/Bamako">Mali (GMT+0)</SelectItem>
                      <SelectItem value="Africa/Lagos">Nigeria (GMT+1)</SelectItem>
                      <SelectItem value="Africa/Douala">Cameroun (GMT+1)</SelectItem>
                      <SelectItem value="Europe/Paris">France (GMT+1)</SelectItem>
                      <SelectItem value="America/New_York">New York (GMT-5)</SelectItem>
                      <SelectItem value="America/Bogota">Bogota (GMT-5)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-500 mt-1">
                    Utilisé pour vérifier les horaires de planification des shifts
                  </p>
                </div>
              </div>

              <div className="p-4 bg-teal-50 rounded-lg border border-teal-200">
                <div className="flex items-start gap-3">
                  <Bell className="w-5 h-5 text-teal-600 mt-0.5" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium text-teal-800">
                      Alertes automatiques
                    </p>
                    <p className="text-sm text-teal-700 mt-1">
                      Les caissiers recevront des alertes popup:<br/>
                      • 30 minutes avant la fin du shift<br/>
                      • 5 minutes avant la fin du shift<br/>
                      • À l'heure de fin (avec bouton de clôture)
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Paramètres Mobile Money OTP */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-orange-50 rounded-lg">
                <Smartphone className="w-5 h-5 text-orange-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Paiements Mobile Money (OTP)
              </h2>
            </div>

            <div className="space-y-4">
              <p className="text-sm text-slate-600">
                Ces numéros seront utilisés par défaut pour la vérification OTP lorsqu'un client n'a pas de numéro de téléphone enregistré.
              </p>
              
              <div>
                <Label htmlFor="orange_money_default_phone" className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-orange-500"></span>
                  Numéro par défaut Orange Money
                </Label>
                <Input
                  id="orange_money_default_phone"
                  type="tel"
                  value={localSettings.orange_money_default_phone}
                  onChange={(e) => setLocalSettings({ ...localSettings, orange_money_default_phone: e.target.value })}
                  placeholder="Ex: +224 628 00 00 00"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="mtn_money_default_phone" className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                  Numéro par défaut MTN Money
                </Label>
                <Input
                  id="mtn_money_default_phone"
                  type="tel"
                  value={localSettings.mtn_money_default_phone}
                  onChange={(e) => setLocalSettings({ ...localSettings, mtn_money_default_phone: e.target.value })}
                  placeholder="Ex: +224 621 00 00 00"
                  className="mt-1"
                />
              </div>

              <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                <div className="flex items-start gap-3">
                  <Smartphone className="w-5 h-5 text-orange-600 mt-0.5" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium text-orange-800">
                      Priorité du numéro OTP
                    </p>
                    <p className="text-sm text-orange-700 mt-1">
                      1. Numéro du client sélectionné (si disponible)<br/>
                      2. Numéro par défaut configuré ici (si le client n'a pas de numéro)
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Méthode de valorisation du stock */}
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-amber-50 rounded-lg">
                <Calculator className="w-5 h-5 text-amber-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Méthode de valorisation du stock
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <Label>Méthode de calcul</Label>
                <Select 
                  value={localSettings.stock_valuation_method} 
                  onValueChange={(value) => setLocalSettings({ ...localSettings, stock_valuation_method: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fefo">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">FEFO</span>
                        <span className="text-slate-500">- Premier Périmé, Premier Sorti ⭐</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="fifo">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">FIFO</span>
                        <span className="text-slate-500">- Premier Entré, Premier Sorti</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="lifo">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">LIFO</span>
                        <span className="text-slate-500">- Dernier Entré, Premier Sorti</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="weighted_average">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">CMP</span>
                        <span className="text-slate-500">- Coût Moyen Pondéré</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-700 mb-1">
                  {getMethodLabel(localSettings.stock_valuation_method)}
                </p>
                <p className="text-sm text-slate-600">
                  {getMethodDescription(localSettings.stock_valuation_method)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Section PWA / Mode Hors Ligne */}
        <div className="p-6 rounded-xl bg-white border border-slate-100">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-blue-50 rounded-lg">
              {isOnline ? (
                <Wifi className="w-5 h-5 text-blue-600" strokeWidth={1.5} />
              ) : (
                <WifiOff className="w-5 h-5 text-red-600" strokeWidth={1.5} />
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Mode Hors Ligne (PWA)
              </h2>
              <p className="text-sm text-slate-500">
                Gérez la synchronisation et les données hors ligne
              </p>
            </div>
          </div>

          {/* Statut de connexion */}
          <OfflineIndicator showDetails={true} className="mb-6" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Statistiques des données locales */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
                <Database className="w-4 h-4" />
                Données en cache local
              </h3>
              
              {storeCounts && (
                <div className="space-y-2">
                  {Object.entries(storeCounts).map(([store, counts]) => (
                    <div key={store} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <span className="text-sm text-slate-700 capitalize">
                        {store === 'products' ? 'Produits' :
                         store === 'categories' ? 'Catégories' :
                         store === 'customers' ? 'Clients' :
                         store === 'suppliers' ? 'Fournisseurs' :
                         store === 'sales' ? 'Ventes' :
                         store === 'supplies' ? 'Approvisionnements' :
                         store === 'returns' ? 'Retours' :
                         store === 'units' ? 'Unités' :
                         store === 'prescriptions' ? 'Ordonnances' :
                         store}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-900">{counts.total}</span>
                        {counts.unsynced > 0 && (
                          <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                            {counts.unsynced} non sync
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Modifications en attente */}
              {offlineStats && offlineStats.totalPending > 0 && (
                <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-amber-800">
                      Modifications en attente
                    </span>
                    <span className="text-lg font-bold text-amber-900">
                      {offlineStats.totalPending}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(offlineStats.byType).map(([type, count]) => (
                      <span key={type} className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded">
                        {type}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-slate-700 flex items-center gap-2">
                <RefreshCw className="w-4 h-4" />
                Actions de synchronisation
              </h3>

              <div className="space-y-3">
                {/* Précharger les données */}
                <Button
                  onClick={handlePreloadData}
                  disabled={preloading || !isOnline}
                  variant="outline"
                  className="w-full justify-start gap-2"
                >
                  {preloading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      {preloadProgress 
                        ? `${preloadProgress.store} (${preloadProgress.current}/${preloadProgress.total})`
                        : 'Préchargement...'}
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Précharger les données pour le mode hors ligne
                    </>
                  )}
                </Button>

                {/* Synchroniser maintenant */}
                <Button
                  onClick={() => performSync()}
                  disabled={isSyncing || !isOnline}
                  variant="outline"
                  className="w-full justify-start gap-2"
                >
                  {isSyncing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Synchronisation en cours...
                    </>
                  ) : (
                    <>
                      <Cloud className="w-4 h-4" />
                      Synchroniser maintenant
                    </>
                  )}
                </Button>

                {/* Synchronisation complète */}
                <Button
                  onClick={() => forceFullSync()}
                  disabled={isSyncing || !isOnline}
                  variant="outline"
                  className="w-full justify-start gap-2"
                >
                  <Database className="w-4 h-4" />
                  Synchronisation complète (re-télécharger tout)
                </Button>

                {/* Supprimer les modifications en attente */}
                {pendingChangesCount > 0 && (
                  <Button
                    onClick={handleClearPendingChanges}
                    variant="outline"
                    className="w-full justify-start gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <CloudOff className="w-4 h-4" />
                    Supprimer les modifications en attente ({pendingChangesCount})
                  </Button>
                )}
              </div>

              {/* Dernière synchronisation */}
              {lastSyncTime && (
                <div className="flex items-center gap-2 text-sm text-slate-500 mt-4">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Dernière synchronisation: {getTimeSinceLastSync()}</span>
                </div>
              )}

              {/* Info mode offline */}
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200 mt-4">
                <p className="text-sm text-blue-800">
                  <strong>Mode hors ligne activé</strong>
                </p>
                <ul className="text-sm text-blue-700 mt-2 space-y-1 list-disc list-inside">
                  <li>Les données sont automatiquement mises en cache</li>
                  <li>Vous pouvez créer des ventes même sans connexion</li>
                  <li>Les modifications sont synchronisées au retour en ligne</li>
                  <li>Synchronisation automatique toutes les 15 minutes</li>
                </ul>
              </div>
            </div>
          </div>

          {/* File de synchronisation détaillée */}
          <SyncQueuePanel className="mt-6" />
        </div>
      </div>
    </Layout>
  );
};

export default Settings;
