import React, { useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Plus, 
  Users as UsersIcon, 
  Edit, 
  Trash2, 
  Search, 
  Shield, 
  ShieldCheck, 
  ShieldAlert, 
  UserCog,
  BadgeCheck,
  Mail,
  Calendar,
  KeyRound,
  Eye,
  EyeOff,
  UserCheck,
  UserX,
  Power,
  Loader2
} from 'lucide-react';
import { useUsers, useCreateUser, useUpdateUser, useDeleteUser, useToggleUserStatus, useResetUserPassword } from '../hooks';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { Navigate } from 'react-router-dom';

const ROLES = [
  { value: 'admin', label: 'Administrateur', icon: ShieldAlert, color: 'text-red-600 bg-red-50', badge: 'ADM' },
  { value: 'pharmacien', label: 'Pharmacien', icon: ShieldCheck, color: 'text-blue-600 bg-blue-50', badge: 'PHA' },
  { value: 'caissier', label: 'Caissier', icon: Shield, color: 'text-green-600 bg-green-50', badge: 'CAI' },
];

const getRoleInfo = (role) => {
  return ROLES.find(r => r.value === role) || ROLES[2];
};

const generateEmployeeCode = (role, existingCodes = []) => {
  const roleInfo = getRoleInfo(role);
  const prefix = roleInfo.badge;
  
  const existingNumbers = existingCodes
    .filter(code => code && code.startsWith(prefix))
    .map(code => {
      const num = parseInt(code.replace(prefix + '-', ''));
      return isNaN(num) ? 0 : num;
    });
  
  const nextNumber = existingNumbers.length > 0 ? Math.max(...existingNumbers) + 1 : 1;
  return `${prefix}-${String(nextNumber).padStart(3, '0')}`;
};

