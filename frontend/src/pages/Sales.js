import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Plus, Search, ShoppingCart, Trash2, X } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import api from '../services/api';
import { addItem, getAllItems, addLocalChange } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'sonner';

const Sales = () => {
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [cart, setCart] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [productSearch, setProductSearch] = useState('');
  const { isOnline } = useOffline();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      if (isOnline) {
        const [salesRes, productsRes, customersRes] = await Promise.all([
          api.get('/sales'),
          api.get('/products'),
          api.get('/customers'),
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

  const addToCart = (product) => {
    const existing = cart.find((item) => item.product_id === product.id);
    if (existing) {
      setCart(
        cart.map((item) =>
          item.product_id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      );
    } else {
      setCart([...cart, { product_id: product.id, name: product.name, price: product.price, quantity: 1 }]);
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
        customer_id: selectedCustomer || null,
        items: cart,
        total: calculateTotal(),
        payment_method: paymentMethod,
      };

      if (isOnline) {
        const response = await api.post('/sales', saleData);
        await addItem('sales', response.data);
      } else {
        const newSale = { ...saleData, id: Date.now().toString(), created_at: new Date().toISOString() };
        await addItem('sales', newSale);
        await addLocalChange('sale', 'create', newSale);
      }

      toast.success('Vente enregistrée avec succès');
      setCart([]);
      setSelectedCustomer('');
      setPaymentMethod('cash');
      setShowDialog(false);
      loadData();
    } catch (error) {
      console.error('Error creating sale:', error);
      toast.error('Erreur lors de l\'enregistrement de la vente');
    }
  };

  const filteredProducts = products.filter((p) =>
    p.name?.toLowerCase().includes(productSearch.toLowerCase())
  );

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
                  <div>
                    <Label htmlFor="customer">Client (optionnel)</Label>
                    <Select value={selectedCustomer} onValueChange={setSelectedCustomer}>
                      <SelectTrigger data-testid="customer-select">
                        <SelectValue placeholder="Sélectionner un client" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Aucun client</SelectItem>
                        {customers.map((customer) => (
                          <SelectItem key={customer.id} value={customer.id}>
                            {customer.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="payment">Mode de paiement</Label>
                    <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                      <SelectTrigger data-testid="payment-select">
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
                  <Label>Rechercher un produit</Label>
                  <div className="relative mt-2">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
                    <Input
                      placeholder="Rechercher..."
                      value={productSearch}
                      onChange={(e) => setProductSearch(e.target.value)}
                      data-testid="product-search-input"
                      className="pl-10"
                    />
                  </div>
                  {productSearch && filteredProducts.length > 0 && (
                    <div className="mt-2 max-h-48 overflow-y-auto border border-slate-200 rounded-lg">
                      {filteredProducts.slice(0, 5).map((product) => (
                        <button
                          key={product.id}
                          type="button"
                          onClick={() => addToCart(product)}
                          data-testid={`add-to-cart-${product.id}`}
                          className="w-full text-left px-4 py-2 hover:bg-slate-50 transition-colors flex justify-between items-center"
                        >
                          <div>
                            <p className="font-medium text-slate-900">{product.name}</p>
                            <p className="text-sm text-slate-500">Stock: {product.stock}</p>
                          </div>
                          <p className="font-medium text-teal-700">{product.price.toFixed(2)} €</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Cart */}
                <div>
                  <Label>Panier</Label>
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
                    Articles
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Mode de paiement
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Total
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {sales.map((sale) => (
                  <tr key={sale.id} className="hover:bg-slate-50 transition-colors" data-testid={`sale-row-${sale.id}`}>
                    <td className="px-6 py-4 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {new Date(sale.created_at).toLocaleString('fr-FR')}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-900">
                      {sale.items?.length || 0} article(s)
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {sale.payment_method === 'cash' && 'Espèces'}
                      {sale.payment_method === 'card' && 'Carte bancaire'}
                      {sale.payment_method === 'check' && 'Chèque'}
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-teal-700" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {sale.total?.toFixed(2) || '0.00'} €
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sales.length === 0 && (
            <div className="text-center py-12">
              <ShoppingCart className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
                Aucune vente enregistrée
              </p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Sales;