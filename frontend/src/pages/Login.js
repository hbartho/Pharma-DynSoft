import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
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
            PharmaFlow
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
            <p className="text-slate-600">Accédez à votre compte PharmaFlow</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
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
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                data-testid="password-input"
                className="mt-2"
                placeholder="••••••••"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
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

          <div className="mt-8 p-4 bg-teal-50 rounded-lg">
            <p className="text-sm text-teal-800 font-medium mb-2">Compte de démonstration:</p>
            <p className="text-sm text-teal-700">Email: demo@pharmaflow.com</p>
            <p className="text-sm text-teal-700">Mot de passe: demo123</p>
          </div>

          <div className="mt-8 text-center">
            <p className="text-sm text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Made by <span className="font-medium text-teal-700">DynSoftware</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;