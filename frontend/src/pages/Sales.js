import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import api from '../services/api';
import { addItem, getAllItems, addLocalChange, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

const Sales = () => {
  const { user } = useAuth();
  const [appSettings, setAppSettings] = useState({ currency: 'GNF' });
  const [sales, setSales] = useState([]);
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedSale, setSelectedSale] = useState(null);
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
        const [salesRes, productsRes, customersRes, settingsRes] = await Promise.all([
          api.get('/sales', { headers }),
          api.get('/products', { headers }).catch(() => ({ data: [] })),
          api.get('/customers', { headers }),
          api.get('/settings', { headers }).catch(() => ({ data: { currency: 'EUR' } })),
        ]);
        setSales(salesRes.data);
        setProducts(productsRes.data);
        setCustomers(customersRes.data);
        setAppSettings(settingsRes.data);
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

  // Fonction pour formater avec la devise chargée
  const formatAmount = (amount) => {
    const currency = appSettings?.currency || 'EUR';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${formatted} ${symbols[currency] || currency}`;
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

  // Fonction pour générer et télécharger le PDF de la vente
  const generateSalePDF = (sale) => {
    const customerName = getCustomerName(sale.customer_id);
    const saleDate = new Date(sale.created_at).toLocaleString('fr-FR');
    const paymentLabel = getPaymentLabel(sale.payment_method);
    
    // Créer le contenu HTML pour le PDF
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>Reçu de vente - ${saleDate}</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            padding: 40px; 
            max-width: 800px; 
            margin: 0 auto;
            color: #1e293b;
          }
          .header { 
            text-align: center; 
            margin-bottom: 30px; 
            padding-bottom: 20px; 
            border-bottom: 2px solid #0d9488;
          }
          .header h1 { 
            color: #0d9488; 
            font-size: 28px; 
            margin-bottom: 5px;
          }
          .header p { 
            color: #64748b; 
            font-size: 14px;
          }
          .info-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
          }
          .info-item label { 
            display: block; 
            font-size: 12px; 
            color: #64748b; 
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          .info-item span { 
            font-size: 16px; 
            font-weight: 600;
            color: #1e293b;
          }
          .items-section { margin-bottom: 30px; }
          .items-section h3 { 
            font-size: 16px; 
            margin-bottom: 15px; 
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          table { 
            width: 100%; 
            border-collapse: collapse;
          }
          th { 
            text-align: left; 
            padding: 12px; 
            background: #f1f5f9; 
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            border-bottom: 2px solid #e2e8f0;
          }
          th:last-child { text-align: right; }
          td { 
            padding: 12px; 
            border-bottom: 1px solid #e2e8f0;
            font-size: 14px;
          }
          td:last-child { 
            text-align: right; 
            font-weight: 600;
          }
          .total-row { 
            background: #0d9488; 
            color: white;
          }
          .total-row td { 
            padding: 16px 12px; 
            font-size: 18px; 
            font-weight: 700;
            border: none;
          }
          .footer { 
            text-align: center; 
            margin-top: 40px; 
            padding-top: 20px; 
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 12px;
          }
          @media print {
            body { padding: 20px; }
            .no-print { display: none; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${appSettings?.pharmacy_name || 'DynSoft Pharma'}</h1>
          <p>Reçu de vente</p>
        </div>
        
        <div class="info-grid">
          <div class="info-item">
            <label>Date et heure</label>
            <span>${saleDate}</span>
          </div>
          <div class="info-item">
            <label>Client</label>
            <span>${customerName}</span>
          </div>
          <div class="info-item">
            <label>Mode de paiement</label>
            <span>${paymentLabel}</span>
          </div>
          <div class="info-item">
            <label>Référence</label>
            <span>${sale.id?.substring(0, 8).toUpperCase() || 'N/A'}</span>
          </div>
        </div>
        
        <div class="items-section">
          <h3>Articles</h3>
          <table>
            <thead>
              <tr>
                <th>Produit</th>
                <th>Prix unitaire</th>
                <th>Quantité</th>
                <th>Sous-total</th>
              </tr>
            </thead>
            <tbody>
              ${sale.items?.map(item => `
                <tr>
                  <td>${item.name}</td>
                  <td>${formatAmount(item.price || 0)}</td>
                  <td>${item.quantity}</td>
                  <td>${formatAmount((item.price || 0) * item.quantity)}</td>
                </tr>
              `).join('') || ''}
              <tr class="total-row">
                <td colspan="3">TOTAL</td>
                <td>${formatAmount(sale.total || 0)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="footer">
          <p>Merci pour votre achat !</p>
          <p style="margin-top: 5px;">Document généré le ${new Date().toLocaleString('fr-FR')}</p>
        </div>
      </body>
      </html>
    `;
    
    // Ouvrir une nouvelle fenêtre et imprimer/sauvegarder en PDF
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.focus();
    
    // Attendre le chargement puis lancer l'impression
    setTimeout(() => {
      printWindow.print();
    }, 250);
    
    toast.success('Document PDF généré');
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

  // Filtrer les produits : uniquement actifs et correspondant à la recherche
  const filteredProducts = products.filter((p) => {
    // Exclure les produits désactivés
    if (p.is_active === false) return false;
    
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
                          <p className="font-medium text-teal-700">{formatAmount(product.price)}</p>
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
                            <p className="text-sm text-slate-500">{formatAmount(item.price)} / unité</p>
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
                            {formatAmount(item.price * item.quantity)}
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
                    {formatAmount(calculateTotal())}
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
                      {formatAmount(sale.total || 0)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewDetails(sale)}
                          data-testid={`view-sale-${sale.id}`}
                          title="Voir les détails"
                        >
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => generateSalePDF(sale)}
                          data-testid={`pdf-sale-${sale.id}`}
                          className="text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                          title="Télécharger le reçu PDF"
                        >
                          <FileText className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
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
                  <p className="font-medium text-teal-700">{formatAmount(selectedSale.total || 0)}</p>
                </div>
              </div>
              
              <div>
                <p className="text-sm text-slate-500 mb-2">Articles</p>
                <div className="space-y-2">
                  {selectedSale.items?.map((item, index) => (
                    <div key={index} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                      <div>
                        <p className="font-medium">{item.name}</p>
                        <p className="text-sm text-slate-500">{formatAmount(item.price || 0)} × {item.quantity}</p>
                      </div>
                      <p className="font-medium">{formatAmount((item.price || 0) * item.quantity)}</p>
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
              Êtes-vous sûr de vouloir supprimer cette vente de {formatAmount(saleToDelete?.total || 0)} ?
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
