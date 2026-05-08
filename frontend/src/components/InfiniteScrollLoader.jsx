/**
 * InfiniteScrollLoader Component
 * Composant réutilisable pour afficher l'état du scroll infini
 */

import React, { useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Loader2 } from 'lucide-react';

/**
 * Composant pour gérer l'affichage du scroll infini
 * @param {number} loadedCount - Nombre d'éléments chargés
 * @param {number} totalCount - Nombre total d'éléments
 * @param {boolean} hasNextPage - S'il y a une page suivante
 * @param {boolean} isFetchingNextPage - Si une page est en cours de chargement
 * @param {function} fetchNextPage - Fonction pour charger la page suivante
 * @param {string} itemLabel - Label pour les éléments (ex: "produits", "clients")
 */
const InfiniteScrollLoader = ({
  loadedCount = 0,
  totalCount = 0,
  hasNextPage = false,
  isFetchingNextPage = false,
  fetchNextPage,
  itemLabel = 'éléments',
}) => {
  const loadMoreRef = useRef(null);

  // Intersection Observer pour charger automatiquement au scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (loadedCount === 0) return null;

  return (
    <div className="flex flex-col items-center gap-4 py-6">
      {/* Compteur */}
      <p className="text-sm text-slate-600">
        {loadedCount} sur {totalCount} {itemLabel} affichés
      </p>

      {/* Élément observé pour le chargement automatique */}
      <div ref={loadMoreRef} className="h-2 w-full" />

      {/* Indicateur de chargement */}
      {isFetchingNextPage && (
        <div className="flex items-center gap-2 text-teal-600">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Chargement...</span>
        </div>
      )}

      {/* Bouton Charger plus (fallback) */}
      {hasNextPage && !isFetchingNextPage && (
        <Button
          variant="outline"
          onClick={() => fetchNextPage()}
          className="rounded-full"
        >
          Charger plus
        </Button>
      )}

      {/* Fin de la liste */}
      {!hasNextPage && loadedCount > 0 && (
        <p className="text-sm text-slate-400">
          ✓ Tous les {itemLabel} ont été chargés
        </p>
      )}
    </div>
  );
};

export default InfiniteScrollLoader;
