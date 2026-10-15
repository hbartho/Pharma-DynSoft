import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { Calculator, Loader2, RefreshCw, FileDown, FileSpreadsheet } from 'lucide-react';
import { todayInTz } from '../utils/timezoneUtils';
import { getAppTimezone } from '../services/dateService';

const Row = ({ label, value, bold, negative, indent, badge }) => (
  <div className={`flex items-center justify-between py-2 ${indent ? 'pl-6' : ''} ${bold ? 'border-t border-slate-200 mt-1 pt-3' : ''}`}>
    <span className={`text-sm ${bold ? 'font-semibold text-slate-900' : 'text-slate-600'}`}>
      {label} {badge && <span className="ml-2 text-xs text-slate-400">({badge})</span>}
    </span>
    <span className={`text-sm font-mono ${bold ? 'font-bold text-slate-900 text-base' : negative ? 'text-red-600' : 'text-slate-800'}`}>
      {negative && value !== '0 GNF' ? '− ' : ''}{value}
    </span>
  </div>
);

const SOURCE_LABELS = {
  manual: 'Rabais manuels',
  promo_code: 'Codes promo',
  automatic: 'Rabais automatiques',
  product: 'Rabais par produit',
};

export const AccountingSummary = ({ formatAmount }) => {
  const tz = getAppTimezone();
  const today = todayInTz(tz);
  const firstOfMonth = `${today.slice(0, 8)}01`;
  const [range, setRange] = useState({ start: firstOfMonth, end: today });
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(null);

  const handleExport = async (format) => {
    setExporting(format);
    try {
      const res = await api.get('/reports/accounting-summary/export', {
        params: { format, start_date: range.start, end_date: range.end },
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `resume_comptable_${range.start}_${range.end}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(format === 'excel' ? 'Export Excel téléchargé' : 'Export PDF téléchargé');
    } catch (e) {
      toast.error("Erreur lors de l'export");
    } finally {
      setExporting(null);
    }
  };

  const load = useCallback(async (start, end) => {
    setLoading(true);
    try {
      const res = await api.get('/reports/accounting-summary', { params: { start_date: start, end_date: end } });
      setData(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erreur de chargement du résumé comptable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(firstOfMonth, today); }, [load]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm" data-testid="accounting-summary">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-teal-50 rounded-lg">
            <Calculator className="w-5 h-5 text-teal-600" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Résumé comptable
            </h2>
            <p className="text-xs text-slate-500">Rabais, retours et casses justifiés — rien n'apparaît comme perte inexpliquée</p>
          </div>
        </div>
        <div className="flex items-end gap-2">
          <div>
            <Label htmlFor="acc-start" className="text-xs">Du</Label>
            <Input id="acc-start" type="date" value={range.start} max={today} onChange={(e) => setRange({ ...range, start: e.target.value })} className="h-9" data-testid="accounting-start-date" />
          </div>
          <div>
            <Label htmlFor="acc-end" className="text-xs">Au</Label>
            <Input id="acc-end" type="date" value={range.end} max={today} onChange={(e) => setRange({ ...range, end: e.target.value })} className="h-9" data-testid="accounting-end-date" />
          </div>
          <Button size="sm" className="bg-teal-600 hover:bg-teal-700 h-9" onClick={() => load(range.start, range.end)} disabled={loading} data-testid="accounting-refresh">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </Button>
          <Button size="sm" variant="outline" className="h-9" onClick={() => handleExport('pdf')} disabled={!!exporting} data-testid="accounting-export-pdf">
            {exporting === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <FileDown className="w-4 h-4 mr-1" strokeWidth={1.5} />}
            PDF
          </Button>
          <Button size="sm" variant="outline" className="h-9" onClick={() => handleExport('excel')} disabled={!!exporting} data-testid="accounting-export-excel">
            {exporting === 'excel' ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <FileSpreadsheet className="w-4 h-4 mr-1" strokeWidth={1.5} />}
            Excel
          </Button>
        </div>
      </div>

      {!data ? (
        <div className="py-8 text-center text-slate-400"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-10 gap-y-4">
          {/* Colonne 1 : exercice ventes */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Exercice ventes ({data.sales.count} vente{data.sales.count > 1 ? 's' : ''})</p>
            <Row label="Chiffre d'affaires brut" value={formatAmount(data.sales.gross_revenue)} />
            <Row label="Rabais accordés" value={formatAmount(data.sales.total_discounts)} negative badge={Object.values(data.discounts_by_source).reduce((s, v) => s + v.count, 0) + ' rabais'} />
            {Object.entries(data.discounts_by_source).map(([src, v]) => (
              <Row key={src} indent label={SOURCE_LABELS[src] || src} value={formatAmount(v.amount)} negative badge={`${v.count}`} />
            ))}
            <Row label="Retours remboursés" value={formatAmount(data.returns.total_refunded)} negative badge={`${data.returns.count}`} />
            <Row label="CA net encaissé" value={formatAmount(data.net_collected)} bold />
          </div>

          {/* Colonne 2 : justificatifs */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Justificatifs & engagements</p>
            <Row label="Casses/pertes validées (coût d'achat)" value={formatAmount(data.losses.validated_value)} badge={`${data.losses.validated_quantity} unité(s)`} />
            {data.losses.pending_count > 0 && (
              <Row indent label="⚠ Pertes en attente de validation" value={`${data.losses.pending_count}`} />
            )}
            <Row label="Avoirs fournisseurs (période)" value={formatAmount(data.suppliers.credits_period)} badge={`${data.suppliers.credits_count}`} />
            <Row label="Dettes fournisseurs en cours" value={formatAmount(data.suppliers.outstanding_debts)} bold />
            <p className="text-[11px] text-slate-400 mt-3">
              Période : {data.start_date} → {data.end_date} · Chaque rabais, retour et casse est tracé individuellement (historique des rabais, retours, mouvements de stock).
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
