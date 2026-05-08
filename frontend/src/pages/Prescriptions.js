import React, { useState, useRef, useEffect } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, FileText, CheckCircle, Edit, Trash2, X, Loader2, Search, Timer, Calendar, User, Clock, CheckCircle2, Pill, Package } from 'lucide-react';
import { 
  usePrescriptions, 
  useCreatePrescription, 
  useUpdatePrescription, 
  useDeletePrescription, 
  useFulfillPrescription,
  useCustomers 
} from '../hooks';
import { usePrescriptionsInfinite } from '../hooks/useInfiniteScroll';
import { usePrescriptionStats } from '../hooks/usePrescriptions';
import { useProducts } from '../hooks/useProducts';
import { useAuth } from '../contexts/AuthContext';
import { useShiftEligibility } from '../hooks/useShiftSchedules';
import { toast } from 'sonner';

const Prescriptions = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const loadMoreRef = useRef(null);
  
  // Vérifier l'éligibilité de planification
  const { data: shiftEligibility } = useShiftEligibility();
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;

  const [showDialog, setShowDialog] = useState(false);
  const [editingPrescription, setEditingPrescription] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [formData, setFormData] = useState({
    customer_id: '',
    doctor_name: '',
    medications: [],
    notes: '',
  });
  const [medInput, setMedInput] = useState({ name: '', dosage: '', quantity: '' });
  const [showMedSuggestions, setShowMedSuggestions] = useState(false);
  const [medSearchQuery, setMedSearchQuery] = useState('');
  const medInputRef = useRef(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // React Query hooks avec infinite scroll
  const { 
    data: prescriptionsData,
    isLoading,
    isError,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage 
  } = usePrescriptionsInfinite({
    limit: 20,
    search: debouncedSearch,
    status: filterStatus === 'all' ? '' : filterStatus
  });
  
  const prescriptions = prescriptionsData?.pages?.flatMap(page => page.items) || [];
  
  // Récupérer les stats réelles depuis le backend
  const { data: prescriptionStats = { total: 0, pending: 0, fulfilled: 0, cancelled: 0 } } = usePrescriptionStats();
  const totalPrescriptions = prescriptionStats.total;
  const pendingCount = prescriptionStats.pending;
  const fulfilledCount = prescriptionStats.fulfilled;
  const cancelledCount = prescriptionStats.cancelled || 0;
  
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

  const { data: customers = [] } = useCustomers();
  const { data: products = [] } = useProducts();
  const createPrescription = useCreatePrescription();
  const updatePrescription = useUpdatePrescription();
  const deletePrescription = useDeletePrescription();
  const fulfillPrescription = useFulfillPrescription();

  // Filtrer les produits pour les suggestions
  const filteredProducts = products.filter(product => 
    product.is_active !== false && 
    product.name.toLowerCase().includes(medSearchQuery.toLowerCase())
  ).slice(0, 8);

  // Fermer les suggestions quand on clique ailleurs
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (medInputRef.current && !medInputRef.current.contains(event.target)) {
        setShowMedSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMedNameChange = (value) => {
    setMedInput({ ...medInput, name: value });
    setMedSearchQuery(value);
    setShowMedSuggestions(value.length > 0);
  };

  const selectProduct = (product) => {
    setMedInput({ ...medInput, name: product.name });
    setMedSearchQuery('');
    setShowMedSuggestions(false);
  };

  const addMedication = () => {
    if (medInput.name && medInput.dosage && medInput.quantity) {
      setFormData({
        ...formData,
        medications: [...formData.medications, { ...medInput }],
      });
      setMedInput({ name: '', dosage: '', quantity: '' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.medications.length === 0) {
      toast.error('Veuillez ajouter au moins un médicament');
      return;
    }

    if (editingPrescription) {
      updatePrescription.mutate(
        { prescriptionId: editingPrescription.id, data: formData },
        {
          onSuccess: () => {
            setShowDialog(false);
            resetForm();
          },
        }
      );
    } else {
      const prescriptionData = { ...formData, status: 'pending' };
      createPrescription.mutate(prescriptionData, {
        onSuccess: () => {
          setShowDialog(false);
          resetForm();
        },
      });
    }
  };

  const markAsFulfilled = (prescriptionId) => {
    fulfillPrescription.mutate(prescriptionId);
  };

  const handleEdit = (prescription) => {
    setEditingPrescription(prescription);
    setFormData({
      customer_id: prescription.customer_id,
      doctor_name: prescription.doctor_name,
      medications: [...prescription.medications],
      notes: prescription.notes || '',
    });
    setShowDialog(true);
  };

  const handleDeleteConfirm = (prescription) => {
    if (!prescription) return;
    deletePrescription.mutate(prescription.id);
  };

  const resetForm = () => {
    setEditingPrescription(null);
    setFormData({ customer_id: '', doctor_name: '', medications: [], notes: '' });
    setMedInput({ name: '', dosage: '', quantity: '' });
  };

  const removeMedication = (index) => {
    const updatedMedications = formData.medications.filter((_, i) => i !== index);
    setFormData({ ...formData, medications: updatedMedications });
  };

  const getCustomerName = (customerId) => {
    const customer = customers.find((c) => c.id === customerId);
    return customer?.name || 'Inconnu';
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

  const isSubmitting = createPrescription.isPending || updatePrescription.isPending;

  // Trier les ordonnances: en attente d'abord, puis par date
  const sortedPrescriptions = [...prescriptions].sort((a, b) => {
    const aIsPending = a.status === 'pending';
    const bIsPending = b.status === 'pending';
    if (aIsPending !== bIsPending) {
      return aIsPending ? -1 : 1;
    }
    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
  });

  if (isError) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <p className="text-red-500">Erreur lors du chargement des ordonnances</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="prescriptions-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Ordonnances
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des ordonnances médicales • {prescriptions.length} ordonnance{prescriptions.length > 1 ? 's' : ''}
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-prescription-button" 
                className="bg-teal-700 hover:bg-teal-800 rounded-full"
                disabled={!isWithinScheduledHours}
                title={!isWithinScheduledHours ? 'Accès restreint - Hors horaires de travail' : ''}
              >
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Nouvelle ordonnance
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingPrescription ? 'Éditer l\'ordonnance' : 'Nouvelle ordonnance'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="prescription-form">
                <div>
                  <Label htmlFor="customer">Patient *</Label>
                  <Select
                    value={formData.customer_id}
                    onValueChange={(value) => setFormData({ ...formData, customer_id: value })}
                  >
                    <SelectTrigger data-testid="customer-select">
                      <SelectValue placeholder="Sélectionner un patient" />
                    </SelectTrigger>
                    <SelectContent>
                      {customers.map((customer) => (
                        <SelectItem key={customer.id} value={customer.id}>
                          {customer.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="doctor">Nom du médecin *</Label>
                  <Input
                    id="doctor"
                    value={formData.doctor_name}
                    onChange={(e) => setFormData({ ...formData, doctor_name: e.target.value })}
                    required
                    data-testid="doctor-name-input"
                  />
                </div>
                <div>
                  <Label>Médicaments</Label>
                  <div className="mt-2 space-y-2">
                    <div className="flex gap-2">
                      <div className="relative flex-1" ref={medInputRef}>
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                          <Input
                            placeholder="Rechercher un médicament..."
                            value={medInput.name}
                            onChange={(e) => handleMedNameChange(e.target.value)}
                            onFocus={() => medInput.name && setShowMedSuggestions(true)}
                            className="pl-9"
                            data-testid="medication-name-input"
                          />
                        </div>
                        {showMedSuggestions && filteredProducts.length > 0 && (
                          <div className="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                            {filteredProducts.map((product) => (
                              <button
                                key={product.id}
                                type="button"
                                onClick={() => selectProduct(product)}
                                className="w-full px-3 py-2 text-left hover:bg-teal-50 flex items-center justify-between text-sm"
                              >
                                <span className="font-medium text-slate-900">{product.name}</span>
                                {product.stock > 0 && (
                                  <span className="text-xs text-slate-500">Stock: {product.stock}</span>
                                )}
                              </button>
                            ))}
                          </div>
                        )}
                        {showMedSuggestions && medSearchQuery && filteredProducts.length === 0 && (
                          <div className="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg p-3">
                            <p className="text-sm text-slate-500 text-center">Aucun médicament trouvé</p>
                            <p className="text-xs text-slate-400 text-center mt-1">Vous pouvez saisir manuellement</p>
                          </div>
                        )}
                      </div>
                      <Input
                        placeholder="Ex: 1 cuillerée à soupe 3 fois/jour"
                        value={medInput.dosage}
                        onChange={(e) => setMedInput({ ...medInput, dosage: e.target.value })}
                        className="flex-1"
                      />
                      <Input
                        placeholder="Qté"
                        value={medInput.quantity}
                        onChange={(e) => setMedInput({ ...medInput, quantity: e.target.value })}
                        className="w-20"
                      />
                    </div>
                    <Button type="button" onClick={addMedication} size="sm" data-testid="add-medication-button" className="bg-teal-600 hover:bg-teal-700 text-white">
                      <Plus className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      Ajouter
                    </Button>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">* Tous les champs sont obligatoires</p>
                  <div className="mt-3 space-y-2">
                    {formData.medications.map((med, index) => (
                      <div key={index} className="p-2 bg-slate-50 rounded flex justify-between items-center">
                        <span className="text-sm">
                          {med.name} - {med.dosage} - {med.quantity}
                        </span>
                        <button
                          type="button"
                          onClick={() => removeMedication(index)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <X className="w-4 h-4" strokeWidth={1.5} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <Label htmlFor="notes">Notes</Label>
                  <Input
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                    Annuler
                  </Button>
                  <Button 
                    type="submit" 
                    data-testid="prescription-submit-button" 
                    className="bg-teal-700 hover:bg-teal-800"
                    disabled={isSubmitting}
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    {editingPrescription ? 'Mettre à jour' : 'Ajouter'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats - Style identique à Approvisionnements */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                <p className="text-2xl font-bold text-slate-900">{fulfilledCount}</p>
                <p className="text-sm text-slate-500">Traitées</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <X className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{cancelledCount}</p>
                <p className="text-sm text-slate-500">Annulées</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-teal-100 rounded-lg">
                <FileText className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{totalPrescriptions + cancelledCount}</p>
                <p className="text-sm text-slate-500">Total</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter - Style identique à Approvisionnements */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              placeholder="Rechercher par patient, médecin ou médicament..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              disabled={!isWithinScheduledHours}
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus} disabled={!isWithinScheduledHours}>
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
              <SelectItem value="fulfilled">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Traitées
                </div>
              </SelectItem>
              <SelectItem value="cancelled">
                <div className="flex items-center gap-2">
                  <X className="w-4 h-4 text-red-600" />
                  Annulées
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
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
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder aux ordonnances en dehors de vos horaires planifiés.'}
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
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700 mx-auto"></div>
            <p className="text-slate-500 mt-4">Chargement...</p>
          </div>
        ) : sortedPrescriptions.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Aucune ordonnance enregistrée
            </p>
          </div>
        ) : (
          <>
            {/* Liste des ordonnances - Style identique à Approvisionnements */}
            <div className="space-y-4">
              {sortedPrescriptions.map((prescription) => {
                const isPending = prescription.status === 'pending';
                const isCancelled = prescription.status === 'cancelled';
                const isFulfilled = prescription.status === 'fulfilled' || prescription.status === 'completed';
                
                return (
                  <div
                    key={prescription.id}
                    data-testid={`prescription-card-${prescription.id}`}
                    className={`bg-white rounded-xl border p-4 transition-all ${
                      isPending 
                        ? 'border-amber-200 bg-amber-50/30' 
                        : isCancelled
                        ? 'border-red-200 bg-red-50/30'
                        : 'border-emerald-200'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        {/* Status Badge */}
                        <div className="flex items-center gap-3 mb-2">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                            isPending 
                              ? 'bg-amber-100 text-amber-700' 
                              : isCancelled
                              ? 'bg-red-100 text-red-700'
                              : 'bg-emerald-100 text-emerald-700'
                          }`}>
                            {isPending ? (
                              <>
                                <Clock className="w-3.5 h-3.5" />
                                En attente
                              </>
                            ) : isCancelled ? (
                              <>
                                <X className="w-3.5 h-3.5" />
                                Annulée
                              </>
                            ) : (
                              <>
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Traitée
                              </>
                            )}
                          </span>
                          <span className="text-xs text-slate-400 font-mono">
                            #{prescription.id?.slice(-6).toUpperCase() || 'N/A'}
                          </span>
                        </div>
                        
                        {/* Informations principales - Grille comme Approvisionnements */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-slate-500 flex items-center gap-1">
                              <User className="w-3.5 h-3.5" />
                              Patient
                            </p>
                            <p className="font-medium text-slate-900">{getCustomerName(prescription.customer_id)}</p>
                          </div>
                          <div>
                            <p className="text-slate-500 flex items-center gap-1">
                              <User className="w-3.5 h-3.5" />
                              Médecin
                            </p>
                            <p className="font-medium text-slate-900">Dr. {prescription.doctor_name}</p>
                          </div>
                          <div>
                            <p className="text-slate-500 flex items-center gap-1">
                              <Calendar className="w-3.5 h-3.5" />
                              Date
                            </p>
                            <p className="font-medium text-slate-900">{formatDate(prescription.created_at)}</p>
                          </div>
                          <div>
                            <p className="text-slate-500 flex items-center gap-1">
                              <Pill className="w-3.5 h-3.5" />
                              Médicaments
                            </p>
                            <p className="font-medium text-teal-700">
                              {prescription.medications?.length || 0} article{(prescription.medications?.length || 0) > 1 ? 's' : ''}
                            </p>
                          </div>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex gap-2 ml-4">
                        {isPending && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEdit(prescription)}
                              data-testid={`edit-prescription-${prescription.id}`}
                              title="Éditer"
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  data-testid={`delete-prescription-${prescription.id}`}
                                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                  title="Supprimer"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                                    Supprimer l'ordonnance
                                  </AlertDialogTitle>
                                  <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
                                    Êtes-vous sûr de vouloir supprimer cette ordonnance ? Cette action est irréversible.
                                    <br />
                                    <br />
                                    <span className="font-medium">Patient :</span> {getCustomerName(prescription.customer_id)}<br />
                                    <span className="font-medium">Médecin :</span> Dr. {prescription.doctor_name}
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Annuler</AlertDialogCancel>
                                  <AlertDialogAction
                                    onClick={() => handleDeleteConfirm(prescription)}
                                    className="bg-red-600 hover:bg-red-700"
                                    disabled={deletePrescription.isPending}
                                  >
                                    {deletePrescription.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                    Supprimer
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                            <Button
                              size="sm"
                              onClick={() => markAsFulfilled(prescription.id)}
                              data-testid={`fulfill-prescription-${prescription.id}`}
                              className="bg-emerald-600 hover:bg-emerald-700"
                              disabled={fulfillPrescription.isPending}
                              title="Marquer comme traitée"
                            >
                              {fulfillPrescription.isPending ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <CheckCircle className="w-4 h-4" />
                              )}
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                    
                    {/* Liste des médicaments - Full width */}
                    {prescription.medications?.length > 0 && (
                      <div className="mt-3 p-3 bg-slate-50 rounded-lg">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                          Détail des médicaments
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {prescription.medications.map((med, index) => (
                            <span 
                              key={index} 
                              className="inline-flex items-center px-2.5 py-1 rounded-full text-xs bg-white border border-slate-200 text-slate-700"
                            >
                              <Package className="w-3 h-3 mr-1 text-teal-600" />
                              {med.name} ({med.dosage} × {med.quantity})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Notes - Full width */}
                    {prescription.notes && (
                      <div className="mt-2 text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded-lg border border-amber-100">
                        <strong>Notes :</strong> {prescription.notes}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Infinite Scroll Loader */}
            {prescriptions.length > 0 && (
              <div className="flex flex-col items-center gap-4 py-6">
                <p className="text-sm text-slate-600">
                  {prescriptions.length} sur {totalPrescriptions + cancelledCount} ordonnances affichées
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
                    Charger plus d'ordonnances
                  </Button>
                )}
                {!hasNextPage && prescriptions.length > 0 && (
                  <p className="text-sm text-slate-400">✓ Toutes les ordonnances ont été chargées</p>
                )}
              </div>
            )}
          </>
        )}
        </>
        )}
      </div>
    </Layout>
  );
};

export default Prescriptions;
