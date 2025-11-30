import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Plus, Truck } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'sonner';

const Suppliers = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
  });
  const { isOnline } = useOffline();

  useEffect(() => {
    loadSuppliers();
  }, []);

  const loadSuppliers = async () => {
    try {
      if (isOnline) {
        const response = await api.get('/suppliers');
        setSuppliers(response.data);
        for (const supplier of response.data) {
          await addItem('suppliers', supplier);
        }
      } else {
        const localSuppliers = await getAllItems('suppliers');
        setSuppliers(localSuppliers);
      }
    } catch (error) {
      console.error('Error loading suppliers:', error);
      const localSuppliers = await getAllItems('suppliers');
      setSuppliers(localSuppliers);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (isOnline) {
        const response = await api.post('/suppliers', formData);
        await addItem('suppliers', response.data);
      } else {
        const newSupplier = { ...formData, id: Date.now().toString() };
        await addItem('suppliers', newSupplier);
      }
      toast.success('Fournisseur ajouté avec succès');
      loadSuppliers();
      setShowDialog(false);
      setFormData({ name: '', phone: '', email: '', address: '' });
    } catch (error) {
      console.error('Error creating supplier:', error);
      toast.error('Erreur lors de l\'ajout du fournisseur');
    }
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="suppliers-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Fournisseurs
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des fournisseurs
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={setShowDialog}>
            <DialogTrigger asChild>
              <Button data-testid="add-supplier-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un fournisseur
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>Nouveau fournisseur</DialogTitle>
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
                  />
                </div>
                <div>
                  <Label htmlFor="phone">Téléphone</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="address">Adresse</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                    Annuler
                  </Button>
                  <Button type="submit" data-testid="supplier-submit-button" className="bg-teal-700 hover:bg-teal-800">
                    Ajouter
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {suppliers.map((supplier) => (
            <div
              key={supplier.id}
              data-testid={`supplier-card-${supplier.id}`}
              className="p-6 rounded-xl bg-white border border-slate-100 hover:border-teal-200 transition-all"
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="p-2 bg-teal-50 rounded-lg">
                  <Truck className="w-5 h-5 text-teal-700" strokeWidth={1.5} />
                </div>
                <h3 className="font-semibold text-lg text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {supplier.name}
                </h3>
              </div>
              <div className="space-y-2 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                {supplier.phone && (
                  <p>
                    <span className="font-medium">Tél:</span> {supplier.phone}
                  </p>
                )}
                {supplier.email && (
                  <p>
                    <span className="font-medium">Email:</span> {supplier.email}
                  </p>
                )}
                {supplier.address && (
                  <p>
                    <span className="font-medium">Adresse:</span> {supplier.address}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        {suppliers.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Truck className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Aucun fournisseur enregistré
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Suppliers;