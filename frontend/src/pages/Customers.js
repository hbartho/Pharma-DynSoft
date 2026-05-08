import React, { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Plus, Users, Edit, Trash2, Search, Phone, Mail, MapPin, Loader2, CloudOff, Wallet, AlertTriangle, Power, UserCheck, UserX, Timer } from 'lucide-react';
import { useCustomers, useToggleCustomerStatus } from '../hooks/useCustomers';
import { useCustomersInfinite } from '../hooks/useInfiniteScroll';
import { useCustomersDebtSummary } from '../hooks/useDebts';
import { useOfflineMutation } from '../services/offlineMutations';
import { useOffline } from '../contexts/OfflineContext';
import { useSettings } from '../contexts/SettingsContext';
import { useAuth } from '../contexts/AuthContext';
import { useCurrentShift, useCanOperate } from '../hooks/useShifts';
import { useShiftEligibility } from '../hooks/useShiftSchedules';

const Customers = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('active');
  const loadMoreRef = useRef(null);
  const [showDialog, setShowDialog] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [customerToDelete, setCustomerToDelete] = useState(null);
  
  // État pour le modal de désactivation avec warning dette
  const [showToggleDialog, setShowToggleDialog] = useState(false);
  const [customerToToggle, setCustomerToToggle] = useState(null);
  const [customerDebtAmount, setCustomerDebtAmount] = useState(0);
  
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
    max_debt_limit: 0,
  });

  // Contexts
  const { isOnline } = useOffline();
  const { formatAmount } = useSettings();
  const { user } = useAuth();
  
  // Shift management - vérifier si l'utilisateur peut effectuer des opérations
  const { data: currentShift } = useCurrentShift();
  const { canOperate, reason: shiftBlockReason } = useCanOperate(user, currentShift);
  
  // Vérifier l'éligibilité de planification (pour restreindre l'accès hors horaires)
  const { data: shiftEligibility } = useShiftEligibility();
  const isAdmin = user?.role === 'admin';
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // React Query hooks avec infinite scroll
  const { 
    data: customersData,
    isLoading,
    isError,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage 
  } = useCustomersInfinite({
    limit: 20,
    search: debouncedSearch,
    status: filterStatus === 'all' ? '' : filterStatus
  });
  
  // Aplatir les pages
  const customers = customersData?.pages?.flatMap(page => page.items) || [];
  const totalCustomers = customersData?.pages?.[0]?.total || 0;
  
  // Garder la liste complète pour les formulaires
  const { data: allCustomers = [] } = useCustomers();
  
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

  const toggleCustomerStatus = useToggleCustomerStatus();
  const { data: customersDebtSummary = [] } = useCustomersDebtSummary(true); // Clients avec dettes
  
  // Offline-first mutations
  const createCustomer = useOfflineMutation('customers', 'create');
  const updateCustomer = useOfflineMutation('customers', 'update');
  const deleteCustomer = useOfflineMutation('customers', 'delete');

  // Handle toggle status - vérifie les dettes avant désactivation
  const handleToggleStatus = (customer) => {
    // Si le client est déjà inactif, on peut le réactiver directement
    if (customer.is_active === false) {
      toggleCustomerStatus.mutate(customer.id);
      return;
    }
    
    // Sinon, vérifier s'il a des dettes en cours
    const debtInfo = customersDebtSummary.find(c => c.customer_id === customer.id);
    const hasDebt = debtInfo && debtInfo.total_debt > 0;
    
    if (hasDebt) {
      // Afficher le modal de confirmation avec warning
      setCustomerToToggle(customer);
      setCustomerDebtAmount(debtInfo.total_debt);
      setShowToggleDialog(true);
    } else {
      // Pas de dette, désactiver directement
      toggleCustomerStatus.mutate(customer.id);
    }
  };
  
  // Confirmer la désactivation malgré les dettes
  const confirmToggleWithDebt = () => {
    if (customerToToggle) {
      toggleCustomerStatus.mutate(customerToToggle.id);
      setShowToggleDialog(false);
      setCustomerToToggle(null);
      setCustomerDebtAmount(0);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (editingCustomer) {
      updateCustomer.mutate(
        { ...formData, id: editingCustomer.id },
        {
          onSuccess: () => {
            setShowDialog(false);
            resetForm();
          },
        }
      );
    } else {
      createCustomer.mutate(formData, {
        onSuccess: () => {
          setShowDialog(false);
          resetForm();
        },
      });
    }
  };

  const handleEdit = (customer) => {
    setEditingCustomer(customer);
    setFormData({
      name: customer.name || '',
      phone: customer.phone || '',
      email: customer.email || '',
      address: customer.address || '',
      max_debt_limit: customer.max_debt_limit || 0,
    });
    setShowDialog(true);
  };

  const handleDelete = (customer) => {
    setCustomerToDelete(customer);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = () => {
    if (!customerToDelete) return;
    
    deleteCustomer.mutate(customerToDelete.id, {
      onSuccess: () => {
        setShowDeleteDialog(false);
        setCustomerToDelete(null);
      },
    });
  };

  const resetForm = () => {
    setEditingCustomer(null);
    setFormData({ name: '', phone: '', email: '', address: '', max_debt_limit: 0 });
  };

  // Les clients sont déjà filtrés côté serveur
  // On garde juste un tri local par nom si nécessaire
  const sortedCustomers = [...customers].sort((a, b) => (a.name || '').localeCompare(b.name || ''));

  // Compteurs basés sur le total serveur
  const activeCount = totalCustomers;
  const inactiveCount = 0; // Le serveur retourne soit actifs soit inactifs

  const isSubmitting = createCustomer.isPending || updateCustomer.isPending;

  if (isError) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <p className="text-red-500">Erreur lors du chargement des clients</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="customers-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Clients
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion de la base clients • {totalCustomers} client{totalCustomers > 1 ? 's' : ''}
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-customer-button" 
                className="bg-teal-700 hover:bg-teal-800 rounded-full"
                disabled={!canOperate}
                title={!canOperate ? shiftBlockReason : ""}
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un client
                {!isOnline && <CloudOff className="w-3 h-3 ml-2 text-amber-300" />}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingCustomer ? 'Modifier le client' : 'Nouveau client'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="customer-form">
                <div>
                  <Label htmlFor="name">Nom *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="customer-name-input"
                    placeholder="Nom du client"
                  />
                </div>
                <div>
                  <Label htmlFor="phone">Téléphone</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    data-testid="customer-phone-input"
                    placeholder="+33 6 12 34 56 78"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    data-testid="customer-email-input"
                    placeholder="client@email.com"
                  />
                </div>
                <div>
                  <Label htmlFor="address">Adresse</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    data-testid="customer-address-input"
                    placeholder="Adresse complète"
                  />
                </div>
                {/* Seuil de dette - visible uniquement pour les admins */}
                {user?.role === 'admin' && (
                  <div className="pt-4 border-t border-slate-200">
                    <Label htmlFor="max_debt_limit" className="flex items-center gap-2">
                      <Wallet className="w-4 h-4 text-slate-500" />
                      Seuil de crédit maximum
                    </Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Input
                        id="max_debt_limit"
                        type="number"
                        min="0"
                        step="1000"
                        value={formData.max_debt_limit}
                        onChange={(e) => setFormData({ ...formData, max_debt_limit: parseFloat(e.target.value) || 0 })}
                        data-testid="customer-debt-limit-input"
                        placeholder="0"
                        className="flex-1"
                      />
                      <span className="text-sm text-slate-500">GNF</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      0 = pas de crédit autorisé
                    </p>
                  </div>
                )}
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                    Annuler
                  </Button>
                  <Button 
                    type="submit" 
                    data-testid="customer-submit-button" 
                    className="bg-teal-700 hover:bg-teal-800"
                    disabled={isSubmitting}
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    {editingCustomer ? 'Mettre à jour' : 'Ajouter'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Search */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
            <Input
              placeholder="Rechercher par nom, email ou téléphone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="customer-search-input"
              className="pl-10"
              disabled={!isWithinScheduledHours}
            />
          </div>
          {/* Filtre actif/inactif */}
          <div className="flex gap-1 bg-slate-100 p-1 rounded-full">
            <button
              onClick={() => setFilterStatus('active')}
              disabled={!isWithinScheduledHours}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                filterStatus === 'active'
                  ? 'bg-white text-teal-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              } ${!isWithinScheduledHours ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <UserCheck className="w-4 h-4" />
              Actifs
              <span className={`px-1.5 py-0.5 text-xs rounded-full ${filterStatus === 'active' ? 'bg-teal-100 text-teal-700' : 'bg-slate-200 text-slate-600'}`}>
                {totalCustomers}
              </span>
            </button>
            <button
              onClick={() => setFilterStatus('inactive')}
              disabled={!isWithinScheduledHours}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                filterStatus === 'inactive'
                  ? 'bg-white text-orange-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              } ${!isWithinScheduledHours ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <UserX className="w-4 h-4" />
              Inactifs
            </button>
          </div>
        </div>

        {/* Message de restriction pour utilisateurs hors horaires */}
        {!isWithinScheduledHours ? (
          <div className="p-6 bg-amber-50 rounded-xl border border-amber-200">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Timer className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-800">Accès restreint - Hors horaires de travail</h3>
                <p className="text-sm text-amber-700 mt-1">
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder aux clients en dehors de vos horaires planifiés.'}
                </p>
                {shiftEligibility?.schedule && (
                  <p className="text-sm text-amber-600 mt-2">
                    <strong>Horaires prévus :</strong> {shiftEligibility.schedule.start_time} - {shiftEligibility.schedule.end_time}
                  </p>
                )}
                {shiftEligibility?.current_time && (
                  <p className="text-xs text-amber-500 mt-1">
                    Heure actuelle : {shiftEligibility.current_time}
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
        <>
        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
          </div>
        ) : (
          <>
            {/* Customers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedCustomers.map((customer) => {
                const isInactive = customer.is_active === false;
                return (
                <div
                  key={customer.id}
                  data-testid={`customer-card-${customer.id}`}
                  className={`p-6 rounded-xl bg-white border transition-all ${
                    isInactive
                      ? 'border-slate-200 bg-slate-50 opacity-75'
                      : customer._offline || customer._pendingSync
                      ? 'border-amber-200 bg-amber-50/30'
                      : 'border-slate-100 hover:border-teal-200'
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${
                        isInactive 
                          ? 'bg-slate-200' 
                          : customer._offline 
                          ? 'bg-amber-100' 
                          : 'bg-teal-50'
                      }`}>
                        <Users className={`w-5 h-5 ${
                          isInactive 
                            ? 'text-slate-500' 
                            : customer._offline 
                            ? 'text-amber-700' 
                            : 'text-teal-700'
                        }`} strokeWidth={1.5} />
                      </div>
                      <div>
                        <h3 className={`font-semibold text-lg ${isInactive ? 'text-slate-500' : 'text-slate-900'}`} style={{ fontFamily: 'Manrope, sans-serif' }}>
                          {customer.name}
                        </h3>
                        {isInactive && (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-slate-200 text-slate-600 rounded-full">
                            <UserX className="w-3 h-3" />
                            Inactif
                          </span>
                        )}
                        {(customer._offline || customer._pendingSync) && !isInactive && (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                            <CloudOff className="w-3 h-3" />
                            Non synchronisé
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className={`space-y-2 text-sm mb-4 ${isInactive ? 'text-slate-400' : 'text-slate-600'}`} style={{ fontFamily: 'Inter, sans-serif' }}>
                    {customer.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                        <span>{customer.phone}</span>
                      </div>
                    )}
                    {customer.email && (
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                        <span>{customer.email}</span>
                      </div>
                    )}
                    {customer.address && (
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                        <span>{customer.address}</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Informations sur les dettes/crédit */}
                  {!isInactive && (
                    <div className={`p-3 rounded-lg mb-4 ${
                      customer.current_debt > 0 
                        ? 'bg-red-50 border border-red-200' 
                        : customer.max_debt_limit > 0
                        ? 'bg-green-50 border border-green-200'
                        : 'bg-yellow-50 border border-yellow-200'
                    }`}>
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <Wallet className={`w-4 h-4 ${
                            customer.current_debt > 0 
                              ? 'text-red-600' 
                              : customer.max_debt_limit > 0
                              ? 'text-green-600'
                              : 'text-yellow-600'
                          }`} />
                          <span className={
                            customer.current_debt > 0 
                              ? 'text-red-700' 
                              : customer.max_debt_limit > 0
                              ? 'text-green-700'
                              : 'text-yellow-700'
                          }>
                            {customer.current_debt > 0 ? 'Dette:' : 'Crédit dispo:'}
                          </span>
                        </div>
                        <span className={`font-semibold ${
                          customer.current_debt > 0 
                            ? 'text-red-700' 
                            : customer.max_debt_limit > 0
                            ? 'text-green-700'
                            : 'text-yellow-700'
                        }`}>
                          {customer.current_debt > 0 
                            ? formatAmount(customer.current_debt)
                            : formatAmount(customer.max_debt_limit || 0)
                          }
                        </span>
                      </div>
                      {customer.current_debt > 0 && customer.max_debt_limit > 0 && (
                        <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                          <span>Seuil: {formatAmount(customer.max_debt_limit)}</span>
                          <span className={customer.current_debt >= customer.max_debt_limit ? 'text-red-600 font-medium' : ''}>
                            {customer.current_debt >= customer.max_debt_limit && (
                              <span className="flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                Limite atteinte
                              </span>
                            )}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(customer)}
                      data-testid={`edit-customer-${customer.id}`}
                      className="flex-1"
                    >
                      <Edit className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      Éditer
                    </Button>
                    <div className="flex gap-2">
                      {/* Bouton toggle - Admin uniquement */}
                      {user?.role === 'admin' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleStatus(customer)}
                          data-testid={`toggle-customer-${customer.id}`}
                          disabled={toggleCustomerStatus.isPending}
                          className={isInactive 
                            ? 'text-green-600 hover:text-green-700 hover:bg-green-50' 
                            : 'text-orange-600 hover:text-orange-700 hover:bg-orange-50'
                          }
                          title={isInactive ? 'Activer le client' : 'Désactiver le client'}
                        >
                          <Power className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                      )}
                      {/* Bouton suppression - Admin uniquement */}
                      {user?.role === 'admin' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(customer)}
                          data-testid={`delete-customer-${customer.id}`}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              )})}
            </div>

            {/* Infinite Scroll Loader */}
            {customers.length > 0 && (
              <div className="flex flex-col items-center gap-4 py-6">
                <p className="text-sm text-slate-600">
                  {customers.length} sur {totalCustomers} clients affichés
                </p>
                <div ref={loadMoreRef} className="h-2 w-full" />
                {isFetchingNextPage && (
                  <div className="flex items-center gap-2 text-teal-600">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span className="text-sm">Chargement...</span>
                  </div>
                )}
                {hasNextPage && !isFetchingNextPage && (
                  <Button variant="outline" onClick={() => fetchNextPage()} className="rounded-full">
                    Charger plus de clients
                  </Button>
                )}
                {!hasNextPage && customers.length > 0 && (
                  <p className="text-sm text-slate-400">✓ Tous les clients ont été chargés</p>
                )}
              </div>
            )}

            {customers.length === 0 && !isLoading && (
              <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
                <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
                <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
                  {searchQuery ? 'Aucun client trouvé' : 'Aucun client enregistré'}
                </p>
              </div>
            )}
          </>
        )}
        </>
        )}
      </div>

      {/* Dialogue de confirmation de suppression */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white/95 backdrop-blur-sm">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Confirmer la suppression
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
              Êtes-vous sûr de vouloir supprimer le client &ldquo;{customerToDelete?.name}&rdquo; ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={() => {
                setShowDeleteDialog(false);
                setCustomerToDelete(null);
              }}
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
              style={{ fontFamily: 'Inter, sans-serif' }}
              disabled={deleteCustomer.isPending}
            >
              {deleteCustomer.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      
      {/* Dialog de confirmation désactivation avec dette */}
      <AlertDialog open={showToggleDialog} onOpenChange={setShowToggleDialog}>
        <AlertDialogContent className="bg-white/95 backdrop-blur-sm">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-orange-600" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <AlertTriangle className="w-5 h-5" />
              Attention : Client endetté
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }} asChild>
              <div className="space-y-3">
                <p>
                  Vous êtes sur le point de désactiver le client <strong>{customerToToggle?.name}</strong>.
                </p>
                <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <p className="text-orange-800 font-medium">
                    ⚠️ Ce client a une dette en cours de <span className="font-bold">{formatAmount(customerDebtAmount)}</span>
                  </p>
                  <p className="text-orange-600 text-sm mt-1">
                    La désactivation empêchera de nouvelles ventes à ce client, mais la dette restera active.
                  </p>
                </div>
                <p className="text-slate-600">
                  Voulez-vous quand même désactiver ce client ?
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={() => {
                setShowToggleDialog(false);
                setCustomerToToggle(null);
                setCustomerDebtAmount(0);
              }}
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmToggleWithDebt}
              className="bg-orange-600 hover:bg-orange-700"
              style={{ fontFamily: 'Inter, sans-serif' }}
              disabled={toggleCustomerStatus.isPending}
            >
              {toggleCustomerStatus.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Désactiver quand même
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Customers;
