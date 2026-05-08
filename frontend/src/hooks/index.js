/**
 * Export de tous les React Query hooks
 */

// Products
export {
  useProducts,
  useProductsInfinite,
  useProduct,
  useProductAlerts,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useToggleProductStatus,
  useProductSearch,
  useLowStockProducts,
} from './useProducts';

// Infinite Scroll Hooks
export {
  useInfiniteList,
  useCustomersInfinite,
  useSuppliersInfinite,
  useSuppliesInfinite,
  usePrescriptionsInfinite,
  useDebtsInfinite,
  useStockMovementsInfinite,
  useStockLossesInfinite,
  useShiftsInfinite,
  usePriceHistoryInfinite,
  useInventoryMovementsInfinite,
} from './useInfiniteScroll';

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
  useStockValuation,
  useSettingValue,
  useCurrency,
  useLowStockThreshold,
  useReturnDelayDays,
  useExpirationAlertDays,
  usePharmacyName,
} from './useSettings';

// Customers
export {
  useCustomers,
  useCustomer,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useCustomerSearch,
  useCustomerOptions,
} from './useCustomers';

// Suppliers
export {
  useSuppliers,
  useActiveSuppliers,
  useSupplier,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
  useToggleSupplierStatus,
  useSupplierSearch,
  useSupplierOptions,
} from './useSuppliers';

// Users
export {
  useUsers,
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useToggleUserStatus,
  useResetUserPassword,
  useUserSearch,
  useUsersByRole,
} from './useUsers';

// Supplies
export {
  useSupplies,
  useSupply,
  useCreateSupply,
  useUpdateSupply,
  useDeleteSupply,
  useValidateSupply,
  useSuppliesByStatus,
  usePendingSupplies,
  useValidatedSupplies,
  useSupplySearch,
} from './useSupplies';

// Units
export {
  useUnits,
  useCreateUnit,
  useUpdateUnit,
  useDeleteUnit,
  useUnitOptions,
  useUnitName,
} from './useUnits';

// Prescriptions
export {
  usePrescriptions,
  usePrescription,
  useCreatePrescription,
  useUpdatePrescription,
  useDeletePrescription,
  useFulfillPrescription,
  usePrescriptionsByStatus,
  usePendingPrescriptions,
  usePrescriptionSearch,
} from './usePrescriptions';

// Returns
export {
  useReturns,
  useOperationsHistory,
  useReturnsBySale,
  useReturnEligibility,
  useCreateReturn,
  useHistorySearch,
  useReturnStats,
} from './useReturns';

// Reports
export {
  useSalesReport,
  useChartData,
} from './useReports';

// Dashboard
export {
  useDashboardStats,
  useDashboardSales,
  usePendingSuppliesCount,
  useStockMovements,
  usePriceHistory,
  useDashboardData,
} from './useDashboard';

// Re-export existing hooks
export { default as useDataHelpers } from './useDataHelpers';
