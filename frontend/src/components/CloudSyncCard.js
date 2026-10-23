import React, { useEffect, useState, useCallback } from 'react';
import { CloudUpload, Loader2, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';
import api from '../services/api';
import { toast } from 'sonner';

const fmt = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR') : '—');

export const CloudSyncCard = () => {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get('/cloud-sync/local/status');
      setStatus(res.data);
    } catch {
      setStatus({ enabled: false });
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!status?.running) return undefined;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [status?.running, load]);

  const run = async (full) => {
    setBusy(true);
    try {
      const res = await api.post(`/cloud-sync/local/run?full=${full ? 'true' : 'false'}`);
      toast[res.data.started ? 'success' : 'info'](res.data.started ? 'Synchronisation lancée' : res.data.message);
      setTimeout(load, 1500);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erreur');
    } finally { setBusy(false); }
  };

  if (!status?.enabled) return null;
  const ok = status.last_success_at && !status.last_error;

  return (
    <div className="p-6 rounded-xl bg-white border border-sky-100" data-testid="cloud-sync-card">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-sky-50 rounded-lg"><CloudUpload className="w-5 h-5 text-sky-600" strokeWidth={1.5} /></div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>Synchronisation vers DynSoft cloud</h2>
            <p className="text-sm text-slate-600">Chaque nuit à {status.sync_hour}h, dès qu'Internet est disponible · pharmacie <span className="font-mono">{status.slug}</span></p>
            <div className="mt-2 text-sm flex flex-wrap gap-x-4 gap-y-1">
              <span className="flex items-center gap-1" data-testid="cloud-sync-last-success">
                {ok ? <CheckCircle className="w-4 h-4 text-emerald-600" /> : <AlertTriangle className="w-4 h-4 text-amber-500" />}
                Dernière réussite : <strong>{fmt(status.last_success_at)}</strong>
                {status.last_stats?.rows != null && <span className="text-slate-400">({status.last_stats.rows} lignes{status.last_stats.full ? ', complète' : ''})</span>}
              </span>
              <span className="text-slate-500">Dernière tentative : {fmt(status.last_attempt_at)}</span>
            </div>
            {status.last_error && <p className="text-xs text-red-600 mt-1" data-testid="cloud-sync-error">Erreur : {status.last_error}</p>}
            {status.running && <p className="text-xs text-sky-700 mt-1 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Synchronisation en cours…</p>}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => run(true)} disabled={busy || status.running} data-testid="cloud-sync-full-button">Complète</Button>
          <Button onClick={() => run(false)} disabled={busy || status.running} className="bg-sky-600 hover:bg-sky-700" data-testid="cloud-sync-run-button">
            {busy || status.running ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" strokeWidth={1.5} />}
            Synchroniser maintenant
          </Button>
        </div>
      </div>
    </div>
  );
};
