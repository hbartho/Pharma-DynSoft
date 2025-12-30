import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import api from '../services/api';

const Reports = () => {
  const [salesData, setSalesData] = useState(null);
  const [settings, setSettings] = useState({ currency: 'GNF' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const [salesRes, settingsRes] = await Promise.all([
        api.get('/reports/sales?days=30'),
        api.get('/settings')
      ]);
      setSalesData(salesRes.data);
      setSettings(settingsRes.data);
    } catch (error) {
      console.error('Error loading reports:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fonction de formatage des montants avec 2 décimales max
  const formatAmount = (amount) => {
    const currency = settings?.currency || 'GNF';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { 
      minimumFractionDigits: 0, 
      maximumFractionDigits: dec 
    });
    return `${formatted} ${symbols[currency] || currency}`;
  };

  // Transformer et trier les données par date croissante
  const chartData = salesData
    ? Object.entries(salesData.daily_stats)
        .map(([date, data]) => ({
          date,
          dateFormatted: new Date(date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
          revenue: Math.round(data.revenue * 100) / 100,
          count: data.count,
        }))
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .map(({ dateFormatted, revenue, count }) => ({
          date: dateFormatted,
          revenue,
          count,
        }))
    : [];

  return (
    <Layout>
      <div className="space-y-8" data-testid="reports-page">
        <div>
          <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Rapports
          </h1>
          <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
            Statistiques et analyses de votre pharmacie
          </p>
        </div>

        {salesData && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
              <p className="text-sm text-slate-500 mb-2" style={{ fontFamily: 'Inter, sans-serif' }}>
                Total des ventes (30j)
              </p>
              <p className="text-3xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {salesData.total_sales}
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
              <p className="text-sm text-slate-500 mb-2" style={{ fontFamily: 'Inter, sans-serif' }}>
                Revenu total (30j)
              </p>
              <p className="text-3xl font-bold text-teal-700" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {formatAmount(salesData.total_revenue)}
              </p>
            </div>
            <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
              <p className="text-sm text-slate-500 mb-2" style={{ fontFamily: 'Inter, sans-serif' }}>
                Moyenne par vente
              </p>
              <p className="text-3xl font-bold text-emerald-700" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {formatAmount(salesData.total_sales > 0 ? salesData.total_revenue / salesData.total_sales : 0)}
              </p>
            </div>
          </div>
        )}

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Chiffre d'affaires sur 30 jours
          </h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={chartData}>
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
                  formatter={(value) => [formatAmount(value), 'Revenu']}
                />
                <Line type="monotone" dataKey="revenue" stroke="#0F766E" strokeWidth={2} dot={{ fill: '#0F766E' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[400px] flex items-center justify-center text-slate-400">
              Aucune donnée disponible
            </div>
          )}
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="text-xl font-semibold text-slate-900 mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Nombre de ventes quotidiennes
          </h3>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData}>
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
                  formatter={(value) => [value, 'Ventes']}
                />
                <Bar dataKey="count" fill="#10B981" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[400px] flex items-center justify-center text-slate-400">
              Aucune donnée disponible
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Reports;
