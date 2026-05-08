"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
import os

from auth import require_role, get_current_user

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
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        with get_session() as session:
            # Ventes du jour
            today_sales = session.query(Sale).filter(
                Sale.created_at >= today,
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
        if date:
            try:
                selected_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                selected_date = selected_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            except ValueError:
                selected_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            selected_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_of_day = selected_date.replace(hour=23, minute=59, second=59)
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= selected_date,
                    Sale.created_at <= end_of_day,
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
                "date": selected_date.strftime('%Y-%m-%d'),
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
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= week_ago,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            daily_stats = {}
            for i in range(7):
                day = today - timedelta(days=6-i)
                day_str = day.strftime('%Y-%m-%d')
                daily_stats[day_str] = {"date": day_str, "sales_count": 0, "revenue": 0}
            
            for sale in sales:
                if sale.created_at:
                    day_str = sale.created_at.strftime('%Y-%m-%d')
                    if day_str in daily_stats:
                        daily_stats[day_str]["sales_count"] += 1
                        daily_stats[day_str]["revenue"] += sale.total or 0
            
            return {
                "period": "7 derniers jours",
                "start_date": week_ago.strftime('%Y-%m-%d'),
                "end_date": today.strftime('%Y-%m-%d'),
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
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= start_date,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            # Agrégation par jour
            daily_stats = {}
            for i in range(days):
                day = (now - timedelta(days=days-1-i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_str = day.strftime('%Y-%m-%d')
                daily_stats[day_str] = {"count": 0, "revenue": 0}
            
            for sale in sales:
                if sale.created_at:
                    day_str = sale.created_at.strftime('%Y-%m-%d')
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
        now = datetime.now(timezone.utc)
        
        if start_date:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if end_date:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        else:
            end = now
        
        with get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    Sale.created_at >= start,
                    Sale.created_at <= end,
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
                "start_date": start.strftime('%Y-%m-%d'),
                "end_date": end.strftime('%Y-%m-%d'),
                "total_sales": len(sales),
                "total_revenue": round(total_revenue, 2),
                "total_items_sold": total_items,
                "average_sale": round(avg_sale, 2),
                "by_payment_method": by_payment
            }

