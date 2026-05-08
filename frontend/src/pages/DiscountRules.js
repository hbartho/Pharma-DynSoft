import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Plus, Search, Trash2, Edit2, Zap, TrendingUp, Users, 
  Calendar, ShoppingCart, Clock, CheckCircle, XCircle, Settings,
  Power, PowerOff
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
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
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
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

const RULE_TYPES = {
  volume: { label: 'Volume d\'achat', icon: ShoppingCart, color: 'bg-blue-100 text-blue-600', description: 'Rabais selon le montant du panier' },
  loyalty: { label: 'Fidélité client', icon: Users, color: 'bg-purple-100 text-purple-600', description: 'Rabais selon le nombre d\'achats du client' },
  category: { label: 'Catégorie', icon: Settings, color: 'bg-orange-100 text-orange-600', description: 'Rabais sur certaines catégories de produits' },
  expiration: { label: 'Péremption proche', icon: Clock, color: 'bg-red-100 text-red-600', description: 'Rabais sur produits proches de la péremption' }
};

const DiscountRules = () => {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'volume',
    discount_type: 'percent',
    discount_value: '',
    max_discount_amount: '',
    priority: '0',
    is_cumulative: false,
    conditions: {}
  });

  // Fetch rules
  const { data, isLoading } = useQuery({
    queryKey: ['discount-rules'],
    queryFn: async () => {
      const response = await api.get('/discounts/rules');
      return response.data;
    }
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data) => api.post('/discounts/rules', data),
    onSuccess: () => {
      toast.success('Règle créée avec succès');
      queryClient.invalidateQueries(['discount-rules']);
      resetForm();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création');
    }
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => api.put(`/discounts/rules/${id}`, data),
    onSuccess: () => {
      toast.success('Règle mise à jour');
      queryClient.invalidateQueries(['discount-rules']);
      resetForm();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la mise à jour');
    }
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/discounts/rules/${id}`),
    onSuccess: () => {
      toast.success('Règle supprimée');
      queryClient.invalidateQueries(['discount-rules']);
      setDeleteTarget(null);
    }
  });

  // Toggle active mutation
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }) => api.put(`/discounts/rules/${id}`, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries(['discount-rules']);
    }
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      rule_type: 'volume',
      discount_type: 'percent',
      discount_value: '',
      max_discount_amount: '',
      priority: '0',
      is_cumulative: false,
      conditions: {}
    });
    setEditingRule(null);
    setShowForm(false);
  };

  const handleEdit = (rule) => {
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      discount_type: rule.discount_type,
      discount_value: rule.discount_value.toString(),
      max_discount_amount: rule.max_discount_amount?.toString() || '',
      priority: rule.priority?.toString() || '0',
      is_cumulative: rule.is_cumulative,
      conditions: rule.conditions || {}
    });
    setEditingRule(rule);
    setShowForm(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    const payload = {
      name: formData.name,
      description: formData.description || null,
      rule_type: formData.rule_type,
      discount_type: formData.discount_type,
      discount_value: parseFloat(formData.discount_value),
      max_discount_amount: formData.max_discount_amount ? parseFloat(formData.max_discount_amount) : null,
      priority: parseInt(formData.priority) || 0,
      is_cumulative: formData.is_cumulative,
      conditions: formData.conditions
    };

    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const updateCondition = (key, value) => {
    setFormData({
      ...formData,
      conditions: { ...formData.conditions, [key]: value }
    });
  };

  const rules = data?.items || [];
  const activeRules = rules.filter(r => r.is_active).length;

  const getRuleTypeConfig = (type) => RULE_TYPES[type] || RULE_TYPES.volume;

  const renderConditionsForm = () => {
    switch (formData.rule_type) {
      case 'volume':
        return (
          <div className="space-y-2">
            <Label>Montant minimum du panier (GNF)</Label>
            <Input
              type="number"
              value={formData.conditions.min_amount || ''}
              onChange={(e) => updateCondition('min_amount', parseInt(e.target.value))}
              placeholder="50000"
            />
          </div>
        );
      case 'loyalty':
        return (
          <div className="space-y-2">
            <Label>Nombre minimum d'achats</Label>
            <Input
              type="number"
              value={formData.conditions.min_purchases || ''}
              onChange={(e) => updateCondition('min_purchases', parseInt(e.target.value))}
              placeholder="20"
            />
          </div>
        );
      case 'expiration':
        return (
          <div className="space-y-2">
            <Label>Jours avant péremption</Label>
            <Input
              type="number"
              value={formData.conditions.days_before_expiry || ''}
              onChange={(e) => updateCondition('days_before_expiry', parseInt(e.target.value))}
              placeholder="30"
            />
          </div>
        );
      case 'category':
        return (
          <div className="space-y-2">
            <Label>Quantité minimum (dans la catégorie)</Label>
            <Input
              type="number"
              value={formData.conditions.min_quantity || ''}
              onChange={(e) => updateCondition('min_quantity', parseInt(e.target.value))}
              placeholder="3"
            />
            <p className="text-xs text-slate-500">
              Note: Les catégories spécifiques peuvent être configurées via l'API.
            </p>
          </div>
        );
      default:
        return null;
    }
  };

  const renderConditionsSummary = (rule) => {
    const conditions = rule.conditions || {};
    switch (rule.rule_type) {
      case 'volume':
        return conditions.min_amount ? `Panier > ${formatAmount(conditions.min_amount)}` : '';
      case 'loyalty':
        return conditions.min_purchases ? `${conditions.min_purchases}+ achats` : '';
      case 'expiration':
        return conditions.days_before_expiry ? `Expire dans ${conditions.days_before_expiry} jours` : '';
      case 'category':
        return conditions.min_quantity ? `${conditions.min_quantity}+ articles` : '';
      default:
        return '';
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Règles de Rabais</h1>
            <p className="text-slate-500">Configurez les rabais automatiques</p>
          </div>
          <Button onClick={() => setShowForm(true)} className="bg-teal-600 hover:bg-teal-700">
            <Plus className="w-4 h-4 mr-2" />
            Nouvelle règle
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-teal-100 rounded-lg">
                  <Zap className="w-6 h-6 text-teal-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{rules.length}</p>
                  <p className="text-sm text-slate-500">Règles configurées</p>
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
                  <p className="text-2xl font-bold">{activeRules}</p>
                  <p className="text-sm text-slate-500">Règles actives</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Rules List */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-8 text-slate-500">Chargement...</div>
          ) : rules.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Zap className="w-12 h-12 mx-auto text-slate-300 mb-4" />
                <p className="text-slate-500">Aucune règle de rabais configurée</p>
                <Button onClick={() => setShowForm(true)} variant="outline" className="mt-4">
                  Créer votre première règle
                </Button>
              </CardContent>
            </Card>
          ) : (
            rules.map((rule) => {
              const typeConfig = getRuleTypeConfig(rule.rule_type);
              const TypeIcon = typeConfig.icon;
              return (
                <Card key={rule.id} className={`transition-all ${rule.is_active ? '' : 'opacity-60'}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className={`p-3 rounded-lg ${typeConfig.color.split(' ')[0]}`}>
                          <TypeIcon className={`w-6 h-6 ${typeConfig.color.split(' ')[1]}`} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-slate-900">{rule.name}</h3>
                            {rule.is_active ? (
                              <Badge className="bg-emerald-100 text-emerald-700">Actif</Badge>
                            ) : (
                              <Badge className="bg-slate-100 text-slate-600">Inactif</Badge>
                            )}
                            {rule.is_cumulative && (
                              <Badge variant="outline">Cumulable</Badge>
                            )}
                          </div>
                          <p className="text-sm text-slate-500 mt-1">{typeConfig.label}</p>
                          <div className="flex items-center gap-4 mt-2">
                            <span className="font-semibold text-teal-600">
                              {rule.discount_type === 'percent' 
                                ? `-${rule.discount_value}%`
                                : `-${formatAmount(rule.discount_value)}`
                              }
                            </span>
                            <span className="text-sm text-slate-500">
                              {renderConditionsSummary(rule)}
                            </span>
                            <span className="text-xs text-slate-400">
                              Priorité: {rule.priority}
                            </span>
                          </div>
                          {rule.description && (
                            <p className="text-sm text-slate-400 mt-2">{rule.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => toggleActiveMutation.mutate({ id: rule.id, is_active: !rule.is_active })}
                          className={rule.is_active 
                            ? "text-amber-600 hover:text-amber-700 hover:bg-amber-50" 
                            : "text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                          }
                          title={rule.is_active ? "Désactiver la règle" : "Activer la règle"}
                        >
                          {rule.is_active ? (
                            <PowerOff className="w-4 h-4" strokeWidth={1.5} />
                          ) : (
                            <Power className="w-4 h-4" strokeWidth={1.5} />
                          )}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(rule)}>
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="text-red-500"
                          onClick={() => setDeleteTarget(rule)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>

        {/* Form Dialog */}
        <Dialog open={showForm} onOpenChange={(open) => !open && resetForm()}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editingRule ? 'Modifier la règle' : 'Nouvelle règle de rabais'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label>Nom de la règle *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Rabais volume premium"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label>Type de règle *</Label>
                <Select 
                  value={formData.rule_type} 
                  onValueChange={(v) => setFormData({ ...formData, rule_type: v, conditions: {} })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(RULE_TYPES).map(([key, config]) => (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center gap-2">
                          <config.icon className="w-4 h-4" />
                          {config.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-500">
                  {RULE_TYPES[formData.rule_type]?.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
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
                <div className="space-y-2">
                  <Label>Valeur *</Label>
                  <Input
                    type="number"
                    value={formData.discount_value}
                    onChange={(e) => setFormData({ ...formData, discount_value: e.target.value })}
                    placeholder={formData.discount_type === 'percent' ? '5' : '2000'}
                    required
                  />
                </div>
              </div>

              {/* Conditions based on rule type */}
              <div className="p-4 bg-slate-50 rounded-lg space-y-4">
                <h4 className="font-medium text-sm text-slate-700">Conditions d'application</h4>
                {renderConditionsForm()}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Priorité</Label>
                  <Input
                    type="number"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    placeholder="0"
                  />
                  <p className="text-xs text-slate-500">Plus élevé = prioritaire</p>
                </div>
                {formData.discount_type === 'percent' && (
                  <div className="space-y-2">
                    <Label>Plafond (GNF)</Label>
                    <Input
                      type="number"
                      value={formData.max_discount_amount}
                      onChange={(e) => setFormData({ ...formData, max_discount_amount: e.target.value })}
                      placeholder="Aucun"
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  id="is_cumulative"
                  checked={formData.is_cumulative}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_cumulative: checked })}
                />
                <Label htmlFor="is_cumulative" className="cursor-pointer">Cumulable avec d'autres rabais</Label>
              </div>

              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Description optionnelle..."
                  rows={2}
                />
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
                  {editingRule ? 'Mettre à jour' : 'Créer'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation */}
        <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Supprimer cette règle ?</AlertDialogTitle>
              <AlertDialogDescription>
                La règle <strong>{deleteTarget?.name}</strong> sera définitivement supprimée.
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

export default DiscountRules;
