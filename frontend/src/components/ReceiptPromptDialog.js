import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Printer, X } from 'lucide-react';

export const ReceiptPromptDialog = ({ sale, onPrint, onClose, formatAmount }) => {
  const [received, setReceived] = useState('');
  const total = sale?.total ?? sale?.total_amount ?? 0;
  const paid = sale?.has_debt ? total - (sale?.debt_amount || 0) : total;
  const isCash = sale && !sale.is_split_payment && sale.payment_method === 'cash' && paid > 0;
  const receivedNum = parseFloat(received);
  const change = isCash && !Number.isNaN(receivedNum) ? Math.max(0, receivedNum - paid) : null;

  useEffect(() => { setReceived(''); }, [sale?.id]);

  return (
    <Dialog open={!!sale} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-sm" data-testid="receipt-prompt-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Printer className="w-5 h-5 text-teal-700" /> Imprimer le reçu ?</DialogTitle>
          <DialogDescription>
            Vente <span className="font-mono font-semibold">{sale?.sale_number || sale?.id?.substring(0, 8).toUpperCase()}</span> enregistrée
            {total > 0 && formatAmount ? <> — total <strong>{formatAmount(total)}</strong></> : null}.
          </DialogDescription>
        </DialogHeader>
        {isCash && (
          <div className="space-y-1">
            <Label htmlFor="cash-received">Montant reçu du client (espèces)</Label>
            <Input id="cash-received" type="number" min={paid} step="500" value={received} onChange={(e) => setReceived(e.target.value)} placeholder={String(Math.round(paid))} data-testid="receipt-cash-received" autoFocus />
            {change != null && formatAmount && (
              <p className="text-sm font-semibold text-teal-700" data-testid="receipt-change">Monnaie à rendre : {formatAmount(change)}</p>
            )}
          </div>
        )}
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose} data-testid="receipt-prompt-no"><X className="w-4 h-4 mr-1" /> Non</Button>
          <Button className="bg-teal-700 hover:bg-teal-800" onClick={() => onPrint(isCash && !Number.isNaN(receivedNum) ? receivedNum : undefined)} data-testid="receipt-prompt-print">
            <Printer className="w-4 h-4 mr-1" /> Imprimer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
