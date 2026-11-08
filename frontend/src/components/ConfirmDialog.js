import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from './ui/alert-dialog';

const ConfirmContext = createContext(null);

/** Boîte de confirmation standard de l'application (remplace window.confirm). */
export const ConfirmProvider = ({ children }) => {
  const [state, setState] = useState(null);
  const resolver = useRef(null);

  const confirm = useCallback((options) => {
    const opts = typeof options === 'string' ? { description: options } : options || {};
    setState({ title: 'Confirmation', confirmLabel: 'Confirmer', cancelLabel: 'Annuler', destructive: false, ...opts });
    return new Promise((resolve) => { resolver.current = resolve; });
  }, []);

  const close = (value) => {
    setState(null);
    resolver.current?.(value);
    resolver.current = null;
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <AlertDialog open={!!state} onOpenChange={(open) => { if (!open) close(false); }}>
        <AlertDialogContent className="max-w-md" data-testid="confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <span className={`inline-flex h-9 w-9 items-center justify-center rounded-full ${state?.destructive ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                <AlertTriangle className="h-5 w-5" />
              </span>
              {state?.title}
            </AlertDialogTitle>
            <AlertDialogDescription className="pt-1 text-slate-600">{state?.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => close(false)} data-testid="confirm-dialog-cancel">{state?.cancelLabel}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => close(true)}
              className={state?.destructive ? 'bg-red-600 hover:bg-red-700 focus:ring-red-500' : 'bg-teal-600 hover:bg-teal-700'}
              data-testid="confirm-dialog-confirm"
            >
              {state?.confirmLabel}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ConfirmContext.Provider>
  );
};

export const useConfirm = () => {
  const confirm = useContext(ConfirmContext);
  if (!confirm) throw new Error('useConfirm doit être utilisé dans ConfirmProvider');
  return confirm;
};
