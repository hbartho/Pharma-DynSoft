import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, FileText, CheckCircle, Edit, Trash2, X } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems, updateItem, deleteItem as deleteFromDB, addLocalChange } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'sonner';

const Prescriptions = () => {
  const [prescriptions, setPrescriptions] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPrescription, setEditingPrescription] = useState(null);
  const [formData, setFormData] = useState({
    customer_id: '',
    doctor_name: '',
    medications: [],
    notes: '',
  });
  const [medInput, setMedInput] = useState({ name: '', dosage: '', quantity: '' });
  const { isOnline } = useOffline();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      if (isOnline) {
        const [prescriptionsRes, customersRes] = await Promise.all([
          api.get('/prescriptions'),
          api.get('/customers'),
        ]);
        setPrescriptions(prescriptionsRes.data);
        setCustomers(customersRes.data);
      } else {
        const [localPrescriptions, localCustomers] = await Promise.all([
          getAllItems('prescriptions'),
          getAllItems('customers'),
        ]);
        setPrescriptions(localPrescriptions);
        setCustomers(localCustomers);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
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

    try {
      if (editingPrescription) {
        // Mode édition
        await handleEditSubmit(e);
        return;
      }

      // Mode création
      const prescriptionData = { ...formData, status: 'pending' };
      if (isOnline) {
        const response = await api.post('/prescriptions', prescriptionData);
        await addItem('prescriptions', response.data);
      } else {
        const newPrescription = { ...prescriptionData, id: Date.now().toString() };
        await addItem('prescriptions', newPrescription);
      }
      toast.success('Ordonnance ajoutée avec succès');
      loadData();
      setShowDialog(false);
      resetForm();
    } catch (error) {
      console.error('Error creating prescription:', error);
      toast.error('Erreur lors de l\'ajout de l\'ordonnance');
    }
  };

  const markAsFulfilled = async (prescriptionId) => {
    try {
      if (isOnline) {
        await api.put(`/prescriptions/${prescriptionId}?status=fulfilled`);
      }
      toast.success('Ordonnance marquée comme traitée');
      loadData();
    } catch (error) {
      console.error('Error updating prescription:', error);
      toast.error('Erreur lors de la mise à jour');
    }
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

  const handleDelete = async (prescriptionId) => {
    if (!window.confirm('Voulez-vous vraiment supprimer cette ordonnance?')) return;
    
    try {
      if (isOnline) {
        await api.delete(`/prescriptions/${prescriptionId}`);
      } else {
        await deleteFromDB('prescriptions', prescriptionId);
        await addLocalChange('prescription', 'delete', { id: prescriptionId });
      }
      toast.success('Ordonnance supprimée');
      loadData();
    } catch (error) {
      console.error('Error deleting prescription:', error);
      toast.error('Erreur lors de la suppression');
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.medications.length === 0) {
      toast.error('Veuillez ajouter au moins un médicament');
      return;
    }

    try {
      const prescriptionData = { ...formData };
      if (isOnline) {
        await api.put(`/prescriptions/${editingPrescription.id}/edit`, prescriptionData);
      } else {
        const updatedPrescription = { ...editingPrescription, ...prescriptionData };
        await updateItem('prescriptions', updatedPrescription);
        await addLocalChange('prescription', 'update', updatedPrescription);
      }
      toast.success('Ordonnance mise à jour avec succès');
      loadData();
      setShowDialog(false);
      resetForm();
    } catch (error) {
      console.error('Error updating prescription:', error);
      toast.error('Erreur lors de la mise à jour de l\'ordonnance');
    }
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

  return (
    <Layout>
      <div className="space-y-6" data-testid="prescriptions-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Ordonnances
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des ordonnances médicales
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-prescription-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
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
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        placeholder="Médicament"
                        value={medInput.name}
                        onChange={(e) => setMedInput({ ...medInput, name: e.target.value })}
                        data-testid="medication-name-input"
                      />
                      <Input
                        placeholder="Dosage"
                        value={medInput.dosage}
                        onChange={(e) => setMedInput({ ...medInput, dosage: e.target.value })}
                      />
                      <Input
                        placeholder="Quantité"
                        value={medInput.quantity}
                        onChange={(e) => setMedInput({ ...medInput, quantity: e.target.value })}
                      />
                    </div>
                    <Button type="button" onClick={addMedication} variant="outline" size="sm" data-testid="add-medication-button">
                      <Plus className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      Ajouter
                    </Button>
                  </div>
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
                  <Button type="submit" data-testid="prescription-submit-button" className="bg-teal-700 hover:bg-teal-800">
                    {editingPrescription ? 'Mettre à jour' : 'Ajouter'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {prescriptions.map((prescription) => (
            <div
              key={prescription.id}
              data-testid={`prescription-card-${prescription.id}`}
              className="p-6 rounded-xl bg-white border border-slate-100 hover:border-teal-200 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-teal-50 rounded-lg">
                    <FileText className="w-5 h-5 text-teal-700" strokeWidth={1.5} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg text-slate-900 mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      Patient: {getCustomerName(prescription.customer_id)}
                    </h3>
                    <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      Dr. {prescription.doctor_name}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${
                      prescription.status === 'fulfilled'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {prescription.status === 'fulfilled' ? 'Traitée' : 'En attente'}
                  </span>
                  {prescription.status === 'pending' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEdit(prescription)}
                        data-testid={`edit-prescription-${prescription.id}`}
                        className="mr-1"
                      >
                        <Edit className="w-4 h-4 mr-1" strokeWidth={1.5} />
                        Éditer
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDelete(prescription.id)}
                        data-testid={`delete-prescription-${prescription.id}`}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50 mr-2"
                      >
                        <Trash2 className="w-4 h-4 mr-1" strokeWidth={1.5} />
                        Supprimer
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => markAsFulfilled(prescription.id)}
                        data-testid={`fulfill-prescription-${prescription.id}`}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" strokeWidth={1.5} />
                        Marquer comme traitée
                      </Button>
                    </>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-700" style={{ fontFamily: 'Inter, sans-serif' }}>
                  Médicaments:
                </p>
                <div className="space-y-1">
                  {prescription.medications?.map((med, index) => (
                    <div key={index} className="text-sm text-slate-600 pl-4" style={{ fontFamily: 'Inter, sans-serif' }}>
                      • {med.name} - {med.dosage} - {med.quantity}
                    </div>
                  ))}
                </div>
                {prescription.notes && (
                  <p className="text-sm text-slate-600 mt-3" style={{ fontFamily: 'Inter, sans-serif' }}>
                    <span className="font-medium">Notes:</span> {prescription.notes}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        {prescriptions.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Aucune ordonnance enregistrée
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Prescriptions;