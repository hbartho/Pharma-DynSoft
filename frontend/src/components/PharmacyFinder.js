import React, { useState } from 'react';
import axios from 'axios';
import { Search, MapPin, Phone, Loader2, PackageCheck, Store } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Recherche publique (sans connexion) des pharmacies ayant un produit en stock
export const PharmacyFinder = ({ variant = 'dark' }) => {
  const [product, setProduct] = useState('');
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const dark = variant === 'dark';
  const inputCls = dark
    ? 'bg-white/10 border-white/20 text-white placeholder:text-teal-100/60 focus:bg-white/15 focus:border-white/50'
    : 'bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:border-teal-500';
  const cardCls = dark ? 'bg-white/10 border-white/15 hover:bg-white/15' : 'bg-white border-slate-200 hover:border-teal-300';
  const muted = dark ? 'text-teal-100/80' : 'text-slate-500';

  const search = async (e) => {
    e.preventDefault();
    if (product.trim().length < 3) {
      setError('Saisissez au moins 3 caractères du nom du produit');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/api/public/pharmacies/search`, {
        params: { product: product.trim(), location: location.trim() || undefined },
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Recherche impossible pour le moment. Réessayez.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full" data-testid="pharmacy-finder">
      <div className="flex items-center gap-2 mb-3">
        <Store className={`w-5 h-5 ${dark ? 'text-emerald-300' : 'text-teal-600'}`} strokeWidth={1.5} />
        <h3 className={`font-semibold text-base md:text-lg ${dark ? 'text-white' : 'text-slate-900'}`} style={{ fontFamily: 'Manrope, sans-serif' }}>
          Trouver un produit près de chez vous
        </h3>
      </div>
      <p className={`text-sm mb-4 ${muted}`}>Quelles pharmacies ont ce produit en stock ? Aucune connexion requise.</p>

      <form onSubmit={search} className="space-y-2.5" data-testid="pharmacy-finder-form">
        <div className="relative">
          <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${muted}`} />
          <input
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="Produit (ex. Paracétamol 500mg)"
            maxLength={100}
            className={`w-full h-11 pl-10 pr-3 rounded-xl border text-sm outline-none transition-colors ${inputCls}`}
            data-testid="pharmacy-finder-product-input"
          />
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <MapPin className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${muted}`} />
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Ville ou quartier (optionnel)"
              maxLength={100}
              className={`w-full h-11 pl-10 pr-3 rounded-xl border text-sm outline-none transition-colors ${inputCls}`}
              data-testid="pharmacy-finder-location-input"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className={`h-11 px-5 rounded-xl text-sm font-medium transition-all active:scale-95 disabled:opacity-60 ${
              dark ? 'bg-emerald-400 text-emerald-950 hover:bg-emerald-300' : 'bg-teal-700 text-white hover:bg-teal-800'
            }`}
            data-testid="pharmacy-finder-submit"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Rechercher'}
          </button>
        </div>
      </form>

      {error && <p className={`mt-3 text-sm ${dark ? 'text-amber-200' : 'text-red-600'}`} data-testid="pharmacy-finder-error">{error}</p>}

      {result && !error && (
        <div className="mt-4" data-testid="pharmacy-finder-results">
          <p className={`text-sm mb-2 ${muted}`} data-testid="pharmacy-finder-count">
            {result.count === 0
              ? `Aucune pharmacie n'a « ${result.product} » en stock${result.location ? ` à ${result.location}` : ''}.`
              : `${result.count} pharmacie${result.count > 1 ? 's' : ''} ${result.count > 1 ? 'ont' : 'a'} ce produit en stock${result.location ? ` à ${result.location}` : ''} :`}
          </p>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {result.pharmacies.map((ph, i) => (
              <div key={i} className={`rounded-xl border p-3 transition-colors ${cardCls}`} data-testid="pharmacy-finder-result">
                <div className="flex items-start justify-between gap-2">
                  <p className={`font-semibold ${dark ? 'text-white' : 'text-slate-900'}`}>{ph.name}</p>
                  <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${dark ? 'bg-emerald-400/20 text-emerald-200' : 'bg-emerald-50 text-emerald-700'}`}>
                    <PackageCheck className="w-3 h-3" /> Disponible
                  </span>
                </div>
                {ph.address && <p className={`text-sm mt-1 flex items-center gap-1.5 ${muted}`}><MapPin className="w-3.5 h-3.5 shrink-0" />{ph.address}</p>}
                {ph.phone && (
                  <a href={`tel:${ph.phone.replace(/\s+/g, '')}`} className={`text-sm mt-0.5 flex items-center gap-1.5 hover:underline ${dark ? 'text-emerald-200' : 'text-teal-700'}`}>
                    <Phone className="w-3.5 h-3.5 shrink-0" />{ph.phone}
                  </a>
                )}
                <p className={`text-xs mt-1.5 ${muted}`}>
                  {ph.products.join(' · ')}{ph.total_matches > ph.products.length ? ` · +${ph.total_matches - ph.products.length}` : ''}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
