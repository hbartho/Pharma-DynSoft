import React, { useState } from 'react';
import api from '../services/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from './ui/dialog';
import { toast } from 'sonner';
import { KeyRound, Loader2 } from 'lucide-react';

export const ChangePasswordDialog = ({ open, onOpenChange }) => {
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.next !== form.confirm) {
      toast.error('Les deux nouveaux mots de passe ne correspondent pas');
      return;
    }
    if (form.next.length < 6) {
      toast.error('Le nouveau mot de passe doit contenir au moins 6 caractères');
      return;
    }
    setSaving(true);
    try {
      await api.put('/auth/change-password', {
        current_password: form.current,
        new_password: form.next,
      });
      toast.success('Mot de passe mis à jour avec succès');
      setForm({ current: '', next: '', confirm: '' });
      onOpenChange(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erreur lors du changement de mot de passe');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-teal-600" strokeWidth={1.5} />
            Changer mon mot de passe
          </DialogTitle>
          <DialogDescription>
            Votre mot de passe est stocké de façon sécurisée (haché).
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="cp-current">Mot de passe actuel</Label>
            <Input id="cp-current" type="password" value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} required data-testid="cp-current-input" />
          </div>
          <div>
            <Label htmlFor="cp-new">Nouveau mot de passe (min. 6 caractères)</Label>
            <Input id="cp-new" type="password" value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })} required minLength={6} data-testid="cp-new-input" />
          </div>
          <div>
            <Label htmlFor="cp-confirm">Confirmer le nouveau mot de passe</Label>
            <Input id="cp-confirm" type="password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} required minLength={6} data-testid="cp-confirm-input" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
            <Button type="submit" className="bg-teal-600 hover:bg-teal-700" disabled={saving} data-testid="cp-submit-button">
              {saving && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Modifier
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
