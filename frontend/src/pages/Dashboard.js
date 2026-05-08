import React, { useState } from 'react';
import Layout from '../components/Layout';
import StatsCard from '../components/StatsCard';
import { DollarSign, Package, AlertTriangle, FileText, Coins, PackagePlus, TrendingUp, ArrowUpRight, Loader2, Banknote, CreditCard, Smartphone, FileCheck, Wallet, Calendar, ChevronLeft, ChevronRight, Tag } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { useSettings } from '../contexts/SettingsContext';
import { useDashboardData } from '../hooks/useDashboard';
import { SkeletonDashboard } from '../components/ui/skeleton-shimmer';
import { Button } from '../components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Calendar as CalendarComponent } from '../components/ui/calendar';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';

// Couleurs pour les modes de paiement
const PAYMENT_COLORS = {
  cash: '#22c55e',        // Vert
  card: '#3b82f6',        // Bleu
  check: '#8b5cf6',       // Violet
  orange_money: '#f97316', // Orange
  mtn_money: '#eab308',   // Jaune
  mobile_money: '#f97316', // Orange (fallback pour les anciennes ventes)
  credit: '#ef4444',      // Rouge
};

// Icônes pour les modes de paiement
const getPaymentIcon = (method) => {
  switch (method) {
    case 'cash': return Banknote;
    case 'card': return CreditCard;
    case 'check': return FileCheck;
    case 'orange_money':
    case 'mtn_money': return Smartphone;
    case 'credit': return Wallet;
    default: return Coins;
  }
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { formatAmount } = useSettings();
  
  // État pour la date sélectionnée (null = aujourd'hui)
  const [selectedDate, setSelectedDate] = useState(new Date());
  
  // Formater la date pour l'API (ISO string)
  const formattedDate = selectedDate ? selectedDate.toISOString() : null;
  
  const {
    stats,
    pendingSupplies,
    salesChartData,
    salesByPayment,
    isLoading,
    isSalesByPaymentLoading,
  } = useDashboardData(formattedDate);

  // Vérifier si c'est aujourd'hui
  const isToday = selectedDate && 
    selectedDate.toDateString() === new Date().toDateString();

  // Navigation rapide entre les dates
  const goToPreviousDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() - 1);
    setSelectedDate(newDate);
  };

  const goToNextDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + 1);
    // Ne pas permettre d'aller dans le futur
    if (newDate <= new Date()) {
      setSelectedDate(newDate);
    }
  };

  const goToToday = () => {
    setSelectedDate(new Date());
  };

  if (isLoading) {
    return (
      <Layout>
        <SkeletonDashboard />
      </Layout>
    );
  }

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
            {salesChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={salesChartData}>
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

        {/* Ventes par Mode de Paiement avec sélecteur de date */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-4">
              <h3 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Ventes par Mode de Paiement
              </h3>
              
              {/* Sélecteur de date */}
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={goToPreviousDay}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={`h-9 px-3 font-medium ${isToday ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : ''}`}
                    >
                      <Calendar className="mr-2 h-4 w-4" />
                      {isToday ? "Aujourd'hui" : format(selectedDate, 'dd MMM yyyy', { locale: fr })}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <CalendarComponent
                      mode="single"
                      selected={selectedDate}
                      onSelect={(date) => date && setSelectedDate(date)}
                      disabled={(date) => date > new Date()}
                      initialFocus
                      locale={fr}
                    />
                    {!isToday && (
                      <div className="p-2 border-t">
                        <Button
                          variant="ghost"
                          className="w-full text-sm"
                          onClick={goToToday}
                        >
                          Revenir à aujourd'hui
                        </Button>
                      </div>
                    )}
                  </PopoverContent>
                </Popover>
                
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={goToNextDay}
                  disabled={isToday}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
            
            <div className="text-right">
              <p className="text-sm text-slate-500">
                Total {isToday ? "du jour" : `du ${format(selectedDate, 'dd/MM/yyyy', { locale: fr })}`}
              </p>
              <p className="text-2xl font-bold text-emerald-600" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {isSalesByPaymentLoading ? (
                  <Loader2 className="w-6 h-6 animate-spin inline" />
                ) : (
                  formatAmount(salesByPayment.total_revenue)
                )}
              </p>
              {/* Affichage des rabais */}
              {!isSalesByPaymentLoading && salesByPayment.discount_info?.total_discount > 0 && (
                <div className="flex items-center justify-end gap-1.5 mt-1">
                  <Tag className="w-3.5 h-3.5 text-green-600" />
                  <span className="text-sm text-green-600 font-medium">
                    Rabais: -{formatAmount(salesByPayment.discount_info.total_discount)}
                  </span>
                  <span className="text-xs text-slate-400">
                    ({salesByPayment.discount_info.discount_count} vente{salesByPayment.discount_info.discount_count > 1 ? 's' : ''})
                  </span>
                </div>
              )}
            </div>
          </div>

          {isSalesByPaymentLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
            </div>
          ) : salesByPayment.by_payment.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Liste des modes de paiement */}
              <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
                {salesByPayment.by_payment.map((payment, idx) => {
                  const Icon = getPaymentIcon(payment.method);
                  const color = PAYMENT_COLORS[payment.method] || '#64748b';
                  const percentage = salesByPayment.total_revenue > 0 
                    ? ((payment.total / salesByPayment.total_revenue) * 100).toFixed(1)
                    : 0;
                  
                  // Informations sur les ventes partielles (mixtes)
                  const hasPartialSales = payment.partial_sales_count > 0;
                  const fullCount = payment.full_sales_count ?? 0;
                  const partialCount = payment.partial_sales_count ?? 0;
                  
                  return (
                    <div 
                      key={payment.method}
                      className="p-4 rounded-lg border transition-all hover:shadow-md"
                      style={{ borderColor: color + '40', backgroundColor: color + '08' }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div 
                            className="p-2 rounded-lg"
                            style={{ backgroundColor: color + '20' }}
                          >
                            <Icon className="w-5 h-5" style={{ color: color }} strokeWidth={1.5} />
                          </div>
                          <div>
                            <p className="font-medium text-slate-800" style={{ fontFamily: 'Inter, sans-serif' }}>
                              {payment.label}
                            </p>
                            <p className="text-xs text-slate-500">
                              {hasPartialSales ? (
                                <>
                                  {fullCount > 0 && <span>{fullCount} vente{fullCount > 1 ? 's' : ''}</span>}
                                  {fullCount > 0 && partialCount > 0 && <span> + </span>}
                                  {partialCount > 0 && <span className="text-amber-600">{partialCount} partielle{partialCount > 1 ? 's' : ''}</span>}
                                </>
                              ) : (
                                <>{payment.count} vente{payment.count > 1 ? 's' : ''}</>
                              )}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                            {formatAmount(payment.total)}
                          </p>
                          <p className="text-xs font-medium" style={{ color: color }}>
                            {percentage}%
                          </p>
                        </div>
                      </div>
                      {/* Barre de progression */}
                      <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            width: `${percentage}%`,
                            backgroundColor: color 
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Graphique en camembert */}
              <div className="lg:col-span-2 flex items-center justify-center">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={salesByPayment.by_payment}
                      dataKey="total"
                      nameKey="label"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      label={({ label, percent }) => `${label} (${(percent * 100).toFixed(0)}%)`}
                      labelLine={{ stroke: '#64748b', strokeWidth: 1 }}
                    >
                      {salesByPayment.by_payment.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={PAYMENT_COLORS[entry.method] || '#64748b'}
                        />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value) => formatAmount(value)}
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        fontFamily: 'Inter, sans-serif',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Banknote className="w-12 h-12 mb-3 opacity-50" />
              <p className="text-lg font-medium">
                Aucune vente {isToday ? "aujourd'hui" : `le ${format(selectedDate, 'dd/MM/yyyy', { locale: fr })}`}
              </p>
              <p className="text-sm">
                {isToday 
                  ? "Les statistiques apparaîtront ici une fois les premières ventes effectuées"
                  : "Sélectionnez une autre date pour voir les statistiques"
                }
              </p>
            </div>
          )}

          {/* Résumé rapide */}
          {salesByPayment.total_count > 0 && (
            <div className="mt-6 pt-4 border-t border-slate-100">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <span className="text-slate-500">
                    <strong className="text-slate-700">{salesByPayment.total_count}</strong> vente{salesByPayment.total_count > 1 ? 's' : ''} au total
                  </span>
                  <span className="text-slate-500">
                    •
                  </span>
                  <span className="text-slate-500">
                    <strong className="text-slate-700">{salesByPayment.by_payment.length}</strong> mode{salesByPayment.by_payment.length > 1 ? 's' : ''} de paiement
                  </span>
                </div>
                <button 
                  onClick={() => navigate('/sales')}
                  className="text-primary hover:underline font-medium flex items-center gap-1"
                >
                  Voir toutes les ventes
                  <ArrowUpRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
