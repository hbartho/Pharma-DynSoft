import { cn } from "@/lib/utils"

/**
 * Skeleton avec effet Shimmer moderne
 * L'effet de brillance traverse l'élément de gauche à droite
 */
function SkeletonShimmer({ className, ...props }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-slate-200",
        "before:absolute before:inset-0",
        "before:-translate-x-full",
        "before:animate-[shimmer_1.5s_infinite]",
        "before:bg-gradient-to-r",
        "before:from-transparent before:via-white/60 before:to-transparent",
        className
      )}
      {...props}
    />
  );
}

/**
 * Skeleton pour une ligne de texte
 */
function SkeletonText({ className, width = "w-full", ...props }) {
  return (
    <SkeletonShimmer
      className={cn("h-4", width, className)}
      {...props}
    />
  );
}

/**
 * Skeleton pour un avatar/cercle
 */
function SkeletonAvatar({ className, size = "w-10 h-10", ...props }) {
  return (
    <SkeletonShimmer
      className={cn("rounded-full", size, className)}
      {...props}
    />
  );
}

/**
 * Skeleton pour une carte de statistique
 */
function SkeletonStatsCard({ className, ...props }) {
  return (
    <div className={cn("bg-white p-6 rounded-2xl border border-slate-200", className)} {...props}>
      <div className="flex items-center justify-between mb-4">
        <SkeletonShimmer className="h-4 w-24" />
        <SkeletonShimmer className="h-10 w-10 rounded-xl" />
      </div>
      <SkeletonShimmer className="h-8 w-32 mb-2" />
      <SkeletonShimmer className="h-3 w-20" />
    </div>
  );
}

/**
 * Skeleton pour une ligne de tableau
 */
