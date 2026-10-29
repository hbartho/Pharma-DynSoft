import JsBarcode from 'jsbarcode';

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const PAYMENT_LABELS = {
  cash: 'Espèces', card: 'Carte', orange_money: 'Orange Money', mtn_money: 'MTN Money',
  mobile_money: 'Mobile Money', check: 'Chèque', debt: 'Crédit', credit: 'Crédit', transfer: 'Virement',
};

const barcodeSvg = (text) => {
  try {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    JsBarcode(svg, text, { format: 'CODE128', width: 1.4, height: 38, displayValue: false, margin: 0 });
    return svg.outerHTML;
  } catch { return ''; }
};

/** Construit le HTML d'un ticket 80 mm pour une vente. */
export const buildReceiptHtml = ({ sale, settings = {}, agentName, customerName, formatAmount }) => {
  const fmt = formatAmount || ((n) => `${Math.round(n || 0).toLocaleString('fr-FR')} GNF`);
  const saleNumber = sale.sale_number || sale.id?.substring(0, 8).toUpperCase() || '';
  const date = new Date(sale.created_at || Date.now()).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  const subtotal = (sale.items || []).reduce((s, i) => s + (i.unit_price || i.price || 0) * (i.quantity || 0), 0);
  const discount = sale.discount_amount || sale.discount || 0;
  const total = sale.total ?? sale.total_amount ?? subtotal - discount;
  const paid = sale.amount_paid ?? (sale.has_debt ? total - (sale.debt_amount || 0) : total);
  const received = sale.cash_received ?? sale.amount_received;
  const change = received != null ? Math.max(0, received - paid) : null;

  let payment;
  if (sale.is_split_payment && sale.split_payments?.length) {
    payment = sale.split_payments.map((p) => `${PAYMENT_LABELS[p.method] || p.method} ${fmt(p.amount)}`).join('<br/>');
  } else {
    payment = PAYMENT_LABELS[sale.payment_method] || sale.payment_method || '';
  }

  const rows = (sale.items || []).map((i) => {
    const name = i.product_name || i.name || 'Article';
    const price = i.unit_price || i.price || 0;
    return `<tr><td class="n" colspan="3">${esc(name)}</td></tr>
      <tr><td class="q">${i.quantity} x ${fmt(price)}</td><td></td><td class="r">${fmt(price * i.quantity)}</td></tr>`;
  }).join('');

  return `<!doctype html><html><head><meta charset="utf-8"><title>Reçu ${esc(saleNumber)}</title>
<style>
  @page { size: 80mm auto; margin: 3mm; }
  * { box-sizing: border-box; }
  body { width: 72mm; margin: 0 auto; font-family: "Courier New", monospace; font-size: 11px; color: #000; }
  .c { text-align: center; } .r { text-align: right; } .b { font-weight: 700; }
  h1 { font-size: 15px; margin: 0 0 2px; }
  .muted { font-size: 10px; }
  hr { border: 0; border-top: 1px dashed #000; margin: 5px 0; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 1px 0; vertical-align: top; }
  td.n { font-weight: 600; } td.q { padding-left: 6px; font-size: 10px; }
  .tot td { font-size: 13px; font-weight: 700; padding-top: 3px; }
  .bc { margin: 6px 0 2px; } .bc svg { width: 100%; height: 38px; }
  .foot { margin-top: 6px; font-size: 10px; }
  .pw { margin-top: 8px; font-size: 9px; color: #444; }
</style></head><body>
<div class="c">
  <h1>${esc(settings.pharmacy_name || 'DynSoft Pharma')}</h1>
  ${settings.pharmacy_address ? `<div class="muted">${esc(settings.pharmacy_address)}</div>` : ''}
  ${settings.pharmacy_phone ? `<div class="muted">Tél : ${esc(settings.pharmacy_phone)}</div>` : ''}
</div>
<hr/>
<table>
  <tr><td>N° vente</td><td class="r b" colspan="2">${esc(saleNumber)}</td></tr>
  <tr><td>Date</td><td class="r" colspan="2">${esc(date)}</td></tr>
  <tr><td>Agent</td><td class="r" colspan="2">${esc(agentName || sale.employee_code || '')}</td></tr>
  ${customerName ? `<tr><td>Client</td><td class="r" colspan="2">${esc(customerName)}</td></tr>` : ''}
</table>
<hr/>
<table>${rows}</table>
<hr/>
<table>
  ${discount > 0 ? `<tr><td>Sous-total</td><td></td><td class="r">${fmt(subtotal)}</td></tr>
  <tr><td>Rabais${sale.promo_code ? ` (${esc(sale.promo_code)})` : ''}</td><td></td><td class="r">-${fmt(discount)}</td></tr>` : ''}
  <tr class="tot"><td>TOTAL</td><td></td><td class="r">${fmt(total)}</td></tr>
  <tr><td>Paiement</td><td></td><td class="r">${payment}</td></tr>
  ${sale.has_debt && sale.debt_amount > 0 ? `<tr><td>Payé</td><td></td><td class="r">${fmt(paid)}</td></tr>
  <tr><td class="b">Reste à payer (crédit)</td><td></td><td class="r b">${fmt(sale.debt_amount)}</td></tr>` : ''}
  ${received != null ? `<tr><td>Reçu</td><td></td><td class="r">${fmt(received)}</td></tr>
  <tr><td class="b">Monnaie rendue</td><td></td><td class="r b">${fmt(change)}</td></tr>` : ''}
</table>
<div class="c bc">${barcodeSvg(saleNumber)}<div class="muted">${esc(saleNumber)}</div></div>
<hr/>
<div class="c foot">${esc(settings.receipt_footer || 'Merci de votre visite')}</div>
<div class="c pw">Produit par DynSoft Pharma</div>
<script>window.onload=function(){window.focus();window.print();setTimeout(function(){window.close()},800);};</script>
</body></html>`;
};

/** Ouvre le ticket dans une fenêtre d'impression (imprimante par défaut / kiosk-printing = sans dialogue). */
export const printReceipt = (args) => {
  const html = buildReceiptHtml(args);
  const win = window.open('', '_blank', 'width=420,height=640');
  if (!win) return false;
  win.document.open();
  win.document.write(html);
  win.document.close();
  return true;
};
