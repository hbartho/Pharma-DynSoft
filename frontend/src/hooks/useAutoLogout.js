import { useEffect, useRef } from 'react';

const INACTIVITY_MS = 15 * 60 * 1000;  // 15 min sans activité
const SLEEP_GAP_MS = 2 * 60 * 1000;    // écart d'horloge > 2 min = PC en veille
const TICK_MS = 20 * 1000;
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click'];

/** Déconnecte l'agent après inactivité, après une mise en veille du PC, et marque la fermeture d'onglet. */
export const useAutoLogout = (isAuthenticated, logout) => {
  const lastActivity = useRef(Date.now());
  const lastTick = useRef(Date.now());

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    lastActivity.current = Date.now();
    lastTick.current = Date.now();

    const touch = () => { lastActivity.current = Date.now(); };
    ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, touch, { passive: true }));

    const doLogout = (reason) => logout({ auto: true, reason });

    const check = () => {
      const now = Date.now();
      if (now - lastTick.current > SLEEP_GAP_MS) { doLogout('veille'); return; }
      lastTick.current = now;
      if (now - lastActivity.current > INACTIVITY_MS) doLogout('inactivité');
    };
    const timer = setInterval(check, TICK_MS);

    const onVisible = () => { if (document.visibilityState === 'visible') check(); };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);

    return () => {
      clearInterval(timer);
      ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, touch));
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [isAuthenticated, logout]);
};
