export const DEFAULT_TZ = 'Africa/Conakry';

function getTzOffsetMs(date, tz) {
  const dtf = new Intl.DateTimeFormat('en-US', {
    timeZone: tz, hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
  const parts = Object.fromEntries(dtf.formatToParts(date).map((p) => [p.type, p.value]));
  const asUTC = Date.UTC(
    Number(parts.year), Number(parts.month) - 1, Number(parts.day),
    Number(parts.hour) % 24, Number(parts.minute), Number(parts.second)
  );
  return asUTC - date.getTime();
}

// Heure actuelle "HH:MM" dans le fuseau de la pharmacie
export function nowTimeInTz(tz = DEFAULT_TZ, offsetMinutes = 0) {
  const d = new Date(Date.now() + offsetMinutes * 60000);
  return new Intl.DateTimeFormat('fr-FR', {
    timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(d);
}

// Date du jour "YYYY-MM-DD" dans le fuseau de la pharmacie
export function todayInTz(tz = DEFAULT_TZ) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
}

// Convertit "HH:MM" (heure pharmacie, aujourd'hui — ou demain si déjà passée) en Date UTC
export function tzTimeToUtcDate(hhmm, tz = DEFAULT_TZ) {
  const [h, m] = hhmm.split(':').map(Number);
  const dateStr = todayInTz(tz);
  const guess = new Date(`${dateStr}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00Z`);
  const utc = new Date(guess.getTime() - getTzOffsetMs(guess, tz));
  return utc;
}

// Formate un instant en date "YYYY-MM-DD" dans le fuseau de la pharmacie
export function formatDateInTz(value, tz = DEFAULT_TZ) {
  if (!value) return '';
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(value));
}

// Formate un instant ISO/Date en "HH:MM" dans le fuseau de la pharmacie
export function formatTimeInTz(value, tz = DEFAULT_TZ) {
  if (!value) return '';
  return new Intl.DateTimeFormat('fr-FR', {
    timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(value));
}
