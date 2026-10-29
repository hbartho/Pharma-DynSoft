import { useEffect, useRef } from 'react';

const SLEEP_GAP_MS = 2 * 60 * 1000;    // écart d'horloge > 2 min = PC en veille
const TICK_MS = 20 * 1000;

/** Déconnecte l'agent après une mise en veille du PC (la fermeture d'onglet vide la session automatiquement). */
export const useAutoLogout = (isAuthenticated, logout) => {
  const lastTick = useRef(Date.now());

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    lastTick.current = Date.now();

    const check = () => {
      const now = Date.now();
      if (now - lastTick.current > SLEEP_GAP_MS) { logout({ auto: true, reason: 'veille' }); return; }
      lastTick.current = now;
    };
    const timer = setInterval(check, TICK_MS);

    const onVisible = () => { if (document.visibilityState === 'visible') check(); };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);

    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [isAuthenticated, logout]);
};
