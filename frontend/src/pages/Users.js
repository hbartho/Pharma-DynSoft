import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Users as UsersIcon, Edit, Trash2, Search, Shield, ShieldCheck, ShieldAlert, UserCog } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Navigate } from 'react-router-dom';

const ROLES = [
  { value: 'admin', label: 'Administrateur', icon: ShieldAlert, color: 'text-red-600 bg-red-50' },
  { value: 'pharmacien', label: 'Pharmacien', icon: ShieldCheck, color: 'text-blue-600 bg-blue-50' },
  { value: 'caissier', label: 'Caissier', icon: Shield, color: 'text-green-600 bg-green-50' },
];

const getRoleInfo = (role) => {
  return ROLES.find(r => r.value === role) || ROLES[2];
};

const Users = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'caissier',
    tenant_id: '',
  });

  useEffect(() => {
    if (user?.role === 'admin') {
      loadUsers();
    }
  }, [user]);

  // Redirect if not admin
  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/users');
      setUsers(response.data);
    } catch (error) {
      console.error('Error loading users:', error);
      toast.error('Erreur lors du chargement des utilisateurs');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingUser) {
        // Mode édition - update user
        const updateData = {
          name: formData.name,
          role: formData.role,
        };
        await api.put(`/users/${editingUser.id}`, updateData);
        toast.success('Utilisateur mis à jour avec succès');
      } else {
        // Mode création - create new user
        const createData = {
          ...formData,
          tenant_id: user.tenant_id,
        };
        await api.post('/users', createData);
        toast.success('Utilisateur créé avec succès');
      }
      
      setShowDialog(false);
      resetForm();
      await loadUsers();
    } catch (error) {
      console.error('Error saving user:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'enregistrement');
    }
  };

  const handleEdit = (userToEdit) => {
    setEditingUser(userToEdit);
    setFormData({
      name: userToEdit.name || '',
      email: userToEdit.email || '',
      password: '',
      role: userToEdit.role || 'caissier',
      tenant_id: userToEdit.tenant_id,
    });
    setShowDialog(true);
  };

  const handleDelete = (userToRemove) => {
    if (userToRemove.id === user.id) {
      toast.error('Vous ne pouvez pas supprimer votre propre compte');
      return;
    }
    setUserToDelete(userToRemove);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!userToDelete) return;
    
    try {
      await api.delete(`/users/${userToDelete.id}`);
      toast.success('Utilisateur supprimé avec succès');
      await loadUsers();
      setShowDeleteDialog(false);
      setUserToDelete(null);
    } catch (error) {
      console.error('Error deleting user:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const resetForm = () => {
    setEditingUser(null);
    setFormData({
      name: '',
      email: '',
      password: '',
      role: 'caissier',
      tenant_id: '',
    });
  };

  const filteredUsers = users.filter((u) =>
    u.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.role?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Layout>
      <div className="space-y-6" data-testid="users-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Gestion des utilisateurs
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gérer les comptes et les permissions
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-user-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un utilisateur
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingUser ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="user-form">
                <div>
                  <Label htmlFor="name">Nom complet *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="user-name-input"
                    placeholder="Jean Dupont"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                    disabled={!!editingUser}
                    data-testid="user-email-input"
                    placeholder="jean.dupont@pharmacie.fr"
                  />
                </div>
                {!editingUser && (
                  <div>
                    <Label htmlFor="password">Mot de passe *</Label>
                    <Input
                      id="password"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required={!editingUser}
                      data-testid="user-password-input"
                      placeholder="••••••••"
                    />
                  </div>
                )}
                <div className="min-h-[120px]">
                  <Label htmlFor="role">Rôle *</Label>
                  <Select 
                    value={formData.role} 
                    onValueChange={(value) => setFormData({ ...formData, role: value })}
                  >
                    <SelectTrigger data-testid="user-role-select">
                      <SelectValue placeholder="Sélectionner un rôle" />
                    </SelectTrigger>
                    <SelectContent position="popper" sideOffset={4}>
                      {ROLES.map((role) => (
                        <SelectItem key={role.value} value={role.value}>
                          <div className="flex items-center gap-2">
                            <role.icon className="w-4 h-4" />
                            {role.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 mt-2">
                  <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                    Annuler
                  </Button>
                  <Button type="submit" data-testid="user-submit-button" className="bg-teal-700 hover:bg-teal-800">
                    {editingUser ? 'Mettre à jour' : 'Créer'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Role Legend */}
        <div className="flex items-center gap-4 p-4 bg-white rounded-xl border border-slate-100">
          <span className="text-sm font-medium text-slate-600">Légende des rôles:</span>
          {ROLES.map((role) => {
            const Icon = role.icon;
            return (
              <div key={role.value} className={`flex items-center gap-2 px-3 py-1 rounded-full ${role.color}`}>
                <Icon className="w-4 h-4" strokeWidth={1.5} />
                <span className="text-sm font-medium">{role.label}</span>
              </div>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
          <Input
            placeholder="Rechercher par nom, email ou rôle..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="user-search-input"
            className="pl-10"
          />
        </div>

        {/* Users Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700 mx-auto"></div>
            <p className="text-slate-500 mt-4">Chargement...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredUsers.map((u) => {
              const roleInfo = getRoleInfo(u.role);
              const Icon = roleInfo.icon;
              const isCurrentUser = u.id === user?.id;
              
              return (
                <div
                  key={u.id}
                  data-testid={`user-card-${u.id}`}
                  className={`p-6 rounded-xl bg-white border ${isCurrentUser ? 'border-teal-300 bg-teal-50/30' : 'border-slate-100'} hover:border-teal-200 transition-all`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${roleInfo.color}`}>
                        <Icon className="w-5 h-5" strokeWidth={1.5} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-lg text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                          {u.name}
                          {isCurrentUser && (
                            <span className="ml-2 text-xs font-normal text-teal-600">(Vous)</span>
                          )}
                        </h3>
                        <p className="text-sm text-slate-500">{u.email}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${roleInfo.color}`}>
                      <Icon className="w-3 h-3" strokeWidth={1.5} />
                      {roleInfo.label}
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-3 border-t border-slate-100">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(u)}
                      data-testid={`edit-user-${u.id}`}
                      className="flex-1"
                    >
                      <Edit className="w-4 h-4 mr-1" strokeWidth={1.5} />
                      Éditer
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(u)}
                      disabled={isCurrentUser}
                      data-testid={`delete-user-${u.id}`}
                      className={`${isCurrentUser ? 'opacity-50 cursor-not-allowed' : 'text-red-600 hover:text-red-700 hover:bg-red-50'}`}
                    >
                      <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!loading && filteredUsers.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <UsersIcon className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              {searchQuery ? 'Aucun utilisateur trouvé' : 'Aucun utilisateur enregistré'}
            </p>
          </div>
        )}
      </div>

      {/* Dialogue de confirmation de suppression */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white/95 backdrop-blur-sm">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Confirmer la suppression
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
              Êtes-vous sûr de vouloir supprimer l&apos;utilisateur &ldquo;{userToDelete?.name}&rdquo; ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={() => {
                setShowDeleteDialog(false);
                setUserToDelete(null);
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

export default Users;
