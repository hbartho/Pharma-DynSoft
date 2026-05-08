import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { 
  History, Search, Filter, Calendar, User, Tag, Zap, 
  DollarSign, TrendingDown, BarChart3, Download, RefreshCw,
  ChevronLeft, ChevronRight, Gift, Percent, ShoppingCart
} from 'lucide-react';
import api from '../services/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';

const formatAmount = (amount) => {
  return new Intl.NumberFormat('fr-GN').format(Math.round(amount || 0)) + ' GNF';
};

const SOURCE_CONFIG = {
  manual: { label: 'Manuel', icon: User, color: 'bg-amber-100 text-amber-700', borderColor: 'border-amber-300' },
  promo_code: { label: 'Code Promo', icon: Tag, color: 'bg-purple-100 text-purple-700', borderColor: 'border-purple-300' },
  automatic: { label: 'Automatique', icon: Zap, color: 'bg-blue-100 text-blue-700', borderColor: 'border-blue-300' },
  product: { label: 'Par Produit', icon: ShoppingCart, color: 'bg-green-100 text-green-700', borderColor: 'border-green-300' },
};

const DiscountHistory = () => {
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    source: '',
    agentCode: '',
  });
  const [appliedFilters, setAppliedFilters] = useState({});

  // Fetch history
  const { data: historyData, isLoading, refetch } = useQuery({
    queryKey: ['discount-history', page, limit, appliedFilters],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('skip', ((page - 1) * limit).toString());
      params.append('limit', limit.toString());
      
      if (appliedFilters.dateFrom) params.append('date_from', appliedFilters.dateFrom);
      if (appliedFilters.dateTo) params.append('date_to', appliedFilters.dateTo);
      if (appliedFilters.source && appliedFilters.source !== 'all') params.append('source', appliedFilters.source);
      if (appliedFilters.agentCode) params.append('agent_code', appliedFilters.agentCode);
      
      const response = await api.get(`/discounts/history?${params}`);
      return response.data;
    }
  });

  // Fetch stats
  const { data: statsData } = useQuery({
    queryKey: ['discount-stats', appliedFilters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (appliedFilters.dateFrom) params.append('date_from', appliedFilters.dateFrom);
      if (appliedFilters.dateTo) params.append('date_to', appliedFilters.dateTo);
      
      const response = await api.get(`/discounts/history/stats?${params}`);
      return response.data;
    }
  });

  const applyFilters = () => {
    setAppliedFilters({ ...filters });
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({
      dateFrom: '',
      dateTo: '',
      source: '',
      agentCode: '',
    });
    setAppliedFilters({});
    setPage(1);
  };

  const history = historyData?.items || [];
  const total = historyData?.total || 0;
  const totalPages = Math.ceil(total / limit);

  const stats = statsData || {
    total_discounts: 0,
    total_amount: 0,
    by_source: {},
    by_agent: []
  };

  const getSourceConfig = (source) => SOURCE_CONFIG[source] || SOURCE_CONFIG.manual;

  const exportToCSV = () => {
    if (history.length === 0) return;
    
    const headers = ['Date', 'Vente', 'Source', 'Code/Règle', 'Produit', 'Client', 'Type', 'Valeur', 'Montant', 'Agent', 'Motif'];
    const rows = history.map(h => [
      h.created_at ? format(new Date(h.created_at), 'dd/MM/yyyy HH:mm') : '',
      h.sale_number || '',
      getSourceConfig(h.discount_source).label,
      h.promo_code || h.rule_name || '',
      h.product_name || '',
      h.customer_name || 'Anonyme',
      h.discount_type === 'percent' ? '%' : 'Montant',
      h.discount_value,
      h.discount_amount,
      h.agent_name || h.agent_code || '',
      h.reason || ''
    ]);
    
    const csvContent = [headers, ...rows].map(row => row.join(';')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `historique_rabais_${format(new Date(), 'yyyy-MM-dd')}.csv`;
    link.click();
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Historique des Rabais</h1>
            <p className="text-sm text-slate-500">Suivi et analyse des rabais accordés</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Actualiser</span>
            </Button>
            <Button variant="outline" size="sm" onClick={exportToCSV} disabled={history.length === 0}>
              <Download className="w-4 h-4 sm:mr-2" />
              <span className="hidden sm:inline">Exporter CSV</span>
              <span className="sm:hidden">CSV</span>
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-teal-100 rounded-lg">
                  <History className="w-6 h-6 text-teal-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.total_discounts}</p>
                  <p className="text-sm text-slate-500">Rabais accordés</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-red-100 rounded-lg">
                  <TrendingDown className="w-6 h-6 text-red-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{formatAmount(stats.total_amount)}</p>
                  <p className="text-sm text-slate-500">Total des rabais</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <Tag className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.by_source?.promo_code?.count || 0}</p>
                  <p className="text-sm text-slate-500">Codes promo utilisés</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Zap className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.by_source?.automatic?.count || 0}</p>
                  <p className="text-sm text-slate-500">Rabais automatiques</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Stats by Source */}
        {Object.keys(stats.by_source || {}).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Répartition par Source
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(stats.by_source).map(([source, data]) => {
                  const config = getSourceConfig(source);
                  const SourceIcon = config.icon;
                  return (
                    <div key={source} className={`p-4 rounded-lg border ${config.borderColor} ${config.color.split(' ')[0]}`}>
                      <div className="flex items-center gap-2 mb-2">
                        <SourceIcon className="w-4 h-4" />
                        <span className="font-medium text-sm">{config.label}</span>
                      </div>
                      <p className="text-2xl font-bold">{data.count}</p>
                      <p className="text-sm opacity-75">{formatAmount(data.total)}</p>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats by Agent */}
        {stats.by_agent && stats.by_agent.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <User className="w-5 h-5" />
                Rabais par Agent
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {stats.by_agent.map((agent, idx) => (
                  <div key={idx} className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                    <p className="font-medium text-slate-900">{agent.agent_name || agent.agent_code || 'Inconnu'}</p>
                    <p className="text-sm text-slate-500">{agent.count} rabais</p>
                    <p className="text-lg font-bold text-red-600 mt-1">-{formatAmount(agent.total)}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Filtres
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="space-y-2">
                <Label>Date début</Label>
                <Input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Date fin</Label>
                <Input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Source</Label>
                <Select 
                  value={filters.source || 'all'} 
                  onValueChange={(v) => setFilters({ ...filters, source: v === 'all' ? '' : v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Toutes les sources" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Toutes les sources</SelectItem>
                    <SelectItem value="manual">Manuel</SelectItem>
                    <SelectItem value="promo_code">Code Promo</SelectItem>
                    <SelectItem value="automatic">Automatique</SelectItem>
                    <SelectItem value="product">Par Produit</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Code Agent</Label>
                <Input
                  value={filters.agentCode}
                  onChange={(e) => setFilters({ ...filters, agentCode: e.target.value })}
                  placeholder="ADM-001..."
                />
              </div>
              <div className="flex items-end gap-2">
                <Button onClick={applyFilters} className="bg-teal-600 hover:bg-teal-700">
                  <Search className="w-4 h-4 mr-2" />
                  Filtrer
                </Button>
                <Button variant="outline" onClick={resetFilters}>
                  Réinitialiser
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* History Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">
                Détail des Rabais ({total} résultats)
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-center py-8 text-slate-500">Chargement...</div>
            ) : history.length === 0 ? (
              <div className="text-center py-12">
                <Gift className="w-12 h-12 mx-auto text-slate-300 mb-4" />
                <p className="text-slate-500">Aucun rabais trouvé</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Vente</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Détail</TableHead>
                        <TableHead>Client</TableHead>
                        <TableHead>Rabais</TableHead>
                        <TableHead>Agent</TableHead>
                        <TableHead>Motif</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {history.map((item) => {
                        const sourceConfig = getSourceConfig(item.discount_source);
                        const SourceIcon = sourceConfig.icon;
                        return (
                          <TableRow key={item.id}>
                            <TableCell className="whitespace-nowrap">
                              {item.created_at && format(new Date(item.created_at), 'dd/MM/yyyy HH:mm', { locale: fr })}
                            </TableCell>
                            <TableCell>
                              <span className="font-mono text-sm text-teal-600">
                                {item.sale_number || '-'}
                              </span>
                            </TableCell>
                            <TableCell>
                              <Badge className={`${sourceConfig.color} border-0`}>
                                <SourceIcon className="w-3 h-3 mr-1" />
                                {sourceConfig.label}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {item.promo_code && (
                                <span className="font-mono text-purple-600">{item.promo_code}</span>
                              )}
                              {item.rule_name && (
                                <span className="text-blue-600">{item.rule_name}</span>
                              )}
                              {item.product_name && (
                                <span className="text-green-600">{item.product_name}</span>
                              )}
                              {!item.promo_code && !item.rule_name && !item.product_name && '-'}
                            </TableCell>
                            <TableCell>
                              {item.customer_name || <span className="text-slate-400">Anonyme</span>}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                {item.discount_type === 'percent' ? (
                                  <Percent className="w-3 h-3 text-slate-400" />
                                ) : (
                                  <DollarSign className="w-3 h-3 text-slate-400" />
                                )}
                                <span className="text-sm text-slate-500">
                                  {item.discount_type === 'percent' ? `${item.discount_value}%` : formatAmount(item.discount_value)}
                                </span>
                                <span className="font-bold text-red-600 ml-2">
                                  -{formatAmount(item.discount_amount)}
                                </span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <span className="text-sm">
                                {item.agent_name || item.agent_code || '-'}
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className="text-sm text-slate-500 max-w-[150px] truncate block">
                                {item.reason || '-'}
                              </span>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <p className="text-sm text-slate-500">
                      Page {page} sur {totalPages} ({total} résultats)
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                      >
                        <ChevronLeft className="w-4 h-4" />
                        Précédent
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                      >
                        Suivant
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default DiscountHistory;
