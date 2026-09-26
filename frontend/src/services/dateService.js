import { DEFAULT_TZ } from '../utils/timezoneUtils';

let currentTz = DEFAULT_TZ;

export const setAppTimezone = (tz) => {
  if (tz) currentTz = tz;
};

export const getAppTimezone = () => currentTz;

export const formatDateTz = (value, options = {}) =>
  value ? new Date(value).toLocaleDateString('fr-FR', { timeZone: currentTz, ...options }) : '';

export const formatDateTimeTz = (value) => {
  if (!value) return '';
  const d = new Date(value);
  return `${d.toLocaleDateString('fr-FR', { timeZone: currentTz })} ${d.toLocaleTimeString('fr-FR', { timeZone: currentTz, hour: '2-digit', minute: '2-digit' })}`;
};

// Patch global : toutes les dates affichées via toLocale*String utilisent
// le fuseau de la pharmacie, peu importe le fuseau du navigateur.
export const applyDateLocalePatch = () => {
  const origDate = Date.prototype.toLocaleDateString;
  const origTime = Date.prototype.toLocaleTimeString;
  const origFull = Date.prototype.toLocaleString;
  /* eslint-disable no-extend-native */
  Date.prototype.toLocaleDateString = function (locale, options) {
    return origDate.call(this, locale, { timeZone: currentTz, ...(options || {}) });
  };
  Date.prototype.toLocaleTimeString = function (locale, options) {
    return origTime.call(this, locale, { timeZone: currentTz, ...(options || {}) });
  };
  Date.prototype.toLocaleString = function (locale, options) {
    return origFull.call(this, locale, { timeZone: currentTz, ...(options || {}) });
  };
  /* eslint-enable no-extend-native */
};
