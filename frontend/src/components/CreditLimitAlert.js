import React from 'react';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

/**
 * Alerte seuil de crédit : rouge si dépassé, orange si ≥ 80 % du seuil.
 * credit = { max_debt_limit, current_debt, available_credit, can_use_credit, customer_name }
 */
export const CreditLimitAlert = ({ credit, requestedDebt = 0, formatAmount }) => {
  if (!credit || !credit.can_use_credit || !credit.max_debt_limit) return null;
  const max = credit.max_debt_limit;
  const current = credit.current_debt || 0;
  const projected = current + (requestedDebt || 0);
  const ratio = projected / max;
  if (ratio < 0.8) return null;
  const exceeded = projected > max;

  return (
    <div
      className={`p-3 rounded-lg border-2 flex gap-2 ${exceeded ? 'bg-red-600 border-red-700 text-white' : 'bg-orange-50 border-orange-400 text-orange-900'}`}
      role="alert"
      data-testid={exceeded ? 'credit-limit-exceeded' : 'credit-limit-near'}
    >
      {exceeded ? <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" /> : <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />}
      <div className="text-sm">
        <p className="font-bold">
          {exceeded ? 'Seuil de crédit dépassé' : `Seuil de crédit presque atteint (${Math.round(ratio * 100)} %)`}
        </p>
        <p>
          Dette actuelle {formatAmount(current)}
          {requestedDebt > 0 && <> + cette vente {formatAmount(requestedDebt)}</>} = <strong>{formatAmount(projected)}</strong> / seuil {formatAmount(max)}
        </p>
        {exceeded && <p className="text-xs mt-1 opacity-90">Dépassement de {formatAmount(projected - max)} — la vente à crédit sera refusée.</p>}
      </div>
    </div>
  );
};
