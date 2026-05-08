/**
 * Composant de prompt d'installation PWA personnalisé
 * Affiche une bannière pour inviter l'utilisateur à installer l'application
 */

import React, { useState, useEffect } from 'react';
import { X, Download, Smartphone } from 'lucide-react';
import { Button } from './ui/button';

const PWAInstallPrompt = () => {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);

  useEffect(() => {
    // Vérifier si déjà installé
    const standalone = window.matchMedia('(display-mode: standalone)').matches || 
                       window.navigator.standalone === true;
    setIsStandalone(standalone);

    // Détecter iOS
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    setIsIOS(iOS);

    // Vérifier si l'utilisateur a déjà refusé l'installation
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    const dismissedDate = dismissed ? new Date(dismissed) : null;
    const daysSinceDismissed = dismissedDate 
      ? (new Date() - dismissedDate) / (1000 * 60 * 60 * 24) 
      : null;

    // Écouter l'événement beforeinstallprompt (Chrome, Edge, etc.)
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      
      // Afficher le prompt si pas récemment refusé (7 jours)
      if (!daysSinceDismissed || daysSinceDismissed > 7) {
        setTimeout(() => setShowPrompt(true), 3000); // Afficher après 3 secondes
      }
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Pour iOS, afficher le prompt personnalisé après un délai
    if (iOS && !standalone && (!daysSinceDismissed || daysSinceDismissed > 7)) {
      setTimeout(() => setShowPrompt(true), 5000);
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        console.log('PWA installée');
      }
      
      setDeferredPrompt(null);
      setShowPrompt(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    localStorage.setItem('pwa-install-dismissed', new Date().toISOString());
  };

  // Ne rien afficher si déjà installé ou si pas de prompt disponible
  if (isStandalone || !showPrompt) {
    return null;
  }

  return (
    <div 
      className="fixed bottom-0 left-0 right-0 z-50 animate-in slide-in-from-bottom duration-500"
      style={{ 
        background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
        boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.15)'
      }}
    >
      <div className="max-w-4xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4">
          {/* Icône et texte */}
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <Smartphone className="w-7 h-7 text-white" />
            </div>
            <div className="text-white">
              <h3 className="font-bold text-lg" style={{ fontFamily: 'Manrope, sans-serif' }}>
                Installer PharmaFlow
              </h3>
              <p className="text-white/90 text-sm" style={{ fontFamily: 'Inter, sans-serif' }}>
                {isIOS 
                  ? "Appuyez sur Partager puis 'Sur l'écran d'accueil'"
                  : "Ajoutez l'app à votre écran d'accueil"
                }
              </p>
            </div>
          </div>

          {/* Boutons */}
          <div className="flex items-center gap-2">
            {!isIOS && (
              <Button
                onClick={handleInstallClick}
                className="bg-white text-orange-600 hover:bg-white/90 font-semibold px-6"
              >
                <Download className="w-4 h-4 mr-2" />
                Installer
              </Button>
            )}
            <button
              onClick={handleDismiss}
              className="p-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
              aria-label="Fermer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PWAInstallPrompt;
