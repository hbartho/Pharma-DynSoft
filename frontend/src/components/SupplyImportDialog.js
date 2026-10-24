import React, { useRef, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { FileSpreadsheet, Download, Upload, CheckCircle2, AlertCircle, Loader2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';

const fmt = (n) => new Intl.NumberFormat('fr-FR').format(Math.round(n || 0));

const downloadTemplate = async (format) => {
  try {
    const res = await api.get(`/supplies/import/template?format=${format}`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url; a.download = `modele_approvisionnement.${format}`; a.click();
    URL.revokeObjectURL(url);
  } catch { toast.error('Téléchargement du modèle impossible'); }
};

export const SupplyImportDialog = ({ open, onOpenChange, suppliers = [], onCreate, creating }) => {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [meta, setMeta] = useState({ supplier_id: '', delivery_note_number: '', invoice_number: '' });

  const reset = () => { setFile(null); setPreview(null); setMeta({ supplier_id: '', delivery_note_number: '', invoice_number: '' }); };
  const close = (o) => { if (!o) reset(); onOpenChange(o); };

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/supplies/import/preview', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setPreview(res.data);
      if (res.data.summary.ok === 0) toast.warning('Aucune ligne exploitable dans ce fichier');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Fichier illisible');
    } finally { setLoading(false); }
  };

  const submit = () => {
    if (!meta.supplier_id) { toast.error('Veuillez sélectionner un fournisseur'); return; }
    if (!meta.invoice_number.trim()) { toast.error('Veuillez saisir le N° facture'); return; }
    const okRows = preview.rows.filter((r) => r.status === 'ok');
    onCreate({
      supplier_id: meta.supplier_id,
      delivery_note_number: meta.delivery_note_number || null,
      invoice_number: meta.invoice_number.trim(),
      notes: `Import fichier ${preview.filename}`,
      items: okRows.map((r) => ({
        product_id: r.product_id,
        quantity: r.quantity,
        unit_price: r.unit_price,
        selling_price: r.selling_price || null,
        date_peremption: r.date_peremption,
        lot_number: r.lot_number || null,
        tva_rate: r.tva_rate || 0,
      })),
    }, () => close(false));
  };

  const ok = preview?.summary?.ok || 0;
  const metaValid = !!meta.supplier_id && meta.invoice_number.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="supply-import-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            <FileSpreadsheet className="w-5 h-5 text-teal-700" strokeWidth={1.5} /> Importer un approvisionnement (CSV / Excel)
          </DialogTitle>
          <DialogDescription>
            Une ligne par produit : Produit (ou Référence / Code-barres), Quantité, Prix cession HT, Date péremption, puis Prix public, N° lot et TVA facultatifs.
            L'approvisionnement est créé « En attente » et se valide comme d'habitude.
          </DialogDescription>
        </DialogHeader>

        {!preview ? (
          <div className="space-y-5">
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => downloadTemplate('xlsx')} data-testid="download-template-xlsx"><Download className="w-4 h-4 mr-2" strokeWidth={1.5} />Modèle Excel</Button>
              <Button variant="outline" size="sm" onClick={() => downloadTemplate('csv')} data-testid="download-template-csv"><Download className="w-4 h-4 mr-2" strokeWidth={1.5} />Modèle CSV</Button>
            </div>
            <div
              className="border-2 border-dashed border-teal-200 rounded-xl p-8 text-center bg-teal-50/40 cursor-pointer hover:bg-teal-50"
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) setFile(f); }}
              data-testid="supply-import-dropzone"
            >
              <Upload className="w-8 h-8 mx-auto text-teal-600 mb-2" strokeWidth={1.5} />
              <p className="text-sm text-slate-700">{file ? <strong>{file.name}</strong> : 'Cliquez ou glissez votre fichier ici'}</p>
              <p className="text-xs text-slate-400 mt-1">.xlsx, .xls ou .csv — 5 Mo max</p>
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="supply-import-file-input" />
            </div>
            <DialogFooter>
              <Button onClick={analyze} disabled={!file || loading} className="bg-teal-700 hover:bg-teal-800" data-testid="supply-import-analyze">
                {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" strokeWidth={1.5} />}
                Analyser le fichier
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <Label className="text-sm">Fournisseur <span className="text-red-500">*</span></Label>
                <Select value={meta.supplier_id} onValueChange={(v) => setMeta({ ...meta, supplier_id: v })}>
                  <SelectTrigger className={`mt-1 ${!meta.supplier_id ? 'border-red-300' : ''}`} data-testid="supply-import-supplier"><SelectValue placeholder="Sélectionner un fournisseur" /></SelectTrigger>
                  <SelectContent>{suppliers.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="text-sm">N° bon de livraison</Label><Input className="mt-1" value={meta.delivery_note_number} onChange={(e) => setMeta({ ...meta, delivery_note_number: e.target.value })} data-testid="supply-import-bl" /></div>
              <div><Label className="text-sm">N° facture <span className="text-red-500">*</span></Label><Input className={`mt-1 ${!meta.invoice_number.trim() ? 'border-red-300' : ''}`} placeholder="Ex: FACT-001" value={meta.invoice_number} onChange={(e) => setMeta({ ...meta, invoice_number: e.target.value })} data-testid="supply-import-invoice" /></div>
            </div>
            {!metaValid && <p className="text-xs text-red-600" data-testid="supply-import-meta-hint">Le fournisseur et le N° facture sont obligatoires pour créer l'approvisionnement.</p>}

            <div className="flex flex-wrap gap-3 text-sm" data-testid="supply-import-summary">
              <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> {ok} ligne(s) prête(s)</span>
              {preview.summary.errors > 0 && <span className="px-3 py-1 rounded-full bg-red-50 text-red-700 flex items-center gap-1"><AlertCircle className="w-4 h-4" /> {preview.summary.errors} ligne(s) ignorée(s)</span>}
              <span className="px-3 py-1 rounded-full bg-slate-100 text-slate-700">Total cession : <strong>{fmt(preview.summary.total_amount)} GNF</strong></span>
            </div>

            <div className="border rounded-lg overflow-auto max-h-[45vh]">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 sticky top-0">
                  <tr className="text-left text-slate-500">
                    <th className="px-2 py-2">Ligne</th><th className="px-2 py-2">Produit</th><th className="px-2 py-2 text-right">Qté</th>
                    <th className="px-2 py-2 text-right">Cession HT</th><th className="px-2 py-2 text-right">Prix public</th><th className="px-2 py-2">Péremption</th><th className="px-2 py-2">Lot</th><th className="px-2 py-2">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((r) => (
                    <tr key={r.line} className={r.status === 'ok' ? 'border-t' : 'border-t bg-red-50/60'} data-testid={`import-row-${r.line}`}>
                      <td className="px-2 py-1.5 text-slate-400">{r.line}</td>
                      <td className="px-2 py-1.5">
                        <div className="font-medium text-slate-800">{r.product_name || '—'}</div>
                        {r.matched_by && <div className="text-[10px] text-slate-400">reconnu par {r.matched_by}</div>}
                      </td>
                      <td className="px-2 py-1.5 text-right">{r.quantity ?? '—'}</td>
                      <td className="px-2 py-1.5 text-right">{r.unit_price != null ? fmt(r.unit_price) : '—'}</td>
                      <td className="px-2 py-1.5 text-right">{r.selling_price != null ? fmt(r.selling_price) : <span className="text-slate-400">{r.current_price != null ? `${fmt(r.current_price)} (actuel)` : '—'}</span>}</td>
                      <td className="px-2 py-1.5">{r.date_peremption || '—'}</td>
                      <td className="px-2 py-1.5">{r.lot_number || <span className="text-slate-400">auto</span>}</td>
                      <td className="px-2 py-1.5">
                        {r.status === 'ok' ? <span className="text-emerald-700 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> OK</span>
                          : <span className="text-red-700" title={r.errors.join(' · ')}>{r.errors.join(' · ')}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setPreview(null)} data-testid="supply-import-back"><ArrowLeft className="w-4 h-4 mr-2" />Autre fichier</Button>
              <Button onClick={submit} disabled={ok === 0 || creating || !metaValid} className="bg-teal-700 hover:bg-teal-800" data-testid="supply-import-submit">
                {creating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" strokeWidth={1.5} />}
                Créer l'approvisionnement ({ok} ligne{ok > 1 ? 's' : ''})
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
