"""
DynSoft Pharma - Backend Server
A modular FastAPI application for pharmacy management.
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import logging

from config import CORS_ORIGINS
from database import close_db_connection

# Import all routers
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
from routes.returns import router as returns_router
from routes.units import router as units_router
from routes.supplies import router as supplies_router
from routes.prices import router as prices_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="DynSoft Pharma API",
    description="API for pharmacy management system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(sales_router, prefix="/api")
app.include_router(customers_router, prefix="/api")
app.include_router(suppliers_router, prefix="/api")
app.include_router(prescriptions_router, prefix="/api")
app.include_router(stock_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(returns_router, prefix="/api")
app.include_router(units_router, prefix="/api")
app.include_router(supplies_router, prefix="/api")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await close_db_connection()
    logger.info("Database connection closed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "DynSoft Pharma API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