function SkeletonTableRow({ columns = 5, className, ...props }) {
  return (
    <tr className={cn("border-b border-slate-100", className)} {...props}>
      {Array.from({ length: columns }).map((_, index) => (
        <td key={index} className="px-6 py-4">
          <SkeletonShimmer className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton pour un tableau complet
 */
function SkeletonTable({ rows = 5, columns = 5, className, ...props }) {
  return (
    <div className={cn("bg-white rounded-2xl border border-slate-200 overflow-hidden", className)} {...props}>
      {/* Header */}
      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
        <div className="flex gap-6">
          {Array.from({ length: columns }).map((_, index) => (
            <SkeletonShimmer key={index} className="h-4 w-24" />
          ))}
        </div>
      </div>
      {/* Body */}
      <table className="w-full">
        <tbody>
          {Array.from({ length: rows }).map((_, index) => (
            <SkeletonTableRow key={index} columns={columns} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Skeleton pour une carte produit (grille)
 */
function SkeletonProductCard({ className, ...props }) {
  return (
    <div className={cn("bg-white p-5 rounded-2xl border border-slate-200", className)} {...props}>
      <div className="flex items-start gap-4 mb-4">
        <SkeletonShimmer className="h-12 w-12 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <SkeletonShimmer className="h-5 w-3/4" />
          <SkeletonShimmer className="h-3 w-1/2" />
        </div>
      </div>
      <div className="space-y-3">
        <div className="flex justify-between">
          <SkeletonShimmer className="h-4 w-16" />
          <SkeletonShimmer className="h-4 w-20" />
        </div>
        <div className="flex justify-between">
          <SkeletonShimmer className="h-4 w-12" />
          <SkeletonShimmer className="h-4 w-16" />
        </div>
        <SkeletonShimmer className="h-2 w-full rounded-full" />
      </div>
      <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
        <SkeletonShimmer className="h-8 w-8 rounded-lg" />
        <SkeletonShimmer className="h-8 w-8 rounded-lg" />
        <SkeletonShimmer className="h-8 w-8 rounded-lg" />
      </div>
    </div>
  );
}

/**
 * Skeleton pour la grille de produits
 */
function SkeletonProductGrid({ count = 9, className, ...props }) {
  return (
    <div className={cn("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6", className)} {...props}>
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonProductCard key={index} />
      ))}
    </div>
  );
}

/**
 * Skeleton pour le graphique
 */
function SkeletonChart({ className, ...props }) {
  return (
    <div className={cn("bg-white p-6 rounded-2xl border border-slate-200", className)} {...props}>
      <SkeletonShimmer className="h-6 w-48 mb-6" />
      <div className="flex items-end gap-3 h-64">
        {[40, 65, 45, 80, 55, 70, 60].map((height, index) => (
          <SkeletonShimmer
            key={index}
            className="flex-1 rounded-t-lg"
            style={{ height: `${height}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between mt-4">
        {Array.from({ length: 7 }).map((_, index) => (
          <SkeletonShimmer key={index} className="h-3 w-8" />
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton pour le Dashboard complet
 */
function SkeletonDashboard() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <SkeletonShimmer className="h-10 w-64 mb-2" />
        <SkeletonShimmer className="h-4 w-48" />
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {Array.from({ length: 5 }).map((_, index) => (
          <SkeletonStatsCard key={index} />
        ))}
      </div>
      
      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonChart />
        <SkeletonChart />
      </div>
    </div>
  );
}

/**
 * Skeleton pour la page Ventes
 */
function SkeletonSalesPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <SkeletonShimmer className="h-10 w-32 mb-2" />
          <SkeletonShimmer className="h-4 w-48" />
        </div>
        <div className="flex gap-2">
          <SkeletonShimmer className="h-10 w-28 rounded-full" />
          <SkeletonShimmer className="h-10 w-36 rounded-full" />
        </div>
      </div>
      
      {/* Search */}
      <div className="flex gap-3">
        <SkeletonShimmer className="h-10 flex-1 rounded-lg" />
        <SkeletonShimmer className="h-10 w-48 rounded-lg" />
      </div>
      
      {/* Table */}
      <SkeletonTable rows={8} columns={8} />
    </div>
  );
}

/**
 * Skeleton pour la page Approvisionnements
 */
function SkeletonSuppliesPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <SkeletonShimmer className="h-10 w-56 mb-2" />
          <SkeletonShimmer className="h-4 w-64" />
        </div>
        <SkeletonShimmer className="h-10 w-48 rounded-full" />
      </div>
      
      {/* Filters */}
      <div className="flex gap-3">
        <SkeletonShimmer className="h-10 flex-1 rounded-lg" />
        <SkeletonShimmer className="h-10 w-40 rounded-lg" />
      </div>
      
      {/* Table */}
      <SkeletonTable rows={6} columns={7} />
    </div>
  );
}

/**
 * Skeleton pour la page Produits
 */
function SkeletonProductsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <SkeletonShimmer className="h-10 w-36 mb-2" />
          <SkeletonShimmer className="h-4 w-56" />
        </div>
        <div className="flex gap-2">
          <SkeletonShimmer className="h-10 w-32 rounded-full" />
          <SkeletonShimmer className="h-10 w-28 rounded-full" />
          <SkeletonShimmer className="h-10 w-36 rounded-full" />
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex gap-3">
        <SkeletonShimmer className="h-10 flex-1 rounded-lg" />
        <SkeletonShimmer className="h-10 w-44 rounded-lg" />
        <SkeletonShimmer className="h-10 w-36 rounded-lg" />
      </div>
      
      {/* Product Grid */}
      <SkeletonProductGrid count={9} />
      
      {/* Pagination */}
      <div className="flex justify-center gap-2">
        {Array.from({ length: 5 }).map((_, index) => (
          <SkeletonShimmer key={index} className="h-9 w-9 rounded-lg" />
        ))}
      </div>
    </div>
  );
}

export {
  SkeletonShimmer,
  SkeletonText,
  SkeletonAvatar,
  SkeletonStatsCard,
  SkeletonTableRow,
  SkeletonTable,
  SkeletonProductCard,
  SkeletonProductGrid,
  SkeletonChart,
  SkeletonDashboard,
  SkeletonSalesPage,
  SkeletonSuppliesPage,
  SkeletonProductsPage,
}
