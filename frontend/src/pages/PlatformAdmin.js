import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Checkbox } from '../components/ui/checkbox';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Building2, Plus, Users, LogOut, Trash2, ShieldCheck, KeyRound, Loader2, Store, TrendingUp,
} from 'lucide-react';

const fmtGNF = (n) => `${Math.round(n || 0).toLocaleString('fr-FR')} GNF`;

const emptyForm = {
  name: '', slug: '', address: '', phone: '', email: '',
  admin_first_name: '', admin_last_name: '', admin_email: '', admin_password: '',
  import_products: false, source_slug: 'pharmacie_centrale',
};

export default function PlatformAdmin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [pharmacies, setPharmacies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const [resetTarget, setResetTarget] = useState(null);
  const [resetForm, setResetForm] = useState({ email: '', new_password: '' });
  const [showOwnPassword, setShowOwnPassword] = useState(false);
  const [ownPwForm, setOwnPwForm] = useState({ current_password: '', new_password: '' });
  const [stats, setStats] = useState(null);

  const loadStats = useCallback(async () => {
    try {
      const res = await api.get('/platform/pharmacies/stats');
      setStats(res.data.stats || {});
    } catch (e) {
      // stats non bloquantes
    }
  }, []);

  const loadPharmacies = useCallback(async () => {
    try {
      const res = await api.get('/platform/pharmacies');
      setPharmacies(res.data || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPharmacies(); loadStats(); }, [loadPharmacies, loadStats]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form };
      if (!payload.slug) delete payload.slug;
      const res = await api.post('/platform/pharmacies', payload);
      toast.success(res.data.message);
      setShowCreate(false);
      setForm(emptyForm);
      loadPharmacies();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors de la création');
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (pharmacy) => {
    try {
      await api.put(`/platform/pharmacies/${pharmacy.slug}`, { is_active: !pharmacy.is_active });
      toast.success(pharmacy.is_active ? 'Pharmacie désactivée' : 'Pharmacie activée');
      loadPharmacies();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/platform/pharmacies/${deleteTarget.slug}`, { params: { confirm: deleteConfirm } });
      toast.success('Pharmacie supprimée définitivement');
      setDeleteTarget(null);
      setDeleteConfirm('');
      loadPharmacies();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur de suppression');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/platform/pharmacies/${resetTarget.slug}/reset-admin-password`, resetForm);
      toast.success('Mot de passe réinitialisé');
      setResetTarget(null);
      setResetForm({ email: '', new_password: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const handleChangeOwnPassword = async (e) => {
    e.preventDefault();
    try {
      await api.post('/platform/change-password', ownPwForm);
      toast.success('Mot de passe modifié avec succès');
      setShowOwnPassword(false);
      setOwnPwForm({ current_password: '', new_password: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  return (
    <div className="min-h-screen bg-slate-50" data-testid="platform-admin-page">
      {/* Header */}
      <header className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-teal-600 rounded-lg">
              <ShieldCheck className="w-5 h-5" strokeWidth={1.5} />
            </div>
            <div>
              <h1 className="text-lg font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>
                DynSoft — Administration Plateforme
              </h1>
              <p className="text-xs text-slate-400">Gestion des pharmacies · {user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-slate-800" onClick={() => setShowOwnPassword(true)} data-testid="change-own-password-button">
              <KeyRound className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Mot de passe
            </Button>
            <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-slate-800" onClick={handleLogout} data-testid="platform-logout-button">
              <LogOut className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Déconnexion
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-3">
              <Store className="w-5 h-5 text-teal-600" strokeWidth={1.5} />
              <div>
                <p className="text-2xl font-bold text-slate-900" data-testid="total-pharmacies-count">{pharmacies.length}</p>
                <p className="text-sm text-slate-500">Pharmacies</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-3">
              <Building2 className="w-5 h-5 text-emerald-600" strokeWidth={1.5} />
              <div>
                <p className="text-2xl font-bold text-slate-900">{pharmacies.filter(p => p.is_active).length}</p>
                <p className="text-sm text-slate-500">Actives</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-3">
              <Users className="w-5 h-5 text-blue-600" strokeWidth={1.5} />
              <div>
                <p className="text-2xl font-bold text-slate-900">{pharmacies.reduce((s, p) => s + (p.users_count || 0), 0)}</p>
                <p className="text-sm text-slate-500">Comptes utilisateurs</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-amber-600" strokeWidth={1.5} />
              <div className="min-w-0">
                <p className="text-xl font-bold text-slate-900 truncate" data-testid="total-ca-month">
                  {stats ? fmtGNF(Object.values(stats).reduce((s, v) => s + (v.ca_month || 0), 0)) : '—'}
                </p>
                <p className="text-sm text-slate-500">CA du mois (toutes)</p>
              </div>
            </div>
          </div>
        </div>

        {/* Liste */}
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Pharmacies
            </h2>
            <Button className="bg-teal-600 hover:bg-teal-700" onClick={() => setShowCreate(true)} data-testid="create-pharmacy-button">
              <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
              Nouvelle pharmacie
            </Button>
          </div>

          {loading ? (
            <div className="p-10 text-center text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              Chargement...
            </div>
          ) : pharmacies.length === 0 ? (
            <div className="p-10 text-center text-slate-500" data-testid="no-pharmacies-message">
              Aucune pharmacie. Créez la première !
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {pharmacies.map((p) => (
                <div key={p.id} className="p-5 flex flex-col sm:flex-row sm:items-center gap-4" data-testid={`pharmacy-row-${p.slug}`}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-slate-900">{p.name}</p>
                      <Badge variant="outline" className="text-xs font-mono">{p.slug}</Badge>
                      {p.is_active ? (
                        <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Active</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Désactivée</Badge>
                      )}
                    </div>
                    <p className="text-sm text-slate-500 mt-1">
                      {[p.address, p.phone, p.email].filter(Boolean).join(' · ') || '—'}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {p.users_count || 0} compte(s) · créée le {p.created_at ? new Date(p.created_at).toLocaleDateString('fr-FR') : '—'}
                    </p>
                    {stats?.[p.slug] && !stats[p.slug].error && (
                      <div className="flex flex-wrap gap-x-5 gap-y-1 mt-2 text-xs" data-testid={`pharmacy-stats-${p.slug}`}>
                        <span className="text-slate-600">
                          Aujourd'hui : <strong className="text-slate-900">{fmtGNF(stats[p.slug].ca_today)}</strong>
                          <span className="text-slate-400"> ({stats[p.slug].sales_today} vente{stats[p.slug].sales_today > 1 ? 's' : ''})</span>
                        </span>
                        <span className="text-slate-600">
                          Ce mois : <strong className="text-teal-700">{fmtGNF(stats[p.slug].ca_month)}</strong>
                          <span className="text-slate-400"> ({stats[p.slug].sales_month})</span>
                        </span>
                        <span className="text-slate-600">
                          Total : <strong className="text-slate-900">{fmtGNF(stats[p.slug].ca_total)}</strong>
                          <span className="text-slate-400"> ({stats[p.slug].sales_total})</span>
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Switch checked={p.is_active} onCheckedChange={() => toggleActive(p)} data-testid={`toggle-active-${p.slug}`} />
                      <span className="text-xs text-slate-500">Active</span>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => { setResetTarget(p); setResetForm({ email: '', new_password: '' }); }} data-testid={`reset-password-${p.slug}`}>
                      <KeyRound className="w-4 h-4" strokeWidth={1.5} />
                    </Button>
                    {p.slug !== 'pharmacie_centrale' && (
                      <Button variant="outline" size="sm" className="text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => { setDeleteTarget(p); setDeleteConfirm(''); }} data-testid={`delete-pharmacy-${p.slug}`}>
                        <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Dialog création */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nouvelle pharmacie</DialogTitle>
            <DialogDescription>
              Un espace de données isolé sera créé, avec son compte administrateur.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <Label htmlFor="ph-name">Nom de la pharmacie *</Label>
              <Input id="ph-name" value={form.name} onChange={set('name')} required data-testid="pharmacy-name-input" placeholder="Pharmacie du Marché" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="ph-phone">Téléphone</Label>
                <Input id="ph-phone" value={form.phone} onChange={set('phone')} placeholder="+224..." />
              </div>
              <div>
                <Label htmlFor="ph-email">Email pharmacie</Label>
                <Input id="ph-email" type="email" value={form.email} onChange={set('email')} />
              </div>
            </div>
            <div>
              <Label htmlFor="ph-address">Adresse</Label>
              <Input id="ph-address" value={form.address} onChange={set('address')} placeholder="Conakry, ..." />
            </div>
            <div className="pt-2 border-t border-slate-100">
              <p className="text-sm font-medium text-slate-700 mb-3">Compte administrateur de la pharmacie</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="ad-fn">Prénom *</Label>
                  <Input id="ad-fn" value={form.admin_first_name} onChange={set('admin_first_name')} required data-testid="admin-firstname-input" />
                </div>
                <div>
                  <Label htmlFor="ad-ln">Nom *</Label>
                  <Input id="ad-ln" value={form.admin_last_name} onChange={set('admin_last_name')} required data-testid="admin-lastname-input" />
                </div>
              </div>
              <div className="mt-3">
                <Label htmlFor="ad-email">Email admin *</Label>
                <Input id="ad-email" type="email" value={form.admin_email} onChange={set('admin_email')} required data-testid="admin-email-input" />
              </div>
              <div className="mt-3">
                <Label htmlFor="ad-pw">Mot de passe admin * (min. 6 caractères)</Label>
                <Input id="ad-pw" type="password" value={form.admin_password} onChange={set('admin_password')} required minLength={6} data-testid="admin-password-input" />
              </div>
            </div>
            <div className="pt-2 border-t border-slate-100">
              <p className="text-sm font-medium text-slate-700 mb-2">Données initiales</p>
              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-lg border border-slate-200 hover:border-teal-300 transition-colors">
                <Checkbox
                  checked={form.import_products}
                  onCheckedChange={(v) => setForm({ ...form, import_products: !!v })}
                  data-testid="import-products-checkbox"
                  className="mt-0.5"
                />
                <span className="text-sm">
                  <span className="font-medium text-slate-800">Importer le catalogue produits</span>
                  <span className="block text-xs text-slate-500 mt-0.5">
                    Copie les fiches produits, catégories et unités (avec les prix) — <strong>stock à zéro</strong> — ainsi que les règles de rabais et codes promo, <strong>importés désactivés</strong>. Ventes, stocks et autres données démarrent vides.
                  </span>
                </span>
              </label>
              {form.import_products && (
                <div className="mt-3">
                  <Label htmlFor="source-slug">Pharmacie source du catalogue</Label>
                  <select
                    id="source-slug"
                    value={form.source_slug}
                    onChange={(e) => setForm({ ...form, source_slug: e.target.value })}
                    data-testid="source-pharmacy-select"
                    className="mt-1 w-full h-10 px-3 rounded-md border border-slate-200 bg-white text-sm"
                  >
                    {pharmacies.map((p) => (
                      <option key={p.slug} value={p.slug}>{p.name} ({p.slug})</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Annuler</Button>
              <Button type="submit" className="bg-teal-600 hover:bg-teal-700" disabled={saving} data-testid="submit-create-pharmacy">
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                Créer la pharmacie
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog suppression */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600">Supprimer définitivement ?</DialogTitle>
            <DialogDescription>
              Toutes les données de « {deleteTarget?.name} » (ventes, stock, comptes...) seront détruites.
              Retapez le slug <strong className="font-mono">{deleteTarget?.slug}</strong> pour confirmer.
            </DialogDescription>
          </DialogHeader>
          <Input value={deleteConfirm} onChange={(e) => setDeleteConfirm(e.target.value)} placeholder={deleteTarget?.slug} data-testid="delete-confirm-input" />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Annuler</Button>
            <Button variant="destructive" disabled={deleteConfirm !== deleteTarget?.slug} onClick={handleDelete} data-testid="confirm-delete-pharmacy">
              <Trash2 className="w-4 h-4 mr-2" />
              Supprimer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog changement de mot de passe super admin */}
      <Dialog open={showOwnPassword} onOpenChange={(o) => !o && setShowOwnPassword(false)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Changer mon mot de passe</DialogTitle>
            <DialogDescription>Stocké haché (bcrypt) en base de données.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleChangeOwnPassword} className="space-y-4">
            <div>
              <Label htmlFor="own-current">Mot de passe actuel</Label>
              <Input id="own-current" type="password" value={ownPwForm.current_password} onChange={(e) => setOwnPwForm({ ...ownPwForm, current_password: e.target.value })} required data-testid="own-current-password-input" />
            </div>
            <div>
              <Label htmlFor="own-new">Nouveau mot de passe (min. 8 caractères)</Label>
              <Input id="own-new" type="password" value={ownPwForm.new_password} onChange={(e) => setOwnPwForm({ ...ownPwForm, new_password: e.target.value })} required minLength={8} data-testid="own-new-password-input" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowOwnPassword(false)}>Annuler</Button>
              <Button type="submit" className="bg-teal-600 hover:bg-teal-700" data-testid="submit-own-password">Modifier</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog reset password */}
      <Dialog open={!!resetTarget} onOpenChange={(o) => !o && setResetTarget(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Réinitialiser un mot de passe</DialogTitle>
            <DialogDescription>Pharmacie : {resetTarget?.name}</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div>
              <Label htmlFor="rs-email">Email de l'utilisateur</Label>
              <Input id="rs-email" type="email" value={resetForm.email} onChange={(e) => setResetForm({ ...resetForm, email: e.target.value })} required data-testid="reset-email-input" />
            </div>
            <div>
              <Label htmlFor="rs-pw">Nouveau mot de passe (min. 6)</Label>
              <Input id="rs-pw" type="password" value={resetForm.new_password} onChange={(e) => setResetForm({ ...resetForm, new_password: e.target.value })} required minLength={6} data-testid="reset-password-input" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setResetTarget(null)}>Annuler</Button>
              <Button type="submit" className="bg-teal-600 hover:bg-teal-700" data-testid="submit-reset-password">Réinitialiser</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
