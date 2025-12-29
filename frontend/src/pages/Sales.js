import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Plus, Search, ShoppingCart, Trash2, X, Eye, CreditCard, Banknote, FileCheck } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import api from '../services/api';
import { addItem, getAllItems, addLocalChange, deleteItem as deleteFromDB, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

const Sales = () => {
  const { user } = useAuth();
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedSale, setSelectedSale] = useState(null);
  const [saleToDelete, setSaleToDelete] = useState(null);
  const [cart, setCart] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [productSearch, setProductSearch] = useState('');
  const [customerSearch, setCustomerSearch] = useState('');
  const [showCustomerDropdown, setShowCustomerDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { isOnline } = useOffline();

  const isAdmin = user?.role === 'admin';

  const loadData = async (forceRefresh = false) => {
    try {
      if (isOnline) {
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache' } : {};
        const [salesRes, productsRes, customersRes] = await Promise.all([
          api.get('/sales', { headers }),
          api.get('/products', { headers }).catch(() => ({ data: [] })),
          api.get('/customers', { headers }),
        ]);
        setSales(salesRes.data);
        setProducts(productsRes.data);
        setCustomers(customersRes.data);
      } else {
        const [localSales, localProducts, localCustomers] = await Promise.all([
          getAllItems('sales'),
          getAllItems('products'),
          getAllItems('customers'),
        ]);
        setSales(localSales);
        setProducts(localProducts);
        setCustomers(localCustomers);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  const refreshData = async () => {
    try {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
      }
      
      try {
        const db = await getDB();
        await db.clear('sales');
      } catch (error) {
        console.warn('Could not clear IndexedDB:', error);
      }
      
      await loadData(true);
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  useEffect(() => {
    loadData();
  }, []); // eslint-disable-line

  const addToCart = (product) => {
    if (product.stock <= 0) {
      toast.error('Produit en rupture de stock');
      return;
    }
    
    const existing = cart.find((item) => item.product_id === product.id);
    if (existing) {
      if (existing.quantity >= product.stock) {
        toast.error('Stock insuffisant');
        return;
      }
      setCart(
        cart.map((item) =>
          item.product_id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      );
    } else {
      setCart([...cart, { product_id: product.id, name: product.name, price: product.price, quantity: 1, max_stock: product.stock }]);
    }
    toast.success(`${product.name} ajouté au panier`);
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter((item) => item.product_id !== productId));
  };

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    const item = cart.find(i => i.product_id === productId);
    if (item && quantity > item.max_stock) {
      toast.error('Stock insuffisant');
      return;
    }
    setCart(
      cart.map((item) =>
        item.product_id === productId ? { ...item, quantity: parseInt(quantity) } : item
      )
    );
  };

  const calculateTotal = () => {
    return cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (cart.length === 0) {
      toast.error('Le panier est vide');
      return;
    }

    try {
      const saleData = {
        customer_id: selectedCustomer && selectedCustomer !== 'none' ? selectedCustomer : null,
        items: cart.map(({ product_id, name, price, quantity }) => ({ product_id, name, price, quantity })),
        total: calculateTotal(),
        payment_method: paymentMethod,
      };

      if (isOnline) {
        const response = await api.post('/sales', saleData);
        await addItem('sales', response.data);
      } else {
        const newSale = { ...saleData, id: crypto.randomUUID(), created_at: new Date().toISOString() };
        await addItem('sales', newSale);
        await addLocalChange('sales', 'create', newSale);
      }

      toast.success('Vente enregistrée avec succès');
      setCart([]);
      setSelectedCustomer('');
      setCustomerSearch('');
      setPaymentMethod('cash');
      setProductSearch('');
      setShowDialog(false);
      await refreshData();
    } catch (error) {
      console.error('Error creating sale:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'enregistrement de la vente');
    }
  };

  const handleViewDetails = (sale) => {
    setSelectedSale(sale);
    setShowDetailDialog(true);
  };

  const handleDeleteClick = (sale) => {
    setSaleToDelete(sale);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!saleToDelete) return;
    
    try {
      if (isOnline) {
        await api.delete(`/sales/${saleToDelete.id}`);
        toast.success('Vente supprimée et stock restauré');
        await refreshData();
      } else {
        await deleteFromDB('sales', saleToDelete.id);
        toast.success('Vente supprimée (hors ligne)');
        await loadData();
      }
      setShowDeleteDialog(false);
      setSaleToDelete(null);
    } catch (error) {
      console.error('Error deleting sale:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const getCustomerName = (customerId) => {
    if (!customerId) return 'Client anonyme';
    const customer = customers.find(c => c.id === customerId);
    return customer?.name || 'Client inconnu';
  };

  const getPaymentIcon = (method) => {
    switch (method) {
      case 'card': return <CreditCard className="w-4 h-4" />;
      case 'check': return <FileCheck className="w-4 h-4" />;
      default: return <Banknote className="w-4 h-4" />;
    }
  };

  const getPaymentLabel = (method) => {
    switch (method) {
      case 'card': return 'Carte bancaire';
      case 'check': return 'Chèque';
      default: return 'Espèces';
    }
  };

  const filteredProducts = products.filter((p) => {
    const searchLower = productSearch.toLowerCase();
    return p.name?.toLowerCase().includes(searchLower) || 
           p.barcode?.toLowerCase().includes(searchLower);
  });

  const filteredCustomers = customers.filter((c) =>
    c.name?.toLowerCase().includes(customerSearch.toLowerCase()) ||
    c.phone?.includes(customerSearch)
  );

  const filteredSales = sales.filter((s) => {
    const customerName = getCustomerName(s.customer_id).toLowerCase();
    const paymentLabel = getPaymentLabel(s.payment_method).toLowerCase();
    const query = searchQuery.toLowerCase();
    return customerName.includes(query) || paymentLabel.includes(query) || 
           s.total?.toString().includes(query);
  });

  return (
    <Layout>
      <div className="space-y-6" data-testid="sales-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Ventes
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des ventes et facturation
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={setShowDialog}>
            <DialogTrigger asChild>
              <Button data-testid="new-sale-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Nouvelle vente
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>Nouvelle vente</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6" data-testid="sale-form">
                <div className="grid grid-cols-2 gap-4">
                  {/* Client Search */}
                  <div className="relative">
                    <Label htmlFor="customer">Client (optionnel)</Label>
                    <div className="relative mt-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" strokeWidth={1.5} />
                      <Input
                        placeholder="Rechercher un client par nom ou téléphone..."
                        value={customerSearch}
                        onChange={(e) => {
                          setCustomerSearch(e.target.value);
                          setShowCustomerDropdown(true);
                          if (!e.target.value) {
                            setSelectedCustomer('');
                          }
                        }}
                        onFocus={() => setShowCustomerDropdown(true)}
                        data-testid="customer-search-input"
                        className="pl-9"
                      />
                    </div>
                    {showCustomerDropdown && customerSearch && filteredCustomers.length > 0 && (
                      <div className="absolute z-50 w-full mt-1 max-h-48 overflow-y-auto bg-white border border-slate-200 rounded-lg shadow-lg">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedCustomer('');
                            setCustomerSearch('');
                            setShowCustomerDropdown(false);
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-slate-50 text-slate-500 border-b border-slate-100"
                        >
                          Aucun client (vente anonyme)
                        </button>
                        {filteredCustomers.map((customer) => (
                          <button
                            key={customer.id}
                            type="button"
                            onClick={() => {
                              setSelectedCustomer(customer.id);
                              setCustomerSearch(customer.name);
                              setShowCustomerDropdown(false);
                            }}
                            data-testid={`select-customer-${customer.id}`}
                            className="w-full text-left px-4 py-2 hover:bg-slate-50 transition-colors"
                          >
                            <p className="font-medium text-slate-900">{customer.name}</p>
                            {customer.phone && (
                              <p className="text-sm text-slate-500">{customer.phone}</p>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                    {selectedCustomer && (
                      <p className="mt-1 text-sm text-teal-600">
                        ✓ Client sélectionné: {customers.find(c => c.id === selectedCustomer)?.name}
                      </p>
                    )}
                  </div>
                  <div>
                    <Label htmlFor="payment">Mode de paiement</Label>
                    <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                      <SelectTrigger data-testid="payment-select" className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="cash">Espèces</SelectItem>
                        <SelectItem value="card">Carte bancaire</SelectItem>
                        <SelectItem value="check">Chèque</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Product Search */}
                <div>
                  <Label>Rechercher un produit (par nom ou code-barres)</Label>
                  <div className="relative mt-2">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
                    <Input
                      placeholder="Rechercher par nom ou scanner le code-barres..."
                      value={productSearch}
                      onChange={(e) => setProductSearch(e.target.value)}
                      data-testid="product-search-input"
                      className="pl-10"
                    />
                  </div>
                  {productSearch && filteredProducts.length > 0 && (
                    <div className="mt-2 max-h-48 overflow-y-auto border border-slate-200 rounded-lg">
                      {filteredProducts.slice(0, 8).map((product) => (
                        <button
                          key={product.id}
                          type="button"
                          onClick={() => addToCart(product)}
                          disabled={product.stock <= 0}
                          data-testid={`add-to-cart-${product.id}`}
                          className={`w-full text-left px-4 py-2 transition-colors flex justify-between items-center ${
                            product.stock <= 0 ? 'bg-slate-100 cursor-not-allowed' : 'hover:bg-slate-50'
                          }`}
                        >
                          <div>
                            <p className="font-medium text-slate-900">{product.name}</p>
                            <p className="text-xs text-slate-400">{product.barcode || 'Pas de code-barres'}</p>
                            <p className={`text-sm ${product.stock <= 0 ? 'text-red-500' : 'text-slate-500'}`}>
                              Stock: {product.stock} {product.stock <= 0 && '(Rupture)'}
                            </p>
                          </div>
                          <p className="font-medium text-teal-700">{product.price.toFixed(2)} €</p>
                        </button>
                      ))}
                    </div>
                  )}
                  {productSearch && filteredProducts.length === 0 && (
                    <p className="mt-2 text-sm text-slate-500">Aucun produit trouvé pour &quot;{productSearch}&quot;</p>
                  )}
                </div>

                {/* Cart */}
                <div>
                  <Label>Panier ({cart.length} article{cart.length > 1 ? 's' : ''})</Label>
                  <div className="mt-2 space-y-2" data-testid="cart-items">
                    {cart.length === 0 ? (
                      <p className="text-slate-500 text-center py-4">Le panier est vide</p>
                    ) : (
                      cart.map((item) => (
                        <div key={item.product_id} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                          <div className="flex-1">
                            <p className="font-medium text-slate-900">{item.name}</p>
                            <p className="text-sm text-slate-500">{item.price.toFixed(2)} € / unité</p>
                          </div>
                          <Input
                            type="number"
                            min="1"
                            max={item.max_stock}
                            value={item.quantity}
                            onChange={(e) => updateQuantity(item.product_id, e.target.value)}
                            className="w-20"
                            data-testid={`quantity-${item.product_id}`}
                          />
                          <p className="font-medium text-slate-900 w-24 text-right">
                            {(item.price * item.quantity).toFixed(2)} €
                          </p>
                          <button
                            type="button"
                            onClick={() => removeFromCart(item.product_id)}
                            data-testid={`remove-${item.product_id}`}
                            className="text-red-600 hover:text-red-700"
                          >
                            <X className="w-5 h-5" strokeWidth={1.5} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Total */}
                <div className="flex justify-between items-center p-4 bg-teal-50 rounded-lg">
                  <span className="text-lg font-semibold text-slate-900">Total:</span>
                  <span className="text-2xl font-bold text-teal-700" data-testid="cart-total">
                    {calculateTotal().toFixed(2)} €
                  </span>
                </div>

                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                    Annuler
                  </Button>
                  <Button type="submit" data-testid="sale-submit-button" className="bg-teal-700 hover:bg-teal-800">
                    Valider la vente
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
          <Input
            placeholder="Rechercher par client, mode de paiement..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="sales-search-input"
            className="pl-10"
          />
        </div>

        {/* Sales List */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Date
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Client
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Articles
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Paiement
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Total
                  </th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredSales.map((sale) => (
                  <tr key={sale.id} className="hover:bg-slate-50 transition-colors" data-testid={`sale-row-${sale.id}`}>
                    <td className="px-6 py-4 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {new Date(sale.created_at).toLocaleString('fr-FR')}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-900">
                      {getCustomerName(sale.customer_id)}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-900">
                      {sale.items?.length || 0} article(s)
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      <div className="flex items-center gap-2">
                        {getPaymentIcon(sale.payment_method)}
                        {getPaymentLabel(sale.payment_method)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-teal-700" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {sale.total?.toFixed(2) || '0.00'} €
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewDetails(sale)}
                          data-testid={`view-sale-${sale.id}`}
                        >
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                        {isAdmin && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteClick(sale)}
                            data-testid={`delete-sale-${sale.id}`}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredSales.length === 0 && (
            <div className="text-center py-12">
              <ShoppingCart className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
                {searchQuery ? 'Aucune vente trouvée' : 'Aucune vente enregistrée'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Dialog Détails de la vente */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>Détails de la vente</DialogTitle>
          </DialogHeader>
          {selectedSale && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Date</p>
                  <p className="font-medium">{new Date(selectedSale.created_at).toLocaleString('fr-FR')}</p>
                </div>
                <div>
                  <p className="text-slate-500">Client</p>
                  <p className="font-medium">{getCustomerName(selectedSale.customer_id)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Paiement</p>
                  <p className="font-medium flex items-center gap-2">
                    {getPaymentIcon(selectedSale.payment_method)}
                    {getPaymentLabel(selectedSale.payment_method)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Total</p>
                  <p className="font-medium text-teal-700">{selectedSale.total?.toFixed(2)} €</p>
                </div>
              </div>
              
              <div>
                <p className="text-sm text-slate-500 mb-2">Articles</p>
                <div className="space-y-2">
                  {selectedSale.items?.map((item, index) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                      <div>
                        <p className="font-medium">{item.name}</p>
                        <p className="text-sm text-slate-500">{item.price?.toFixed(2)} € × {item.quantity}</p>
                      </div>
                      <p className="font-medium">{(item.price * item.quantity).toFixed(2)} €</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialogue de confirmation de suppression */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white/95 backdrop-blur-sm">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Confirmer la suppression
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
              Êtes-vous sûr de vouloir supprimer cette vente de {saleToDelete?.total?.toFixed(2)} € ?
              Le stock des produits sera restauré. Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={() => {
                setShowDeleteDialog(false);
                setSaleToDelete(null);
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

export default Sales;
