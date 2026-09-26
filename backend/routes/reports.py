"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
import os

from auth import require_role, get_current_user
from services.tz_service import get_pharmacy_tz, local_day_bounds, parse_local_date, to_local_day_str, now_local

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/reports", tags=["Reports"])

PAYMENT_METHOD_LABELS = {
    'cash': 'Espèces',
    'card': 'Carte bancaire',
    'check': 'Chèque',
    'orange_money': 'Orange Money',
    'mtn_money': 'MTN Money',
    'mobile_money': 'Mobile Money',
    'credit': 'Crédit/Dette',
    'mixed': 'Paiement mixte',
}

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Sale, SaleStatus, PaymentMethod, Product, Prescription, PrescriptionStatus, Setting
    from sqlalchemy import func, and_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    @router.get("/dashboard")
    async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
        """Get dashboard statistics"""
        day_start, day_end = local_day_bounds()
        
        with get_session() as session:
            # Ventes du jour
            today_sales = session.query(Sale).filter(
                Sale.created_at >= day_start,
                Sale.created_at < day_end,
                Sale.status != SaleStatus.CANCELLED
            ).all()
            
            today_revenue = sum(s.total or 0 for s in today_sales)
            
            # Produits
            products = session.query(Product).filter(Product.is_active == True).all()
            low_stock_count = len([p for p in products if (p.stock or 0) <= (p.min_stock or 10)])
            
            # Ordonnances en attente
            pending_prescriptions = session.query(Prescription).filter(
                Prescription.status == PrescriptionStatus.PENDING
            ).count()
            
            # Valeur du stock (estimation simple)
            total_stock_value = sum((p.stock or 0) * (p.purchase_price or p.price * 0.7 or 0) for p in products)
            
            # Méthode de valorisation
            setting = session.query(Setting).filter(Setting.key == 'stock_valuation_method').first()
            method = setting.value if setting else 'weighted_average'
            
            return {
                "today_sales_count": len(today_sales),
                "today_revenue": today_revenue,
                "total_products": len(products),
                "low_stock_count": low_stock_count,
                "pending_prescriptions": pending_prescriptions,
                "total_stock_value": round(total_stock_value, 2),
                "stock_valuation_method": method
            }
    
    @router.get("/today-sales-by-payment")
    async def get_today_sales_by_payment(
        date: str = None,
        current_user: dict = Depends(get_current_user)
    ):
        """Get sales breakdown by payment method for a specific date"""
        tz = get_pharmacy_tz()
        local_date = parse_local_date(date) if date else None
        if local_date is None:
            local_date = now_local(tz).date()
        
        day_start, day_end = local_day_bounds(local_date, tz)
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= day_start,
                    Sale.created_at < day_end,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            by_payment = {}
            
            # Variables pour les rabais
            total_discount = 0
            discount_count = 0
            
            def add_to_payment(method, amount, is_partial=False):
                """
                Ajoute un montant à un mode de paiement.
                is_partial=True signifie que c'est une partie d'une vente mixte
                """
                if method not in by_payment:
                    by_payment[method] = {
                        "method": method,
                        "label": PAYMENT_METHOD_LABELS.get(method, method.replace('_', ' ').title()),
                        "count": 0,
                        "total": 0,
                        "full_sales_count": 0,
                        "partial_sales_count": 0
                    }
                by_payment[method]["total"] += amount
                if is_partial:
                    by_payment[method]["partial_sales_count"] += 1
                else:
                    by_payment[method]["full_sales_count"] += 1
                by_payment[method]["count"] = by_payment[method]["full_sales_count"] + by_payment[method]["partial_sales_count"]
            
            for sale in sales:
                # Comptabiliser les rabais
                sale_discount = sale.discount or 0
                if sale_discount > 0:
                    total_discount += sale_discount
                    discount_count += 1
                
                # Pour les ventes mixtes (split payments), ventiler par mode de paiement
                if sale.is_split_payment and sale.split_payments:
                    for payment in sale.split_payments:
                        method = payment.get('method', 'cash')
                        # Ignorer 'debt' car c'est pas un mode de paiement réel
                        if method == 'debt':
                            continue
                        amount = float(payment.get('amount', 0))
                        add_to_payment(method, amount, is_partial=True)
                else:
                    # Vente simple
                    method = sale.payment_method.value if sale.payment_method else 'cash'
                    add_to_payment(method, sale.total or 0, is_partial=False)
            
            total_revenue = sum(s.total or 0 for s in sales)
            
            return {
                "date": local_date.isoformat(),
                "total_sales": len(sales),
                "total_revenue": total_revenue,
                "by_payment_method": list(by_payment.values()),
                "discount_info": {
                    "total_discount": total_discount,
                    "discount_count": discount_count
                }
            }
    
    @router.get("/weekly")
    async def get_weekly_stats(current_user: dict = Depends(get_current_user)):
        """Get weekly sales statistics"""
        tz = get_pharmacy_tz()
        today_local = now_local(tz).date()
        week_start_utc, _ = local_day_bounds(today_local - timedelta(days=6), tz)
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= week_start_utc,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            daily_stats = {}
            for i in range(7):
                day_str = (today_local - timedelta(days=6-i)).strftime('%Y-%m-%d')
                daily_stats[day_str] = {"date": day_str, "sales_count": 0, "revenue": 0}
            
            for sale in sales:
                if sale.created_at:
                    day_str = to_local_day_str(sale.created_at, tz)
                    if day_str in daily_stats:
                        daily_stats[day_str]["sales_count"] += 1
                        daily_stats[day_str]["revenue"] += sale.total or 0
            
            return {
                "period": "7 derniers jours",
                "start_date": (today_local - timedelta(days=6)).strftime('%Y-%m-%d'),
                "end_date": today_local.strftime('%Y-%m-%d'),
                "daily_stats": list(daily_stats.values()),
                "total_sales": len(sales),
                "total_revenue": sum(s.total or 0 for s in sales)
            }
    
    @router.get("/stock-alerts")
    async def get_stock_alerts(current_user: dict = Depends(get_current_user)):
        """Get products with low stock"""
        with get_session() as session:
            products = session.query(Product).filter(Product.is_active == True).all()
            
            alerts = []
            for p in products:
                stock = p.stock or 0
                min_stock = p.min_stock or 10
                if stock <= min_stock:
                    alerts.append({
                        "id": str(p.id),
                        "name": p.name,
                        "current_stock": stock,
                        "min_stock": min_stock,
                        "shortage": max(0, min_stock - stock),
                        "status": "critical" if stock == 0 else "warning"
                    })
            
            alerts.sort(key=lambda x: x['shortage'], reverse=True)
            
            return {
                "total_alerts": len(alerts),
                "critical_count": len([a for a in alerts if a['status'] == 'critical']),
                "warning_count": len([a for a in alerts if a['status'] == 'warning']),
                "alerts": alerts
            }
    
    @router.get("/sales")
    async def get_sales_report(
        days: int = 30,
        current_user: dict = Depends(get_current_user)
    ):
        """Get sales report for the last N days - used for charts"""
        tz = get_pharmacy_tz()
        today_local = now_local(tz).date()
        start_utc, _ = local_day_bounds(today_local - timedelta(days=days-1), tz)
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= start_utc,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            # Agrégation par jour (fuseau pharmacie)
            daily_stats = {}
            for i in range(days):
                day_str = (today_local - timedelta(days=days-1-i)).strftime('%Y-%m-%d')
                daily_stats[day_str] = {"count": 0, "revenue": 0}
            
            for sale in sales:
                if sale.created_at:
                    day_str = to_local_day_str(sale.created_at, tz)
                    if day_str in daily_stats:
                        daily_stats[day_str]["count"] += 1
                        daily_stats[day_str]["revenue"] += sale.total or 0
            
            total_revenue = sum(s.total or 0 for s in sales)
            
            return {
                "total_sales": len(sales),
                "total_revenue": round(total_revenue, 2),
                "daily_stats": daily_stats
            }

    @router.get("/sales-summary")
    async def get_sales_summary(
        start_date: str = None,
        end_date: str = None,
        current_user: dict = Depends(get_current_user)
    ):
        """Get sales summary for a date range"""
        tz = get_pharmacy_tz()
        now = datetime.now(timezone.utc)
        
        sd = parse_local_date(start_date) if start_date else None
        if sd:
            start, _ = local_day_bounds(sd, tz)
        else:
            first_of_month = now_local(tz).date().replace(day=1)
            start, _ = local_day_bounds(first_of_month, tz)
            sd = first_of_month
        
        ed = parse_local_date(end_date) if end_date else None
        if ed:
            _, end = local_day_bounds(ed, tz)
        else:
            end = now
            ed = now_local(tz).date()
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= start,
                    Sale.created_at < end,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            total_revenue = sum(s.total or 0 for s in sales)
            total_items = sum(len(s.items) if s.items else 0 for s in sales)
            avg_sale = total_revenue / len(sales) if sales else 0
            
            # Par mode de paiement
            by_payment = {}
            for sale in sales:
                method = sale.payment_method.value if sale.payment_method else 'cash'
                if method not in by_payment:
                    by_payment[method] = {"count": 0, "total": 0}
                by_payment[method]["count"] += 1
                by_payment[method]["total"] += sale.total or 0
            
            return {
                "start_date": sd.strftime('%Y-%m-%d'),
                "end_date": ed.strftime('%Y-%m-%d'),
                "total_sales": len(sales),
                "total_revenue": round(total_revenue, 2),
                "total_items_sold": total_items,
                "average_sale": round(avg_sale, 2),
                "by_payment_method": by_payment
            }

