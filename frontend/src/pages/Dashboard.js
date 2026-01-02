import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import StatsCard from '../components/StatsCard';
import { DollarSign, Package, AlertTriangle, FileText, Coins, PackagePlus, TrendingUp, History, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, AreaChart, Area, Legend } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { useSettings } from '../contexts/SettingsContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const Dashboard = () => {
  const navigate = useNavigate();
  const { formatAmount, currency } = useSettings();
  
  const [stats, setStats] = useState({
    today_sales_count: 0,
    today_revenue: 0,
    total_products: 0,
    low_stock_count: 0,
    pending_prescriptions: 0,
    total_stock_value: 0,
    stock_valuation_method: 'weighted_average',
  });
  const [pendingSupplies, setPendingSupplies] = useState(0);
  const [salesData, setSalesData] = useState([]);
  const [stockMovements, setStockMovements] = useState([]);
  const [priceHistory, setPriceHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsResponse, salesResponse, suppliesResponse, stockResponse, pricesResponse] = await Promise.all([
        api.get('/reports/dashboard'),
        api.get('/reports/sales?days=7'),
        api.get('/supplies?status=pending'),
        api.get('/stock/movements?limit=20'),
        api.get('/prices/history?limit=20'),
      ]);

      setStats(statsResponse.data);
      setPendingSupplies(suppliesResponse.data.length);

      // Transformer et trier les données de ventes par date croissante
      const chartData = Object.entries(salesResponse.data.daily_stats)
        .map(([date, data]) => ({
          date,
          dateFormatted: new Date(date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
          revenue: data.revenue,
          count: data.count,
        }))
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .map(({ dateFormatted, revenue, count }) => ({
          date: dateFormatted,
          revenue,
          count,
        }));
      setSalesData(chartData);

      // Transformer les mouvements de stock pour le graphique
      const stockData = stockResponse.data
        .slice(0, 10)
        .reverse()
        .map((mov) => ({
          product: mov.product_name?.substring(0, 15) || 'N/A',
          quantity: mov.movement_quantity,
          type: mov.movement_type,
          stockAfter: mov.stock_after,
          date: new Date(mov.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
        }));
      setStockMovements(stockData);

      // Transformer l'historique des prix pour le graphique
      const priceData = pricesResponse.data
        .slice(0, 10)
        .reverse()
        .map((price) => ({
          product: price.product_name?.substring(0, 15) || 'N/A',
          prixAchat: price.prix_appro || 0,
          prixVente: price.prix_vente_prod || 0,
          date: new Date(price.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
          modifiedBy: price.created_by || 'N/A',
        }));
      setPriceHistory(priceData);

    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  // Statistiques des mouvements de stock
  const stockStats = {
    totalEntries: stockMovements.filter(m => m.quantity > 0).reduce((sum, m) => sum + m.quantity, 0),
    totalExits: Math.abs(stockMovements.filter(m => m.quantity < 0).reduce((sum, m) => sum + m.quantity, 0)),
    recentCount: stockMovements.length,
  };

  return (
    <Layout>
      <div className="space-y-8" data-testid="dashboard-page">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Tableau de bord
          </h1>
          <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
            Vue d'ensemble de votre pharmacie
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          <StatsCard
            title="Ventes aujourd'hui"
            value={stats.today_sales_count}
            icon={DollarSign}
            color="teal"
          />
          <StatsCard
            title="Revenu du jour"
            value={formatAmount(stats.today_revenue)}
            icon={DollarSign}
            color="emerald"
          />
          <StatsCard
            title="Valeur du stock"
            value={formatAmount(stats.total_stock_value || 0)}
            icon={Coins}
            color="purple"
            subtitle={stats.stock_valuation_method === 'fifo' ? 'FIFO' : stats.stock_valuation_method === 'lifo' ? 'LIFO' : 'Moy. Pond.'}
          />
          <StatsCard
            title="Produits en stock"
            value={stats.total_products}
            icon={Package}
            color="blue"
          />
          <StatsCard
            title="Alertes stock"
            value={stats.low_stock_count}
            icon={AlertTriangle}
            color="amber"
          />
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sales Chart */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm" data-testid="sales-chart">
            <h3 className="text-xl font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Ventes des 7 derniers jours
            </h3>
            {salesData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={salesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#64748b" style={{ fontFamily: 'Inter, sans-serif', fontSize: 12 }} />
                  <YAxis stroke="#64748b" style={{ fontFamily: 'Inter, sans-serif', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontFamily: 'Inter, sans-serif',
                    }}
                    formatter={(value) => [formatAmount(value), 'Revenu']}
                  />
                  <Bar dataKey="revenue" fill="#0F766E" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[280px] flex items-center justify-center text-slate-400">
                Aucune donnée disponible
              </div>
            )}
          </div>

          {/* Quick Info */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm" data-testid="quick-info">
            <h3 className="text-xl font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Informations rapides
            </h3>
            <div className="space-y-4">
              <div 
                className="flex items-center justify-between p-4 bg-orange-50 rounded-lg cursor-pointer hover:bg-orange-100 transition-colors"
                onClick={() => navigate('/supplies')}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <PackagePlus className="w-5 h-5 text-orange-700" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      Approvisionnements en attente
                    </p>
                    <p className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {pendingSupplies}
                    </p>
                  </div>
                </div>
                {pendingSupplies > 0 && (
                  <span className="text-xs font-medium text-orange-700 bg-orange-200 px-2 py-1 rounded-full">
                    À valider
                  </span>
                )}
              </div>

              <div 
                className="flex items-center justify-between p-4 bg-teal-50 rounded-lg cursor-pointer hover:bg-teal-100 transition-colors"
                onClick={() => navigate('/prescriptions')}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-teal-100 rounded-lg">
                    <FileText className="w-5 h-5 text-teal-700" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      Ordonnances en attente
                    </p>
                    <p className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {stats.pending_prescriptions}
                    </p>
                  </div>
                </div>
                {stats.pending_prescriptions > 0 && (
                  <span className="text-xs font-medium text-teal-700 bg-teal-200 px-2 py-1 rounded-full">
                    À traiter
                  </span>
                )}
              </div>

              <div 
                className="flex items-center justify-between p-4 bg-amber-50 rounded-lg cursor-pointer hover:bg-amber-100 transition-colors"
                onClick={() => navigate('/products')}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-100 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-amber-700" strokeWidth={1.5} />
                  </div>
                  <div>
                    <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      Produits à réapprovisionner
                    </p>
                    <p className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {stats.low_stock_count}
                    </p>
                  </div>
                </div>
                {stats.low_stock_count > 0 && (
                  <span className="text-xs font-medium text-amber-700 bg-amber-200 px-2 py-1 rounded-full">
                    Stock bas
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Charts Row 2 - Stock & Price History */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <Tabs defaultValue="stock" className="w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Historiques
              </h3>
              <TabsList className="grid w-[300px] grid-cols-2">
                <TabsTrigger value="stock" className="flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Stock
                </TabsTrigger>
                <TabsTrigger value="prices" className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  Prix
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Stock Movements Tab */}
            <TabsContent value="stock" className="mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Stock Movement Stats */}
                <div className="space-y-4">
                  <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                    <div className="flex items-center gap-2 mb-1">
                      <ArrowUpRight className="w-4 h-4 text-emerald-600" />
                      <span className="text-sm text-emerald-700">Entrées récentes</span>
                    </div>
                    <p className="text-2xl font-bold text-emerald-800">+{stockStats.totalEntries}</p>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg border border-red-100">
                    <div className="flex items-center gap-2 mb-1">
                      <ArrowDownRight className="w-4 h-4 text-red-600" />
                      <span className="text-sm text-red-700">Sorties récentes</span>
                    </div>
                    <p className="text-2xl font-bold text-red-800">-{stockStats.totalExits}</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-sm text-slate-600">Mouvements affichés</span>
                    <p className="text-2xl font-bold text-slate-800">{stockStats.recentCount}</p>
                  </div>
                </div>

                {/* Stock Movement Chart */}
                <div className="lg:col-span-2">
                  {stockMovements.length > 0 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={stockMovements} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis type="number" stroke="#64748b" style={{ fontSize: 12 }} />
                        <YAxis dataKey="product" type="category" width={100} stroke="#64748b" style={{ fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#fff',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            fontFamily: 'Inter, sans-serif',
                          }}
                          formatter={(value, name) => {
                            if (name === 'quantity') return [value > 0 ? `+${value}` : value, 'Quantité'];
                            return [value, 'Stock après'];
                          }}
                        />
                        <Legend />
                        <Bar 
                          dataKey="quantity" 
                          name="Mouvement"
                          fill={(entry) => entry.quantity > 0 ? '#10b981' : '#ef4444'}
                          radius={[0, 4, 4, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[280px] flex items-center justify-center text-slate-400">
                      Aucun mouvement de stock récent
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Stock Movements Table */}
              {stockMovements.length > 0 && (
                <div className="mt-6 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-2 px-3 font-medium text-slate-600">Produit</th>
                        <th className="text-left py-2 px-3 font-medium text-slate-600">Type</th>
                        <th className="text-right py-2 px-3 font-medium text-slate-600">Quantité</th>
                        <th className="text-right py-2 px-3 font-medium text-slate-600">Stock après</th>
                        <th className="text-right py-2 px-3 font-medium text-slate-600">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stockMovements.slice().reverse().slice(0, 5).map((mov, idx) => (
                        <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="py-2 px-3 font-medium">{mov.product}</td>
                          <td className="py-2 px-3">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              mov.type === 'supply' ? 'bg-emerald-100 text-emerald-700' :
                              mov.type === 'sale' ? 'bg-blue-100 text-blue-700' :
                              mov.type === 'adjustment' ? 'bg-amber-100 text-amber-700' :
                              'bg-slate-100 text-slate-700'
                            }`}>
                              {mov.type === 'supply' ? 'Appro' : mov.type === 'sale' ? 'Vente' : mov.type}
                            </span>
                          </td>
                          <td className={`py-2 px-3 text-right font-medium ${mov.quantity > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {mov.quantity > 0 ? `+${mov.quantity}` : mov.quantity}
                          </td>
                          <td className="py-2 px-3 text-right">{mov.stockAfter}</td>
                          <td className="py-2 px-3 text-right text-slate-500">{mov.date}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </TabsContent>

            {/* Price History Tab */}
            <TabsContent value="prices" className="mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Price Stats */}
                <div className="space-y-4">
                  <div className="p-4 bg-purple-50 rounded-lg border border-purple-100">
                    <span className="text-sm text-purple-700">Modifications de prix</span>
                    <p className="text-2xl font-bold text-purple-800">{priceHistory.length}</p>
                    <p className="text-xs text-purple-600 mt-1">Dernières mises à jour</p>
                  </div>
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-sm text-slate-600">Traçabilité</span>
                    <p className="text-lg font-medium text-slate-800 mt-1">
                      {priceHistory[priceHistory.length - 1]?.modifiedBy || 'N/A'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">Dernier modificateur</p>
                  </div>
                </div>

                {/* Price History Chart */}
                <div className="lg:col-span-2">
                  {priceHistory.length > 0 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={priceHistory}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="product" stroke="#64748b" style={{ fontSize: 11 }} angle={-45} textAnchor="end" height={80} />
                        <YAxis stroke="#64748b" style={{ fontSize: 12 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#fff',
                            border: '1px solid #e2e8f0',
                            borderRadius: '8px',
                            fontFamily: 'Inter, sans-serif',
                          }}
                          formatter={(value, name) => {
                            if (name === 'prixAchat') return [formatAmount(value), 'Prix achat'];
                            if (name === 'prixVente') return [formatAmount(value), 'Prix vente'];
                            return [value, name];
                          }}
                        />
                        <Legend />
                        <Area type="monotone" dataKey="prixAchat" name="Prix achat" stroke="#8b5cf6" fill="#8b5cf680" />
                        <Area type="monotone" dataKey="prixVente" name="Prix vente" stroke="#0d9488" fill="#0d948880" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[280px] flex items-center justify-center text-slate-400">
                      Aucun historique de prix récent
                    </div>
                  )}
                </div>
              </div>

              {/* Recent Price Changes Table */}
              {priceHistory.length > 0 && (
                <div className="mt-6 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-2 px-3 font-medium text-slate-600">Produit</th>
                        <th className="text-right py-2 px-3 font-medium text-slate-600">Prix achat</th>
                        <th className="text-right py-2 px-3 font-medium text-slate-600">Prix vente</th>
                        <th className="text-left py-2 px-3 font-medium text-slate-600">Modifié par</th>
                        <th className="text-right py-2 px-3 font-medium text-slate-600">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {priceHistory.slice().reverse().slice(0, 5).map((price, idx) => (
                        <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="py-2 px-3 font-medium">{price.product}</td>
                          <td className="py-2 px-3 text-right text-purple-600">{formatAmount(price.prixAchat)}</td>
                          <td className="py-2 px-3 text-right text-teal-600">{formatAmount(price.prixVente)}</td>
                          <td className="py-2 px-3">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono">
                              {price.modifiedBy}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right text-slate-500">{price.date}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
