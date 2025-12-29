from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from database import db
from auth import require_role, get_current_user
from routes.stock import get_valuation_for_product

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/dashboard")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    today_sales = [s for s in sales if datetime.fromisoformat(s['created_at']) >= today]
    today_revenue = sum(s['total'] for s in today_sales)
    
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    low_stock_count = len([p for p in products if p['stock'] <= p['min_stock']])
    
    prescriptions = await db.prescriptions.find({"tenant_id": current_user['tenant_id'], "status": "pending"}, {"_id": 0}).to_list(1000)
    
    # Calculer la valeur totale du stock
    settings = await db.settings.find_one({"tenant_id": current_user['tenant_id']}, {"_id": 0})
    method = settings.get('stock_valuation_method', 'weighted_average') if settings else 'weighted_average'
    
    total_stock_value = 0
    for product in products:
        valuation = await get_valuation_for_product(product['id'], current_user['tenant_id'], method)
        
        if valuation['total_value'] == 0 and product.get('stock', 0) > 0:
            estimated_cost = product.get('price', 0) * 0.7
            total_stock_value += product['stock'] * estimated_cost
        else:
            total_stock_value += valuation['total_value']
    
    return {
        "today_sales_count": len(today_sales),
        "today_revenue": today_revenue,
        "total_products": len(products),
        "low_stock_count": low_stock_count,
        "pending_prescriptions": len(prescriptions),
        "total_stock_value": round(total_stock_value, 2),
        "stock_valuation_method": method
    }

@router.get("/sales")
async def get_sales_report(days: int = 7, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get sales report for a specific period"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(10000)
    
    filtered_sales = [s for s in sales if datetime.fromisoformat(s['created_at']) >= start_date]
    
    daily_stats = {}
    for sale in filtered_sales:
        sale_date = datetime.fromisoformat(sale['created_at']).date().isoformat()
        if sale_date not in daily_stats:
            daily_stats[sale_date] = {"count": 0, "revenue": 0}
        daily_stats[sale_date]['count'] += 1
        daily_stats[sale_date]['revenue'] += sale['total']
    
    return {
        "period_days": days,
        "total_sales": len(filtered_sales),
        "total_revenue": sum(s['total'] for s in filtered_sales),
        "daily_stats": daily_stats
    }
