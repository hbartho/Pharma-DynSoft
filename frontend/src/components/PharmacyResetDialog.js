import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Loader2, RotateCcw, Trash2, DatabaseBackup, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';

const fmtSize = (b) => (b >= 1048576 ? `${(b / 1048576).toFixed(1)} Mo` : `${Math.max(1, Math.round(b / 1024))} Ko`);

export const PharmacyResetDialog = ({ pharmacy, onClose, onDone }) => {
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [backups, setBackups] = useState([]);
  const [result, setResult] = useState(null);

  const loadBackups = async (slug) => {
    try {
      const res = await api.get(`/platform/pharmacies/${slug}/backups`);
      setBackups(res.data || []);
    } catch { setBackups([]); }
  };

  useEffect(() => {
    if (pharmacy) { setConfirm(''); setResult(null); loadBackups(pharmacy.slug); }
  }, [pharmacy]);

  const runReset = async () => {
    setBusy(true);
    try {
      const res = await api.post(`/platform/pharmacies/${pharmacy.slug}/reset-data`, null, { params: { confirm } });
      setResult(res.data);
      toast.success(res.data.message, { description: `${res.data.deleted_total} enregistrement(s) archivés dans ${res.data.backup_schema}` });
      await loadBackups(pharmacy.slug);
      onDone?.();
    } catch (e) {
      toast.error('Réinitialisation refusée', { description: e.response?.data?.detail || e.message, duration: 8000 });
    } finally { setBusy(false); }
  };

  const dropBackup = async (name) => {
    try {
      await api.delete(`/platform/pharmacies/${pharmacy.slug}/backups/${name}`);
      toast.success('Sauvegarde supprimée');
      await loadBackups(pharmacy.slug);
    } catch (e) {
      toast.error('Suppression impossible', { description: e.response?.data?.detail || e.message });
    }
  };

  return (
    <Dialog open={!!pharmacy} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg" data-testid="pharmacy-reset-dialog">
        <DialogHeader>
          <DialogTitle className="text-amber-700 flex items-center gap-2"><RotateCcw className="w-5 h-5" /> Réinitialiser les données de « {pharmacy?.name} »</DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-2 text-sm">
              <p className="flex gap-2 text-amber-900 bg-amber-50 border border-amber-200 rounded-md p-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>Supprime ventes, approvisionnements, lots, mouvements, dettes clients et fournisseurs, retours, inventaires, shifts, plannings et historiques. Le stock de tous les produits repasse à 0.</span>
              </p>
              <p><strong>Conservés :</strong> utilisateurs, produits (et prix), catégories, unités, fournisseurs, clients, paramètres et règles, codes promo.</p>
              <p>Une sauvegarde automatique des données effacées est conservée en base et peut être supprimée ci-dessous.</p>
            </div>
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" data-testid="pharmacy-reset-result">
            <p className="font-semibold">{result.message}</p>
            <p>{result.deleted_total} enregistrement(s) supprimé(s), {result.products_reset} produit(s) remis à stock 0.</p>
            <p className="font-mono text-xs mt-1">Sauvegarde : {result.backup_schema}</p>
          </div>
        ) : (
          <div>
            <p className="text-sm text-slate-600 mb-1">Retapez le slug <strong className="font-mono">{pharmacy?.slug}</strong> pour confirmer.</p>
            <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder={pharmacy?.slug} data-testid="pharmacy-reset-confirm-input" />
          </div>
        )}

        <div className="border-t pt-3">
          <p className="text-xs font-semibold text-slate-500 flex items-center gap-1 mb-2"><DatabaseBackup className="w-3.5 h-3.5" /> Sauvegardes de réinitialisation ({backups.length})</p>
          {backups.length === 0 ? (
            <p className="text-xs text-slate-400" data-testid="pharmacy-backups-empty">Aucune sauvegarde</p>
          ) : (
            <ul className="space-y-1 max-h-32 overflow-y-auto" data-testid="pharmacy-backups-list">
              {backups.map((b) => (
                <li key={b.name} className="flex items-center justify-between text-xs bg-slate-50 rounded px-2 py-1">
                  <span className="font-mono truncate">{b.name}</span>
                  <span className="text-slate-500 ml-2 shrink-0">{b.created_at ? new Date(b.created_at).toLocaleString('fr-FR') : ''} · {fmtSize(b.size_bytes)}</span>
                  <Button variant="ghost" size="sm" className="h-6 px-1 text-red-600 ml-1" onClick={() => dropBackup(b.name)} title="Supprimer la sauvegarde" data-testid={`drop-backup-${b.name}`}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{result ? 'Fermer' : 'Annuler'}</Button>
          {!result && (
            <Button className="bg-amber-600 hover:bg-amber-700" disabled={confirm !== pharmacy?.slug || busy} onClick={runReset} data-testid="confirm-pharmacy-reset">
              {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-2" />}
              Réinitialiser
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
