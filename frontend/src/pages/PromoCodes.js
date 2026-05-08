import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { 
  Plus, Search, Trash2, Edit2, Tag, Percent, DollarSign, 
  Calendar, Users, CheckCircle, XCircle, Copy, Gift
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";

const formatAmount = (amount) => {
  return new Intl.NumberFormat('fr-GN').format(Math.round(amount || 0)) + ' GNF';
};

const PromoCodes = () => {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingCode, setEditingCode] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    discount_type: 'percent',
    discount_value: '',
    min_purchase_amount: '0',
    max_discount_amount: '',
    start_date: '',
    end_date: '',
    max_uses: '',
    max_uses_per_customer: '1',
    first_purchase_only: false
  });

  // Fetch promo codes
  const { data, isLoading } = useQuery({
    queryKey: ['promo-codes', search, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (statusFilter) params.append('status', statusFilter);
      const response = await api.get(`/discounts/promo-codes?${params}`);
      return response.data;
    }
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => api.post('/discounts/promo-codes', data),
    onSuccess: () => {
      toast.success('Code promo créé avec succès');
      queryClient.invalidateQueries(['promo-codes']);
      resetForm();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création');
    }
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.put(`/discounts/promo-codes/${id}`, data),
    onSuccess: () => {
      toast.success('Code promo mis à jour');
      queryClient.invalidateQueries(['promo-codes']);
      resetForm();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la mise à jour');
    }
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/discounts/promo-codes/${id}`),
    onSuccess: () => {
      toast.success('Code promo supprimé');
      queryClient.invalidateQueries(['promo-codes']);
      setDeleteTarget(null);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  });

  const resetForm = () => {
    setFormData({
      code: '',
      name: '',
      description: '',
      discount_type: 'percent',
      discount_value: '',
      min_purchase_amount: '0',
      max_discount_amount: '',
      start_date: '',
      end_date: '',
      max_uses: '',
      max_uses_per_customer: '1',
      first_purchase_only: false
    });
    setEditingCode(null);
    setShowForm(false);
  };

  const handleEdit = (code) => {
    setFormData({
      code: code.code,
      name: code.name,
      description: code.description || '',
      discount_type: code.discount_type,
      discount_value: code.discount_value.toString(),
      min_purchase_amount: code.min_purchase_amount?.toString() || '0',
      max_discount_amount: code.max_discount_amount?.toString() || '',
      start_date: code.start_date ? code.start_date.split('T')[0] : '',
      end_date: code.end_date ? code.end_date.split('T')[0] : '',
      max_uses: code.max_uses?.toString() || '',
      max_uses_per_customer: code.max_uses_per_customer?.toString() || '1',
      first_purchase_only: code.first_purchase_only
    });
    setEditingCode(code);
    setShowForm(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    const payload = {
      code: formData.code.toUpperCase(),
      name: formData.name,
      description: formData.description || null,
      discount_type: formData.discount_type,
      discount_value: parseFloat(formData.discount_value),
      min_purchase_amount: parseFloat(formData.min_purchase_amount) || 0,
      max_discount_amount: formData.max_discount_amount ? parseFloat(formData.max_discount_amount) : null,
      start_date: formData.start_date || null,
      end_date: formData.end_date || null,
      max_uses: formData.max_uses ? parseInt(formData.max_uses) : null,
      max_uses_per_customer: parseInt(formData.max_uses_per_customer) || 1,
      first_purchase_only: formData.first_purchase_only
    };

    if (editingCode) {
      updateMutation.mutate({ id: editingCode.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const copyCode = (code) => {
    navigator.clipboard.writeText(code);
    toast.success('Code copié !');
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-emerald-100 text-emerald-700">Actif</Badge>;
      case 'inactive':
        return <Badge className="bg-slate-100 text-slate-700">Inactif</Badge>;
      case 'expired':
        return <Badge className="bg-red-100 text-red-700">Expiré</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const promoCodes = data?.items || [];

  // Stats
  const stats = {
    total: promoCodes.length,
    active: promoCodes.filter(c => c.status === 'active').length,
    totalUsed: promoCodes.reduce((sum, c) => sum + (c.current_uses || 0), 0)
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Codes Promo</h1>
            <p className="text-slate-500">Gérez vos codes promotionnels</p>
          </div>
          <Button onClick={() => setShowForm(true)} className="bg-teal-600 hover:bg-teal-700">
            <Plus className="w-4 h-4 mr-2" />
            Nouveau code
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-teal-100 rounded-lg">
                  <Tag className="w-6 h-6 text-teal-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.total}</p>
                  <p className="text-sm text-slate-500">Codes créés</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-100 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-emerald-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.active}</p>
                  <p className="text-sm text-slate-500">Codes actifs</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <Users className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.totalUsed}</p>
                  <p className="text-sm text-slate-500">Utilisations</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Rechercher un code..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={statusFilter || 'all'} onValueChange={(v) => setStatusFilter(v === 'all' ? '' : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Tous les statuts" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les statuts</SelectItem>
              <SelectItem value="active">Actifs</SelectItem>
              <SelectItem value="inactive">Inactifs</SelectItem>
              <SelectItem value="expired">Expirés</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Promo Codes List */}
        <div className="grid gap-4">
          {isLoading ? (
            <div className="text-center py-8 text-slate-500">Chargement...</div>
          ) : promoCodes.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Gift className="w-12 h-12 mx-auto text-slate-300 mb-4" />
                <p className="text-slate-500">Aucun code promo trouvé</p>
                <Button onClick={() => setShowForm(true)} variant="outline" className="mt-4">
                  Créer votre premier code
                </Button>
              </CardContent>
            </Card>
          ) : (
            promoCodes.map((code) => (
              <Card key={code.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className={`p-3 rounded-lg ${code.discount_type === 'percent' ? 'bg-purple-100' : 'bg-green-100'}`}>
                        {code.discount_type === 'percent' 
                          ? <Percent className="w-6 h-6 text-purple-600" />
                          : <DollarSign className="w-6 h-6 text-green-600" />
                        }
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-lg font-bold text-slate-900">{code.code}</span>
                          <button 
                            onClick={() => copyCode(code.code)}
                            className="p-1 hover:bg-slate-100 rounded"
                          >
                            <Copy className="w-4 h-4 text-slate-400" />
                          </button>
                          {getStatusBadge(code.status)}
                        </div>
                        <p className="text-sm text-slate-600 mt-1">{code.name}</p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                          <span className="font-semibold text-teal-600">
                            {code.discount_type === 'percent' 
                              ? `-${code.discount_value}%`
                              : `-${formatAmount(code.discount_value)}`
                            }
                          </span>
                          {code.min_purchase_amount > 0 && (
                            <span>Min: {formatAmount(code.min_purchase_amount)}</span>
                          )}
                          {code.max_uses && (
                            <span>{code.current_uses}/{code.max_uses} utilisations</span>
                          )}
                          {code.first_purchase_only && (
                            <Badge variant="outline" className="text-xs">Nouveaux clients</Badge>
                          )}
                        </div>
                        {(code.start_date || code.end_date) && (
                          <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
                            <Calendar className="w-3 h-3" />
                            {code.start_date && format(new Date(code.start_date), 'dd/MM/yyyy', { locale: fr })}
                            {code.start_date && code.end_date && ' → '}
                            {code.end_date && format(new Date(code.end_date), 'dd/MM/yyyy', { locale: fr })}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(code)}>
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-red-500 hover:text-red-700"
                        onClick={() => setDeleteTarget(code)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>

        {/* Form Dialog */}
        <Dialog open={showForm} onOpenChange={(open) => !open && resetForm()}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editingCode ? 'Modifier le code promo' : 'Nouveau code promo'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Code *</Label>
                  <Input
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    placeholder="PROMO2026"
                    className="font-mono"
                    required
                    disabled={!!editingCode}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Type de réduction *</Label>
                  <Select 
                    value={formData.discount_type} 
                    onValueChange={(v) => setFormData({ ...formData, discount_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percent">Pourcentage (%)</SelectItem>
                      <SelectItem value="amount">Montant fixe (GNF)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Nom *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Promotion de bienvenue"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Valeur de réduction *</Label>
                  <Input
                    type="number"
                    value={formData.discount_value}
                    onChange={(e) => setFormData({ ...formData, discount_value: e.target.value })}
                    placeholder={formData.discount_type === 'percent' ? '10' : '5000'}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Montant minimum d'achat</Label>
                  <Input
                    type="number"
                    value={formData.min_purchase_amount}
                    onChange={(e) => setFormData({ ...formData, min_purchase_amount: e.target.value })}
                    placeholder="0"
                  />
                </div>
              </div>

              {formData.discount_type === 'percent' && (
                <div className="space-y-2">
                  <Label>Plafond de réduction (GNF)</Label>
                  <Input
                    type="number"
                    value={formData.max_discount_amount}
                    onChange={(e) => setFormData({ ...formData, max_discount_amount: e.target.value })}
                    placeholder="Aucun plafond"
                  />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Date de début</Label>
                  <Input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Date de fin</Label>
                  <Input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nombre max d'utilisations</Label>
                  <Input
                    type="number"
                    value={formData.max_uses}
                    onChange={(e) => setFormData({ ...formData, max_uses: e.target.value })}
                    placeholder="Illimité"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Utilisations par client</Label>
                  <Input
                    type="number"
                    value={formData.max_uses_per_customer}
                    onChange={(e) => setFormData({ ...formData, max_uses_per_customer: e.target.value })}
                    placeholder="1"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Switch
                  checked={formData.first_purchase_only}
                  onCheckedChange={(checked) => setFormData({ ...formData, first_purchase_only: checked })}
                />
                <Label>Réservé aux nouveaux clients (première commande)</Label>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={resetForm}>
                  Annuler
                </Button>
                <Button 
                  type="submit" 
                  className="bg-teal-600 hover:bg-teal-700"
                  disabled={createMutation.isPending || updateMutation.isPending}
                >
                  {editingCode ? 'Mettre à jour' : 'Créer'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Supprimer ce code promo ?</AlertDialogTitle>
              <AlertDialogDescription>
                Le code <strong>{deleteTarget?.code}</strong> sera définitivement supprimé.
                Cette action est irréversible.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Annuler</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => deleteMutation.mutate(deleteTarget.id)}
                className="bg-red-600 hover:bg-red-700"
              >
                Supprimer
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </Layout>
  );
};

export default PromoCodes;
