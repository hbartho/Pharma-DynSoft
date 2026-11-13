import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Wallet, Loader2 } from 'lucide-react';
import api from '../services/api';

const Line = ({ label, value, sign, bold, muted }) => (
  <div className={`flex items-center justify-between gap-3 py-1.5 ${bold ? 'border-t border-slate-200 mt-1 pt-2' : ''}`}>
    <span className={`text-sm ${bold ? 'font-semibold text-slate-900' : muted ? 'text-slate-400' : 'text-slate-600'}`}>{label}</span>
    <span className={`text-sm tabular-nums ${bold ? 'font-bold text-slate-900' : sign === '-' ? 'text-red-600' : sign === '+' ? 'text-emerald-700' : 'text-slate-800'}`}>
      {sign === '-' ? '− ' : sign === '+' ? '+ ' : ''}{value}
    </span>
  </div>
);

/** Trésorerie d'une journée : mêmes chiffres que la synthèse comptable (même source /reports/accounting-summary). */
export const DailyCashCard = ({ date, formatAmount }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['accounting-summary', date, date],
    queryFn: async () => (await api.get('/reports/accounting-summary', { params: { start_date: date, end_date: date } })).data,
    enabled: !!date,
    staleTime: 60 * 1000,
  });

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm" data-testid="daily-cash-card">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center">
          <Wallet className="w-5 h-5 text-emerald-700" strokeWidth={1.5} />
        </div>
        <div>
          <h3 className="text-xl font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>Trésorerie du jour</h3>
          <p className="text-xs text-slate-500">Identique à la synthèse comptable (Rapports) pour cette date</p>
        </div>
      </div>
      {isLoading || !data ? (
        <div className="flex items-center gap-2 text-slate-400 py-6"><Loader2 className="w-4 h-4 animate-spin" /> Chargement…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Résultat</p>
            <Line label={`CA brut (${data.sales.count} vente${data.sales.count > 1 ? 's' : ''})`} value={formatAmount(data.sales.gross_revenue)} />
            <Line label="Rabais accordés" value={formatAmount(data.sales.total_discounts)} sign="-" />
            <Line label={`Retours remboursés (${data.returns.count})`} value={formatAmount(data.returns.total_refunded)} sign="-" />
            <Line label="CA net encaissé" value={formatAmount(data.net_collected)} bold />
            <Line label={`Créances clients abandonnées (${data.write_offs.count})`} value={formatAmount(data.write_offs.total)} sign="-" />
            <Line label="Résultat net" value={formatAmount(data.net_result)} bold />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Encaissements réels</p>
            <Line label="CA net encaissé" value={formatAmount(data.net_collected)} />
            <Line label="Ventes à crédit (non encaissées)" value={formatAmount(data.credit_sales)} sign="-" />
            <Line label={`Remboursements dettes clients (${data.debt_payments.count})`} value={formatAmount(data.debt_payments.total)} sign="+" />
            <Line label="Total réellement encaissé" value={formatAmount(data.cash_collected)} bold />
            <Line label={`Paiements fournisseurs (${data.suppliers.payments_count})`} value={formatAmount(data.suppliers.payments_period)} sign="-" />
            <Line label="Flux net de trésorerie" value={formatAmount(data.net_cash_flow)} bold />
          </div>
        </div>
      )}
    </div>
  );
};
