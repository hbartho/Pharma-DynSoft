import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Building2, KeyRound, Eye, EyeOff, AlertCircle, Mail, Lock, LogIn, Zap, Wifi, MapPin, Pill } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';
import logoImage from '../images/logo.jpg';
import loginBg from '../images/pharmacy-login-bg.jpg';
import { PharmacyFinder } from '../components/PharmacyFinder';

const FEATURES = [
  { icon: Zap, title: 'Recherche rapide', text: 'Trouvez un produit ou une pharmacie en quelques secondes.' },
  { icon: Wifi, title: 'Fonctionne offline', text: 'Accédez aux informations même sans connexion internet.' },
  { icon: MapPin, title: 'Proximité', text: 'Des résultats adaptés à votre ville ou quartier.' },
  { icon: Pill, title: 'Disponibilité', text: 'Vérifiez le stock en temps réel dans les pharmacies.' },
];

const Brand = ({ size = 'lg' }) => (
  <div className="flex items-center gap-4">
    <div className={`${size === 'lg' ? 'w-20 h-20 rounded-3xl' : 'w-16 h-16 rounded-2xl'} bg-white shadow-lg flex items-center justify-center shrink-0 overflow-hidden`}>
      <img src={logoImage} alt="DynSoft Pharma" className={`${size === 'lg' ? 'w-14 h-14' : 'w-11 h-11'} object-contain`} />
    </div>
    <div>
      <h1 className={`${size === 'lg' ? 'text-4xl sm:text-5xl lg:text-6xl text-white' : 'text-4xl sm:text-5xl text-slate-900'} font-extrabold leading-none tracking-tight`} style={{ fontFamily: 'Manrope, sans-serif' }}>
        DynSoft Pharma
      </h1>
      {size === 'lg' && <p className="text-base md:text-lg text-green-50 mt-2">Gestion moderne de pharmacie avec fonctionnement offline</p>}
    </div>
  </div>
);

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
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

  const [loginError, setLoginError] = useState('');

  const friendlyLoginError = (message, status) => {
    if (!status) return 'Connexion au serveur impossible. Vérifiez votre réseau.';
    if (/incorrect email or password/i.test(message || '')) return 'Email ou mot de passe incorrect';
    if (/login failed/i.test(message || '')) return 'Erreur de connexion';
    return message || 'Erreur de connexion';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    setLoading(true);
    setLoginError('');

    const result = await login(formData.email, formData.password);
    
    if (result.success) {
      toast.success('Connexion réussie!');
      navigate(result.user?.role === 'super_admin' ? '/platform' : '/dashboard');
    } else {
      const msg = friendlyLoginError(result.message, result.status);
      setLoginError(msg);
      toast.error(msg);
    }
    
    setLoading(false);
  };

  const handleChange = (e) => {
    setLoginError('');
    setFormData({ ...formData, [e.target.name]: e.target.value });
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
    <div className="min-h-screen flex bg-green-800" style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Panneau gauche : image pharmacie + recherche publique */}
      <div className="hidden lg:flex lg:w-[61%] relative bg-cover bg-center" style={{ backgroundImage: `url(${loginBg})` }}>
        <div className="absolute inset-0 bg-gradient-to-b from-green-800/70 via-green-700/75 to-green-800/90" />
        <div className="relative z-10 flex flex-col justify-between w-full px-10 xl:px-14 py-10 text-white">
          <Brand size="lg" />

          <div className="my-8 w-full max-w-5xl">
            <PharmacyFinder variant="dark" />
          </div>

          <div className="grid grid-cols-4 divide-x divide-white/25" data-testid="login-features">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex flex-col items-center text-center px-4">
                <div className="w-14 h-14 rounded-full bg-green-600 shadow-lg flex items-center justify-center mb-3">
                  <Icon className="w-7 h-7 text-white" strokeWidth={2} />
                </div>
                <p className="font-bold text-base md:text-lg" style={{ fontFamily: 'Manrope, sans-serif' }}>{title}</p>
                <p className="text-sm text-green-50/90 mt-1.5 leading-snug">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Panneau droit : connexion */}
      <div className="flex-1 flex items-start lg:items-center justify-center px-6 sm:px-10 py-10 bg-slate-50 lg:rounded-l-[2.5rem] lg:-ml-10 relative z-20 shadow-2xl">
        <div className="w-full max-w-lg">
          <div className="mb-10">
            <Brand size="sm" />
          </div>

          <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-7 sm:p-9">
            <div className="mb-8">
              <h2 className="text-4xl font-extrabold text-slate-900 mb-2 tracking-tight" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Connexion
              </h2>
              <p className="text-base md:text-lg text-slate-600">Accédez à votre compte DynSoft Pharma</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
              <div>
                <Label htmlFor="email" className="flex items-center gap-2 text-base font-semibold text-slate-800">
                  <Mail className="w-5 h-5 text-green-700" /> Email
                </Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  data-testid="email-input"
                  className="mt-2 h-12 rounded-xl text-base px-4"
                  placeholder="votre@email.com"
                />
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="flex items-center gap-2 text-base font-semibold text-slate-800">
                    <Lock className="w-5 h-5 text-green-700" /> Mot de passe
                  </Label>
                  <button
                    type="button"
                    onClick={() => setShowPasswordDialog(true)}
                    className="text-sm text-green-700 hover:text-green-800 font-semibold flex items-center gap-1.5"
                    data-testid="change-password-link"
                  >
                    <KeyRound className="w-4 h-4" />
                    Changer ?
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
                    className="h-12 rounded-xl text-base px-4 pr-12"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
                    aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {loginError && (
                <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700" data-testid="login-error">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{loginError}</span>
                </div>
              )}

              <Button
                type="submit"
                disabled={loading}
                data-testid="login-submit-button"
                className="w-full h-14 bg-green-700 hover:bg-green-800 text-white rounded-2xl text-lg font-semibold transition-all active:scale-[0.98] flex items-center justify-center gap-3"
              >
                <LogIn className="w-5 h-5" />
                {loading ? 'Connexion...' : 'Se connecter'}
              </Button>
            </form>
          </div>

          {/* Recherche publique sur mobile/tablette (le panneau vert est masqué) */}
          <div className="lg:hidden mt-10" data-testid="pharmacy-finder-mobile">
            <PharmacyFinder variant="light" />
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
