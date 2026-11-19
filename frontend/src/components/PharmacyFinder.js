import React, { useState } from 'react';
import axios from 'axios';
import { Search, MapPin, Phone, Loader2, PackageCheck, Store, Pill, LocateFixed, Clock } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const TABS = [
  { id: 'product', label: 'Rechercher un produit', icon: Pill },
  { id: 'pharmacy', label: 'Rechercher une pharmacie', icon: Store },
];

const COPY = {
  product: {
    title: 'Trouver un produit près de chez vous',
    subtitle: "Consultez la disponibilité d'un médicament dans les pharmacies autour de vous.",
    placeholder: 'Produit (ex. Paracétamol 500mg, Ibuprofène...)',
  },
  pharmacy: {
    title: 'Trouver une pharmacie',
    subtitle: 'Cherchez par nom, ou indiquez seulement une ville / un quartier pour voir toutes ses pharmacies.',
    placeholder: 'Nom de la pharmacie (optionnel si lieu renseigné)',
  },
};

// Recherche publique (sans connexion) : produits en stock ou annuaire des pharmacies
export const PharmacyFinder = ({ variant = 'dark' }) => {
  const [tab, setTab] = useState('product');
  const [term, setTerm] = useState('');
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const copy = COPY[tab];
  const inputCls = 'w-full h-12 pl-11 pr-3 rounded-xl border border-slate-200 bg-white text-slate-900 text-sm placeholder:text-slate-400 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-600/20 transition-colors';

  const switchTab = (id) => {
    setTab(id);
    setTerm('');
    setResult(null);
    setError('');
  };

  const useMyPosition = () => {
    if (!navigator.geolocation) {
      setError("La géolocalisation n'est pas disponible sur cet appareil");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const { data } = await axios.get('https://nominatim.openstreetmap.org/reverse', {
            params: { format: 'jsonv2', lat: coords.latitude, lon: coords.longitude, 'accept-language': 'fr' },
          });
          const a = data.address || {};
          const place = a.suburb || a.neighbourhood || a.quarter || a.city_district || a.town || a.city || a.village || a.county || '';
          if (place) setLocation(place);
          else setError('Impossible de déterminer votre quartier, saisissez-le manuellement');
        } catch {
          setError('Impossible de déterminer votre position, saisissez votre ville ou quartier');
        } finally {
          setLocating(false);
        }
      },
      () => {
        setLocating(false);
        setError('Accès à la position refusé : saisissez votre ville ou quartier');
      },
      { timeout: 8000 }
    );
  };

  const search = async (e) => {
    e.preventDefault();
    const q = term.trim();
    const loc = location.trim();
    if (tab === 'product' && q.length < 3) {
      setError('Saisissez au moins 3 caractères du nom du produit');
      return;
    }
    if (tab === 'pharmacy' && q.length < 2 && loc.length < 2) {
      setError('Indiquez un nom de pharmacie ou une ville / un quartier');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const url = tab === 'product' ? `${API}/api/public/pharmacies/search` : `${API}/api/public/pharmacies`;
      const params = tab === 'product' ? { product: q, location: loc || undefined } : { name: q || undefined, location: loc || undefined };
      const { data } = await axios.get(url, { params });
      setResult({ ...data, tab });
    } catch (err) {
      setResult(null);
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Recherche impossible pour le moment. Réessayez.');
    } finally {
      setLoading(false);
    }
  };

  const countText = () => {
    if (!result) return '';
    const where = result.location ? ` à ${result.location}` : '';
    if (result.count === 0) {
      return result.tab === 'product'
        ? `Aucune pharmacie n'a « ${result.product} » en stock${where}.`
        : `Aucune pharmacie trouvée${result.name ? ` pour « ${result.name} »` : ''}${where}.`;
    }
    const n = result.count;
    const verb = n > 1 ? 'ont' : 'a';
    return result.tab === 'product'
      ? `${n} pharmacie${n > 1 ? 's' : ''} ${verb} ce produit en stock${where} :`
      : `${n} pharmacie${n > 1 ? 's' : ''} trouvée${n > 1 ? 's' : ''}${where} :`;
  };

  return (
    <div className="w-full" data-testid="pharmacy-finder">
      {/* Onglets */}
      <div className="flex gap-2 pl-3 sm:pl-6" role="tablist">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = tab === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => switchTab(id)}
              className={`flex items-center gap-2.5 px-5 sm:px-7 py-3 rounded-t-2xl text-sm sm:text-base font-semibold transition-colors ${
                active ? 'bg-green-700 text-white shadow-md' : 'bg-white/90 text-slate-800 hover:bg-white'
              }`}
              data-testid={`pharmacy-finder-tab-${id}`}
            >
              <Icon className="w-5 h-5" strokeWidth={2} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Carte de recherche */}
      <div className={`bg-white rounded-3xl shadow-xl p-5 sm:p-7 ${variant === 'light' ? 'border border-slate-200' : ''}`}>
        <div className="flex items-start gap-4 mb-5">
          <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center shrink-0">
            <Search className="w-7 h-7 text-green-700" strokeWidth={2.2} />
          </div>
          <div>
            <h3 className="text-xl sm:text-2xl font-bold text-slate-900 leading-tight" style={{ fontFamily: 'Manrope, sans-serif' }} data-testid="pharmacy-finder-title">
              {copy.title}
            </h3>
            <p className="text-sm sm:text-base text-slate-600 mt-1">{copy.subtitle}</p>
          </div>
        </div>

        <form onSubmit={search} className="space-y-3" data-testid="pharmacy-finder-form">
          <div className="relative">
            {tab === 'product' ? (
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            ) : (
              <Store className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            )}
            <input
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder={copy.placeholder}
              maxLength={100}
              className={inputCls}
              data-testid={tab === 'product' ? 'pharmacy-finder-product-input' : 'pharmacy-finder-name-input'}
            />
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 flex items-center rounded-xl border border-slate-200 bg-white focus-within:border-green-600 focus-within:ring-2 focus-within:ring-green-600/20 transition-colors">
              <MapPin className="absolute left-4 w-5 h-5 text-slate-500 pointer-events-none" />
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Ville ou quartier (optionnel)"
                maxLength={100}
                className="flex-1 h-12 pl-11 pr-2 bg-transparent text-slate-900 text-sm placeholder:text-slate-400 outline-none"
                data-testid="pharmacy-finder-location-input"
              />
              <button
                type="button"
                onClick={useMyPosition}
                disabled={locating}
                title="Utiliser ma position"
                className="h-12 px-3.5 border-l border-slate-200 text-slate-600 hover:text-green-700 hover:bg-green-50 rounded-r-xl transition-colors disabled:opacity-50"
                data-testid="pharmacy-finder-locate"
              >
                {locating ? <Loader2 className="w-5 h-5 animate-spin" /> : <LocateFixed className="w-5 h-5" />}
              </button>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="h-12 px-7 rounded-xl bg-green-700 hover:bg-green-800 text-white font-semibold text-base flex items-center justify-center gap-2.5 transition-all active:scale-95 disabled:opacity-60"
              data-testid="pharmacy-finder-submit"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" strokeWidth={2.4} />}
              Rechercher
            </button>
          </div>
        </form>

        {error && <p className="mt-3 text-sm text-red-600" data-testid="pharmacy-finder-error">{error}</p>}

        {result && !error && (
          <div className="mt-5" data-testid="pharmacy-finder-results">
            <p className="text-sm font-medium text-slate-700 mb-2" data-testid="pharmacy-finder-count">{countText()}</p>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {result.pharmacies.map((ph, i) => (
                <div key={i} className="rounded-xl border border-slate-200 bg-slate-50 hover:border-green-300 p-3 transition-colors" data-testid="pharmacy-finder-result">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-semibold text-slate-900">{ph.name}</p>
                    {result.tab === 'product' && (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full whitespace-nowrap bg-green-100 text-green-800">
                        <PackageCheck className="w-3 h-3" /> Disponible
                      </span>
                    )}
                  </div>
                  {ph.address && <p className="text-sm mt-1 flex items-center gap-1.5 text-slate-600"><MapPin className="w-3.5 h-3.5 shrink-0" />{ph.address}</p>}
                  {ph.hours_today && (
                    <p className="text-sm mt-0.5 flex items-center gap-1.5 text-slate-600" data-testid="pharmacy-finder-hours">
                      <Clock className="w-3.5 h-3.5 shrink-0" />
                      <span>Aujourd'hui : {ph.hours_today}</span>
                      {ph.is_open_now != null && (
                        <span className={`text-xs px-1.5 py-0.5 rounded-full ${ph.is_open_now ? 'bg-green-100 text-green-800' : 'bg-slate-200 text-slate-600'}`}>
                          {ph.is_open_now ? 'Ouvert' : 'Fermé'}
                        </span>
                      )}
                    </p>
                  )}
                  {ph.phone && (
                    <a href={`tel:${ph.phone.replace(/\s+/g, '')}`} className="text-sm mt-0.5 flex items-center gap-1.5 text-green-700 hover:underline">
                      <Phone className="w-3.5 h-3.5 shrink-0" />{ph.phone}
                    </a>
                  )}
                  {ph.products && (
                    <p className="text-xs mt-1.5 text-slate-500">
                      {ph.products.join(' · ')}{ph.total_matches > ph.products.length ? ` · +${ph.total_matches - ph.products.length}` : ''}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
