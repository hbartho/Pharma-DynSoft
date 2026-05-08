import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { 
  DollarSign, 
  Search, 
  Save, 
  Package, 
  Calendar, 
  Truck,
  Edit,
  Loader2,
  Filter,
  RefreshCw,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight
} from 'lucide-react';
import { useStockLots, useBulkUpdateStockLots, useUpdateStockLot } from '../hooks/useStockLots';
import { useSupplies } from '../hooks/useSupplies';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import { toast } from 'sonner';
import { Navigate } from 'react-router-dom';

const PriceManagement = () => {
  const { user } = useAuth();
  const { formatAmount } = useSettings();
  
  // Redirect if not admin
  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSupplyId, setSelectedSupplyId] = useState('all');
  const [editedPrices, setEditedPrices] = useState({});
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingLot, setEditingLot] = useState(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Fetch data - Auto-refresh every 30 seconds
  const { data: stockLots = [], isLoading, refetch, isFetching } = useStockLots({ 
    supplyId: selectedSupplyId !== 'all' ? selectedSupplyId : undefined,
    activeOnly: true,
    refetchInterval: 30000 // 30 secondes
  });
  const { data: supplies = [] } = useSupplies();
  const bulkUpdate = useBulkUpdateStockLots();
  const updateLot = useUpdateStockLot();

  // Filter validated supplies for the dropdown
  const validatedSupplies = supplies.filter(s => s.status === 'validated');

  // Filter lots by search
  const filteredLots = stockLots.filter(lot => {
    const matchesSearch = !searchQuery || 
      lot.product_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lot.lot_number?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lot.supplier_name?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  // Pagination calculations
  const totalPages = Math.ceil(filteredLots.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedLots = filteredLots.slice(startIndex, endIndex);

  // Reset to page 1 when search or filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedSupplyId]);

  // Check if there are unsaved changes
  const hasChanges = Object.keys(editedPrices).length > 0;

  // Handle price change in the table
  const handlePriceChange = (lotId, field, value) => {
    setEditedPrices(prev => ({
      ...prev,
      [lotId]: {
        ...prev[lotId],
        [field]: value
      }
    }));
  };

  // Get display value for a field
  const getDisplayValue = (lot, field) => {
    if (editedPrices[lot.id] && editedPrices[lot.id][field] !== undefined) {
      return editedPrices[lot.id][field];
    }
    return lot[field] || '';
  };

  // Save all changes
  const handleSaveAll = async () => {
    const updates = Object.entries(editedPrices).map(([lotId, changes]) => ({
      lot_id: lotId,
      ...changes
    }));

    if (updates.length === 0) {
      toast.info('Aucune modification à enregistrer');
      return;
    }

    bulkUpdate.mutate(updates, {
      onSuccess: () => {
        setEditedPrices({});
        refetch();
      }
    });
  };

  // Open edit dialog for a single lot
  const handleEditLot = (lot) => {
    setEditingLot({
      ...lot,
      new_selling_price: lot.selling_price,
      new_purchase_price: lot.purchase_price,
    });
    setShowEditDialog(true);
  };

  // Save single lot edit
  const handleSaveLot = () => {
    if (!editingLot) return;

    const updates = {};
    if (editingLot.new_selling_price !== editingLot.selling_price) {
      updates.selling_price = parseFloat(editingLot.new_selling_price);
    }
    if (editingLot.new_purchase_price !== editingLot.purchase_price) {
      updates.purchase_price = parseFloat(editingLot.new_purchase_price);
    }

    if (Object.keys(updates).length === 0) {
      toast.info('Aucune modification');
      setShowEditDialog(false);
      return;
    }

    updateLot.mutate(
      { lotId: editingLot.id, data: updates },
      {
        onSuccess: () => {
          setShowEditDialog(false);
          setEditingLot(null);
          refetch();
        }
      }
    );
  };

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('fr-FR');
    } catch {
      return '-';
    }
  };

  // Check if lot is near expiration (30 days)
  const isNearExpiration = (lot) => {
    if (!lot.expiration_date) return false;
    const expDate = new Date(lot.expiration_date);
    const now = new Date();
    const diffDays = Math.floor((expDate - now) / (1000 * 60 * 60 * 24));
    return diffDays >= 0 && diffDays <= 30;
  };

  const isExpired = (lot) => {
    if (!lot.expiration_date) return false;
    return new Date(lot.expiration_date) < new Date();
  };

  return (
    <Layout>
      <div className="p-6" data-testid="price-management-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-teal-100 rounded-lg">
              <DollarSign className="w-6 h-6 text-teal-700" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Gestion des Prix
              </h1>
              <p className="text-sm text-slate-500 flex items-center gap-2">
                Modifier les prix des lots de stock par approvisionnement
                <span className="inline-flex items-center gap-1 text-xs text-teal-600 bg-teal-50 px-2 py-0.5 rounded-full">
                  <RefreshCw className="w-3 h-3" />
                  Auto-actualisation
                </span>
              </p>
            </div>
          </div>

          {/* Save button */}
          {hasChanges && (
            <Button
              onClick={handleSaveAll}
              className="bg-emerald-600 hover:bg-emerald-700"
              disabled={bulkUpdate.isPending}
              data-testid="save-all-prices-btn"
            >
              {bulkUpdate.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Enregistrer ({Object.keys(editedPrices).length} modification(s))
            </Button>
          )}
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Rechercher un produit, lot..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
                data-testid="search-lots-input"
              />
            </div>

            {/* Supply filter */}
            <div>
              <Select value={selectedSupplyId} onValueChange={setSelectedSupplyId}>
                <SelectTrigger data-testid="supply-filter-select">
                  <Filter className="w-4 h-4 mr-2 text-slate-400" />
                  <SelectValue placeholder="Filtrer par approvisionnement" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les approvisionnements</SelectItem>
                  {validatedSupplies.map((supply) => (
                    <SelectItem key={supply.id} value={supply.id}>
                      {supply.supplier_name} - {formatDate(supply.supply_date)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Refresh info */}
            <div className="flex items-center gap-2">
              {isFetching && !isLoading && (
                <span className="text-xs text-teal-600 flex items-center gap-1">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Actualisation...
                </span>
              )}
              <Button
                variant="outline"
                onClick={() => refetch()}
                disabled={isLoading || isFetching}
                size="sm"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${(isLoading || isFetching) ? 'animate-spin' : ''}`} />
                Actualiser
              </Button>
            </div>
          </div>
        </div>

        {/* Stock Lots Table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
            </div>
          ) : filteredLots.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Package className="w-12 h-12 mx-auto mb-4 text-slate-300" />
              <p>Aucun lot de stock trouvé</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Produit</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Fournisseur</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Qté</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Prix Cession</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Prix Public</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Prix Modifié</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Coef.</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Expiration</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Modifié par</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {paginatedLots.map((lot) => {
                    const displaySellingPrice = getDisplayValue(lot, 'selling_price');
                    const displayPurchasePrice = getDisplayValue(lot, 'purchase_price');
                    const coefficient = lot.markup_coefficient || 1.0;
                    // Prix public de base = prix cession × coefficient catégorie
                    const prixPublicBase = lot.prix_public_base || Math.round(displayPurchasePrice * coefficient);
                    // Prix modifié = si différent du prix base
                    const prixModifie = lot.prix_public_modifie || (displaySellingPrice !== prixPublicBase ? displaySellingPrice : null);
                    // Calculer le coefficient réel appliqué (prix vente / prix achat)
                    const actualCoef = displayPurchasePrice > 0 
                      ? (displaySellingPrice / displayPurchasePrice).toFixed(2) 
                      : '-';
                    const isModified = editedPrices[lot.id] !== undefined;
                    const nearExp = isNearExpiration(lot);
                    const expired = isExpired(lot);

                    return (
                      <tr 
                        key={lot.id} 
                        className={`hover:bg-slate-50 ${isModified ? 'bg-amber-50' : ''} ${expired ? 'bg-red-50' : ''}`}
                        data-testid={`lot-row-${lot.id}`}
                      >
                        <td className="px-4 py-3">
                          <div className="font-medium text-slate-900">{lot.product_name}</div>
                          <div className="text-xs text-slate-500">
                            {lot.category_name && <span className="mr-2">{lot.category_name}</span>}
                            {lot.lot_number && <span>Lot: {lot.lot_number}</span>}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {lot.supplier_name || '-'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Badge variant={lot.current_quantity <= 5 ? 'destructive' : 'secondary'}>
                            {lot.current_quantity}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">
                          <Input
                            type="number"
                            value={displayPurchasePrice}
                            onChange={(e) => handlePriceChange(lot.id, 'purchase_price', parseFloat(e.target.value) || 0)}
                            className="w-28 text-right text-sm"
                            step="100"
                          />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-medium text-emerald-700">
                            {formatAmount(prixPublicBase)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Input
                            type="number"
                            value={prixModifie || ''}
                            placeholder={formatAmount(prixPublicBase).replace(' GNF', '')}
                            onChange={(e) => handlePriceChange(lot.id, 'selling_price', parseFloat(e.target.value) || prixPublicBase)}
                            className={`w-28 text-right text-sm ${prixModifie ? 'font-medium text-orange-600 border-orange-300' : ''}`}
                            step="100"
                          />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex flex-col items-center">
                            <span className={`text-sm font-bold ${
                              parseFloat(actualCoef) >= coefficient ? 'text-emerald-600' : 'text-amber-600'
                            }`}>
                              ×{actualCoef}
                            </span>
                            <span className="text-xs text-slate-400">
                              (Cat: ×{coefficient})
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className={`text-sm ${expired ? 'text-red-600 font-medium' : nearExp ? 'text-orange-600' : 'text-slate-600'}`}>
                            {formatDate(lot.expiration_date)}
                            {expired && <AlertTriangle className="w-3 h-3 inline ml-1" />}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {lot.updated_by ? (
                            <div className="text-xs">
                              <div className="font-medium text-slate-700">{lot.updated_by}</div>
                              <div className="text-slate-400">{formatDate(lot.updated_at)}</div>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEditLot(lot)}
                            data-testid={`edit-lot-${lot.id}`}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Footer with pagination */}
          {filteredLots.length > 0 && (
            <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <div className="text-sm text-slate-500">
                Affichage {startIndex + 1}-{Math.min(endIndex, filteredLots.length)} sur {filteredLots.length} lot(s)
              </div>
              
              {/* Pagination controls */}
              {totalPages > 1 && (
                <div className="flex items-center gap-1">
                  {/* First page */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentPage(1)}
                    disabled={currentPage === 1}
                    className="h-8 w-8 p-0"
                    data-testid="pagination-first"
                  >
                    <ChevronsLeft className="w-4 h-4" />
                  </Button>
                  
                  {/* Previous page */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="h-8 w-8 p-0"
                    data-testid="pagination-prev"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  
                  {/* Page numbers */}
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <Button
                          key={pageNum}
                          variant={currentPage === pageNum ? "default" : "ghost"}
                          size="sm"
                          onClick={() => setCurrentPage(pageNum)}
                          className={`h-8 w-8 p-0 ${currentPage === pageNum ? 'bg-teal-600 hover:bg-teal-700 text-white' : ''}`}
                          data-testid={`pagination-page-${pageNum}`}
                        >
                          {pageNum}
                        </Button>
                      );
                    })}
                  </div>
                  
                  {/* Next page */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="h-8 w-8 p-0"
                    data-testid="pagination-next"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                  
                  {/* Last page */}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentPage(totalPages)}
                    disabled={currentPage === totalPages}
                    className="h-8 w-8 p-0"
                    data-testid="pagination-last"
                  >
                    <ChevronsRight className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Edit Dialog */}
        <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                Modifier les prix du lot
              </DialogTitle>
            </DialogHeader>
            
            {editingLot && (
              <div className="space-y-4">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="font-medium text-slate-900">{editingLot.product_name}</p>
                  <div className="flex flex-wrap gap-2 mt-1 text-sm text-slate-500">
                    {editingLot.category_name && (
                      <span className="px-2 py-0.5 bg-teal-100 text-teal-700 rounded">
                        {editingLot.category_name}
                      </span>
                    )}
                    {editingLot.lot_number && <span>Lot: {editingLot.lot_number}</span>}
                  </div>
                  <div className="mt-2 space-y-1 text-sm text-slate-500">
                    <p>
                      Quantité restante: <span className="font-medium">{editingLot.current_quantity}</span>
                    </p>
                    {editingLot.supplier_name && (
                      <p>
                        Fournisseur: <span className="font-medium">{editingLot.supplier_name}</span>
                      </p>
                    )}
                    {editingLot.supply_id && (
                      <p>
                        N° Approvisionnement: <span className="font-mono font-medium bg-slate-200 px-1 rounded">{editingLot.supply_id.substring(0, 8)}</span>
                      </p>
                    )}
                    {editingLot.updated_by && (
                      <p className="text-amber-600">
                        Dernière modification: <span className="font-medium">{editingLot.updated_by}</span> le {formatDate(editingLot.updated_at)}
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Prix de cession</Label>
                    <Input
                      type="number"
                      value={editingLot.new_purchase_price}
                      onChange={(e) => setEditingLot({
                        ...editingLot,
                        new_purchase_price: parseFloat(e.target.value) || 0
                      })}
                      className="mt-1"
                      step="100"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Actuel: {formatAmount(editingLot.purchase_price)}
                    </p>
                  </div>
                  <div>
                    <Label>Prix public</Label>
                    <Input
                      type="number"
                      value={editingLot.new_selling_price}
                      onChange={(e) => setEditingLot({
                        ...editingLot,
                        new_selling_price: parseFloat(e.target.value) || 0
                      })}
                      className="mt-1"
                      step="100"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Actuel: {formatAmount(editingLot.selling_price)}
                    </p>
                  </div>
                </div>

                {/* Coefficient preview */}
                {editingLot.new_selling_price && editingLot.new_purchase_price && (
                  <div className="p-3 bg-teal-50 rounded-lg">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="text-sm text-teal-700">
                          Coefficient appliqué: <span className="font-bold text-lg">
                            ×{(editingLot.new_selling_price / editingLot.new_purchase_price).toFixed(2)}
                          </span>
                        </p>
                        <p className="text-xs text-teal-600">
                          Coefficient catégorie: ×{editingLot.markup_coefficient || 1.0}
                        </p>
                      </div>
                      {editingLot.new_purchase_price > 0 && (
                        <div className={`text-sm font-medium px-2 py-1 rounded ${
                          (editingLot.new_selling_price / editingLot.new_purchase_price) >= (editingLot.markup_coefficient || 1.0)
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}>
                          {(editingLot.new_selling_price / editingLot.new_purchase_price) >= (editingLot.markup_coefficient || 1.0)
                            ? '✓ Conforme'
                            : '⚠ Sous le coef.'
                          }
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 pt-4">
                  <Button
                    variant="outline"
                    onClick={() => setShowEditDialog(false)}
                    className="flex-1"
                  >
                    Annuler
                  </Button>
                  <Button
                    onClick={handleSaveLot}
                    className="flex-1 bg-teal-600 hover:bg-teal-700"
                    disabled={updateLot.isPending}
                  >
                    {updateLot.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Enregistrer
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default PriceManagement;
