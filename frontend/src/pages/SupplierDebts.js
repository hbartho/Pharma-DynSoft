import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2, Calendar, CreditCard, AlertTriangle, Check, X, 
  Search, Filter, ChevronDown, Banknote, ArrowUpRight, Clock,
  FileText, Trash2, DollarSign, TrendingDown
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';
import { toast } from 'sonner';
import api from '../services/api';
import Layout from '../components/Layout';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';

// Formateur de montant
const formatAmount = (amount) => {
  if (amount === null || amount === undefined) return '0 GNF';
  return new Intl.NumberFormat('fr-GN', { 
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount) + ' GNF';
};

// Statuts avec couleurs
const statusConfig = {
  pending: { label: 'En attente', color: 'bg-amber-100 text-amber-800', icon: Clock },
  partial: { label: 'Partiel', color: 'bg-blue-100 text-blue-800', icon: TrendingDown },
  paid: { label: 'Payé', color: 'bg-green-100 text-green-800', icon: Check },
  overdue: { label: 'En retard', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
  written_off: { label: 'Abandonné', color: 'bg-slate-100 text-slate-800', icon: X },
};

// Modes de paiement
const paymentMethods = [
  { value: 'cash', label: 'Espèces', icon: Banknote },
  { value: 'transfer', label: 'Virement', icon: ArrowUpRight },
  { value: 'check', label: 'Chèque', icon: FileText },
];

export default function SupplierDebts() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedDebt, setSelectedDebt] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showWriteOffModal, setShowWriteOffModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  
  // Form states
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    method: 'cash',
    reference: '',
    notes: ''
  });
  const [writeOffForm, setWriteOffForm] = useState({
    reason: '',
    notes: ''
  });

  // Fetch supplier debts
  const { data: debtsData, isLoading } = useQuery({
    queryKey: ['supplier-debts', statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      const response = await api.get(`/supplier-debts?${params.toString()}`);
      return response.data;
    }
  });

  // Fetch suppliers for filter
  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => {
      const response = await api.get('/suppliers');
      return response.data;
    }
  });

  // Payment mutation
  const paymentMutation = useMutation({
    mutationFn: async ({ debtId, data }) => {
      const response = await api.post(`/supplier-debts/${debtId}/payment`, data);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Paiement enregistré avec succès');
      queryClient.invalidateQueries(['supplier-debts']);
      setShowPaymentModal(false);
      setPaymentForm({ amount: '', method: 'cash', reference: '', notes: '' });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors du paiement');
    }
  });

  // Write-off mutation
  const writeOffMutation = useMutation({
    mutationFn: async ({ debtId, data }) => {
      const response = await api.post(`/supplier-debts/${debtId}/write-off`, data);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Dette abandonnée');
      queryClient.invalidateQueries(['supplier-debts']);
      setShowWriteOffModal(false);
      setWriteOffForm({ reason: '', notes: '' });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || "Erreur lors de l'abandon");
    }
  });

  // Filtered debts
  const filteredDebts = useMemo(() => {
    if (!debtsData?.items) return [];
    return debtsData.items.filter(debt => {
      const matchesSearch = searchTerm === '' || 
        debt.supplier_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (debt.supply_number && debt.supply_number.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (debt.invoice_number && debt.invoice_number.toLowerCase().includes(searchTerm.toLowerCase()));
      return matchesSearch;
    });
  }, [debtsData, searchTerm]);

  // Stats
  const stats = debtsData?.stats || { total_debt: 0, total_overdue: 0, overdue_count: 0 };

  // Handlers
  const handlePayment = (debt) => {
    setSelectedDebt(debt);
    setPaymentForm({ ...paymentForm, amount: debt.remaining_amount.toString() });
    setShowPaymentModal(true);
  };

  const handleWriteOff = (debt) => {
    setSelectedDebt(debt);
    setShowWriteOffModal(true);
  };

  const handleViewDetails = (debt) => {
    setSelectedDebt(debt);
    setShowDetailsModal(true);
  };

  const submitPayment = () => {
    if (!paymentForm.amount || parseFloat(paymentForm.amount) <= 0) {
      toast.error('Montant invalide');
      return;
    }
    paymentMutation.mutate({
      debtId: selectedDebt.id,
      data: {
        amount: parseFloat(paymentForm.amount),
        method: paymentForm.method,
        reference: paymentForm.reference || null,
        notes: paymentForm.notes || null
      }
    });
  };

  const submitWriteOff = () => {
    if (!writeOffForm.reason) {
      toast.error('Veuillez indiquer une raison');
      return;
    }
    writeOffMutation.mutate({
      debtId: selectedDebt.id,
      data: writeOffForm
    });
  };

  return (
    <Layout>
    <div className="p-6 space-y-6" data-testid="supplier-debts-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Dettes Fournisseurs
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Gestion des créances envers les fournisseurs
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-4 border shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <DollarSign className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Total des dettes</p>
              <p className="text-xl font-bold text-slate-800">{formatAmount(stats.total_debt)}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-xl p-4 border shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">En retard (+3 mois)</p>
              <p className="text-xl font-bold text-red-600">{formatAmount(stats.total_overdue)}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-4 border shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Dettes en retard</p>
              <p className="text-xl font-bold text-amber-600">{stats.overdue_count} dettes</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Rechercher par fournisseur, n° appro, facture..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
            data-testid="search-supplier-debts"
          />
        </div>
        
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" data-testid="status-filter">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Statut" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les statuts</SelectItem>
            <SelectItem value="pending">En attente</SelectItem>
            <SelectItem value="partial">Partiellement payé</SelectItem>
            <SelectItem value="overdue">En retard (+3 mois)</SelectItem>
            <SelectItem value="paid">Payé</SelectItem>
            <SelectItem value="written_off">Abandonné</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">Chargement...</div>
        ) : filteredDebts.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <Building2 className="w-12 h-12 mx-auto text-slate-300 mb-3" />
            <p>Aucune dette fournisseur</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b">
                <tr>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase">Fournisseur</th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-slate-500 uppercase">Référence</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-slate-500 uppercase">Montant initial</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-slate-500 uppercase">Payé</th>
                  <th className="text-right py-3 px-4 text-xs font-medium text-slate-500 uppercase">Restant</th>
                  <th className="text-center py-3 px-4 text-xs font-medium text-slate-500 uppercase">Échéance</th>
                  <th className="text-center py-3 px-4 text-xs font-medium text-slate-500 uppercase">Statut</th>
                  <th className="text-center py-3 px-4 text-xs font-medium text-slate-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredDebts.map((debt) => {
                  const config = statusConfig[debt.status] || statusConfig.pending;
                  const StatusIcon = config.icon;
                  
                  return (
                    <tr key={debt.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <Building2 className="w-4 h-4 text-slate-400" />
                          <span className="font-medium text-slate-800">{debt.supplier_name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm">
                          <p className="text-slate-800">{debt.supply_number || '-'}</p>
                          {debt.invoice_number && (
                            <p className="text-slate-500 text-xs">Fact: {debt.invoice_number}</p>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-medium text-slate-800">
                        {formatAmount(debt.original_amount)}
                      </td>
                      <td className="py-3 px-4 text-right text-green-600 font-medium">
                        {formatAmount(debt.paid_amount)}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-slate-800">
                        {formatAmount(debt.remaining_amount)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {debt.due_date ? (
                          <div className={`text-sm ${debt.is_overdue ? 'text-red-600 font-medium' : 'text-slate-600'}`}>
                            {format(new Date(debt.due_date), 'dd/MM/yyyy', { locale: fr })}
                            {debt.is_overdue && (
                              <p className="text-xs text-red-500">
                                +{debt.days_overdue} jours
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-400">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
                          <StatusIcon className="w-3 h-3" />
                          {config.label}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" data-testid={`actions-${debt.id}`}>
                              <ChevronDown className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleViewDetails(debt)}>
                              <FileText className="w-4 h-4 mr-2" />
                              Voir détails
                            </DropdownMenuItem>
                            {debt.status !== 'paid' && debt.status !== 'written_off' && (
                              <>
                                <DropdownMenuItem onClick={() => handlePayment(debt)}>
                                  <CreditCard className="w-4 h-4 mr-2" />
                                  Enregistrer paiement
                                </DropdownMenuItem>
                                <DropdownMenuItem 
                                  onClick={() => handleWriteOff(debt)}
                                  className="text-red-600"
                                >
                                  <Trash2 className="w-4 h-4 mr-2" />
                                  Abandonner dette
                                </DropdownMenuItem>
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Payment Modal */}
      <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Enregistrer un paiement
            </DialogTitle>
          </DialogHeader>
          
          {selectedDebt && (
            <div className="space-y-4">
              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="text-sm text-slate-500">Fournisseur</p>
                <p className="font-medium">{selectedDebt.supplier_name}</p>
                <p className="text-sm text-slate-500 mt-2">Restant dû</p>
                <p className="font-bold text-lg text-teal-700">{formatAmount(selectedDebt.remaining_amount)}</p>
              </div>
              
              <div className="space-y-3">
                <div>
                  <Label>Montant du paiement *</Label>
                  <Input
                    type="number"
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                    placeholder="0"
                    max={selectedDebt.remaining_amount}
                    data-testid="payment-amount"
                  />
                </div>
                
                <div>
                  <Label>Mode de paiement</Label>
                  <Select 
                    value={paymentForm.method} 
                    onValueChange={(v) => setPaymentForm({ ...paymentForm, method: v })}
                  >
                    <SelectTrigger data-testid="payment-method">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {paymentMethods.map(m => (
                        <SelectItem key={m.value} value={m.value}>
                          <div className="flex items-center gap-2">
                            <m.icon className="w-4 h-4" />
                            {m.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label>Référence (n° chèque, virement...)</Label>
                  <Input
                    value={paymentForm.reference}
                    onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })}
                    placeholder="Ex: CHQ-001, VIR-2024-001"
                    data-testid="payment-reference"
                  />
                </div>
                
                <div>
                  <Label>Notes</Label>
                  <Textarea
                    value={paymentForm.notes}
                    onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                    placeholder="Notes optionnelles..."
                    rows={2}
                  />
                </div>
              </div>
              
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setShowPaymentModal(false)}>
                  Annuler
                </Button>
                <Button 
                  onClick={submitPayment}
                  disabled={paymentMutation.isPending}
                  className="bg-teal-600 hover:bg-teal-700"
                  data-testid="confirm-payment"
                >
                  {paymentMutation.isPending ? 'Enregistrement...' : 'Confirmer le paiement'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Write-off Modal */}
      <Dialog open={showWriteOffModal} onOpenChange={setShowWriteOffModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Abandonner la dette
            </DialogTitle>
          </DialogHeader>
          
          {selectedDebt && (
            <div className="space-y-4">
              <div className="bg-red-50 p-3 rounded-lg border border-red-200">
                <p className="text-sm text-red-600 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Cette action est irréversible
                </p>
                <p className="font-medium mt-2">{selectedDebt.supplier_name}</p>
                <p className="font-bold text-lg text-red-700">{formatAmount(selectedDebt.remaining_amount)}</p>
              </div>
              
              <div className="space-y-3">
                <div>
                  <Label>Raison de l'abandon *</Label>
                  <Textarea
                    value={writeOffForm.reason}
                    onChange={(e) => setWriteOffForm({ ...writeOffForm, reason: e.target.value })}
                    placeholder="Ex: Fournisseur en faillite, Litige commercial résolu..."
                    rows={3}
                    data-testid="writeoff-reason"
                  />
                </div>
                
                <div>
                  <Label>Notes additionnelles</Label>
                  <Textarea
                    value={writeOffForm.notes}
                    onChange={(e) => setWriteOffForm({ ...writeOffForm, notes: e.target.value })}
                    placeholder="Notes optionnelles..."
                    rows={2}
                  />
                </div>
              </div>
              
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={() => setShowWriteOffModal(false)}>
                  Annuler
                </Button>
                <Button 
                  onClick={submitWriteOff}
                  disabled={writeOffMutation.isPending}
                  variant="destructive"
                  data-testid="confirm-writeoff"
                >
                  {writeOffMutation.isPending ? 'Abandon...' : 'Confirmer l\'abandon'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Details Modal */}
      <Dialog open={showDetailsModal} onOpenChange={setShowDetailsModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Détails de la dette
            </DialogTitle>
          </DialogHeader>
          
          {selectedDebt && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">Fournisseur</p>
                  <p className="font-medium">{selectedDebt.supplier_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">N° Approvisionnement</p>
                  <p className="font-medium">{selectedDebt.supply_number || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">N° Facture</p>
                  <p className="font-medium">{selectedDebt.invoice_number || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Date d'échéance</p>
                  <p className={`font-medium ${selectedDebt.is_overdue ? 'text-red-600' : ''}`}>
                    {selectedDebt.due_date 
                      ? format(new Date(selectedDebt.due_date), 'dd/MM/yyyy', { locale: fr })
                      : '-'
                    }
                  </p>
                </div>
              </div>
              
              <div className="bg-slate-50 p-3 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Montant initial</span>
                  <span className="font-medium">{formatAmount(selectedDebt.original_amount)}</span>
                </div>
                <div className="flex justify-between text-green-600">
                  <span>Montant payé</span>
                  <span className="font-medium">- {formatAmount(selectedDebt.paid_amount)}</span>
                </div>
                <div className="flex justify-between border-t pt-2 text-lg font-bold">
                  <span className="text-slate-700">Restant dû</span>
                  <span className="text-teal-700">{formatAmount(selectedDebt.remaining_amount)}</span>
                </div>
              </div>
              
              {/* Payment History */}
              {selectedDebt.payments && selectedDebt.payments.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-slate-700 mb-2">Historique des paiements</p>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {selectedDebt.payments.map((payment, idx) => (
                      <div key={idx} className="bg-white border rounded-lg p-2 text-sm">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">
                              {payment.type === 'write_off' ? 'Abandon' : formatAmount(payment.amount)}
                            </p>
                            <p className="text-slate-500 text-xs">
                              {format(new Date(payment.date), 'dd/MM/yyyy HH:mm', { locale: fr })}
                            </p>
                          </div>
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            payment.type === 'write_off' 
                              ? 'bg-red-100 text-red-700' 
                              : 'bg-green-100 text-green-700'
                          }`}>
                            {payment.type === 'write_off' ? 'Abandon' : payment.method}
                          </span>
                        </div>
                        {payment.reference && (
                          <p className="text-slate-500 text-xs mt-1">Réf: {payment.reference}</p>
                        )}
                        {payment.notes && (
                          <p className="text-slate-600 text-xs mt-1">{payment.notes}</p>
                        )}
                        {payment.reason && (
                          <p className="text-red-600 text-xs mt-1">Raison: {payment.reason}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="flex justify-end pt-2">
                <Button variant="outline" onClick={() => setShowDetailsModal(false)}>
                  Fermer
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
    </Layout>
  );
}
