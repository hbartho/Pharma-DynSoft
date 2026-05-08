import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Loader2, Wallet, Clock, AlertTriangle, CheckCircle2, Calculator, Banknote, Bell, Timer, CalendarX, CalendarCheck } from 'lucide-react';
import { useOpenShift, useCloseShift, useMarkShiftAlert } from '../hooks/useShifts';
import { useShiftEligibility } from '../hooks/useShiftSchedules';
import { useSettingsQuery } from '../hooks/useSettings';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

// Modal d'ouverture de shift
export function OpenShiftModal({ isOpen, onClose, onSuccess }) {
  const [openingAmount, setOpeningAmount] = useState('');
  const [expectedEndTime, setExpectedEndTime] = useState('');
  const openShift = useOpenShift();
  const { data: settings } = useSettingsQuery();
  const { user } = useAuth();
  
  // Vérifier l'éligibilité à ouvrir un shift (planification)
  const { data: eligibility, isLoading: eligibilityLoading, refetch: refetchEligibility } = useShiftEligibility();
  
  // Refetch quand le modal s'ouvre
  useEffect(() => {
    if (isOpen) {
      refetchEligibility();
    }
  }, [isOpen, refetchEligibility]);
  
  // Calculer l'heure de fin par défaut basée sur la planification ou les paramètres
  useEffect(() => {
    if (isOpen && !expectedEndTime) {
      // Priorité: heure de fin de la planification > paramètres par défaut
      if (eligibility?.suggested_end_time) {
        setExpectedEndTime(eligibility.suggested_end_time);
      } else {
        const defaultDuration = settings?.default_shift_duration_hours || 8;
        const now = new Date();
        const endTime = new Date(now.getTime() + defaultDuration * 60 * 60 * 1000);
        const hours = String(endTime.getHours()).padStart(2, '0');
        const minutes = String(endTime.getMinutes()).padStart(2, '0');
        setExpectedEndTime(`${hours}:${minutes}`);
      }
    }
  }, [isOpen, settings, eligibility]);

  const [durationError, setDurationError] = useState('');
  // Utiliser la durée max de la planification si disponible
  const MAX_SHIFT_HOURS = eligibility?.max_duration_hours || 8;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setDurationError('');
    
    const amount = parseFloat(openingAmount) || 0;
    
    if (amount < 0) {
      return;
    }
    
    // Convertir l'heure saisie (HH:MM) en date/heure ISO complète
    let endTimeISO = null;
    if (expectedEndTime) {
      const [hours, minutes] = expectedEndTime.split(':').map(Number);
      const now = new Date();
      const endDate = new Date(now);
      endDate.setHours(hours, minutes, 0, 0);
      
      // Si l'heure de fin est avant maintenant (moins de 5 min de tolérance), 
      // c'est probablement pour demain
      const diffMinutes = (endDate - now) / (1000 * 60);
      if (diffMinutes < -5) {
        endDate.setDate(endDate.getDate() + 1);
      }
      
      // Vérifier que la durée ne dépasse pas 8 heures
      const durationHours = (endDate - now) / (1000 * 60 * 60);
      if (durationHours > MAX_SHIFT_HOURS) {
        setDurationError(`La durée du shift ne peut pas dépasser ${MAX_SHIFT_HOURS} heures. Durée actuelle: ${durationHours.toFixed(1)}h`);
        return;
      }
      
      endTimeISO = endDate.toISOString();
    }
    
    openShift.mutate({ 
      opening_amount: amount,
      expected_end_time: endTimeISO
    }, {
      onSuccess: () => {
        setOpeningAmount('');
        setExpectedEndTime('');
        setDurationError('');
        onSuccess?.();
        onClose();
      }
    });
  };
  
  const handleClose = () => {
    setDurationError('');
    setOpeningAmount('');
    setExpectedEndTime('');
    onClose();
  };
  
  // Vérifier si l'utilisateur peut ouvrir un shift
  const isAdmin = user?.role === 'admin';
  const canOpenShift = isAdmin || eligibility?.is_eligible;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-teal-700">
            <Wallet className="w-5 h-5" />
            Ouverture de Caisse
          </DialogTitle>
          <DialogDescription>
            Saisissez le montant en caisse et l'heure de fin prévue pour démarrer votre shift.
          </DialogDescription>
        </DialogHeader>
        
        {/* Message si non planifié (caissier/pharmacien) */}
        {!isAdmin && eligibilityLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-teal-600 mr-2" />
            <span className="text-slate-600">Vérification de la planification...</span>
          </div>
        ) : !isAdmin && !eligibility?.is_eligible ? (
          <div className="py-4">
            <div className={`p-4 rounded-lg border ${
              eligibility?.schedule 
                ? 'bg-amber-50 border-amber-200'  // Hors horaires (mais planifié)
                : 'bg-red-50 border-red-200'       // Non planifié
            }`}>
              <div className="flex items-start gap-3">
                {eligibility?.schedule ? (
                  <Timer className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <CalendarX className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <p className={`font-medium ${eligibility?.schedule ? 'text-amber-800' : 'text-red-800'}`}>
                    {eligibility?.schedule ? 'Hors horaires de travail' : 'Non planifié aujourd\'hui'}
                  </p>
                  <p className={`text-sm mt-1 ${eligibility?.schedule ? 'text-amber-700' : 'text-red-700'}`}>
                    {eligibility?.reason || "Vous n'êtes pas planifié pour travailler aujourd'hui."}
                  </p>
                  {eligibility?.schedule && (
                    <div className="mt-2 p-2 bg-white/50 rounded text-sm">
                      <span className={eligibility?.schedule ? 'text-amber-600' : 'text-red-600'}>
                        Horaires prévus : <strong>{eligibility.schedule.start_time} - {eligibility.schedule.end_time}</strong>
                      </span>
                    </div>
                  )}
                  {!eligibility?.schedule && (
                    <p className="text-xs text-red-600 mt-2">
                      Contactez votre administrateur pour être ajouté au calendrier de planification.
                    </p>
                  )}
                </div>
              </div>
            </div>
            <DialogFooter className="mt-4">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                className="w-full"
              >
                Fermer
              </Button>
            </DialogFooter>
          </div>
        ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Info planification si disponible */}
          {!isAdmin && eligibility?.schedule && (
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center gap-2 text-green-700">
                <CalendarCheck className="w-4 h-4" />
                <span className="text-sm font-medium">Planification du jour</span>
              </div>
              <div className="mt-1 text-sm text-green-600">
                {eligibility.schedule.start_time} - {eligibility.schedule.end_time}
                <span className="text-green-500 ml-2">(max {eligibility.max_duration_hours}h)</span>
              </div>
            </div>
          )}
          
          <div className="p-4 bg-teal-50 rounded-lg border border-teal-200">
            <Label htmlFor="opening-amount" className="text-teal-800 font-medium">
              Fond de caisse (GNF)
            </Label>
            <div className="relative mt-2">
              <Banknote className="absolute left-3 top-1/2 transform -translate-y-1/2 text-teal-600 w-5 h-5" />
              <Input
                id="opening-amount"
                type="number"
                min="0"
                step="100"
                value={openingAmount}
                onChange={(e) => setOpeningAmount(e.target.value)}
                placeholder="Ex: 500 000"
                className="pl-10 text-lg font-medium"
                autoFocus
                data-testid="opening-amount-input"
              />
            </div>
            <p className="text-xs text-teal-600 mt-2">
              Comptez les espèces dans la caisse et entrez le montant total.
            </p>
          </div>
          
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
            <Label htmlFor="end-time" className="text-slate-700 font-medium flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Heure de fin prévue (max {MAX_SHIFT_HOURS}h)
            </Label>
            <div className="relative mt-2">
              <Input
                id="end-time"
                type="time"
                value={expectedEndTime}
                onChange={(e) => { setExpectedEndTime(e.target.value); setDurationError(''); }}
                className={`text-lg font-medium ${durationError ? 'border-red-500' : ''}`}
                data-testid="expected-end-time-input"
              />
            </div>
            {durationError ? (
              <p className="text-xs text-red-600 mt-2 font-medium">
                ⚠️ {durationError}
              </p>
            ) : (
              <p className="text-xs text-slate-500 mt-2">
                Vous recevrez des alertes 30min et 5min avant la fin du shift.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button
              type="submit"
              disabled={openShift.isPending || !canOpenShift}
              className="w-full bg-teal-600 hover:bg-teal-700"
              data-testid="open-shift-btn"
            >
              {openShift.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Ouverture en cours...
                </>
              ) : (
                <>
                  <Clock className="w-4 h-4 mr-2" />
                  Ouvrir le shift
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Modal de clôture de shift
export function CloseShiftModal({ isOpen, onClose, onSuccess }) {
  const [actualAmount, setActualAmount] = useState('');
  const [closingNotes, setClosingNotes] = useState('');
  const [expectedData, setExpectedData] = useState(null);
  const [loadingExpected, setLoadingExpected] = useState(false);
  const closeShift = useCloseShift();

  // Charger les données attendues à l'ouverture de la modal
  useEffect(() => {
    if (isOpen) {
      loadExpectedData();
    }
  }, [isOpen]);

  const loadExpectedData = async () => {
    setLoadingExpected(true);
    try {
      const response = await api.get('/shifts/calculate-expected');
      setExpectedData(response.data);
    } catch (error) {
      console.error('Error loading expected data:', error);
    } finally {
      setLoadingExpected(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(actualAmount) || 0;
    
    closeShift.mutate({
      actual_closing_amount: amount,
      closing_notes: closingNotes || null
    }, {
      onSuccess: () => {
        setActualAmount('');
        setClosingNotes('');
        setExpectedData(null);
        onSuccess?.();
        onClose();
      }
    });
  };

  const calculateDifference = () => {
    if (!expectedData) return 0;
    const actual = parseFloat(actualAmount) || 0;
    return actual - expectedData.expected_closing_amount;
  };

  const difference = calculateDifference();
  const hasDifference = Math.abs(difference) > 0.01;

  const formatAmount = (amount) => {
    return (amount || 0).toLocaleString('fr-FR') + ' GNF';
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-amber-700">
            <Calculator className="w-5 h-5" />
            Clôture de Caisse
          </DialogTitle>
          <DialogDescription>
            Comptez les espèces dans la caisse et saisissez le montant total.
          </DialogDescription>
        </DialogHeader>
        
        {loadingExpected ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
            <span className="ml-2 text-slate-600">Calcul en cours...</span>
          </div>
        ) : expectedData ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Résumé du shift */}
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3">
              <h4 className="font-medium text-slate-700 text-sm uppercase tracking-wide">Résumé du shift</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-slate-500">Fond de caisse</p>
                  <p className="font-semibold text-slate-800">{formatAmount(expectedData.opening_amount)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Ventes espèces</p>
                  <p className="font-semibold text-teal-700">+ {formatAmount(expectedData.total_cash_sales)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Nombre de ventes</p>
                  <p className="font-semibold text-slate-800">{expectedData.total_sales_count}</p>
                </div>
                <div className="bg-teal-100 p-2 rounded-lg -m-1">
                  <p className="text-teal-700 text-xs">Montant attendu</p>
                  <p className="font-bold text-teal-800 text-lg">{formatAmount(expectedData.expected_closing_amount)}</p>
                </div>
              </div>
            </div>
            
            {/* Saisie du montant compté */}
            <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
              <Label htmlFor="actual-amount" className="text-amber-800 font-medium">
                Montant compté en caisse (GNF)
              </Label>
              <div className="relative mt-2">
                <Banknote className="absolute left-3 top-1/2 transform -translate-y-1/2 text-amber-600 w-5 h-5" />
                <Input
                  id="actual-amount"
                  type="number"
                  min="0"
                  step="100"
                  value={actualAmount}
                  onChange={(e) => setActualAmount(e.target.value)}
                  placeholder="Ex: 500 000"
                  className="pl-10 text-lg font-medium"
                  autoFocus
                  data-testid="actual-amount-input"
                />
              </div>
            </div>
            
            {/* Affichage de l'écart */}
            {actualAmount && (
              <div className={`p-4 rounded-lg border ${
                hasDifference 
                  ? 'bg-red-50 border-red-200' 
                  : 'bg-green-50 border-green-200'
              }`}>
                <div className="flex items-center gap-2">
                  {hasDifference ? (
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  )}
                  <span className={`font-medium ${hasDifference ? 'text-red-700' : 'text-green-700'}`}>
                    {hasDifference ? 'Écart détecté' : 'Caisse équilibrée'}
                  </span>
                </div>
                {hasDifference && (
                  <div className="mt-2">
                    <p className={`text-2xl font-bold ${difference > 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {difference > 0 ? '+' : ''}{formatAmount(difference)}
                    </p>
                    <p className="text-sm text-slate-600 mt-1">
                      {difference > 0 
                        ? 'Excédent de caisse (argent en trop)' 
                        : 'Manque de caisse (argent manquant)'}
                    </p>
                  </div>
                )}
              </div>
            )}
            
            {/* Notes en cas d'écart - OBLIGATOIRE */}
            {hasDifference && actualAmount && (
              <div>
                <Label htmlFor="closing-notes" className="text-slate-700">
                  Explication de l'écart <span className="text-red-500">*</span>
                </Label>
                <textarea
                  id="closing-notes"
                  value={closingNotes}
                  onChange={(e) => setClosingNotes(e.target.value)}
                  placeholder="Expliquez la raison de l'écart..."
                  className={`mt-1 w-full p-3 border rounded-lg resize-none h-20 text-sm ${
                    !closingNotes.trim() ? 'border-red-300 bg-red-50' : 'border-slate-300'
                  }`}
                  data-testid="closing-notes-input"
                  required
                />
                {!closingNotes.trim() && (
                  <p className="text-xs text-red-500 mt-1">
                    Une explication est requise en cas d'écart de caisse
                  </p>
                )}
              </div>
            )}
            
            <DialogFooter className="gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={closeShift.isPending}
              >
                Annuler
              </Button>
              <Button
                type="submit"
                disabled={closeShift.isPending || !actualAmount || (hasDifference && !closingNotes.trim())}
                className={hasDifference ? 'bg-amber-600 hover:bg-amber-700' : 'bg-teal-600 hover:bg-teal-700'}
                data-testid="close-shift-btn"
              >
                {closeShift.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Clôture en cours...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Clôturer le shift
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <div className="text-center py-8 text-red-600">
            Erreur lors du chargement des données
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Fonction pour jouer un son d'alerte
const playAlertSound = (alertType) => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    
    // Configuration du son selon le type d'alerte
    const soundConfig = {
      '30min': { frequency: 440, duration: 0.3, repeat: 2, gap: 0.15 },  // Ton doux, 2 bips
      '5min': { frequency: 523, duration: 0.25, repeat: 3, gap: 0.12 },  // Ton plus aigu, 3 bips
      'end': { frequency: 659, duration: 0.2, repeat: 5, gap: 0.1 }      // Ton urgent, 5 bips rapides
    };
    
    const config = soundConfig[alertType] || soundConfig['30min'];
    
    const playBeep = (startTime) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = config.frequency;
      oscillator.type = 'sine';
      
      // Envelope pour un son plus doux
      gainNode.gain.setValueAtTime(0, startTime);
      gainNode.gain.linearRampToValueAtTime(0.3, startTime + 0.02);
      gainNode.gain.linearRampToValueAtTime(0, startTime + config.duration);
      
      oscillator.start(startTime);
      oscillator.stop(startTime + config.duration);
    };
    
    // Jouer les bips avec un délai entre chaque
    for (let i = 0; i < config.repeat; i++) {
      playBeep(audioContext.currentTime + i * (config.duration + config.gap));
    }
  } catch (error) {
    console.warn('Impossible de jouer le son d\'alerte:', error);
  }
};

// Modal d'alerte de fin de shift (pour l'alerte 'end' uniquement)
export function ShiftAlertModal({ isOpen, onClose, alertType, expectedEndTime, onCloseShift }) {
  const markAlert = useMarkShiftAlert();
  
  // Jouer le son quand la modal s'ouvre
  useEffect(() => {
    if (isOpen && alertType) {
      playAlertSound(alertType);
    }
  }, [isOpen, alertType]);
  
  const handleDismiss = () => {
    markAlert.mutate(alertType);
    onClose();
  };
  
  const handleCloseShift = () => {
    markAlert.mutate(alertType);
    onClose();
    onCloseShift?.();
  };
  
  const formatEndTime = () => {
    if (!expectedEndTime) return '';
    const date = new Date(expectedEndTime);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  // Notifications simples pour 30min et 5min (avec bouton OK uniquement)
  if (alertType === '30min' || alertType === '5min') {
    const isWarning5min = alertType === '5min';
    return (
      <Dialog open={isOpen} onOpenChange={handleDismiss}>
        <DialogContent className={`max-w-sm ${isWarning5min ? 'bg-orange-50 border-orange-300' : 'bg-amber-50 border-amber-300'} border-2`}>
          <DialogHeader>
            <DialogTitle className={`flex items-center gap-3 ${isWarning5min ? 'text-orange-800' : 'text-amber-800'}`}>
              {isWarning5min ? (
                <AlertTriangle className="w-6 h-6 text-orange-500" />
              ) : (
                <Timer className="w-6 h-6 text-amber-500" />
              )}
              {isWarning5min ? 'Attention - 5 minutes' : 'Rappel - 30 minutes'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="py-3">
            <p className={`${isWarning5min ? 'text-orange-700' : 'text-amber-700'}`}>
              {isWarning5min 
                ? 'Votre shift se termine dans 5 minutes. Préparez-vous à clôturer la caisse.'
                : 'Votre shift se termine dans 30 minutes.'
              }
            </p>
            {expectedEndTime && (
              <div className="mt-3 flex items-center gap-2 text-slate-600 text-sm">
                <Clock className="w-4 h-4" />
                <span>Fin prévue: <strong>{formatEndTime()}</strong></span>
              </div>
            )}
          </div>
          
          <DialogFooter>
            <Button
              onClick={handleDismiss}
              className={`w-full ${isWarning5min ? 'bg-orange-600 hover:bg-orange-700' : 'bg-amber-600 hover:bg-amber-700'} text-white`}
              data-testid="shift-alert-ok-btn"
            >
              OK
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  // Modal de fin de shift (alerte 'end') - comportement actuel avec bouton clôturer
  if (alertType !== 'end') return null;

  return (
    <Dialog open={isOpen} onOpenChange={handleDismiss}>
      <DialogContent className="max-w-md bg-red-50 border-red-300 border-2">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 text-red-800">
            <Bell className="w-6 h-6 text-red-500 animate-bounce" />
            Fin de shift
          </DialogTitle>
        </DialogHeader>
        
        <div className="py-4">
          <p className="text-red-800 text-lg">
            L'heure de fin de votre shift est arrivée. Veuillez clôturer votre caisse.
          </p>
          {expectedEndTime && (
            <div className="mt-4 flex items-center gap-2 text-slate-600">
              <Clock className="w-4 h-4" />
              <span>Heure de fin prévue: <strong>{formatEndTime()}</strong></span>
            </div>
          )}
        </div>
        
        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={handleDismiss}
            className="flex-1"
          >
            Plus tard
          </Button>
          <Button
            onClick={handleCloseShift}
            className="flex-1 bg-red-600 hover:bg-red-700 text-white"
            data-testid="close-shift-now-btn"
          >
            <Calculator className="w-4 h-4 mr-2" />
            Clôturer maintenant
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
