import React, { useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Plus, Edit, Trash2, GripVertical, CreditCard, Banknote, Smartphone, 
  FileCheck, Wallet, CircleDollarSign, Power, PowerOff, X, Check,
  ArrowUp, ArrowDown, Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { 
  usePaymentMethods, 
  useCreatePaymentMethod, 
  useUpdatePaymentMethod, 
  useDeletePaymentMethod 
} from '../hooks/usePaymentMethods';
import { SkeletonTable } from '../components/ui/skeleton-shimmer';

// Mapping des icônes disponibles
const ICON_OPTIONS = [
  { value: 'banknote', label: 'Billets', Icon: Banknote },
  { value: 'credit-card', label: 'Carte', Icon: CreditCard },
  { value: 'smartphone', label: 'Mobile', Icon: Smartphone },
  { value: 'file-check', label: 'Chèque', Icon: FileCheck },
  { value: 'wallet', label: 'Portefeuille', Icon: Wallet },
  { value: 'circle-dollar-sign', label: 'Dollar', Icon: CircleDollarSign },
];

// Mapping des couleurs disponibles
const COLOR_OPTIONS = [
  { value: 'green', label: 'Vert', class: 'bg-green-500' },
  { value: 'orange', label: 'Orange', class: 'bg-orange-500' },
  { value: 'purple', label: 'Violet', class: 'bg-purple-500' },
  { value: 'blue', label: 'Bleu', class: 'bg-blue-500' },
  { value: 'yellow', label: 'Jaune', class: 'bg-yellow-500' },
  { value: 'red', label: 'Rouge', class: 'bg-red-500' },
  { value: 'teal', label: 'Sarcelle', class: 'bg-teal-500' },
  { value: 'pink', label: 'Rose', class: 'bg-pink-500' },
];

// Types de champs disponibles
const FIELD_TYPES = [
  { value: 'text', label: 'Texte' },
  { value: 'tel', label: 'Téléphone' },
  { value: 'number', label: 'Nombre' },
  { value: 'email', label: 'Email' },
];

const PaymentMethods = () => {
  // React Query hooks
  const { data: paymentMethods = [], isLoading } = usePaymentMethods(false); // all methods
  const createPaymentMethod = useCreatePaymentMethod();
  const updatePaymentMethod = useUpdatePaymentMethod();
  const deletePaymentMethod = useDeletePaymentMethod();

  // Local state
  const [showDialog, setShowDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [editingMethod, setEditingMethod] = useState(null);
  const [methodToDelete, setMethodToDelete] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    icon: 'banknote',
    color: 'green',
    is_active: true,
    display_order: 0,
    required_fields: [],
  });
  
  // Champ en cours d'édition
  const [newField, setNewField] = useState({
    name: '',
    label: '',
    type: 'text',
    placeholder: '',
    required: true,
    maxLength: null,
  });

  // Obtenir l'icône par son nom
  const getIconComponent = (iconName) => {
    const icon = ICON_OPTIONS.find(i => i.value === iconName);
    return icon ? icon.Icon : Banknote;
  };

  // Obtenir la classe de couleur
  const getColorClass = (colorName, type = 'bg') => {
    const colorMap = {
      green: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200' },
      orange: { bg: 'bg-orange-100', text: 'text-orange-700', border: 'border-orange-200' },
      purple: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-200' },
      blue: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
      yellow: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-200' },
      red: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
      teal: { bg: 'bg-teal-100', text: 'text-teal-700', border: 'border-teal-200' },
      pink: { bg: 'bg-pink-100', text: 'text-pink-700', border: 'border-pink-200' },
    };
    return colorMap[colorName]?.[type] || colorMap.green[type];
  };

  // Ouvrir le dialog pour créer
  const handleCreate = () => {
    setEditingMethod(null);
    setFormData({
      code: '',
      name: '',
      icon: 'banknote',
      color: 'green',
      is_active: true,
      display_order: paymentMethods.length + 1,
      required_fields: [],
    });
    setShowDialog(true);
  };

  // Ouvrir le dialog pour éditer
  const handleEdit = (method) => {
    setEditingMethod(method);
    setFormData({
      code: method.code,
      name: method.name,
      icon: method.icon || 'banknote',
      color: method.color || 'green',
      is_active: method.is_active,
      display_order: method.display_order || 0,
      required_fields: method.required_fields || [],
    });
    setShowDialog(true);
  };

  // Ajouter un champ requis
  const handleAddField = () => {
    if (!newField.name.trim() || !newField.label.trim()) {
      toast.error('Le nom et le label du champ sont obligatoires');
      return;
    }
    
    // Vérifier que le nom n'existe pas déjà
    if (formData.required_fields.some(f => f.name === newField.name)) {
      toast.error('Un champ avec ce nom existe déjà');
      return;
    }
    
    setFormData({
      ...formData,
      required_fields: [...formData.required_fields, { ...newField }],
    });
    
    // Réinitialiser le formulaire de nouveau champ
    setNewField({
      name: '',
      label: '',
      type: 'text',
      placeholder: '',
      required: true,
      maxLength: null,
    });
  };

  // Supprimer un champ requis
  const handleRemoveField = (fieldName) => {
    setFormData({
      ...formData,
      required_fields: formData.required_fields.filter(f => f.name !== fieldName),
    });
  };

  // Déplacer un champ vers le haut
  const handleMoveFieldUp = (index) => {
    if (index === 0) return;
    const fields = [...formData.required_fields];
    [fields[index - 1], fields[index]] = [fields[index], fields[index - 1]];
    setFormData({ ...formData, required_fields: fields });
  };

  // Déplacer un champ vers le bas
  const handleMoveFieldDown = (index) => {
    if (index === formData.required_fields.length - 1) return;
    const fields = [...formData.required_fields];
    [fields[index], fields[index + 1]] = [fields[index + 1], fields[index]];
    setFormData({ ...formData, required_fields: fields });
  };

  // Soumettre le formulaire
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.code.trim() || !formData.name.trim()) {
      toast.error('Le code et le nom sont obligatoires');
      return;
    }
    
    // Nettoyer les champs requis
    const cleanedFields = formData.required_fields.map(field => ({
      name: field.name,
      label: field.label,
      type: field.type,
      placeholder: field.placeholder || '',
      required: field.required,
      ...(field.maxLength ? { maxLength: parseInt(field.maxLength) } : {}),
    }));
    
    const dataToSend = {
      ...formData,
      required_fields: cleanedFields,
    };
    
    if (editingMethod) {
      updatePaymentMethod.mutate(
        { id: editingMethod.id, data: dataToSend },
        {
          onSuccess: () => {
            toast.success('Mode de paiement mis à jour');
            setShowDialog(false);
          },
          onError: (error) => {
            toast.error(error.response?.data?.detail || 'Erreur lors de la mise à jour');
          },
        }
      );
    } else {
      createPaymentMethod.mutate(dataToSend, {
        onSuccess: () => {
          toast.success('Mode de paiement créé');
          setShowDialog(false);
        },
        onError: (error) => {
          toast.error(error.response?.data?.detail || 'Erreur lors de la création');
        },
      });
    }
  };

  // Confirmer la suppression
  const handleDeleteConfirm = () => {
    if (!methodToDelete) return;
    
    deletePaymentMethod.mutate(methodToDelete.id, {
      onSuccess: () => {
        toast.success('Mode de paiement supprimé');
        setShowDeleteDialog(false);
        setMethodToDelete(null);
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
      },
    });
  };

  // Toggle status
  const handleToggleStatus = (method) => {
    updatePaymentMethod.mutate(
      { id: method.id, data: { is_active: !method.is_active } },
      {
        onSuccess: () => {
          toast.success(method.is_active ? 'Mode désactivé' : 'Mode activé');
        },
      }
    );
  };

  // Trier les méthodes par ordre d'affichage
  const sortedMethods = [...paymentMethods].sort((a, b) => 
    (a.display_order || 0) - (b.display_order || 0)
  );

  return (
    <Layout>
      <div className="space-y-6" data-testid="payment-methods-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Modes de paiement
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gérez les modes de paiement disponibles pour les ventes
            </p>
          </div>
          <Button 
            onClick={handleCreate}
            className="bg-teal-700 hover:bg-teal-800 rounded-full"
            data-testid="new-payment-method-button"
          >
            <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
            Nouveau mode
          </Button>
        </div>

        {/* Liste des modes de paiement */}
        {isLoading ? (
          <SkeletonTable rows={5} columns={6} />
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Ordre</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Mode</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Code</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Champs requis</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Statut</th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {sortedMethods.map((method, index) => {
                  const IconComponent = getIconComponent(method.icon);
                  return (
                    <tr 
                      key={method.id} 
                      className={`hover:bg-slate-50 transition-colors ${!method.is_active ? 'opacity-50' : ''}`}
                      data-testid={`payment-method-row-${method.code}`}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <GripVertical className="w-4 h-4 text-slate-400" />
                          <span className="text-sm font-medium text-slate-600">{method.display_order || index + 1}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${getColorClass(method.color, 'bg')}`}>
                            <IconComponent className={`w-5 h-5 ${getColorClass(method.color, 'text')}`} />
                          </div>
                          <span className="font-medium text-slate-900">{method.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <code className="text-sm bg-slate-100 px-2 py-1 rounded text-slate-700">
                          {method.code}
                        </code>
                      </td>
                      <td className="px-6 py-4">
                        {method.required_fields?.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {method.required_fields.map((field, idx) => (
                              <span 
                                key={idx}
                                className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded"
                              >
                                {field.label}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-sm text-slate-400">Aucun</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button
                          onClick={() => handleToggleStatus(method)}
                          className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                            method.is_active
                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          {method.is_active ? (
                            <>
                              <Power className="w-3 h-3" />
                              Actif
                            </>
                          ) : (
                            <>
                              <PowerOff className="w-3 h-3" />
                              Inactif
                            </>
                          )}
                        </button>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEdit(method)}
                            data-testid={`edit-${method.code}`}
                          >
                            <Edit className="w-4 h-4" strokeWidth={1.5} />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setMethodToDelete(method);
                              setShowDeleteDialog(true);
                            }}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            data-testid={`delete-${method.code}`}
                          >
                            <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            
            {sortedMethods.length === 0 && (
              <div className="text-center py-12">
                <CreditCard className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
                <p className="text-slate-500">Aucun mode de paiement configuré</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Dialog Création/Édition */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              {editingMethod ? 'Modifier le mode de paiement' : 'Nouveau mode de paiement'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Informations de base */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="code">Code <span className="text-red-500">*</span></Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toLowerCase().replace(/\s/g, '_') })}
                  placeholder="ex: mobile_money"
                  className="mt-1"
                  disabled={!!editingMethod}
                />
                <p className="text-xs text-slate-500 mt-1">Identifiant unique (non modifiable après création)</p>
              </div>
              <div>
                <Label htmlFor="name">Nom <span className="text-red-500">*</span></Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="ex: Mobile Money"
                  className="mt-1"
                />
              </div>
            </div>

            {/* Icône et Couleur */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Icône</Label>
                <Select value={formData.icon} onValueChange={(v) => setFormData({ ...formData, icon: v })}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ICON_OPTIONS.map((icon) => (
                      <SelectItem key={icon.value} value={icon.value}>
                        <div className="flex items-center gap-2">
                          <icon.Icon className="w-4 h-4" />
                          {icon.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Couleur</Label>
                <Select value={formData.color} onValueChange={(v) => setFormData({ ...formData, color: v })}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COLOR_OPTIONS.map((color) => (
                      <SelectItem key={color.value} value={color.value}>
                        <div className="flex items-center gap-2">
                          <div className={`w-4 h-4 rounded ${color.class}`} />
                          {color.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Ordre et Statut */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="display_order">Ordre d'affichage</Label>
                <Input
                  id="display_order"
                  type="number"
                  min="1"
                  value={formData.display_order}
                  onChange={(e) => setFormData({ ...formData, display_order: parseInt(e.target.value) || 1 })}
                  className="mt-1"
                />
              </div>
              <div className="flex items-center gap-3 pt-6">
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label>Mode actif</Label>
              </div>
            </div>

            {/* Prévisualisation */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <p className="text-sm font-medium text-slate-700 mb-3">Prévisualisation</p>
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${getColorClass(formData.color, 'bg')}`}>
                  {(() => {
                    const IconComponent = getIconComponent(formData.icon);
                    return <IconComponent className={`w-5 h-5 ${getColorClass(formData.color, 'text')}`} />;
                  })()}
                </div>
                <span className="font-medium text-slate-900">{formData.name || 'Nom du mode'}</span>
                <code className="text-xs bg-slate-200 px-2 py-0.5 rounded">{formData.code || 'code'}</code>
              </div>
            </div>

            {/* Champs requis */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label className="text-base">Champs requis</Label>
                <span className="text-sm text-slate-500">{formData.required_fields.length} champ(s)</span>
              </div>
              
              {/* Liste des champs existants */}
              {formData.required_fields.length > 0 && (
                <div className="space-y-2">
                  {formData.required_fields.map((field, index) => (
                    <div 
                      key={field.name}
                      className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200"
                    >
                      <div className="flex flex-col gap-1">
                        <button
                          type="button"
                          onClick={() => handleMoveFieldUp(index)}
                          disabled={index === 0}
                          className="p-0.5 hover:bg-slate-200 rounded disabled:opacity-30"
                        >
                          <ArrowUp className="w-3 h-3" />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleMoveFieldDown(index)}
                          disabled={index === formData.required_fields.length - 1}
                          className="p-0.5 hover:bg-slate-200 rounded disabled:opacity-30"
                        >
                          <ArrowDown className="w-3 h-3" />
                        </button>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900">{field.label}</span>
                          <code className="text-xs bg-slate-200 px-1.5 py-0.5 rounded">{field.name}</code>
                          <span className="text-xs text-slate-500">({field.type})</span>
                          {field.required && (
                            <span className="text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded">requis</span>
                          )}
                        </div>
                        {field.placeholder && (
                          <p className="text-xs text-slate-500 mt-0.5">Placeholder: {field.placeholder}</p>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveField(field.name)}
                        className="p-1 text-red-500 hover:bg-red-50 rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Formulaire d'ajout de champ */}
              <div className="p-4 bg-slate-100 rounded-lg space-y-3">
                <p className="text-sm font-medium text-slate-700">Ajouter un champ</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Nom technique</Label>
                    <Input
                      value={newField.name}
                      onChange={(e) => setNewField({ ...newField, name: e.target.value.toLowerCase().replace(/\s/g, '_') })}
                      placeholder="ex: phone_number"
                      className="mt-1 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Label affiché</Label>
                    <Input
                      value={newField.label}
                      onChange={(e) => setNewField({ ...newField, label: e.target.value })}
                      placeholder="ex: Numéro de téléphone"
                      className="mt-1 text-sm"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label className="text-xs">Type</Label>
                    <Select value={newField.type} onValueChange={(v) => setNewField({ ...newField, type: v })}>
                      <SelectTrigger className="mt-1 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {FIELD_TYPES.map((type) => (
                          <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Placeholder</Label>
                    <Input
                      value={newField.placeholder}
                      onChange={(e) => setNewField({ ...newField, placeholder: e.target.value })}
                      placeholder="ex: 620 00 00 00"
                      className="mt-1 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Max. caractères</Label>
                    <Input
                      type="number"
                      value={newField.maxLength || ''}
                      onChange={(e) => setNewField({ ...newField, maxLength: e.target.value ? parseInt(e.target.value) : null })}
                      placeholder="Illimité"
                      className="mt-1 text-sm"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={newField.required}
                      onCheckedChange={(checked) => setNewField({ ...newField, required: checked })}
                    />
                    <Label className="text-xs">Champ obligatoire</Label>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAddField}
                    className="text-teal-700 border-teal-200 hover:bg-teal-50"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Ajouter
                  </Button>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                Annuler
              </Button>
              <Button 
                type="submit" 
                className="bg-teal-700 hover:bg-teal-800"
                disabled={createPaymentMethod.isPending || updatePaymentMethod.isPending}
              >
                {(createPaymentMethod.isPending || updatePaymentMethod.isPending) && (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                )}
                {editingMethod ? 'Mettre à jour' : 'Créer'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog de confirmation de suppression */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce mode de paiement ?</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer le mode "{methodToDelete?.name}" ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
            >
              {deletePaymentMethod.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default PaymentMethods;
