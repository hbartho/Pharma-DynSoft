import React, { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { 
  History, 
  Calendar, 
  User, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp,
  TrendingDown,
  Clock,
  Banknote,
  Eye,
  Filter,
  BarChart3,
  Percent,
  Play,
  Timer,
  Plus,
  Loader2,
  Trash2
} from 'lucide-react';
import { useShiftsHistory, useShiftsStats, useShiftDetails, useActiveShifts, useExtendShift, useDeleteShift } from '../hooks/useShifts';
import { useShiftsInfinite } from '../hooks/useInfiniteScroll';
import { useUsers } from '../hooks/useUsers';
import { SkeletonTable } from '../components/ui/skeleton-shimmer';

const ShiftsHistory = () => {
  const loadMoreRef = useRef(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedUserId, setSelectedUserId] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedShiftId, setSelectedShiftId] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showExtendDialog, setShowExtendDialog] = useState(false);
  const [shiftToExtend, setShiftToExtend] = useState(null);
  const [extensionMinutes, setExtensionMinutes] = useState(60);
  
  // Données avec infinite scroll
  const { 
    data: shiftsData,
    isLoading: shiftsLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage 
  } = useShiftsInfinite({
    limit: 20,
    status: filterStatus === 'all' ? '' : filterStatus,
    user_id: selectedUserId === 'all' ? '' : selectedUserId,
    start_date: startDate || '',
    end_date: endDate || ''
  });
  
  const shifts = shiftsData?.pages?.flatMap(page => page.items) || [];
  const totalShifts = shiftsData?.pages?.[0]?.total || 0;
  
  // Intersection Observer pour infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    if (loadMoreRef.current) observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);
  
  const { data: stats, isLoading: statsLoading } = useShiftsStats();
  const { data: users = [] } = useUsers();
  const { data: shiftDetails } = useShiftDetails(selectedShiftId);
  const { data: activeShifts = [], isLoading: activeShiftsLoading } = useActiveShifts();
  const extendShift = useExtendShift();
  const deleteShift = useDeleteShift();

  const handleDeleteShift = (shiftId) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce shift ? Cette action est irréversible.')) {
      deleteShift.mutate(shiftId, {
        onSuccess: () => {
          setShowDetailDialog(false);
          setSelectedShiftId(null);
        }
      });
    }
  };

  const handleExtendShift = () => {
    if (shiftToExtend) {
      extendShift.mutate(
        { shiftId: shiftToExtend.id, extensionMinutes },
        {
          onSuccess: () => {
            setShowExtendDialog(false);
            setShiftToExtend(null);
            setExtensionMinutes(60);
          }
        }
      );
    }
  };

  const formatAmount = (amount) => {
    return (amount || 0).toLocaleString('fr-FR') + ' GNF';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (openedAt, closedAt) => {
    if (!openedAt || !closedAt) return '-';
    const start = new Date(openedAt);
    const end = new Date(closedAt);
    const diffMs = end - start;
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}min`;
  };

  // Calculer l'écart de ponctualité (clôture vs heure prévue)
  const getPunctualityInfo = (shift) => {
    if (!shift.closed_at || !shift.expected_end_time) {
      return { status: 'unknown', label: '-', color: 'slate', minutes: 0 };
    }
    
    const closedAt = new Date(shift.closed_at);
    const expectedEnd = new Date(shift.expected_end_time);
    const diffMinutes = Math.round((closedAt - expectedEnd) / (1000 * 60));
    
    // Tolérance de 5 minutes
    if (Math.abs(diffMinutes) <= 5) {
      return { 
        status: 'on-time', 
        label: 'À l\'heure', 
        color: 'green',
        icon: 'check',
        minutes: diffMinutes 
      };
    } else if (diffMinutes > 0) {
      const hours = Math.floor(diffMinutes / 60);
      const mins = diffMinutes % 60;
      return { 
        status: 'late', 
        label: hours > 0 ? `+${hours}h ${mins}min` : `+${mins}min`, 
        color: 'amber',
        icon: 'late',
        minutes: diffMinutes 
      };
    } else {
      const absDiff = Math.abs(diffMinutes);
      const hours = Math.floor(absDiff / 60);
      const mins = absDiff % 60;
      return { 
        status: 'early', 
        label: hours > 0 ? `-${hours}h ${mins}min` : `-${mins}min`, 
        color: 'blue',
        icon: 'early',
        minutes: diffMinutes 
      };
    }
  };

  const handleViewDetails = (shiftId) => {
    setSelectedShiftId(shiftId);
    setShowDetailDialog(true);
  };

  const clearFilters = () => {
    setStartDate('');
    setEndDate('');
    setSelectedUserId('all');
    setFilterStatus('all');
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="shifts-history-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Historique des Shifts
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Suivi et contrôle des caisses
            </p>
          </div>
        </div>

        {/* Statistiques */}
        {!statsLoading && stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-teal-100 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-teal-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Shifts (30j)</p>
                  <p className="text-2xl font-bold text-slate-900">{stats.total_shifts}</p>
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${stats.total_discrepancies > 0 ? 'bg-amber-100' : 'bg-green-100'}`}>
                  <Percent className={`w-5 h-5 ${stats.total_discrepancies > 0 ? 'text-amber-600' : 'text-green-600'}`} />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Taux d&apos;écart</p>
                  <p className="text-2xl font-bold text-slate-900">{stats.discrepancy_rate}%</p>
                  <p className="text-xs text-slate-400">{stats.total_discrepancies} écart(s)</p>
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Excédents</p>
                  <p className="text-lg font-bold text-green-700">+{formatAmount(stats.total_positive_diff)}</p>
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-red-100 rounded-lg">
                  <TrendingDown className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Manques</p>
                  <p className="text-lg font-bold text-red-700">{formatAmount(stats.total_negative_diff)}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Shifts Actifs - Section pour prolonger */}
        {activeShifts.length > 0 && (
          <div className="p-4 bg-gradient-to-r from-teal-50 to-emerald-50 rounded-xl border border-teal-200 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Play className="w-5 h-5 text-teal-600" />
              <span className="font-bold text-teal-800">Shifts en cours ({activeShifts.length})</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeShifts.map((shift) => {
                const isExpired = shift.is_expired;
                const expectedEnd = shift.expected_end_time ? new Date(shift.expected_end_time) : null;
                const now = new Date();
                const remainingMinutes = expectedEnd ? Math.floor((expectedEnd - now) / (1000 * 60)) : null;
                
                return (
                  <div 
                    key={shift.id} 
                    className={`p-4 bg-white rounded-lg border-2 ${isExpired ? 'border-red-400 bg-red-50' : 'border-teal-200'}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-slate-500" />
                          <span className="font-medium text-slate-900">{shift.user_name}</span>
                        </div>
                        {(() => {
                          const code = shift.employee_code || '';
                          const isAdmin = code.startsWith('ADM');
                          const isPharma = code.startsWith('PHA');
                          const isCaissier = code.startsWith('CAI');
                          const colorClass = isAdmin ? 'bg-purple-100 text-purple-700' :
                                            isPharma ? 'bg-teal-100 text-teal-700' :
                                            isCaissier ? 'bg-amber-100 text-amber-700' :
                                            'bg-slate-100 text-slate-600';
                          if (!code) return null;
                          return (
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${colorClass}`}>
                              {code}
                            </span>
                          );
                        })()}
                      </div>
                      {isExpired && (
                        <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full animate-pulse">
                          EXPIRÉ
                        </span>
                      )}
                    </div>
                    
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2 text-slate-600">
                        <Clock className="w-4 h-4" />
                        <span>Ouvert: {formatDate(shift.opened_at)}</span>
                      </div>
                      {expectedEnd && (
                        <div className={`flex items-center gap-2 ${isExpired ? 'text-red-600' : 'text-slate-600'}`}>
                          <Timer className="w-4 h-4" />
                          <span>
                            Fin prévue: {expectedEnd.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                            {!isExpired && remainingMinutes !== null && (
                              <span className="ml-2 text-xs text-teal-600">
                                ({remainingMinutes > 0 ? `${remainingMinutes} min restantes` : 'Bientôt expiré'})
                              </span>
                            )}
                          </span>
                        </div>
                      )}
                      <div className="flex items-center gap-2 text-slate-600">
                        <Banknote className="w-4 h-4" />
                        <span>Fond: {formatAmount(shift.opening_amount)}</span>
                      </div>
                    </div>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setShiftToExtend(shift);
                        setShowExtendDialog(true);
                      }}
                      className={`w-full mt-3 ${isExpired ? 'border-red-400 text-red-700 hover:bg-red-50' : 'border-teal-400 text-teal-700 hover:bg-teal-50'}`}
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Prolonger le shift
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Filtres */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-4 h-4 text-slate-500" />
            <span className="font-medium text-slate-700">Filtres</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <Label className="text-sm text-slate-600">Date début</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-sm text-slate-600">Date fin</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-sm text-slate-600">Caissier</Label>
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Tous les caissiers" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les caissiers</SelectItem>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.name || `${user.first_name} ${user.last_name}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-sm text-slate-600">Statut</Label>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Tous les statuts" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les statuts</SelectItem>
                  <SelectItem value="completed">Terminés</SelectItem>
                  <SelectItem value="active">En cours</SelectItem>
                  <SelectItem value="discrepancy">Avec écart</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button variant="outline" onClick={clearFilters} className="w-full">
                Réinitialiser
              </Button>
            </div>
          </div>
        </div>

        {/* Table des shifts */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Header avec compteur */}
          {!shiftsLoading && shifts.length > 0 && (
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">
                  Affichage de {shifts.length} shift{shifts.length > 1 ? 's' : ''} 
                  {totalShifts > shifts.length && ` sur ${totalShifts} au total`}
                </span>
                {filterStatus !== 'all' && (
                  <span className="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded-full">
                    Filtre: {filterStatus === 'completed' ? 'Terminés' : 
                            filterStatus === 'active' ? 'En cours' : 
                            filterStatus === 'discrepancy' ? 'Avec écart' : filterStatus}
                  </span>
                )}
              </div>
            </div>
          )}
          
          {shiftsLoading ? (
            <SkeletonTable rows={8} columns={8} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Caissier</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider">Durée</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Ponctualité</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">Ouverture</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">Ventes</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">Attendu</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider">Compté</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Écart</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shifts.map((shift) => (
                    <tr key={shift.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3 text-sm text-slate-900">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-slate-400" />
                          {formatDate(shift.closed_at || shift.opened_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center">
                            <User className="w-4 h-4 text-teal-600" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-slate-900">{shift.user_name}</p>
                            <p className="text-xs text-slate-500">{shift.employee_code}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-600">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-400" />
                          {formatDuration(shift.opened_at, shift.closed_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {(() => {
                          const punctuality = getPunctualityInfo(shift);
                          return (
                            <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                              punctuality.status === 'on-time' ? 'bg-green-100 text-green-700' :
                              punctuality.status === 'late' ? 'bg-amber-100 text-amber-700' :
                              punctuality.status === 'early' ? 'bg-blue-100 text-blue-700' :
                              'bg-slate-100 text-slate-500'
                            }`}>
                              {punctuality.status === 'on-time' && <CheckCircle2 className="w-3 h-3" />}
                              {punctuality.status === 'late' && <AlertTriangle className="w-3 h-3" />}
                              {punctuality.status === 'early' && <Clock className="w-3 h-3" />}
                              {punctuality.label}
                            </div>
                          );
                        })()}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-900 text-right font-medium">
                        {formatAmount(shift.opening_amount)}
                      </td>
                      <td className="px-4 py-3 text-sm text-teal-700 text-right font-medium">
                        +{formatAmount(shift.total_cash_sales)}
                        <span className="text-xs text-slate-400 ml-1">({shift.total_sales_count})</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-900 text-right font-medium">
                        {formatAmount(shift.expected_closing_amount)}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-900 text-right font-medium">
                        {formatAmount(shift.actual_closing_amount)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {shift.has_discrepancy ? (
                          <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                            shift.difference > 0 
                              ? 'bg-green-100 text-green-700' 
                              : 'bg-red-100 text-red-700'
                          }`}>
                            <AlertTriangle className="w-3 h-3" />
                            {shift.difference > 0 ? '+' : ''}{formatAmount(shift.difference)}
                          </div>
                        ) : (
                          <div className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                            <CheckCircle2 className="w-3 h-3" />
                            OK
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetails(shift.id)}
                          data-testid={`view-shift-${shift.id}`}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                  
                  {/* Infinite scroll loading indicator */}
                  {isFetchingNextPage && (
                    <tr>
                      <td colSpan="10" className="px-4 py-8 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Loader2 className="w-5 h-5 animate-spin text-teal-600" />
                          <span className="text-slate-600">Chargement...</span>
                        </div>
                      </td>
                    </tr>
                  )}
                  
                  {/* Intersection observer target */}
                  {hasNextPage && (
                    <tr>
                      <td colSpan="10" className="px-4 py-2">
                        <div ref={loadMoreRef} className="h-4" />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          
          {!shiftsLoading && shifts.length === 0 && (
            <div className="text-center py-12">
              <History className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">Aucun shift clôturé trouvé</p>
            </div>
          )}
        </div>
      </div>

      {/* Dialog détails du shift */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="w-5 h-5 text-teal-600" />
              Détails du Shift
            </DialogTitle>
          </DialogHeader>
          
          {shiftDetails && (
            <div className="space-y-4">
              {/* Infos caissier */}
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                  <User className="w-5 h-5 text-teal-600" />
                </div>
                <div>
                  <p className="font-medium text-slate-900">{shiftDetails.user_name}</p>
                  <p className="text-sm text-slate-500">{shiftDetails.employee_code}</p>
                </div>
              </div>
              
              {/* Horaires */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-green-600 uppercase">Ouverture</p>
                  <p className="font-medium text-green-800">{formatDate(shiftDetails.opened_at)}</p>
                </div>
                <div className="p-3 bg-amber-50 rounded-lg">
                  <p className="text-xs text-amber-600 uppercase">Clôture</p>
                  <p className="font-medium text-amber-800">{formatDate(shiftDetails.closed_at)}</p>
                </div>
              </div>
              
              {/* Ponctualité */}
              {shiftDetails.expected_end_time && (
                <div className={`p-3 rounded-lg border ${
                  (() => {
                    const p = getPunctualityInfo(shiftDetails);
                    return p.status === 'on-time' ? 'bg-green-50 border-green-200' :
                           p.status === 'late' ? 'bg-amber-50 border-amber-200' :
                           p.status === 'early' ? 'bg-blue-50 border-blue-200' :
                           'bg-slate-50 border-slate-200';
                  })()
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-500 uppercase">Heure de fin prévue</p>
                      <p className="font-medium text-slate-700">
                        {new Date(shiftDetails.expected_end_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-slate-500 uppercase">Ponctualité</p>
                      {(() => {
                        const p = getPunctualityInfo(shiftDetails);
                        return (
                          <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${
                            p.status === 'on-time' ? 'bg-green-100 text-green-700' :
                            p.status === 'late' ? 'bg-amber-100 text-amber-700' :
                            p.status === 'early' ? 'bg-blue-100 text-blue-700' :
                            'bg-slate-100 text-slate-500'
                          }`}>
                            {p.status === 'on-time' && '✅'}
                            {p.status === 'late' && '⚠️'}
                            {p.status === 'early' && '🕐'}
                            {p.label}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Montants */}
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">Fond de caisse</span>
                  <span className="font-semibold">{formatAmount(shiftDetails.opening_amount)}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-teal-50 rounded-lg">
                  <span className="text-teal-700">Ventes espèces ({shiftDetails.total_sales_count})</span>
                  <span className="font-semibold text-teal-800">+ {formatAmount(shiftDetails.total_cash_sales)}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-100 rounded-lg border-2 border-slate-300">
                  <span className="font-medium text-slate-700">Montant attendu</span>
                  <span className="font-bold text-lg">{formatAmount(shiftDetails.expected_closing_amount)}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-slate-100 rounded-lg">
                  <span className="text-slate-600">Montant compté</span>
                  <span className="font-semibold">{formatAmount(shiftDetails.actual_closing_amount)}</span>
                </div>
              </div>
              
              {/* Écart */}
              {shiftDetails.has_discrepancy && (
                <div className={`p-4 rounded-lg ${
                  shiftDetails.difference > 0 ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-center gap-2">
                    <AlertTriangle className={`w-5 h-5 ${shiftDetails.difference > 0 ? 'text-green-600' : 'text-red-600'}`} />
                    <span className={`font-medium ${shiftDetails.difference > 0 ? 'text-green-700' : 'text-red-700'}`}>
                      Écart: {shiftDetails.difference > 0 ? '+' : ''}{formatAmount(shiftDetails.difference)}
                    </span>
                  </div>
                  {shiftDetails.closing_notes && (
                    <p className="mt-2 text-sm text-slate-600 italic">
                      Note: {shiftDetails.closing_notes}
                    </p>
                  )}
                </div>
              )}
              
              {!shiftDetails.has_discrepancy && (
                <div className="p-4 bg-green-50 rounded-lg border border-green-200 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                  <span className="font-medium text-green-700">Caisse équilibrée</span>
                </div>
              )}
              
              {/* Bouton de suppression (admin uniquement) */}
              <DialogFooter className="pt-4 border-t">
                <Button
                  variant="outline"
                  onClick={() => setShowDetailDialog(false)}
                >
                  Fermer
                </Button>
                {!shiftDetails.is_active && (
                  <Button
                    variant="destructive"
                    onClick={() => handleDeleteShift(shiftDetails.id)}
                    disabled={deleteShift.isPending}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    {deleteShift.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4 mr-2" />
                    )}
                    Supprimer
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog prolongation de shift */}
      <Dialog open={showExtendDialog} onOpenChange={setShowExtendDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Timer className="w-5 h-5 text-teal-600" />
              Prolonger le Shift
            </DialogTitle>
          </DialogHeader>
          
          {shiftToExtend && (
            <div className="space-y-4">
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <User className="w-4 h-4 text-slate-500" />
                  <span className="font-medium">{shiftToExtend.user_name}</span>
                  {(() => {
                    const code = shiftToExtend.employee_code || '';
                    const isAdmin = code.startsWith('ADM');
                    const isPharma = code.startsWith('PHA');
                    const isCaissier = code.startsWith('CAI');
                    const colorClass = isAdmin ? 'bg-purple-100 text-purple-700' :
                                      isPharma ? 'bg-teal-100 text-teal-700' :
                                      isCaissier ? 'bg-amber-100 text-amber-700' :
                                      'bg-slate-100 text-slate-600';
                    if (!code) return null;
                    return (
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${colorClass}`}>
                        {code}
                      </span>
                    );
                  })()}
                </div>
                {shiftToExtend.expected_end_time && (
                  <div className="text-sm text-slate-600">
                    <span>Heure de fin actuelle: </span>
                    <strong className={shiftToExtend.is_expired ? 'text-red-600' : 'text-slate-700'}>
                      {new Date(shiftToExtend.expected_end_time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                    </strong>
                    {shiftToExtend.is_expired && (
                      <span className="ml-2 text-red-600 text-xs">(expiré)</span>
                    )}
                  </div>
                )}
              </div>
              
              <div>
                <Label className="text-sm text-slate-600">Durée de prolongation</Label>
                <Select value={extensionMinutes.toString()} onValueChange={(v) => setExtensionMinutes(parseInt(v))}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="15">15 minutes</SelectItem>
                    <SelectItem value="30">30 minutes</SelectItem>
                    <SelectItem value="60">1 heure</SelectItem>
                    <SelectItem value="120">2 heures</SelectItem>
                    <SelectItem value="180">3 heures</SelectItem>
                    <SelectItem value="240">4 heures</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {shiftToExtend.expected_end_time && (
                <div className="p-3 bg-teal-50 rounded-lg border border-teal-200">
                  <p className="text-sm text-teal-700">
                    <strong>Nouvelle heure de fin:</strong>{' '}
                    {(() => {
                      const currentEnd = new Date(shiftToExtend.expected_end_time);
                      const now = new Date();
                      const baseTime = currentEnd < now ? now : currentEnd;
                      const newEnd = new Date(baseTime.getTime() + extensionMinutes * 60 * 1000);
                      return newEnd.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
                    })()}
                  </p>
                </div>
              )}
            </div>
          )}
          
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowExtendDialog(false)}>
              Annuler
            </Button>
            <Button 
              onClick={handleExtendShift}
              disabled={extendShift.isPending}
              className="bg-teal-600 hover:bg-teal-700"
            >
              {extendShift.isPending ? 'Prolongation...' : 'Prolonger'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default ShiftsHistory;
