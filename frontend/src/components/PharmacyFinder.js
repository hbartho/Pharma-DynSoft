import React, { useState } from 'react';
import axios from 'axios';
import { Search, MapPin, Phone, Loader2, PackageCheck, Store, Pill, LocateFixed, Clock, CalendarDays, Moon } from 'lucide-react';

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

const CrossIcon = ({ className = '' }) => (
  <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
    <path d="M24 6h16a4 4 0 0 1 4 4v10h10a4 4 0 0 1 4 4v16a4 4 0 0 1-4 4H44v10a4 4 0 0 1-4 4H24a4 4 0 0 1-4-4V44H10a4 4 0 0 1-4-4V24a4 4 0 0 1 4-4h10V10a4 4 0 0 1 4-4z" fill="#16a34a" />
  </svg>
);

// Carte résultat : identité + contact à gauche, statut et horaires à droite (produits masqués pour l'annuaire)
const PharmacyResultCard = ({ ph, showProducts }) => {
  const hasStatus = ph.is_open_now != null;
  const extra = ph.total_matches > (ph.products?.length || 0) ? ph.total_matches - ph.products.length : 0;
  return (
    <div className="relative rounded-2xl border border-emerald-400/40 bg-gradient-to-br from-emerald-900 via-emerald-800 to-emerald-900 text-white p-4 sm:p-5 shadow-lg" data-testid="pharmacy-finder-result">
      {showProducts && (
        <span className="absolute top-3 right-3 inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-emerald-600/80 border border-emerald-300/40 text-emerald-50" data-testid="pharmacy-result-available">
          <PackageCheck className="w-3.5 h-3.5" /> Disponible
        </span>
      )}
      {ph.on_duty && (
        <span className={`absolute top-3 ${showProducts ? 'right-32' : 'right-3'} inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-amber-400 text-amber-950`} data-testid="pharmacy-result-on-duty">
          <Moon className="w-3.5 h-3.5" /> De garde
        </span>
      )}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1.1fr] gap-4 md:gap-5">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-white flex items-center justify-center shrink-0 shadow">
              <CrossIcon className="w-8 h-8" />
            </div>
            <p className="text-xl font-extrabold leading-tight truncate" style={{ fontFamily: 'Manrope, sans-serif' }}>{ph.name}</p>
          </div>
          <div className="mt-3 space-y-1.5 text-sm">
            {ph.address && <p className="flex items-center gap-2"><MapPin className="w-4 h-4 text-emerald-200 shrink-0" />{ph.address}</p>}
            {ph.phone && (
              <a href={`tel:${ph.phone.replace(/\s+/g, '')}`} className="flex items-center gap-2 text-emerald-200 hover:text-white hover:underline">
                <Phone className="w-4 h-4 shrink-0" />{ph.phone}
              </a>
            )}
            {showProducts && ph.products?.length > 0 && (
              <p className="flex items-start gap-2" data-testid="pharmacy-result-products">
                <Pill className="w-4 h-4 text-emerald-200 shrink-0 mt-0.5" />
                <span className="uppercase">{ph.products.join(' · ')}{extra > 0 ? ` · +${extra}` : ''}</span>
              </p>
            )}
          </div>
        </div>
        <div className="hidden md:block w-px bg-emerald-400/40 self-stretch" />
        <div className="min-w-0">
          {hasStatus ? (
            <div className={`inline-flex items-center gap-3 rounded-xl px-4 py-2 font-bold ${ph.is_open_now ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'}`} data-testid="pharmacy-result-status">
              <span className={`w-3.5 h-3.5 rounded-full ${ph.is_open_now ? 'bg-green-500' : 'bg-rose-500'}`} />
              <span className="text-lg">{ph.is_open_now ? 'Ouverte' : 'Fermée'}</span>
              {ph.status_label && <span className="h-5 w-px bg-current/30" />}
              {ph.status_label && <span className="font-medium text-base">{ph.status_label}</span>}
            </div>
          ) : (
            <p className="text-sm text-emerald-100/80 italic" data-testid="pharmacy-result-no-hours">Horaires non renseignés</p>
          )}
          {ph.hours_groups?.length > 0 && (
            <div className="mt-3">
              <p className="flex items-center gap-2 text-sm font-semibold"><Clock className="w-4 h-4" /> Horaires d'ouverture :</p>
              <div className="mt-1.5 flex flex-wrap items-center gap-2" data-testid="pharmacy-result-hours">
                <CalendarDays className="w-4 h-4 text-emerald-200" />
                {ph.hours_groups.map((g, i) => (
                  <span
                    key={i}
                    className={`text-sm px-3 py-1 rounded-lg border ${g.hours === 'Fermé' ? 'bg-rose-700/80 border-rose-300/50' : 'bg-emerald-700/50 border-emerald-300/40'}`}
                  >
                    {g.days} : {g.hours}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
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
            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {result.pharmacies.map((ph, i) => (
                <PharmacyResultCard key={i} ph={ph} showProducts={result.tab === 'product'} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
