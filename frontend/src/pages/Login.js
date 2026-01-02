import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Building2, KeyRound, Eye, EyeOff, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [agencies, setAgencies] = useState([]);
  const [selectedAgency, setSelectedAgency] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  
  // État pour le dialogue de changement de mot de passe
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [passwordChangeData, setPasswordChangeData] = useState({
    email: '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [changingPassword, setChangingPassword] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Charger les agences depuis les paramètres
  useEffect(() => {
    const loadAgencies = async () => {
      try {
        const response = await api.get('/settings/agencies');
        const agenciesList = response.data || [];
        setAgencies(agenciesList);
        
        // Sélectionner la première agence par défaut
        if (agenciesList.length > 0) {
          setSelectedAgency(agenciesList[0]);
        }
      } catch (error) {
        console.error('Error loading agencies:', error);
        // Agence par défaut en cas d'erreur
        const defaultAgency = {
          tenant_id: 'default',
          pharmacy_name: 'DynSoft Pharma',
          currency: 'GNF'
        };
        setAgencies([defaultAgency]);
        setSelectedAgency(defaultAgency);
      }
    };
    loadAgencies();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!selectedAgency) {
      toast.error('Veuillez sélectionner une agence');
      return;
    }
    
    setLoading(true);

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      toast.success('Connexion réussie!');
      navigate('/dashboard');
    } else {
      toast.error(result.message || 'Erreur de connexion');
    }
    
    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleAgencyChange = (tenantId) => {
    const agency = agencies.find(a => a.tenant_id === tenantId);
    if (agency) {
      setSelectedAgency(agency);
    }
  };

  const handlePasswordChangeSubmit = async (e) => {
    e.preventDefault();
    
    // Validations
    if (passwordChangeData.newPassword !== passwordChangeData.confirmPassword) {
      toast.error('Les nouveaux mots de passe ne correspondent pas');
      return;
    }
    
    if (passwordChangeData.newPassword.length < 6) {
      toast.error('Le nouveau mot de passe doit contenir au moins 6 caractères');
      return;
    }
    
    setChangingPassword(true);
    
    try {
      // D'abord, se connecter pour vérifier les identifiants actuels
      const loginResult = await login(passwordChangeData.email, passwordChangeData.currentPassword);
      
      if (!loginResult.success) {
        toast.error('Email ou mot de passe actuel incorrect');
        setChangingPassword(false);
        return;
      }
      
      // Ensuite, changer le mot de passe
      await api.put('/auth/change-password', {
        current_password: passwordChangeData.currentPassword,
        new_password: passwordChangeData.newPassword,
      });
      
      toast.success('Mot de passe mis à jour avec succès');
      setShowPasswordDialog(false);
      setPasswordChangeData({
        email: '',
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
      
      // Pré-remplir le formulaire de connexion avec le nouvel email
      setFormData({
        email: passwordChangeData.email,
        password: '',
      });
      
    } catch (error) {
      console.error('Error changing password:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors du changement de mot de passe');
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="min-h-screen flex" style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Left side - Image */}
      <div
        className="hidden lg:flex lg:w-1/2 bg-cover bg-center relative"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1582146804102-b4a01b0a51ae?crop=entropy&cs=srgb&fm=jpg&q=85')`,
        }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-teal-900/90 to-emerald-900/90"></div>
        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          <h1 className="text-5xl font-bold mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
            DynSoft Pharma
          </h1>
          <p className="text-xl text-teal-50">
            Gestion moderne de pharmacie avec fonctionnement offline
          </p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="flex-1 flex items-center justify-center px-8 bg-white">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Connexion
            </h2>
            <p className="text-slate-600">Accédez à votre compte DynSoft Pharma</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
            {/* Agence / Nom de la pharmacie - Dropdown */}
            <div>
              <Label htmlFor="agency-select" className="text-sm font-medium text-slate-700 mb-2 block">
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-teal-600" />
                  Agence
                </div>
              </Label>
              <Select
                value={selectedAgency?.tenant_id || ''}
                onValueChange={handleAgencyChange}
              >
                <SelectTrigger 
                  id="agency-select"
                  className="w-full h-12 bg-gradient-to-r from-teal-50 to-emerald-50 border-teal-200 hover:border-teal-300 focus:ring-teal-500"
                >
                  <SelectValue placeholder="Sélectionnez une agence">
                    {selectedAgency && (
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-teal-700" />
                        <span className="font-medium text-teal-900">
                          {selectedAgency.pharmacy_name}
                        </span>
                      </div>
                    )}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {agencies.map((agency) => (
                    <SelectItem 
                      key={agency.tenant_id} 
                      value={agency.tenant_id}
                      className="py-3"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-1.5 bg-teal-100 rounded-lg">
                          <Building2 className="w-4 h-4 text-teal-700" />
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900">{agency.pharmacy_name}</p>
                          <p className="text-xs text-slate-500">Devise: {agency.currency}</p>
                        </div>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                data-testid="email-input"
                className="mt-2"
                placeholder="votre@email.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Mot de passe</Label>
                <button
                  type="button"
                  onClick={() => setShowPasswordDialog(true)}
                  className="text-sm text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1"
                >
                  <KeyRound className="w-3 h-3" />
                  Changer
                </button>
              </div>
              <div className="relative mt-2">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleChange}
                  required
                  data-testid="password-input"
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
            </div>

            <Button
              type="submit"
              disabled={loading || !selectedAgency}
              data-testid="login-submit-button"
              className="w-full bg-teal-700 hover:bg-teal-800 text-white rounded-full py-6 text-lg font-medium transition-all active:scale-95"
            >
              {loading ? 'Connexion...' : 'Se connecter'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-slate-600">
              Pas de compte?{' '}
              <Link to="/register" className="text-teal-700 hover:text-teal-800 font-medium" data-testid="register-link">
                Créer un compte
              </Link>
            </p>
          </div>

          <div className="mt-8 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <p className="text-sm font-semibold text-slate-800 mb-3">🔐 Comptes de démonstration:</p>
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setFormData({ email: 'admin@pharmaflow.com', password: 'admin123' })}
                className="w-full text-left p-2 rounded-lg hover:bg-teal-50 transition-colors border border-transparent hover:border-teal-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">ADM-001</span>
                    <p className="text-sm text-slate-700 mt-1">admin@pharmaflow.com</p>
                  </div>
                  <span className="text-xs text-slate-400">admin123</span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ email: 'pharmacien@pharmaflow.com', password: 'pharma123' })}
                className="w-full text-left p-2 rounded-lg hover:bg-teal-50 transition-colors border border-transparent hover:border-teal-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-medium text-teal-600 bg-teal-50 px-2 py-0.5 rounded-full">PHA-001</span>
                    <p className="text-sm text-slate-700 mt-1">pharmacien@pharmaflow.com</p>
                  </div>
                  <span className="text-xs text-slate-400">pharma123</span>
                </div>
              </button>
              <button
                type="button"
                onClick={() => setFormData({ email: 'caissier@pharmaflow.com', password: 'caisse123' })}
                className="w-full text-left p-2 rounded-lg hover:bg-teal-50 transition-colors border border-transparent hover:border-teal-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">CAI-001</span>
                    <p className="text-sm text-slate-700 mt-1">caissier@pharmaflow.com</p>
                  </div>
                  <span className="text-xs text-slate-400">caisse123</span>
                </div>
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-3 text-center">Cliquez pour remplir automatiquement</p>
          </div>

          <div className="mt-8 text-center">
            <p className="text-sm text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Made by <span className="font-medium text-teal-700">DynSoftware</span>
            </p>
          </div>
        </div>
      </div>

      {/* Dialog de changement de mot de passe */}
      <Dialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <KeyRound className="w-5 h-5 text-teal-600" />
              Changer le mot de passe
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handlePasswordChangeSubmit} className="space-y-4">
            <div>
              <Label htmlFor="change-email">Email</Label>
              <Input
                id="change-email"
                type="email"
                value={passwordChangeData.email}
                onChange={(e) => setPasswordChangeData({...passwordChangeData, email: e.target.value})}
                required
                className="mt-1"
                placeholder="votre@email.com"
              />
            </div>
            
            <div>
              <Label htmlFor="current-password">Mot de passe actuel</Label>
              <div className="relative mt-1">
                <Input
                  id="current-password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={passwordChangeData.currentPassword}
                  onChange={(e) => setPasswordChangeData({...passwordChangeData, currentPassword: e.target.value})}
                  required
                  placeholder="••••••••"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            
            <div>
              <Label htmlFor="new-password">Nouveau mot de passe</Label>
              <div className="relative mt-1">
                <Input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={passwordChangeData.newPassword}
                  onChange={(e) => setPasswordChangeData({...passwordChangeData, newPassword: e.target.value})}
                  required
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
            
            <div>
              <Label htmlFor="confirm-password">Confirmer le nouveau mot de passe</Label>
              <Input
                id="confirm-password"
                type="password"
                value={passwordChangeData.confirmPassword}
                onChange={(e) => setPasswordChangeData({...passwordChangeData, confirmPassword: e.target.value})}
                required
                className="mt-1"
                placeholder="••••••••"
              />
              {passwordChangeData.newPassword && passwordChangeData.confirmPassword && 
                passwordChangeData.newPassword !== passwordChangeData.confirmPassword && (
                <p className="text-xs text-red-500 mt-1">Les mots de passe ne correspondent pas</p>
              )}
            </div>
            
            <DialogFooter className="mt-6">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setShowPasswordDialog(false)}
              >
                Annuler
              </Button>
              <Button 
                type="submit" 
                disabled={changingPassword || !passwordChangeData.email || !passwordChangeData.currentPassword || !passwordChangeData.newPassword || !passwordChangeData.confirmPassword}
                className="bg-teal-700 hover:bg-teal-800"
              >
                {changingPassword ? 'Modification...' : 'Modifier'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Login;
