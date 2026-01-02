/**
 * Export de tous les React Query hooks
 */

// Products
export {
  useProducts,
  useProduct,
  useProductAlerts,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useProductSearch,
  useLowStockProducts,
} from './useProducts';

// Categories
export {
  useCategories,
  useCategory,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useCategoryById,
  useCategoryName,
  useCategoryOptions,
} from './useCategories';

// Sales
export {
  useSales,
  useSale,
  useSalesHistory,
  useCreateSale,
  useTodaySales,
  useSaleSearch,
  useSalesStats,
} from './useSales';

// Settings
export {
  useSettingsQuery,
  useUpdateSettings,
  useSettingValue,
  useCurrency,
  useLowStockThreshold,
  useReturnDelayDays,
  useExpirationAlertDays,
  usePharmacyName,
} from './useSettings';

// Re-export existing hooks
export { default as useDataHelpers } from './useDataHelpers';
