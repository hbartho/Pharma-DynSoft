import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Plus, Users } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'sonner';

const Customers = () => {
  const [customers, setCustomers] = useState([]);
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
  });
  const { isOnline } = useOffline();

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      if (isOnline) {
        const response = await api.get('/customers');
        setCustomers(response.data);
        for (const customer of response.data) {
          await addItem('customers', customer);
        }
      } else {
        const localCustomers = await getAllItems('customers');
        setCustomers(localCustomers);
      }
    } catch (error) {
      console.error('Error loading customers:', error);
      const localCustomers = await getAllItems('customers');
      setCustomers(localCustomers);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (isOnline) {
        const response = await api.post('/customers', formData);
        await addItem('customers', response.data);
      } else {
        const newCustomer = { ...formData, id: Date.now().toString() };
        await addItem('customers', newCustomer);
      }
      toast.success('Client ajouté avec succès');
      loadCustomers();
      setShowDialog(false);
      setFormData({ name: '', phone: '', email: '', address: '' });
    } catch (error) {
      console.error('Error creating customer:', error);
      toast.error('Erreur lors de l\'ajout du client');
    }
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="customers-page">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Clients
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion de la base clients
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={setShowDialog}>
            <DialogTrigger asChild>
              <Button data-testid="add-customer-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un client
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>Nouveau client</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="customer-form">
                <div>
                  <Label htmlFor="name">Nom *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="customer-name-input"
                  />
                </div>
                <div>
                  <Label htmlFor="phone">Téléphone</Label>
                  <Input
                    id="phone"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    data-testid="customer-phone-input"
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
                  <Button type="submit" data-testid="customer-submit-button" className="bg-teal-700 hover:bg-teal-800">
                    Ajouter
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {customers.map((customer) => (
            <div
              key={customer.id}
              data-testid={`customer-card-${customer.id}`}
              className="p-6 rounded-xl bg-white border border-slate-100 hover:border-teal-200 transition-all"
            >
              <h3 className="font-semibold text-lg text-slate-900 mb-3" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {customer.name}
              </h3>
              <div className="space-y-2 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                {customer.phone && (
                  <p>
                    <span className="font-medium">Tél:</span> {customer.phone}
                  </p>
                )}
                {customer.email && (
                  <p>
                    <span className="font-medium">Email:</span> {customer.email}
                  </p>
                )}
                {customer.address && (
                  <p>
                    <span className="font-medium">Adresse:</span> {customer.address}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>

        {customers.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Aucun client enregistré
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Customers;