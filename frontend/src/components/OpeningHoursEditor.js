import React from 'react';
import { Clock, CalendarDays } from 'lucide-react';
import { Switch } from './ui/switch';
import { Checkbox } from './ui/checkbox';

export const DAYS = [
  { key: 'mon', label: 'Lundi' },
  { key: 'tue', label: 'Mardi' },
  { key: 'wed', label: 'Mercredi' },
  { key: 'thu', label: 'Jeudi' },
  { key: 'fri', label: 'Vendredi' },
  { key: 'sat', label: 'Samedi' },
  { key: 'sun', label: 'Dimanche' },
];

export const defaultOpeningHours = () => ({
  enabled: true,
  days: {
    mon: { open: '08:00', close: '20:00', closed: false },
    tue: { open: '08:00', close: '20:00', closed: false },
    wed: { open: '08:00', close: '20:00', closed: false },
    thu: { open: '08:00', close: '20:00', closed: false },
    fri: { open: '08:00', close: '20:00', closed: false },
    sat: { open: '08:00', close: '18:00', closed: false },
    sun: { open: '09:00', close: '13:00', closed: true },
  },
});

// Éditeur des horaires d'ouverture (7 jours, ouverture / fermeture / fermé)
export const OpeningHoursEditor = ({ value, onChange, idPrefix = 'oh' }) => {
  const hours = value || defaultOpeningHours();
  const setDay = (key, patch) => onChange({ ...hours, days: { ...hours.days, [key]: { ...hours.days[key], ...patch } } });
  const disabledAll = !hours.enabled;

  return (
    <div className="rounded-xl border border-slate-200 bg-white" data-testid="opening-hours-editor">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50 rounded-t-xl">
        <div className="flex items-center gap-2 text-slate-800 font-semibold">
          <Clock className="w-5 h-5 text-teal-700" /> Horaires d'ouverture
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
          <Switch checked={hours.enabled} onCheckedChange={(v) => onChange({ ...hours, enabled: !!v })} data-testid="opening-hours-toggle" />
          Activer les horaires
        </label>
      </div>
      <div className={`divide-y divide-slate-100 ${disabledAll ? 'opacity-50 pointer-events-none' : ''}`}>
        {DAYS.map(({ key, label }) => {
          const d = hours.days[key];
          return (
            <div key={key} className="grid grid-cols-[88px_1fr_auto_1fr_auto] items-center gap-2 px-4 py-2.5" data-testid={`opening-hours-row-${key}`}>
              <span className="text-sm font-medium text-slate-700">{label}</span>
              <div className="relative">
                <Clock className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                <input
                  id={`${idPrefix}-${key}-open`}
                  type="time"
                  value={d.open}
                  disabled={d.closed}
                  onChange={(e) => setDay(key, { open: e.target.value })}
                  className="w-full h-9 pl-8 pr-2 rounded-md border border-slate-200 text-sm disabled:bg-slate-100 disabled:text-slate-400"
                  data-testid={`opening-hours-${key}-open`}
                />
              </div>
              <span className="text-xs text-slate-500">à</span>
              <div className="relative">
                <Clock className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                <input
                  id={`${idPrefix}-${key}-close`}
                  type="time"
                  value={d.close}
                  disabled={d.closed}
                  onChange={(e) => setDay(key, { close: e.target.value })}
                  className="w-full h-9 pl-8 pr-2 rounded-md border border-slate-200 text-sm disabled:bg-slate-100 disabled:text-slate-400"
                  data-testid={`opening-hours-${key}-close`}
                />
              </div>
              <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer pl-1">
                <Checkbox checked={d.closed} onCheckedChange={(v) => setDay(key, { closed: !!v })} data-testid={`opening-hours-${key}-closed`} />
                Fermé
              </label>
            </div>
          );
        })}
      </div>
      <div className="m-4 flex items-start gap-2 rounded-lg bg-sky-50 border border-sky-100 px-3 py-2.5 text-xs text-sky-800">
        <CalendarDays className="w-4 h-4 mt-0.5 shrink-0" />
        <span>Les horaires seront affichés sur la fiche de la pharmacie et permettront aux clients de connaître les heures d'ouverture.</span>
      </div>
    </div>
  );
};
