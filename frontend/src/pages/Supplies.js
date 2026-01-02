import React, { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Package, 
  Truck, 
  CheckCircle2, 
  Clock, 
  FileText,
  Calendar,
  User,
  ShoppingCart,
  AlertTriangle,
  Eye,
  X,
  RefreshCw,
  PlusCircle
} from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

const Supplies = () => {
  const { user } = useAuth();
  const [appSettings, setAppSettings] = useState({ currency: 'GNF' });
  const [supplies, setSupplies] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showDialog, setShowDialog] = useState(false);
  const [showViewDialog, setShowViewDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showValidateDialog, setShowValidateDialog] = useState(false);
  const [showAddSupplierDialog, setShowAddSupplierDialog] = useState(false);
  const [showAddProductDialog, setShowAddProductDialog] = useState(false);
  const [editingSupply, setEditingSupply] = useState(null);
  const [viewingSupply, setViewingSupply] = useState(null);
  const [supplyToDelete, setSupplyToDelete] = useState(null);
  const [supplyToValidate, setSupplyToValidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  
  // Form state
  const [formData, setFormData] = useState({
    supply_date: new Date().toISOString().split('T')[0],
    supplier_id: '',
    purchase_order_ref: '',
    delivery_note_number: '',
    invoice_number: '',
    is_credit_note: false,
    notes: '',
    items: []
  });
  
  // Item form state
  const [itemForm, setItemForm] = useState({
    product_id: '',
    quantity: '',
    unit_price: ''
  });
  const [productSearch, setProductSearch] = useState('');

  // Quick add supplier form
  const [supplierForm, setSupplierForm] = useState({
    name: '',
    contact: '',
    phone: '',
    email: '',
    address: ''
  });

  // Quick add product form
  const [productForm, setProductForm] = useState({
    name: '',
    internal_reference: '',
    barcode: '',
    purchase_price: '',
    price: '',
    stock: '0',
    min_stock: '10'
  });

  // Check if user is admin
  const isAdmin = user?.role === 'admin';

  // Load settings
  const loadAppSettings = async () => {
    try {
      const response = await api.get('/settings');
      setAppSettings(response.data);
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const formatAmount = (amount) => {
    const currency = appSettings?.currency || 'EUR';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${formatted} ${symbols[currency] || currency}`;
  };

  const loadSupplies = async () => {
    try {
      setLoading(true);
      const response = await api.get('/supplies');
      // L'API retourne déjà trié: En attente d'abord, puis par date décroissante
      console.log('Supplies loaded:', response.data.map(s => ({id: s.id?.slice(0,8), is_validated: s.is_validated})));
      setSupplies(response.data);
    } catch (error) {
      console.error('Error loading supplies:', error);
      toast.error('Erreur lors du chargement des approvisionnements');
    } finally {
      setLoading(false);
    }
  };

  const loadSuppliers = useCallback(async () => {
    try {
      const response = await api.get('/suppliers');
      setSuppliers(response.data);
    } catch (error) {
      console.error('Error loading suppliers:', error);
    }
  }, []);

  const loadProducts = useCallback(async () => {
    try {
      const response = await api.get('/products');
      setProducts(response.data.filter(p => p.is_active !== false));
    } catch (error) {
      console.error('Error loading products:', error);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      await loadAppSettings();
      await Promise.all([loadSupplies(), loadSuppliers(), loadProducts()]);
    };
    init();
  }, [loadSuppliers, loadProducts]);

  // Rafraîchir le formulaire
  const refreshForm = useCallback(() => {
    setRefreshKey(prev => prev + 1);
    toast.success('Liste mise à jour');
  }, []);

  const resetForm = () => {
    setEditingSupply(null);
    setFormData({
      supply_date: new Date().toISOString().split('T')[0],
      supplier_id: '',
      purchase_order_ref: '',
      delivery_note_number: '',
      invoice_number: '',
      is_credit_note: false,
      notes: '',
      items: []
    });
    setItemForm({ product_id: '', quantity: '', unit_price: '' });
    setProductSearch('');
  };

  const handleAddItem = () => {
    if (!itemForm.product_id || !itemForm.quantity || !itemForm.unit_price) {
      toast.error('Veuillez remplir tous les champs du produit');
      return;
    }
    
    const product = products.find(p => p.id === itemForm.product_id);
    if (!product) return;
    
    // Check if product already in list
    const existingIndex = formData.items.findIndex(item => item.product_id === itemForm.product_id);
    
    if (existingIndex >= 0) {
      // Update existing item
      const updatedItems = [...formData.items];
      updatedItems[existingIndex] = {
        ...updatedItems[existingIndex],
        quantity: parseInt(itemForm.quantity),
        unit_price: parseFloat(itemForm.unit_price),
        total_price: parseInt(itemForm.quantity) * parseFloat(itemForm.unit_price)
      };
      setFormData({ ...formData, items: updatedItems });
      toast.success(`Produit "${product.name}" mis à jour`);
    } else {
      // Add new item
      const newItem = {
        id: crypto.randomUUID(),
        product_id: itemForm.product_id,
        product_name: product.name,
        quantity: parseInt(itemForm.quantity),
        unit_price: parseFloat(itemForm.unit_price),
        total_price: parseInt(itemForm.quantity) * parseFloat(itemForm.unit_price)
      };
      setFormData({ ...formData, items: [...formData.items, newItem] });
      toast.success(`Produit "${product.name}" ajouté`);
    }
    
    setItemForm({ product_id: '', quantity: '', unit_price: '' });
    setProductSearch('');
    refreshForm();
  };

  const handleRemoveItem = (itemId) => {
    const item = formData.items.find(i => i.id === itemId);
    setFormData({
      ...formData,
      items: formData.items.filter(item => item.id !== itemId)
    });
    toast.success(`Produit "${item?.product_name}" retiré`);
    refreshForm();
  };

  const handleEditItem = (item) => {
    setItemForm({
      product_id: item.product_id,
      quantity: item.quantity.toString(),
      unit_price: item.unit_price.toString()
    });
    setProductSearch(item.product_name);
  };

  const handleSelectProduct = (productId) => {
    const product = products.find(p => p.id === productId);
    if (product) {
      setItemForm({
        ...itemForm,
        product_id: productId,
        unit_price: (product.purchase_price || 0).toString()
      });
      setProductSearch('');
    }
  };

  const calculateTotal = () => {
    return formData.items.reduce((sum, item) => sum + (item.total_price || 0), 0);
  };

  // Quick add supplier
  const handleAddSupplier = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/suppliers', supplierForm);
      toast.success('Fournisseur ajouté avec succès');
      setShowAddSupplierDialog(false);
      setSupplierForm({ name: '', contact: '', phone: '', email: '', address: '' });
      await loadSuppliers();
      // Sélectionner automatiquement le nouveau fournisseur
      setFormData({ ...formData, supplier_id: response.data.id });
    } catch (error) {
      console.error('Error adding supplier:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'ajout du fournisseur');
    }
  };

  // Quick add product
  const handleAddProduct = async (e) => {
    e.preventDefault();
    try {
      const productData = {
        name: productForm.name,
        internal_reference: productForm.internal_reference || null,
        barcode: productForm.barcode || null,
        purchase_price: parseFloat(productForm.purchase_price) || 0,
        price: parseFloat(productForm.price) || 0,
        stock: parseInt(productForm.stock) || 0,
        min_stock: parseInt(productForm.min_stock) || 10
      };
      const response = await api.post('/products', productData);
      toast.success('Produit ajouté avec succès');
      setShowAddProductDialog(false);
      setProductForm({ name: '', internal_reference: '', barcode: '', purchase_price: '', price: '', stock: '0', min_stock: '10' });
      await loadProducts();
      // Pré-sélectionner le nouveau produit
      setItemForm({
        product_id: response.data.id,
        quantity: '',
        unit_price: productData.purchase_price.toString()
      });
      setProductSearch(response.data.name);
    } catch (error) {
      console.error('Error adding product:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'ajout du produit');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.items.length === 0) {
      toast.error('Veuillez ajouter au moins un produit');
      return;
    }
    
    try {
      const submitData = {
        supply_date: new Date(formData.supply_date).toISOString(),
        supplier_id: formData.supplier_id || null,
        purchase_order_ref: formData.purchase_order_ref || null,
        delivery_note_number: formData.delivery_note_number || null,
        invoice_number: formData.invoice_number || null,
        is_credit_note: formData.is_credit_note,
        notes: formData.notes || null,
        items: formData.items.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          unit_price: item.unit_price
        }))
      };
      
      if (editingSupply) {
        await api.put(`/supplies/${editingSupply.id}`, submitData);
        toast.success('Approvisionnement mis à jour');
      } else {
        await api.post('/supplies', submitData);
        toast.success('Approvisionnement créé (en attente de validation)');
      }
      
      setShowDialog(false);
      resetForm();
      await loadSupplies();
    } catch (error) {
      console.error('Error saving supply:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'enregistrement');
    }
  };

  const handleEdit = (supply) => {
    if (supply.is_validated) {
      toast.error('Impossible de modifier un approvisionnement validé');
      return;
    }
    
    setEditingSupply(supply);
    setFormData({
      supply_date: supply.supply_date ? new Date(supply.supply_date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
      supplier_id: supply.supplier_id || '',
      purchase_order_ref: supply.purchase_order_ref || '',
      delivery_note_number: supply.delivery_note_number || '',
      invoice_number: supply.invoice_number || '',
      is_credit_note: supply.is_credit_note || false,
      notes: supply.notes || '',
      items: supply.items || []
    });
    setShowDialog(true);
  };

  const handleView = (supply) => {
    setViewingSupply(supply);
    setShowViewDialog(true);
  };

  const handleDelete = (supply) => {
    if (supply.is_validated) {
      toast.error('Impossible de supprimer un approvisionnement validé');
      return;
    }
    setSupplyToDelete(supply);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!supplyToDelete) return;
    
    try {
      await api.delete(`/supplies/${supplyToDelete.id}`);
      toast.success('Approvisionnement supprimé');
      setShowDeleteDialog(false);
      setSupplyToDelete(null);
      await loadSupplies();
    } catch (error) {
      console.error('Error deleting supply:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const handleValidate = (supply) => {
    if (!isAdmin) {
      toast.error('Seul un administrateur peut valider un approvisionnement');
      return;
    }
    setSupplyToValidate(supply);
    setShowValidateDialog(true);
  };

  const handleValidateConfirm = async () => {
    if (!supplyToValidate) return;
    
    try {
      await api.post(`/supplies/${supplyToValidate.id}/validate`);
      toast.success('Approvisionnement validé - Stocks mis à jour');
      setShowValidateDialog(false);
      setSupplyToValidate(null);
      await loadSupplies();
    } catch (error) {
      console.error('Error validating supply:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la validation');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric' 
    });
  };

  const filteredSupplies = supplies
    .filter(supply => {
      // Si pas de recherche, tout passe
      const matchesSearch = !searchQuery || 
        supply.purchase_order_ref?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        supply.delivery_note_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        supply.invoice_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        supply.supplier_name?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = 
        statusFilter === 'all' ||
        (statusFilter === 'pending' && supply.is_validated === false) ||
        (statusFilter === 'validated' && supply.is_validated === true);
      
      return matchesSearch && matchesStatus;
    });

  const pendingCount = supplies.filter(s => s.is_validated === false).length;
  const validatedCount = supplies.filter(s => s.is_validated === true).length;

  const filteredProducts = products.filter(p => 
    productSearch && (
      p.name?.toLowerCase().includes(productSearch.toLowerCase()) ||
      p.internal_reference?.toLowerCase().includes(productSearch.toLowerCase()) ||
      p.barcode?.toLowerCase().includes(productSearch.toLowerCase())
    )
  );

  return (
    <Layout>
      <div className="space-y-6" data-testid="supplies-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Approvisionnements
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des entrées de stock • {supplies.length} approvisionnement{supplies.length > 1 ? 's' : ''}
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { 
            setShowDialog(open); 
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button data-testid="add-supply-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Nouvel approvisionnement
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingSupply ? 'Modifier l\'approvisionnement' : 'Nouvel approvisionnement'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Info générale */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="supply_date">Date d'approvisionnement *</Label>
                    <Input
                      id="supply_date"
                      type="date"
                      value={formData.supply_date}
                      onChange={(e) => setFormData({ ...formData, supply_date: e.target.value })}
                      required
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="supplier" className="flex items-center justify-between">
                      Fournisseur
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowAddSupplierDialog(true)}
                        className="h-6 px-2 text-xs text-teal-600 hover:text-teal-700"
                      >
                        <PlusCircle className="w-3 h-3 mr-1" />
                        Nouveau
                      </Button>
                    </Label>
                    <Select 
                      value={formData.supplier_id || 'none'} 
                      onValueChange={(value) => setFormData({ ...formData, supplier_id: value === 'none' ? '' : value })}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Sélectionner un fournisseur" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Aucun fournisseur</SelectItem>
                        {suppliers.map((supplier) => (
                          <SelectItem key={supplier.id} value={supplier.id}>
                            {supplier.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="purchase_order_ref">Réf. Bon de commande</Label>
                    <Input
                      id="purchase_order_ref"
                      value={formData.purchase_order_ref}
                      onChange={(e) => setFormData({ ...formData, purchase_order_ref: e.target.value })}
                      placeholder="BC-001"
                      className="mt-1"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="delivery_note_number">N° Bon de livraison</Label>
                    <Input
                      id="delivery_note_number"
                      value={formData.delivery_note_number}
                      onChange={(e) => setFormData({ ...formData, delivery_note_number: e.target.value })}
                      placeholder="BL-001"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="invoice_number">N° Facture</Label>
                    <Input
                      id="invoice_number"
                      value={formData.invoice_number}
                      onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                      placeholder="FACT-001"
                      className="mt-1"
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-slate-50">
                      <input
                        type="checkbox"
                        checked={formData.is_credit_note}
                        onChange={(e) => setFormData({ ...formData, is_credit_note: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-300"
                      />
                      <span className="text-sm text-slate-700">Avoir</span>
                    </label>
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="notes">Notes</Label>
                  <Input
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Notes ou observations..."
                    className="mt-1"
                  />
                </div>

                {/* Section Produits */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-slate-900 flex items-center gap-2">
                      <Package className="w-5 h-5 text-teal-600" />
                      Produits à approvisionner
                    </h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddProductDialog(true)}
                      className="text-teal-600 hover:text-teal-700"
                    >
                      <PlusCircle className="w-4 h-4 mr-1" />
                      Nouveau produit
                    </Button>
                  </div>
                  
                  {/* Formulaire d'ajout de produit */}
                  <div className="p-4 bg-slate-50 rounded-lg mb-4" key={refreshKey}>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <div className="md:col-span-2 relative">
                        <Label className="text-sm">Rechercher un produit</Label>
                        <div className="relative mt-1">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                          <Input
                            placeholder="Nom, référence ou code-barres..."
                            value={productSearch}
                            onChange={(e) => setProductSearch(e.target.value)}
                            className="pl-9"
                          />
                        </div>
                        {productSearch && filteredProducts.length > 0 && (
                          <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                            {filteredProducts.slice(0, 8).map(product => (
                              <button
                                key={product.id}
                                type="button"
                                onClick={() => handleSelectProduct(product.id)}
                                className="w-full text-left px-3 py-2 hover:bg-slate-50 flex justify-between items-center"
                              >
                                <div>
                                  <p className="font-medium text-sm">{product.name}</p>
                                  <p className="text-xs text-slate-500">
                                    {product.internal_reference && `Réf: ${product.internal_reference}`}
                                    {product.internal_reference && product.barcode && ' • '}
                                    {product.barcode && `Code: ${product.barcode}`}
                                  </p>
                                </div>
                                <span className="text-xs text-slate-400">Stock: {product.stock}</span>
                              </button>
                            ))}
                          </div>
                        )}
                        {itemForm.product_id && (
                          <p className="text-xs text-teal-600 mt-1">
                            ✓ {products.find(p => p.id === itemForm.product_id)?.name}
                          </p>
                        )}
                      </div>
                      <div>
                        <Label className="text-sm">Quantité</Label>
                        <Input
                          type="number"
                          min="1"
                          value={itemForm.quantity}
                          onChange={(e) => setItemForm({ ...itemForm, quantity: e.target.value })}
                          placeholder="0"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">Prix d'achat unitaire</Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={itemForm.unit_price}
                          onChange={(e) => setItemForm({ ...itemForm, unit_price: e.target.value })}
                          placeholder="0.00"
                          className="mt-1"
                        />
                      </div>
                    </div>
                    <div className="mt-3 flex justify-end">
                      <Button
                        type="button"
                        onClick={handleAddItem}
                        variant="outline"
                        size="sm"
                        disabled={!itemForm.product_id || !itemForm.quantity || !itemForm.unit_price}
                      >
                        <Plus className="w-4 h-4 mr-1" />
                        Ajouter le produit
                      </Button>
                    </div>
                  </div>

                  {/* Liste des produits */}
                  {formData.items.length === 0 ? (
                    <div className="text-center py-8 border-2 border-dashed border-slate-200 rounded-lg">
                      <Package className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                      <p className="text-sm text-slate-500">Aucun produit ajouté</p>
                      <p className="text-xs text-slate-400">Recherchez et ajoutez des produits ci-dessus</p>
                    </div>
                  ) : (
                    <div className="border border-slate-200 rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="text-left px-4 py-2 font-medium text-slate-600">Produit</th>
                            <th className="text-right px-4 py-2 font-medium text-slate-600">Qté</th>
                            <th className="text-right px-4 py-2 font-medium text-slate-600">Prix unit.</th>
                            <th className="text-right px-4 py-2 font-medium text-slate-600">Total</th>
                            <th className="px-4 py-2 w-20"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {formData.items.map((item) => (
                            <tr key={item.id} className="hover:bg-slate-50">
                              <td className="px-4 py-2 font-medium text-slate-900">{item.product_name}</td>
                              <td className="px-4 py-2 text-right">{item.quantity}</td>
                              <td className="px-4 py-2 text-right">{formatAmount(item.unit_price)}</td>
                              <td className="px-4 py-2 text-right font-medium">{formatAmount(item.total_price)}</td>
                              <td className="px-4 py-2">
                                <div className="flex gap-1 justify-end">
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleEditItem(item)}
                                    className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 h-7 w-7 p-0"
                                    title="Modifier"
                                  >
                                    <Edit className="w-3.5 h-3.5" />
                                  </Button>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleRemoveItem(item.id)}
                                    className="text-red-600 hover:text-red-700 hover:bg-red-50 h-7 w-7 p-0"
                                    title="Supprimer"
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot className="bg-teal-50">
                          <tr>
                            <td colSpan="3" className="px-4 py-3 font-medium text-slate-700">
                              Total approvisionnement ({formData.items.length} produit{formData.items.length > 1 ? 's' : ''})
                            </td>
                            <td className="px-4 py-3 text-right font-bold text-teal-700 text-lg">{formatAmount(calculateTotal())}</td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t">
                  <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                    Annuler
                  </Button>
                  <Button type="submit" className="bg-teal-700 hover:bg-teal-800" disabled={formData.items.length === 0}>
                    {editingSupply ? 'Mettre à jour' : 'Enregistrer (en attente)'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{pendingCount}</p>
                <p className="text-sm text-slate-500">En attente</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{validatedCount}</p>
                <p className="text-sm text-slate-500">Validés</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-teal-100 rounded-lg">
                <ShoppingCart className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{supplies.length}</p>
                <p className="text-sm text-slate-500">Total</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              placeholder="Rechercher par référence, bon de livraison, facture ou fournisseur..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filtrer par statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les statuts</SelectItem>
              <SelectItem value="pending">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-600" />
                  En attente
                </div>
              </SelectItem>
              <SelectItem value="validated">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Validés
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Supplies List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700 mx-auto"></div>
            <p className="text-slate-500 mt-4">Chargement...</p>
          </div>
        ) : filteredSupplies.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Truck className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">Aucun approvisionnement trouvé</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredSupplies.map((supply) => (
              <div
                key={supply.id}
                className={`bg-white rounded-xl border p-4 transition-all ${
                  supply.is_validated 
                    ? 'border-emerald-200' 
                    : 'border-amber-200 bg-amber-50/30'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                        supply.is_validated 
                          ? 'bg-emerald-100 text-emerald-700' 
                          : 'bg-amber-100 text-amber-700'
                      }`}>
                        {supply.is_validated ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Validé
                          </>
                        ) : (
                          <>
                            <Clock className="w-3.5 h-3.5" />
                            En attente
                          </>
                        )}
                      </span>
                      {supply.is_credit_note && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                          Avoir
                        </span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          Date
                        </p>
                        <p className="font-medium text-slate-900">{formatDate(supply.supply_date)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <Truck className="w-3.5 h-3.5" />
                          Fournisseur
                        </p>
                        <p className="font-medium text-slate-900">{supply.supplier_name || 'Non spécifié'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" />
                          Références
                        </p>
                        <p className="font-medium text-slate-900 text-xs">
                          {supply.purchase_order_ref && <span className="block">BC: {supply.purchase_order_ref}</span>}
                          {supply.delivery_note_number && <span className="block">BL: {supply.delivery_note_number}</span>}
                          {supply.invoice_number && <span className="block">Fact: {supply.invoice_number}</span>}
                          {!supply.purchase_order_ref && !supply.delivery_note_number && !supply.invoice_number && '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <Package className="w-3.5 h-3.5" />
                          Produits / Montant
                        </p>
                        <p className="font-medium text-slate-900">
                          {supply.items?.length || 0} article{(supply.items?.length || 0) > 1 ? 's' : ''}
                        </p>
                        <p className="font-bold text-teal-700">{formatAmount(supply.total_amount)}</p>
                      </div>
                    </div>
                    
                    <div className="mt-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        Saisi par {supply.created_by_name || 'Inconnu'} le {formatDate(supply.created_at)}
                        {supply.is_validated && supply.validated_at && (
                          <span className="ml-2 text-emerald-600">
                            • Validé le {formatDate(supply.validated_at)}
                          </span>
                        )}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleView(supply)}
                      title="Voir détails"
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    {!supply.is_validated && (
                      <>
                        {isAdmin && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleValidate(supply)}
                            className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                            title="Valider (Admin uniquement)"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(supply)}
                          title="Modifier"
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(supply)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          title="Supprimer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* View Dialog */}
      <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-teal-600" />
              Détails de l'approvisionnement
            </DialogTitle>
          </DialogHeader>
          {viewingSupply && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium ${
                  viewingSupply.is_validated 
                    ? 'bg-emerald-100 text-emerald-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {viewingSupply.is_validated ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      Validé
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4" />
                      En attente de validation
                    </>
                  )}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Date d'approvisionnement</p>
                  <p className="font-medium">{formatDate(viewingSupply.supply_date)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Fournisseur</p>
                  <p className="font-medium">{viewingSupply.supplier_name || 'Non spécifié'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Réf. Bon de commande</p>
                  <p className="font-medium">{viewingSupply.purchase_order_ref || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">N° Bon de livraison</p>
                  <p className="font-medium">{viewingSupply.delivery_note_number || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">N° Facture</p>
                  <p className="font-medium">{viewingSupply.invoice_number || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Saisi par</p>
                  <p className="font-medium">{viewingSupply.created_by_name || 'Inconnu'}</p>
                </div>
              </div>
              
              {viewingSupply.notes && (
                <div>
                  <p className="text-slate-500 text-sm">Notes</p>
                  <p className="font-medium">{viewingSupply.notes}</p>
                </div>
              )}
              
              <div className="border-t pt-4">
                <h4 className="font-medium text-slate-900 mb-3">Produits ({viewingSupply.items?.length || 0})</h4>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="text-left px-4 py-2 font-medium text-slate-600">Produit</th>
                        <th className="text-right px-4 py-2 font-medium text-slate-600">Qté</th>
                        <th className="text-right px-4 py-2 font-medium text-slate-600">Prix unit.</th>
                        <th className="text-right px-4 py-2 font-medium text-slate-600">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {viewingSupply.items?.map((item, index) => (
                        <tr key={index}>
                          <td className="px-4 py-2 font-medium">{item.product_name}</td>
                          <td className="px-4 py-2 text-right">{item.quantity}</td>
                          <td className="px-4 py-2 text-right">{formatAmount(item.unit_price)}</td>
                          <td className="px-4 py-2 text-right font-medium">{formatAmount(item.total_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-teal-50">
                      <tr>
                        <td colSpan="3" className="px-4 py-3 font-medium">Total</td>
                        <td className="px-4 py-3 text-right font-bold text-teal-700">{formatAmount(viewingSupply.total_amount)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Quick Add Supplier Dialog */}
      <Dialog open={showAddSupplierDialog} onOpenChange={setShowAddSupplierDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-teal-600" />
              Nouveau fournisseur
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddSupplier} className="space-y-4">
            <div>
              <Label htmlFor="supplier-name">Nom *</Label>
              <Input
                id="supplier-name"
                value={supplierForm.name}
                onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                required
                placeholder="Nom du fournisseur"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="supplier-contact">Contact</Label>
              <Input
                id="supplier-contact"
                value={supplierForm.contact}
                onChange={(e) => setSupplierForm({ ...supplierForm, contact: e.target.value })}
                placeholder="Personne de contact"
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="supplier-phone">Téléphone</Label>
                <Input
                  id="supplier-phone"
                  value={supplierForm.phone}
                  onChange={(e) => setSupplierForm({ ...supplierForm, phone: e.target.value })}
                  placeholder="+224 xxx"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="supplier-email">Email</Label>
                <Input
                  id="supplier-email"
                  type="email"
                  value={supplierForm.email}
                  onChange={(e) => setSupplierForm({ ...supplierForm, email: e.target.value })}
                  placeholder="email@exemple.com"
                  className="mt-1"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="supplier-address">Adresse</Label>
              <Input
                id="supplier-address"
                value={supplierForm.address}
                onChange={(e) => setSupplierForm({ ...supplierForm, address: e.target.value })}
                placeholder="Adresse complète"
                className="mt-1"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowAddSupplierDialog(false)}>
                Annuler
              </Button>
              <Button type="submit" className="bg-teal-700 hover:bg-teal-800">
                Ajouter
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Quick Add Product Dialog */}
      <Dialog open={showAddProductDialog} onOpenChange={setShowAddProductDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-teal-600" />
              Nouveau produit
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddProduct} className="space-y-4">
            <div>
              <Label htmlFor="product-name">Nom du produit *</Label>
              <Input
                id="product-name"
                value={productForm.name}
                onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                required
                placeholder="Nom du produit"
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="product-ref">Référence interne</Label>
                <Input
                  id="product-ref"
                  value={productForm.internal_reference}
                  onChange={(e) => setProductForm({ ...productForm, internal_reference: e.target.value.toUpperCase() })}
                  placeholder="MED-001"
                  className="mt-1 font-mono"
                />
              </div>
              <div>
                <Label htmlFor="product-barcode">Code-barres</Label>
                <Input
                  id="product-barcode"
                  value={productForm.barcode}
                  onChange={(e) => setProductForm({ ...productForm, barcode: e.target.value })}
                  placeholder="123456789"
                  className="mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="product-purchase">Prix d'achat *</Label>
                <Input
                  id="product-purchase"
                  type="number"
                  step="0.01"
                  min="0"
                  value={productForm.purchase_price}
                  onChange={(e) => setProductForm({ ...productForm, purchase_price: e.target.value })}
                  required
                  placeholder="0.00"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="product-price">Prix de vente *</Label>
                <Input
                  id="product-price"
                  type="number"
                  step="0.01"
                  min="0"
                  value={productForm.price}
                  onChange={(e) => setProductForm({ ...productForm, price: e.target.value })}
                  required
                  placeholder="0.00"
                  className="mt-1"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="product-stock">Stock initial</Label>
                <Input
                  id="product-stock"
                  type="number"
                  min="0"
                  value={productForm.stock}
                  onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="product-minstock">Stock minimum</Label>
                <Input
                  id="product-minstock"
                  type="number"
                  min="0"
                  value={productForm.min_stock}
                  onChange={(e) => setProductForm({ ...productForm, min_stock: e.target.value })}
                  className="mt-1"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowAddProductDialog(false)}>
                Annuler
              </Button>
              <Button type="submit" className="bg-teal-700 hover:bg-teal-800">
                Ajouter
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer cet approvisionnement ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowDeleteDialog(false); setSupplyToDelete(null); }}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Validate Confirmation */}
      <AlertDialog open={showValidateDialog} onOpenChange={setShowValidateDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              Confirmer la validation
            </AlertDialogTitle>
            <AlertDialogDescription>
              <div className="space-y-2">
                <p>Voulez-vous valider cet approvisionnement ?</p>
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium">Cette action va :</p>
                      <ul className="list-disc list-inside mt-1 text-amber-700">
                        <li>Mettre à jour les stocks des {supplyToValidate?.items?.length || 0} produit(s)</li>
                        <li>Rendre l'approvisionnement non modifiable</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowValidateDialog(false); setSupplyToValidate(null); }}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleValidateConfirm} className="bg-emerald-600 hover:bg-emerald-700">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Valider l'approvisionnement
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Supplies;
