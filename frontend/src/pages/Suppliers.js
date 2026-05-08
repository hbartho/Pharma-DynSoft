import React, { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Plus, Truck, Edit, Trash2, Search, Phone, Mail, MapPin, Power, PowerOff, Filter, Eye, EyeOff, Loader2, CloudOff, Timer } from 'lucide-react';
import { useSuppliers, useToggleSupplierStatus } from '../hooks';
import { useSuppliersInfinite } from '../hooks/useInfiniteScroll';
import { useOfflineMutation } from '../services/offlineMutations';
import { useAuth } from '../contexts/AuthContext';
import { useOffline } from '../contexts/OfflineContext';
import { useCurrentShift, useCanOperate } from '../hooks/useShifts';
import { useShiftEligibility } from '../hooks/useShiftSchedules';

const Suppliers = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('active');
  const loadMoreRef = useRef(null);
  const [showDialog, setShowDialog] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [supplierToDelete, setSupplierToDelete] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
  });
  
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  
  // Shift management
  const { data: currentShift } = useCurrentShift();
  const { canOperate, reason: shiftBlockReason } = useCanOperate(user, currentShift);
  
  // Vérifier l'éligibilité de planification
  const { data: shiftEligibility } = useShiftEligibility();
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;
  
  // Offline context
  const { isOnline } = useOffline();

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // React Query hooks avec infinite scroll
  const { 
    data: suppliersData,
    isLoading,
    isError,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage 
  } = useSuppliersInfinite({
    limit: 20,
    search: debouncedSearch,
    status: filterStatus === 'all' ? '' : filterStatus
  });
  
  const suppliers = suppliersData?.pages?.flatMap(page => page.items) || [];
  const totalSuppliers = suppliersData?.pages?.[0]?.total || 0;
  
  // Garder la liste complète pour les formulaires
  const { data: allSuppliers = [] } = useSuppliers();
  
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

  const toggleStatus = useToggleSupplierStatus();
  
  // Offline-first mutations
  const createSupplier = useOfflineMutation('suppliers', 'create');
  const updateSupplier = useOfflineMutation('suppliers', 'update');
  const deleteSupplier = useOfflineMutation('suppliers', 'delete');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (editingSupplier) {
      updateSupplier.mutate(
        { ...formData, id: editingSupplier.id },
        {
          onSuccess: () => {
            setShowDialog(false);
            resetForm();
          },
        }
      );
    } else {
      createSupplier.mutate(formData, {
        onSuccess: () => {
          setShowDialog(false);
          resetForm();
        },
      });
    }
  };

  const handleEdit = (supplier) => {
    setEditingSupplier(supplier);
    setFormData({
      name: supplier.name || '',
      phone: supplier.phone || '',
      email: supplier.email || '',
      address: supplier.address || '',
    });
    setShowDialog(true);
  };

  const handleDelete = (supplier) => {
    setSupplierToDelete(supplier);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = () => {
    if (!supplierToDelete) return;
    
    deleteSupplier.mutate(supplierToDelete.id, {
      onSuccess: () => {
        setShowDeleteDialog(false);
        setSupplierToDelete(null);
      },
      onError: () => {
        setShowDeleteDialog(false);
        setSupplierToDelete(null);
      },
    });
  };

  const handleToggleStatus = (supplier) => {
    toggleStatus.mutate(supplier.id);
  };

  const resetForm = () => {
    setEditingSupplier(null);
    setFormData({ name: '', phone: '', email: '', address: '' });
  };

  // Les fournisseurs sont déjà filtrés côté serveur
  const sortedSuppliers = [...suppliers].sort((a, b) => {
    const aActive = a.is_active !== false ? 1 : 0;
    const bActive = b.is_active !== false ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    return (a.name || '').localeCompare(b.name || '');
  });

  const isSubmitting = createSupplier.isPending || updateSupplier.isPending;

  if (isError) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <p className="text-red-500">Erreur lors du chargement des fournisseurs</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="suppliers-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Fournisseurs
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des fournisseurs • {totalSuppliers} fournisseur{totalSuppliers > 1 ? 's' : ''}
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-supplier-button" 
                className="bg-teal-700 hover:bg-teal-800 rounded-full"
                disabled={!canOperate}
                title={!canOperate ? shiftBlockReason : ''}
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un fournisseur
                {!isOnline && <CloudOff className="w-3 h-3 ml-2 text-amber-300" />}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingSupplier ? 'Modifier le fournisseur' : 'Nouveau fournisseur'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="supplier-form">
                <div>
                  <Label htmlFor="name">Nom *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="supplier-name-input"
                    placeholder="Nom du fournisseur"
                  />
                </div>
                <div>
                  <Label htmlFor="phone">Téléphone</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    data-testid="supplier-phone-input"
                    placeholder="+224 620 00 00 00"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    data-testid="supplier-email-input"
                    placeholder="contact@fournisseur.com"
                  />
                </div>
                <div>
                  <Label htmlFor="address">Adresse</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    data-testid="supplier-address-input"
                    placeholder="Adresse complète"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                    Annuler
                  </Button>
                  <Button 
                    type="submit" 
                    data-testid="supplier-submit-button" 
                    className="bg-teal-700 hover:bg-teal-800"
                    disabled={isSubmitting}
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    {editingSupplier ? 'Mettre à jour' : 'Ajouter'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4 items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
            <Input
              placeholder="Rechercher par nom, email ou téléphone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="supplier-search-input"
              className="pl-10"
              disabled={!isWithinScheduledHours}
            />
          </div>
          
          {/* Filtre Admin: Afficher/Masquer inactifs */}
          {isAdmin && (
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg">
              <Filter className="w-4 h-4 text-slate-500" />
              <Label htmlFor="filter-status" className="text-sm text-slate-600 cursor-pointer">
                Statut:
              </Label>
              <select
                id="filter-status"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                disabled={!isWithinScheduledHours}
                className="text-sm border rounded px-2 py-1"
              >
                <option value="active">Actifs</option>
                <option value="inactive">Inactifs</option>
                <option value="all">Tous</option>
              </select>
            </div>
          )}
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
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder aux fournisseurs en dehors de vos horaires planifiés.'}
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
            {/* Suppliers Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedSuppliers.map((supplier) => {
                const isActive = supplier.is_active !== false;
                const isPending = supplier._offline || supplier._pendingSync;
                
                return (
                  <div
                    key={supplier.id}
                    data-testid={`supplier-card-${supplier.id}`}
                    className={`p-6 rounded-xl bg-white border transition-all ${
                      isPending
                        ? 'border-amber-200 bg-amber-50/30'
                        : isActive 
                          ? 'border-slate-100 hover:border-teal-200' 
                          : 'border-red-100 bg-red-50/30 opacity-75'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${isPending ? 'bg-amber-100' : isActive ? 'bg-teal-50' : 'bg-red-100'}`}>
                          <Truck className={`w-5 h-5 ${isPending ? 'text-amber-700' : isActive ? 'text-teal-700' : 'text-red-500'}`} strokeWidth={1.5} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                            {supplier.name}
                          </h3>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {isPending && (
                              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                                <CloudOff className="w-3 h-3" />
                                Non synchronisé
                              </span>
                            )}
                            <Badge 
                              variant={isActive ? 'default' : 'destructive'}
                              className={`text-xs ${isActive ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100' : ''}`}
                            >
                              {isActive ? 'Actif' : 'Inactif'}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-2 text-sm text-slate-600 mb-4" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {supplier.phone && (
                        <div className="flex items-center gap-2">
                          <Phone className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                          <span>{supplier.phone}</span>
                        </div>
                      )}
                      {supplier.email && (
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                          <span>{supplier.email}</span>
                        </div>
                      )}
                      {supplier.address && (
                        <div className="flex items-center gap-2">
                          <MapPin className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                          <span>{supplier.address}</span>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 pt-3 border-t border-slate-100">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(supplier)}
                        data-testid={`edit-supplier-${supplier.id}`}
                        className="flex-1"
                      >
                        <Edit className="w-4 h-4 mr-1" strokeWidth={1.5} />
                        Éditer
                      </Button>
                      
                      {/* Bouton Activer/Désactiver - Admin uniquement */}
                      {isAdmin && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleStatus(supplier)}
                          data-testid={`toggle-supplier-${supplier.id}`}
                          className={isActive 
                            ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-50' 
                            : 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50'
                          }
                          title={isActive ? 'Désactiver' : 'Activer'}
                          disabled={toggleStatus.isPending}
                        >
                          {isActive ? (
                            <PowerOff className="w-4 h-4" strokeWidth={1.5} />
                          ) : (
                            <Power className="w-4 h-4" strokeWidth={1.5} />
                          )}
                        </Button>
                      )}
                      
                      {isAdmin && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(supplier)}
                          data-testid={`delete-supplier-${supplier.id}`}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Infinite Scroll Loader */}
            {suppliers.length > 0 && (
              <div className="flex flex-col items-center gap-4 py-6">
                <p className="text-sm text-slate-600">
                  {suppliers.length} sur {totalSuppliers} fournisseurs affichés
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
                    Charger plus de fournisseurs
                  </Button>
                )}
                {!hasNextPage && suppliers.length > 0 && (
                  <p className="text-sm text-slate-400">✓ Tous les fournisseurs ont été chargés</p>
                )}
              </div>
            )}

            {suppliers.length === 0 && !isLoading && (
              <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
                <Truck className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
                <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
                  {searchQuery ? 'Aucun fournisseur trouvé' : 'Aucun fournisseur enregistré'}
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
              Êtes-vous sûr de vouloir supprimer le fournisseur &ldquo;{supplierToDelete?.name}&rdquo; ?
              <br />
              <span className="text-amber-600 font-medium">
                Note: Si ce fournisseur a déjà effectué des approvisionnements, la suppression sera refusée.
                Vous pourrez alors le désactiver à la place.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={() => {
                setShowDeleteDialog(false);
                setSupplierToDelete(null);
              }}
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
              style={{ fontFamily: 'Inter, sans-serif' }}
              disabled={deleteSupplier.isPending}
            >
              {deleteSupplier.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Suppliers;
