from routes.auth import router as auth_router
from routes.products import router as products_router
from routes.categories import router as categories_router
from routes.sales import router as sales_router
from routes.customers import router as customers_router
from routes.suppliers import router as suppliers_router
from routes.prescriptions import router as prescriptions_router
from routes.stock import router as stock_router
from routes.settings import router as settings_router
from routes.reports import router as reports_router
from routes.sync import router as sync_router
from routes.users import router as users_router

__all__ = [
    'auth_router',
    'products_router',
    'categories_router',
    'sales_router',
    'customers_router',
    'suppliers_router',
    'prescriptions_router',
    'stock_router',
    'settings_router',
    'reports_router',
    'sync_router',
    'users_router'
]