const Users = () => {
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [userToDelete, setUserToDelete] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showResetPasswordDialog, setShowResetPasswordDialog] = useState(false);
  const [userToResetPassword, setUserToResetPassword] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    employee_code: '',
    email: '',
    password: '',
    role: 'caissier',
    tenant_id: '',
  });

  // React Query hooks
  const { data: users = [], isLoading, isError } = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const deleteUser = useDeleteUser();
  const toggleStatus = useToggleUserStatus();
  const resetPassword = useResetUserPassword();

  // Redirect if not admin
  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  const handleRoleChange = (role) => {
    const existingCodes = users.map(u => u.employee_code);
    const newCode = generateEmployeeCode(role, existingCodes);
    setFormData({ 
      ...formData, 
      role,
      employee_code: editingUser ? formData.employee_code : newCode 
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (editingUser) {
      const updateData = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        employee_code: formData.employee_code,
        role: formData.role,
      };
      updateUser.mutate(
        { userId: editingUser.id, data: updateData },
        {
          onSuccess: () => {
            setShowDialog(false);
            resetForm();
          },
        }
      );
    } else {
      const createData = {
        first_name: formData.first_name,
        last_name: formData.last_name,
        employee_code: formData.employee_code,
        email: formData.email,
        password: formData.password,
        role: formData.role,
        tenant_id: user.tenant_id,
      };
      createUser.mutate(createData, {
        onSuccess: () => {
          setShowDialog(false);
          resetForm();
        },
      });
    }
  };

  const handleEdit = (userToEdit) => {
    setEditingUser(userToEdit);
    setFormData({
      first_name: userToEdit.first_name || '',
      last_name: userToEdit.last_name || '',
      employee_code: userToEdit.employee_code || '',
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

  const handleDeleteConfirm = () => {
    if (!userToDelete) return;
    
    deleteUser.mutate(userToDelete.id, {
      onSuccess: () => {
        setShowDeleteDialog(false);
        setUserToDelete(null);
      },
    });
  };

  const handleResetPassword = (userToReset) => {
    setUserToResetPassword(userToReset);
    setNewPassword('');
    setShowResetPasswordDialog(true);
  };

  const handleResetPasswordConfirm = () => {
    if (!userToResetPassword || !newPassword) return;
    
    if (newPassword.length < 6) {
      toast.error('Le mot de passe doit contenir au moins 6 caractères');
      return;
    }
    
    resetPassword.mutate(
      { userId: userToResetPassword.id, newPassword },
      {
        onSuccess: () => {
          setShowResetPasswordDialog(false);
          setUserToResetPassword(null);
          setNewPassword('');
        },
      }
    );
  };

  const handleToggleStatus = (userToToggle) => {
    if (userToToggle.id === user.id) {
      toast.error('Vous ne pouvez pas désactiver votre propre compte');
      return;
    }
    toggleStatus.mutate(userToToggle.id);
  };

  const resetForm = () => {
    setEditingUser(null);
    setFormData({
      first_name: '',
      last_name: '',
      employee_code: '',
      email: '',
      password: '',
      role: 'caissier',
      tenant_id: '',
    });
    setShowPassword(false);
  };

  const openNewUserDialog = () => {
    resetForm();
    const existingCodes = users.map(u => u.employee_code);
    const newCode = generateEmployeeCode('caissier', existingCodes);
    setFormData(prev => ({ ...prev, employee_code: newCode }));
    setShowDialog(true);
  };

  const filteredUsers = users.filter((u) => {
    const fullName = `${u.first_name || ''} ${u.last_name || ''}`.toLowerCase();
    const query = searchQuery.toLowerCase();
    return fullName.includes(query) ||
      u.email?.toLowerCase().includes(query) ||
      u.employee_code?.toLowerCase().includes(query) ||
      u.role?.toLowerCase().includes(query);
  });

  const sortedUsers = [...filteredUsers].sort((a, b) => {
    const roleOrder = { admin: 0, pharmacien: 1, caissier: 2 };
    if (roleOrder[a.role] !== roleOrder[b.role]) {
      return roleOrder[a.role] - roleOrder[b.role];
    }
    return `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
  });

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric' 
    });
  };

  const isSubmitting = createUser.isPending || updateUser.isPending;

  if (isError) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <p className="text-red-500">Erreur lors du chargement des utilisateurs</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="users-page">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-1 sm:mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Gestion des utilisateurs
            </h1>
            <p className="text-sm sm:text-base text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gérer les comptes • {users.length} utilisateur{users.length > 1 ? 's' : ''}
            </p>
          </div>
          <Button 
            onClick={openNewUserDialog}
            data-testid="add-user-button" 
            size="sm"
            className="bg-teal-700 hover:bg-teal-800 rounded-full w-full sm:w-auto"
          >
            <Plus className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
            <span className="hidden sm:inline">Ajouter un utilisateur</span>
            <span className="sm:hidden">Ajouter</span>
          </Button>
        </div>

        {/* Role Legend - responsive */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-4 p-3 sm:p-4 bg-white rounded-xl border border-slate-100">
          <span className="text-xs sm:text-sm font-medium text-slate-600 w-full sm:w-auto mb-1 sm:mb-0">Rôles:</span>
          {ROLES.map((role) => {
            const Icon = role.icon;
            const count = users.filter(u => u.role === role.value).length;
            return (
              <div key={role.value} className={`flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 rounded-full ${role.color}`}>
                <Icon className="w-3 h-3 sm:w-4 sm:h-4" strokeWidth={1.5} />
                <span className="text-xs sm:text-sm font-medium">{role.label}</span>
                <span className="text-xs opacity-75">({count})</span>
              </div>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
          <Input
            placeholder="Rechercher par nom, email, code employé ou rôle..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="user-search-input"
            className="pl-10"
          />
        </div>

        {/* Users Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {sortedUsers.map((u) => {
              const roleInfo = getRoleInfo(u.role);
              const Icon = roleInfo.icon;
              const isCurrentUser = u.id === user?.id;
              const fullName = `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'Sans nom';
              const isActive = u.is_active !== false;
              
              return (
                <div
                  key={u.id}
                  data-testid={`user-card-${u.id}`}
                  className={`p-5 rounded-xl bg-white border ${isCurrentUser ? 'border-teal-300 ring-2 ring-teal-100' : 'border-slate-100'} ${!isActive ? 'opacity-60 bg-slate-50' : ''} hover:border-teal-200 hover:shadow-sm transition-all`}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start gap-3">
                      <div className={`p-2.5 rounded-xl ${roleInfo.color}`}>
                        <Icon className="w-5 h-5" strokeWidth={1.5} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-lg text-slate-900 truncate" style={{ fontFamily: 'Manrope, sans-serif' }}>
                          {fullName}
                          {isCurrentUser && (
                            <span className="ml-2 text-xs font-normal text-teal-600 bg-teal-50 px-2 py-0.5 rounded-full">(Vous)</span>
                          )}
                        </h3>
                        <div className="flex items-center gap-1.5 mt-1">
                          <BadgeCheck className="w-3.5 h-3.5 text-slate-400" strokeWidth={1.5} />
                          <span className="text-sm font-mono text-slate-600">{u.employee_code || 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                    <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                      {isActive ? <UserCheck className="w-3.5 h-3.5" /> : <UserX className="w-3.5 h-3.5" />}
                      {isActive ? 'Actif' : 'Inactif'}
                    </div>
                  </div>
                  
                  {/* Info */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center gap-2 text-sm text-slate-600">
                      <Mail className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                      <span className="truncate">{u.email}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <Calendar className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                      <span>Créé le {formatDate(u.created_at)}</span>
                    </div>
                  </div>
                  
                  {/* Role Badge */}
                  <div className="mb-4">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${roleInfo.color}`}>
                      <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
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
                      onClick={() => handleToggleStatus(u)}
                      disabled={isCurrentUser || toggleStatus.isPending}
                      data-testid={`toggle-status-${u.id}`}
                      title={isActive ? 'Désactiver l\'utilisateur' : 'Activer l\'utilisateur'}
                      className={`${isCurrentUser ? 'opacity-50 cursor-not-allowed' : isActive ? 'text-amber-600 hover:text-amber-700 hover:bg-amber-50' : 'text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50'}`}
                    >
                      <Power className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleResetPassword(u)}
                      data-testid={`reset-password-${u.id}`}
                      className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                    >
                      <KeyRound className="w-4 h-4" strokeWidth={1.5} />
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

        {!isLoading && sortedUsers.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <UsersIcon className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              {searchQuery ? 'Aucun utilisateur trouvé' : 'Aucun utilisateur enregistré'}
            </p>
          </div>
        )}
      </div>

      {/* Dialog Créer/Modifier utilisateur */}
      <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <UserCog className="w-5 h-5 text-teal-600" />
              {editingUser ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="user-form">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="first_name">Prénom *</Label>
                <Input
                  id="first_name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                  data-testid="user-firstname-input"
                  placeholder="Jean"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="last_name">Nom *</Label>
                <Input
                  id="last_name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                  data-testid="user-lastname-input"
                  placeholder="Dupont"
                  className="mt-1"
                />
              </div>
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
                className="mt-1"
              />
              {editingUser && (
                <p className="text-xs text-slate-500 mt-1">L'email ne peut pas être modifié</p>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="role">Rôle *</Label>
                <Select 
                  value={formData.role} 
                  onValueChange={handleRoleChange}
                >
                  <SelectTrigger data-testid="user-role-select" className="mt-1">
                    <SelectValue placeholder="Sélectionner un rôle" />
                  </SelectTrigger>
                  <SelectContent>
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
              <div>
                <Label htmlFor="employee_code">Code employé *</Label>
                <Input
                  id="employee_code"
                  value={formData.employee_code}
                  onChange={(e) => setFormData({ ...formData, employee_code: e.target.value.toUpperCase() })}
                  required
                  data-testid="user-employeecode-input"
                  placeholder="ADM-001"
                  className="mt-1 font-mono"
                />
              </div>
            </div>
            
            {!editingUser && (
              <div>
                <Label htmlFor="password">Mot de passe *</Label>
                <div className="relative mt-1">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required={!editingUser}
                    data-testid="user-password-input"
                    placeholder="••••••••"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-slate-500 mt-1">Minimum 6 caractères</p>
              </div>
            )}
            
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                Annuler
              </Button>
              <Button 
                type="submit" 
                data-testid="user-submit-button" 
                className="bg-teal-700 hover:bg-teal-800"
                disabled={isSubmitting}
              >
                {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {editingUser ? 'Mettre à jour' : 'Créer'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialogue de confirmation de suppression */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Confirmer la suppression
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
              Êtes-vous sûr de vouloir supprimer l'utilisateur <strong>{userToDelete?.first_name} {userToDelete?.last_name}</strong> ({userToDelete?.employee_code}) ?
              <br />
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={() => {
                setShowDeleteDialog(false);
                setUserToDelete(null);
              }}
            >
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
              disabled={deleteUser.isPending}
            >
              {deleteUser.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialogue de réinitialisation de mot de passe */}
      <Dialog open={showResetPasswordDialog} onOpenChange={(open) => { 
        setShowResetPasswordDialog(open); 
        if (!open) {
          setUserToResetPassword(null);
          setNewPassword('');
        }
      }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <KeyRound className="w-5 h-5 text-amber-600" />
              Réinitialiser le mot de passe
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Définir un nouveau mot de passe pour <strong>{userToResetPassword?.first_name} {userToResetPassword?.last_name}</strong>
            </p>
            <div>
              <Label htmlFor="new-password">Nouveau mot de passe *</Label>
              <div className="relative mt-1">
                <Input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">Minimum 6 caractères</p>
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => { 
                  setShowResetPasswordDialog(false);
                  setUserToResetPassword(null);
                  setNewPassword('');
                }}
              >
                Annuler
              </Button>
              <Button 
                onClick={handleResetPasswordConfirm}
                disabled={!newPassword || newPassword.length < 6 || resetPassword.isPending}
                className="bg-amber-600 hover:bg-amber-700"
              >
                {resetPassword.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Réinitialiser
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Users;
