import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import StatsCard from '../components/StatsCard';
import { DollarSign, Package, AlertTriangle, FileText, Coins } from 'lucide-react';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Dashboard = () => {
  const [stats, setStats] = useState({
    today_sales_count: 0,
    today_revenue: 0,
    total_products: 0,
    low_stock_count: 0,
    pending_prescriptions: 0,
    total_stock_value: 0,
    stock_valuation_method: 'weighted_average',
  });
  const [salesData, setSalesData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsResponse, salesResponse] = await Promise.all([
        api.get('/reports/dashboard'),
        api.get('/reports/sales?days=7'),
      ]);

      setStats(statsResponse.data);

      // Transformer et trier les données par date croissante
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
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
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
            value={`${stats.today_revenue.toFixed(2)} €`}
            icon={DollarSign}
            color="emerald"
          />
          <StatsCard
            title="Valeur du stock"
            value={`${stats.total_stock_value?.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) || '0.00'} €`}
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

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sales Chart */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm" data-testid="sales-chart">
            <h3 className="text-xl font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Ventes des 7 derniers jours
            </h3>
            {salesData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={salesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#64748b" style={{ fontFamily: 'Inter, sans-serif' }} />
                  <YAxis stroke="#64748b" style={{ fontFamily: 'Inter, sans-serif' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      fontFamily: 'Inter, sans-serif',
                    }}
                  />
                  <Bar dataKey="revenue" fill="#0F766E" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-slate-400">
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
              <div className="flex items-center justify-between p-4 bg-teal-50 rounded-lg">
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
              </div>

              <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg">
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
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;