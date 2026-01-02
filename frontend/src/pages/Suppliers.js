import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Plus, Truck, Edit, Trash2, Search, Phone, Mail, MapPin, Power, PowerOff, Filter, Eye, EyeOff } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems, updateItem, deleteItem as deleteFromDB, addLocalChange, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

const Suppliers = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [supplierToDelete, setSupplierToDelete] = useState(null);
  const [showInactive, setShowInactive] = useState(true); // Admin uniquement
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
  });
  const { isOnline } = useOffline();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const loadSuppliers = async (forceRefresh = false) => {
    try {
      if (isOnline) {
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache' } : {};
        const response = await api.get('/suppliers', { headers });
        setSuppliers(response.data);
        
        // Clear IndexedDB before updating if forced refresh
        if (forceRefresh) {
          try {
            const db = await getDB();
            await db.clear('suppliers');
          } catch (error) {
            console.warn('Could not clear IndexedDB:', error);
          }
        }
        
        for (const supplier of response.data) {
          await addItem('suppliers', supplier);
        }
      } else {
        const localSuppliers = await getAllItems('suppliers');
        // En mode offline, filtrer les inactifs pour les non-admin
        const filtered = isAdmin ? localSuppliers : localSuppliers.filter(s => s.is_active !== false);
        setSuppliers(filtered);
      }
    } catch (error) {
      console.error('Error loading suppliers:', error);
      const localSuppliers = await getAllItems('suppliers');
      const filtered = isAdmin ? localSuppliers : localSuppliers.filter(s => s.is_active !== false);
      setSuppliers(filtered);
    }
  };

  const refreshData = async () => {
    try {
      // Clear browser cache for API calls
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
      }
      
      // Clear IndexedDB
      try {
        const db = await getDB();
        await db.clear('suppliers');
      } catch (error) {
        console.warn('Could not clear IndexedDB:', error);
      }
      
      // Force reload data with no-cache headers
      await loadSuppliers(true);
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  useEffect(() => {
    loadSuppliers();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingSupplier) {
        // Mode édition
        if (isOnline) {
          await api.put(`/suppliers/${editingSupplier.id}`, formData);
          toast.success('Fournisseur mis à jour avec succès');
          setShowDialog(false);
          resetForm();
          await refreshData();
        } else {
          const updatedSupplier = { ...formData, id: editingSupplier.id };
          await updateItem('suppliers', updatedSupplier);
          await addLocalChange('supplier', 'update', updatedSupplier);
          toast.success('Fournisseur mis à jour (synchronisation en attente)');
          setShowDialog(false);
          resetForm();
          await loadSuppliers();
        }
      } else {
        // Mode création
        if (isOnline) {
          const response = await api.post('/suppliers', formData);
          await addItem('suppliers', response.data);
          toast.success('Fournisseur ajouté avec succès');
          setShowDialog(false);
          resetForm();
          await refreshData();
        } else {
          const newSupplier = { ...formData, id: crypto.randomUUID(), is_active: true };
          await addItem('suppliers', newSupplier);
          await addLocalChange('supplier', 'create', newSupplier);
          toast.success('Fournisseur ajouté (synchronisation en attente)');
          setShowDialog(false);
          resetForm();
          await loadSuppliers();
        }
      }
    } catch (error) {
      console.error('Error saving supplier:', error);
      toast.error('Erreur lors de l\'enregistrement du fournisseur');
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

  const handleDeleteConfirm = async () => {
    if (!supplierToDelete) return;
    
    try {
      if (isOnline) {
        await api.delete(`/suppliers/${supplierToDelete.id}`);
        toast.success('Fournisseur supprimé avec succès');
        await refreshData();
      } else {
        await deleteFromDB('suppliers', supplierToDelete.id);
        await addLocalChange('supplier', 'delete', { id: supplierToDelete.id });
        toast.success('Fournisseur supprimé (synchronisation en attente)');
        await loadSuppliers();
      }
      setShowDeleteDialog(false);
      setSupplierToDelete(null);
    } catch (error) {
      console.error('Error deleting supplier:', error);
      // Afficher le message d'erreur du serveur (règle d'affaires)
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression du fournisseur';
      toast.error(errorMessage);
      setShowDeleteDialog(false);
      setSupplierToDelete(null);
    }
  };

  const handleToggleStatus = async (supplier) => {
    if (!isAdmin) {
      toast.error('Seul l\'administrateur peut activer/désactiver les fournisseurs');
      return;
    }

    try {
      if (isOnline) {
        const response = await api.patch(`/suppliers/${supplier.id}/toggle-status`);
        const newStatus = response.data.is_active;
        toast.success(newStatus ? 'Fournisseur activé' : 'Fournisseur désactivé');
        await refreshData();
      } else {
        const updatedSupplier = { ...supplier, is_active: !supplier.is_active };
        await updateItem('suppliers', updatedSupplier);
        await addLocalChange('supplier', 'update', updatedSupplier);
        toast.success('Statut modifié (synchronisation en attente)');
        await loadSuppliers();
      }
    } catch (error) {
      console.error('Error toggling supplier status:', error);
      toast.error('Erreur lors du changement de statut');
    }
  };

  const resetForm = () => {
    setEditingSupplier(null);
    setFormData({ name: '', phone: '', email: '', address: '' });
  };

  // Filtrer les fournisseurs
  let filteredSuppliers = suppliers.filter((s) =>
    s.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.phone?.includes(searchQuery)
  );

  // Admin: filtrer par statut si nécessaire
  if (isAdmin && !showInactive) {
    filteredSuppliers = filteredSuppliers.filter(s => s.is_active !== false);
  }

  // Trier: actifs en premier
  filteredSuppliers.sort((a, b) => {
    const aActive = a.is_active !== false ? 1 : 0;
    const bActive = b.is_active !== false ? 1 : 0;
    if (aActive !== bActive) return bActive - aActive;
    return (a.name || '').localeCompare(b.name || '');
  });

  const activeCount = suppliers.filter(s => s.is_active !== false).length;
  const inactiveCount = suppliers.filter(s => s.is_active === false).length;

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
              Gestion des fournisseurs
              {isAdmin && (
                <span className="ml-2 text-sm">
                  ({activeCount} actif{activeCount > 1 ? 's' : ''}, {inactiveCount} inactif{inactiveCount > 1 ? 's' : ''})
                </span>
              )}
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-supplier-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un fournisseur
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
                  <Button type="submit" data-testid="supplier-submit-button" className="bg-teal-700 hover:bg-teal-800">
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
            />
          </div>
          
          {/* Filtre Admin: Afficher/Masquer inactifs */}
          {isAdmin && (
            <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 rounded-lg">
              <Filter className="w-4 h-4 text-slate-500" />
              <Label htmlFor="show-inactive" className="text-sm text-slate-600 cursor-pointer">
                Afficher inactifs
              </Label>
              <Switch
                id="show-inactive"
                checked={showInactive}
                onCheckedChange={setShowInactive}
              />
              {showInactive ? (
                <Eye className="w-4 h-4 text-emerald-600" />
              ) : (
                <EyeOff className="w-4 h-4 text-slate-400" />
              )}
            </div>
          )}
        </div>

        {/* Suppliers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSuppliers.map((supplier) => {
            const isActive = supplier.is_active !== false;
            
            return (
              <div
                key={supplier.id}
                data-testid={`supplier-card-${supplier.id}`}
                className={`p-6 rounded-xl bg-white border transition-all ${
                  isActive 
                    ? 'border-slate-100 hover:border-teal-200' 
                    : 'border-red-100 bg-red-50/30 opacity-75'
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${isActive ? 'bg-teal-50' : 'bg-red-100'}`}>
                      <Truck className={`w-5 h-5 ${isActive ? 'text-teal-700' : 'text-red-500'}`} strokeWidth={1.5} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                        {supplier.name}
                      </h3>
                      {/* Badge statut */}
                      <Badge 
                        variant={isActive ? 'default' : 'destructive'}
                        className={`mt-1 text-xs ${isActive ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100' : ''}`}
                      >
                        {isActive ? 'Actif' : 'Inactif'}
                      </Badge>
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
                    >
                      {isActive ? (
                        <PowerOff className="w-4 h-4" strokeWidth={1.5} />
                      ) : (
                        <Power className="w-4 h-4" strokeWidth={1.5} />
                      )}
                    </Button>
                  )}
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(supplier)}
                    data-testid={`delete-supplier-${supplier.id}`}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        {filteredSuppliers.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Truck className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              {searchQuery ? 'Aucun fournisseur trouvé' : 'Aucun fournisseur enregistré'}
            </p>
          </div>
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
            >
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Suppliers;
