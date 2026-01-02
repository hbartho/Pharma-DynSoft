import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Settings as SettingsIcon, Save, Package, Calculator, Building2, Coins, RotateCcw, Clock, Calendar, AlertTriangle, Wifi, WifiOff, Cloud, CloudOff, RefreshCw, Download, Database, CheckCircle } from 'lucide-react';
import api from '../services/api';
import { useSettings } from '../contexts/SettingsContext';
import { useOffline } from '../contexts/OfflineContext';
import { formatCurrency } from '../services/currencyService';
import { preloadDataForOffline, getOfflineStats } from '../services/offlineOperations';
import { getStoreCounts, clearLocalChanges } from '../services/indexedDB';
import { toast } from 'sonner';
import OfflineIndicator from '../components/OfflineIndicator';

const Settings = () => {
  const { refreshSettings } = useSettings();
  const { isOnline, isSyncing, performSync, forceFullSync, pendingChangesCount, lastSyncTime, getTimeSinceLastSync } = useOffline();
  const [settings, setSettings] = useState({
    stock_valuation_method: 'weighted_average',
    currency: 'GNF',
    pharmacy_name: '',
    low_stock_threshold: 10,
    return_delay_days: 3,
    expiration_alert_days: 30,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [stockValuation, setStockValuation] = useState(null);
  const [offlineStats, setOfflineStats] = useState(null);
  const [storeCounts, setStoreCounts] = useState(null);
  const [preloading, setPreloading] = useState(false);
  const [preloadProgress, setPreloadProgress] = useState(null);

  useEffect(() => {
    loadSettings();
    loadStockValuation();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await api.get('/settings');
      setSettings({
        stock_valuation_method: response.data.stock_valuation_method || 'weighted_average',
        currency: response.data.currency || 'EUR',
        pharmacy_name: response.data.pharmacy_name || '',
        low_stock_threshold: response.data.low_stock_threshold || 10,
        return_delay_days: response.data.return_delay_days || 3,
        expiration_alert_days: response.data.expiration_alert_days || 30,
      });
    } catch (error) {
      console.error('Error loading settings:', error);
      toast.error('Erreur lors du chargement des paramètres');
    } finally {
      setLoading(false);
    }
  };

  const loadStockValuation = async () => {
    try {
      const response = await api.get('/stock/valuation');
      setStockValuation(response.data);
    } catch (error) {
      console.error('Error loading stock valuation:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/settings', settings);
      toast.success('Paramètres enregistrés avec succès');
      // Rafraîchir le contexte global des settings
      refreshSettings();
      // Recharger la valorisation avec la nouvelle méthode et devise
      await loadStockValuation();
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('Erreur lors de l\'enregistrement des paramètres');
    } finally {
      setSaving(false);
    }
  };

  const getMethodLabel = (method) => {
    switch (method) {
      case 'fifo': return 'FIFO (Premier Entré, Premier Sorti)';
      case 'lifo': return 'LIFO (Dernier Entré, Premier Sorti)';
      case 'weighted_average': return 'Moyenne Pondérée';
      default: return method;
    }
  };

  const getMethodDescription = (method) => {
    switch (method) {
      case 'fifo':
        return 'Les premiers articles achetés sont considérés comme les premiers vendus. Recommandé pour les produits périssables.';
      case 'lifo':
        return 'Les derniers articles achetés sont considérés comme les premiers vendus. Peut réduire les bénéfices imposables en période d\'inflation.';
      case 'weighted_average':
        return 'Le coût moyen de tous les articles en stock est calculé. Méthode simple et couramment utilisée.';
      default:
        return '';
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
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
          <Button onClick={handleSave} disabled={saving} className="bg-teal-600 hover:bg-teal-700">
            <Save className="w-4 h-4 mr-2" strokeWidth={1.5} />
            {saving ? 'Enregistrement...' : 'Enregistrer'}
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
                  value={settings.pharmacy_name}
                  onChange={(e) => setSettings({ ...settings, pharmacy_name: e.target.value })}
                  placeholder="Ma Pharmacie"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="currency">Devise</Label>
                <Select 
                  value={settings.currency} 
                  onValueChange={(value) => setSettings({ ...settings, currency: value })}
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
                  value={settings.low_stock_threshold}
                  onChange={(e) => setSettings({ ...settings, low_stock_threshold: parseInt(e.target.value) || 10 })}
                  className="mt-1"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Alerte affichée quand le stock d'un produit est en dessous de ce seuil
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
                    value={settings.return_delay_days}
                    onChange={(e) => setSettings({ ...settings, return_delay_days: parseInt(e.target.value) || 3 })}
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
                      {settings.return_delay_days === 0 
                        ? "Les retours sont désactivés (délai de 0 jour)."
                        : settings.return_delay_days === 1
                          ? "Les retours sont autorisés uniquement le jour même de la vente."
                          : `Les retours sont autorisés jusqu'à ${settings.return_delay_days} jours après la vente.`
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
                    value={settings.expiration_alert_days}
                    onChange={(e) => setSettings({ ...settings, expiration_alert_days: parseInt(e.target.value) || 30 })}
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
                      Les produits dont la date de péremption est dans les <strong>{settings.expiration_alert_days} prochains jours</strong> seront mis en évidence dans la liste des produits et le tableau de bord.
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
                  value={settings.stock_valuation_method} 
                  onValueChange={(value) => setSettings({ ...settings, stock_valuation_method: value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
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
                        <span className="font-medium">Moyenne Pondérée</span>
                        <span className="text-slate-500">- Coût Moyen</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-700 mb-1">
                  {getMethodLabel(settings.stock_valuation_method)}
                </p>
                <p className="text-sm text-slate-600">
                  {getMethodDescription(settings.stock_valuation_method)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Résumé de la valorisation du stock */}
        {stockValuation && (
          <div className="p-6 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-emerald-50 rounded-lg">
                <Coins className="w-5 h-5 text-emerald-600" strokeWidth={1.5} />
              </div>
              <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Valorisation actuelle du stock
              </h2>
              <span className="text-sm px-2 py-1 bg-slate-100 rounded-full text-slate-600">
                Méthode: {getMethodLabel(stockValuation.method)}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-emerald-50 rounded-lg">
                <p className="text-sm text-emerald-700 mb-1">Valeur totale du stock</p>
                <p className="text-2xl font-bold text-emerald-900">
                  {formatCurrency(stockValuation.total_value, settings.currency)}
                </p>
              </div>
              <div className="p-4 bg-teal-50 rounded-lg">
                <p className="text-sm text-teal-700 mb-1">Nombre de produits</p>
                <p className="text-2xl font-bold text-teal-900">
                  {stockValuation.products_count}
                </p>
              </div>
              <div className="p-4 bg-amber-50 rounded-lg">
                <p className="text-sm text-amber-700 mb-1">Coût moyen par produit</p>
                <p className="text-2xl font-bold text-amber-900">
                  {formatCurrency(stockValuation.total_value / stockValuation.products_count || 0, settings.currency)}
                </p>
              </div>
            </div>

            {/* Top 5 produits par valeur */}
            <div>
              <h3 className="text-sm font-medium text-slate-700 mb-3">Top 5 produits par valeur de stock</h3>
              <div className="space-y-2">
                {stockValuation.products
                  .sort((a, b) => b.total_value - a.total_value)
                  .slice(0, 5)
                  .map((product, index) => (
                    <div key={product.product_id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 flex items-center justify-center bg-slate-200 rounded-full text-xs font-medium text-slate-700">
                          {index + 1}
                        </span>
                        <div>
                          <p className="font-medium text-slate-900">{product.product_name}</p>
                          <p className="text-sm text-slate-500">
                            {product.stock} unités × {formatCurrency(product.unit_cost, settings.currency)}
                            {product.estimated && <span className="ml-2 text-amber-600">(estimé)</span>}
                          </p>
                        </div>
                      </div>
                      <p className="font-semibold text-slate-900">
                        {formatCurrency(product.total_value, settings.currency)}
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Settings;
