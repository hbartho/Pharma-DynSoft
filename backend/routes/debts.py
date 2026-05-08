"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy.orm.attributes import flag_modified
import os
import uuid

from models.debt import (
    Debt, DebtCreate, DebtPayment, DebtPaymentCreate,
    CustomerDebtSummary, DebtDashboardStats
)
from auth import get_current_user, require_open_shift

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/debts", tags=["debts"])

def get_period_dates(period: str):
    """Calculer les dates de début et fin selon la période"""
    now = datetime.now(timezone.utc)
    
    if period == "week":
        start = now - relativedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return None, None
    
    return start, now

class WriteOffRequest(BaseModel):
    """Requête pour abandonner/passer en perte une dette"""
    reason: str

class BulkPaymentRequest(BaseModel):
    """Requête pour un remboursement en masse"""
    customer_id: str
    amount: float
    payment_method: str = "cash"
    payment_details: Optional[dict] = None
    notes: Optional[str] = None

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Debt as DebtModel, DebtStatus, Customer, Sale
    from database.repositories import CustomerRepository
    from sqlalchemy import func, and_, desc, or_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def debt_to_dict(d, sale_number: str = None) -> dict:
        if d is None:
            return None
        return {
            "id": str(d.id),
            "customer_id": str(d.customer_id) if d.customer_id else None,
            "sale_id": str(d.sale_id) if d.sale_id else None,
            "sale_number": sale_number,
            "original_amount": d.original_amount,
            "remaining_amount": d.remaining_amount,
            "status": d.status.value if d.status else "pending",
            "due_date": d.due_date.isoformat() if d.due_date else None,
            "payments": d.payments or [],
            "notes": d.notes,
            "created_at": d.created_at,
            "tenant_id": "pharmacie_centrale",
        }
    
    @router.get("/paginated")
    async def get_debts_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None, description="all, pending, partial, paid, written_off"),
        customer_id: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les dettes avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(DebtModel, Sale.sale_number).outerjoin(
                Sale, DebtModel.sale_id == Sale.id
            ).join(Customer, DebtModel.customer_id == Customer.id, isouter=True)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(Customer.name.ilike(search_term))
            
            if customer_id:
                try:
                    query = query.filter(DebtModel.customer_id == uuid.UUID(customer_id))
                except ValueError:
                    pass
            
            if status == 'pending':
                query = query.filter(DebtModel.status == DebtStatus.PENDING)
            elif status == 'partial':
                query = query.filter(DebtModel.status == DebtStatus.PARTIAL)
            elif status == 'paid':
                query = query.filter(DebtModel.status == DebtStatus.PAID)
            elif status == 'written_off':
                query = query.filter(DebtModel.status == DebtStatus.WRITTEN_OFF)
            elif status != 'all':
                # Par défaut, montrer uniquement pending et partial
                query = query.filter(DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]))
            
            # Count for pagination (need separate count query)
            count_query = session.query(func.count(DebtModel.id)).outerjoin(
                Sale, DebtModel.sale_id == Sale.id
            ).join(Customer, DebtModel.customer_id == Customer.id, isouter=True)
            
            if search:
                count_query = count_query.filter(Customer.name.ilike(f"%{search}%"))
            if customer_id:
                try:
                    count_query = count_query.filter(DebtModel.customer_id == uuid.UUID(customer_id))
                except ValueError:
                    pass
            if status == 'pending':
                count_query = count_query.filter(DebtModel.status == DebtStatus.PENDING)
            elif status == 'partial':
                count_query = count_query.filter(DebtModel.status == DebtStatus.PARTIAL)
            elif status == 'paid':
                count_query = count_query.filter(DebtModel.status == DebtStatus.PAID)
            elif status == 'written_off':
                count_query = count_query.filter(DebtModel.status == DebtStatus.WRITTEN_OFF)
            elif status != 'all':
                count_query = count_query.filter(DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]))
            
            total = count_query.scalar()
            query = query.order_by(desc(DebtModel.created_at))
            
            offset = (page - 1) * limit
            results = query.offset(offset).limit(limit).all()
            
            # Charger les noms des clients
            customer_repo = CustomerRepository()
            customers = {str(c['id']): c['name'] for c in customer_repo.get_all()}
            
            debts = []
            for d, sale_number in results:
                data = debt_to_dict(d, sale_number=sale_number)
                data['customer_name'] = customers.get(data['customer_id'], 'Client inconnu')
                debts.append(data)
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": debts,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.get("/dashboard", response_model=dict)
    async def get_debt_dashboard(
        current_user: dict = Depends(get_current_user),
        period: Optional[str] = Query(None, description="Période: week, month, quarter, year, all")
    ):
        """Obtenir les statistiques du dashboard des dettes"""
        period_start, period_end = get_period_dates(period) if period and period != "all" else (None, None)
        
        with get_session() as session:
            # Total des créances (dettes actives non filtrées par période - total global)
            # Exclure les dettes < 1 GNF (erreurs d'arrondi)
            total_query = session.query(
                func.sum(DebtModel.remaining_amount).label('total'),
                func.count(DebtModel.id).label('count')
            ).filter(
                DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                DebtModel.remaining_amount >= 1
            )
            
            total_result = total_query.first()
            total_receivables = total_result.total or 0
            total_debts_count = total_result.count or 0
            
            # Clients endettés (total global) - Exclure les dettes < 1 GNF (erreurs d'arrondi)
            customers_query = session.query(func.count(func.distinct(DebtModel.customer_id))).filter(
                DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                DebtModel.remaining_amount >= 1
            )
            total_customers_with_debt = customers_query.scalar() or 0
            
            # Récupérer le paramètre debt_overdue_days depuis les settings
            from database.repositories import SettingsRepository
            settings_repo = SettingsRepository()
            settings = settings_repo.get_all()
            debt_overdue_days = settings.get('debt_overdue_days', 90)  # Par défaut 90 jours
            
            # Dettes en retard (total global)
            # Une dette est en retard si:
            # 1. Elle a une due_date et cette date est dépassée, OU
            # 2. Elle n'a pas de due_date mais a été créée il y a plus de debt_overdue_days jours
            now = datetime.now(timezone.utc)
            today = now.date()
            overdue_threshold_date = now - relativedelta(days=debt_overdue_days)
            
            overdue_query = session.query(
                func.sum(DebtModel.remaining_amount).label('total'),
                func.count(DebtModel.id).label('count')
            ).filter(
                DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                DebtModel.remaining_amount >= 1,
                or_(
                    # Cas 1: due_date définie et dépassée
                    and_(DebtModel.due_date != None, DebtModel.due_date < today),
                    # Cas 2: pas de due_date mais créée il y a plus de X jours
                    and_(DebtModel.due_date == None, DebtModel.created_at < overdue_threshold_date)
                )
            )
            overdue_result = overdue_query.first()
            overdue_amount = overdue_result.total or 0
            overdue_count = overdue_result.count or 0
            
            average_debt = total_receivables / total_customers_with_debt if total_customers_with_debt > 0 else 0
            
            # Calculer les encaissements de la période en parcourant les paiements
            collected_this_period = 0
            written_off_this_period = 0
            written_off_count = 0
            
            # Récupérer toutes les dettes pour analyser les paiements
            all_debts = session.query(DebtModel).all()
            
            for debt in all_debts:
                payments = debt.payments or []
                for payment in payments:
                    payment_date_str = payment.get('created_at') or payment.get('date', '')
                    payment_type = payment.get('type', 'payment')
                    payment_amount = payment.get('amount', 0)
                    
                    # Parser la date du paiement
                    payment_date = None
                    if payment_date_str:
                        try:
                            if isinstance(payment_date_str, str):
                                # Essayer plusieurs formats
                                for fmt in ['%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                                    try:
                                        payment_date = datetime.strptime(payment_date_str[:26].replace('Z', ''), fmt.replace('%z', ''))
                                        if payment_date.tzinfo is None:
                                            payment_date = payment_date.replace(tzinfo=timezone.utc)
                                        break
                                    except ValueError:
                                        continue
                        except Exception:
                            pass
                    
                    # Vérifier si le paiement est dans la période
                    in_period = True
                    if period_start and payment_date:
                        in_period = payment_date >= period_start
                    
                    if in_period:
                        if payment_type == 'write_off':
                            written_off_this_period += payment_amount
                            written_off_count += 1
                        else:
                            # C'est un paiement normal
                            collected_this_period += payment_amount
            
            # Nouvelles dettes de la période
            new_debts_query = session.query(
                func.sum(DebtModel.original_amount).label('total'),
                func.count(DebtModel.id).label('count')
            )
            if period_start:
                new_debts_query = new_debts_query.filter(DebtModel.created_at >= period_start)
            new_debts_result = new_debts_query.first()
            new_debts_amount = new_debts_result.total or 0
            new_debts_count = new_debts_result.count or 0
            
            period_labels = {
                "week": "cette semaine",
                "month": "ce mois",
                "quarter": "ce trimestre",
                "year": "cette année",
                "all": "tout",
                None: "ce mois"
            }
            
            return {
                "total_receivables": total_receivables,
                "total_customers_with_debt": total_customers_with_debt,
                "total_debts_count": total_debts_count,
                "overdue_amount": overdue_amount,
                "overdue_count": overdue_count,
                "collected_this_period": collected_this_period,
                "new_debts_amount": new_debts_amount,
                "new_debts_count": new_debts_count,
                "average_debt_per_customer": round(average_debt, 2),
                "written_off_this_period": written_off_this_period,
                "written_off_count": written_off_count,
                "period": period or "month",
                "period_label": period_labels.get(period, "ce mois"),
            }
    
    @router.get("/customers-summary", response_model=List[dict])
    async def get_customers_debt_summary(
        current_user: dict = Depends(get_current_user),
        only_with_debt: bool = False
    ):
        """Obtenir le résumé des dettes par client"""
        from database.repositories import SettingsRepository
        
        customer_repo = CustomerRepository()
        customers = customer_repo.get_all()
        
        # Récupérer le paramètre debt_overdue_days depuis les settings
        settings_repo = SettingsRepository()
        settings = settings_repo.get_all()
        debt_overdue_days = settings.get('debt_overdue_days', 90)
        
        # Calculer les dates pour déterminer les dettes en retard
        now = datetime.now(timezone.utc)
        today = now.date()
        overdue_threshold_date = now - relativedelta(days=debt_overdue_days)
        
        with get_session() as session:
            result = []
            for customer in customers:
                customer_uuid = uuid.UUID(customer['id'])
                
                # Calculer la dette totale
                debt_total = session.query(func.sum(DebtModel.remaining_amount)).filter(
                    DebtModel.customer_id == customer_uuid,
                    DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                    DebtModel.remaining_amount >= 1
                ).scalar() or 0
                
                debt_count = session.query(func.count(DebtModel.id)).filter(
                    DebtModel.customer_id == customer_uuid,
                    DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                    DebtModel.remaining_amount >= 1
                ).scalar() or 0
                
                # Calculer les dettes en retard pour ce client
                overdue_amount = session.query(func.sum(DebtModel.remaining_amount)).filter(
                    DebtModel.customer_id == customer_uuid,
                    DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                    DebtModel.remaining_amount >= 1,
                    or_(
                        # Cas 1: due_date définie et dépassée
                        and_(DebtModel.due_date != None, DebtModel.due_date < today),
                        # Cas 2: pas de due_date mais créée il y a plus de X jours
                        and_(DebtModel.due_date == None, DebtModel.created_at < overdue_threshold_date)
                    )
                ).scalar() or 0
                
                overdue_count = session.query(func.count(DebtModel.id)).filter(
                    DebtModel.customer_id == customer_uuid,
                    DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]),
                    DebtModel.remaining_amount >= 1,
                    or_(
                        and_(DebtModel.due_date != None, DebtModel.due_date < today),
                        and_(DebtModel.due_date == None, DebtModel.created_at < overdue_threshold_date)
                    )
                ).scalar() or 0
                
                # Filtrer les clients avec dette < 1 GNF (éviter les erreurs d'arrondi)
                if only_with_debt and debt_total < 1:
                    continue
                
                result.append({
                    "customer_id": customer['id'],
                    "customer_name": customer.get('name'),
                    "customer_phone": customer.get('phone'),
                    "max_debt_limit": customer.get('max_debt_limit', 0),
                    "total_debt": debt_total,
                    "debts_count": debt_count,
                    "overdue_amount": overdue_amount,
                    "overdue_count": overdue_count,
                    "has_overdue": overdue_count > 0,
                    "available_credit": max(0, customer.get('max_debt_limit', 0) - debt_total)
                })
            
            result.sort(key=lambda x: x['total_debt'], reverse=True)
            return result
    
    @router.get("", response_model=List[dict])
    async def get_debts(
        current_user: dict = Depends(get_current_user),
        customer_id: Optional[str] = None,
        status: Optional[str] = None
    ):
        """Récupérer toutes les dettes"""
        with get_session() as session:
            query = session.query(DebtModel, Sale.sale_number).outerjoin(
                Sale, DebtModel.sale_id == Sale.id
            )
            
            if customer_id:
                query = query.filter(DebtModel.customer_id == uuid.UUID(customer_id))
            if status:
                status_map = {
                    'pending': DebtStatus.PENDING,
                    'partial': DebtStatus.PARTIAL,
                    'paid': DebtStatus.PAID,
                    'written_off': DebtStatus.WRITTEN_OFF
                }
                if status in status_map:
                    query = query.filter(DebtModel.status == status_map[status])
            
            results = query.order_by(desc(DebtModel.created_at)).all()
            return [debt_to_dict(d, sale_number=sn) for d, sn in results]
    
    @router.get("/{debt_id}", response_model=dict)
    async def get_debt(debt_id: str, current_user: dict = Depends(get_current_user)):
        """Récupérer une dette par ID"""
        with get_session() as session:
            result = session.query(DebtModel, Sale.sale_number).outerjoin(
                Sale, DebtModel.sale_id == Sale.id
            ).filter(DebtModel.id == uuid.UUID(debt_id)).first()
            if not result:
                raise HTTPException(status_code=404, detail="Dette non trouvée")
            debt, sale_number = result
            return debt_to_dict(debt, sale_number=sale_number)
    
    @router.get("/{debt_id}/payments", response_model=List[dict])
    async def get_debt_payments(debt_id: str, current_user: dict = Depends(get_current_user)):
        """Récupérer l'historique des paiements d'une dette"""
        with get_session() as session:
            debt = session.query(DebtModel).filter(DebtModel.id == uuid.UUID(debt_id)).first()
            if not debt:
                raise HTTPException(status_code=404, detail="Dette non trouvée")
            return debt.payments or []
    
    @router.get("/customer/{customer_id}", response_model=List[dict])
    async def get_customer_debts(
        customer_id: str,
        current_user: dict = Depends(get_current_user),
        include_paid: bool = False
    ):
        """Récupérer les dettes d'un client"""
        with get_session() as session:
            query = session.query(DebtModel, Sale.sale_number).outerjoin(
                Sale, DebtModel.sale_id == Sale.id
            ).filter(DebtModel.customer_id == uuid.UUID(customer_id))
            
            if not include_paid:
                query = query.filter(DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL]))
            
            results = query.order_by(desc(DebtModel.created_at)).all()
            return [debt_to_dict(d, sale_number=sn) for d, sn in results]
    
    @router.get("/customer/{customer_id}/available-credit", response_model=dict)
    async def get_customer_available_credit(customer_id: str, current_user: dict = Depends(get_current_user)):
        """Vérifier le crédit disponible d'un client"""
        customer_repo = CustomerRepository()
        customer = customer_repo.get_by_id_str(customer_id)
        
        if not customer:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        max_limit = customer.get("max_debt_limit", 0)
        
        with get_session() as session:
            current_debt = session.query(func.sum(DebtModel.remaining_amount)).filter(
                DebtModel.customer_id == uuid.UUID(customer_id),
                DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL])
            ).scalar() or 0
        
        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name"),
            "max_debt_limit": max_limit,
            "current_debt": current_debt,
            "available_credit": max(0, max_limit - current_debt),
            "can_use_credit": max_limit > 0
        }
    
    @router.post("/payment", response_model=dict)
    async def create_debt_payment(
        payment_data: DebtPaymentCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Enregistrer un remboursement de dette"""
        with get_session() as session:
            debt = session.query(DebtModel).filter(DebtModel.id == uuid.UUID(payment_data.debt_id)).first()
            
            if not debt:
                raise HTTPException(status_code=404, detail="Dette non trouvée")
            
            if debt.status == DebtStatus.PAID:
                raise HTTPException(status_code=400, detail="Cette dette est déjà entièrement payée")
            
            if payment_data.amount <= 0:
                raise HTTPException(status_code=400, detail="Le montant doit être supérieur à 0")
            
            if payment_data.amount > debt.remaining_amount:
                raise HTTPException(status_code=400, detail=f"Le montant ne peut pas dépasser {debt.remaining_amount}")
            
            # Ajouter le paiement à l'historique
            payments = debt.payments or []
            new_payment = {
                "id": str(uuid.uuid4()),
                "amount": payment_data.amount,
                "payment_method": payment_data.payment_method,
                "notes": payment_data.notes,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user.get("employee_code", "N/A")
            }
            payments.append(new_payment)
            
            # Mettre à jour la dette
            new_remaining = debt.remaining_amount - payment_data.amount
            new_status = DebtStatus.PAID if new_remaining <= 0 else DebtStatus.PARTIAL
            
            debt.remaining_amount = max(0, new_remaining)
            debt.status = new_status
            debt.payments = payments
            
            session.commit()
            
            return {
                **new_payment,
                "debt_new_remaining": max(0, new_remaining),
                "debt_new_status": new_status.value
            }
    
    @router.post("/{debt_id}/write-off", response_model=dict)
    async def write_off_debt(
        debt_id: str,
        request: WriteOffRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """Abandonner/passer en perte une dette (Admin uniquement)"""
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=403, 
                detail="Seuls les administrateurs peuvent abandonner une dette"
            )
        
        with get_session() as session:
            debt = session.query(DebtModel).filter(DebtModel.id == uuid.UUID(debt_id)).first()
            
            if not debt:
                raise HTTPException(status_code=404, detail="Dette non trouvée")
            
            if debt.status == DebtStatus.WRITTEN_OFF:
                raise HTTPException(status_code=400, detail="Cette dette est déjà abandonnée")
            
            if debt.status == DebtStatus.PAID:
                raise HTTPException(status_code=400, detail="Cette dette est déjà payée")
            
            remaining_amount = debt.remaining_amount
            now = datetime.now(timezone.utc)
            
            debt.status = DebtStatus.WRITTEN_OFF
            debt.remaining_amount = 0
            debt.updated_at = now
            
            # Ajouter à l'historique
            payments = debt.payments or []
            payments.append({
                "id": str(uuid.uuid4()),
                "type": "write_off",
                "amount": remaining_amount,
                "reason": request.reason,
                "created_at": now.isoformat(),
                "created_by": current_user.get("employee_code", "N/A")
            })
            debt.payments = payments
            
            # IMPORTANT: Forcer SQLAlchemy à détecter le changement sur la colonne JSON
            flag_modified(debt, 'payments')
            
            session.commit()
            
            return {
                "success": True,
                "debt_id": debt_id,
                "written_off_amount": remaining_amount,
                "reason": request.reason,
                "message": f"Dette de {remaining_amount} abandonnée avec succès."
            }
    
    @router.post("/payment/bulk", response_model=dict)
    async def create_bulk_payment(
        request: BulkPaymentRequest,
        current_user: dict = Depends(require_open_shift)
    ):
        """Rembourser plusieurs dettes d'un client (FIFO)"""
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Le montant doit être supérieur à 0")
        
        with get_session() as session:
            debts = session.query(DebtModel).filter(
                DebtModel.customer_id == uuid.UUID(request.customer_id),
                DebtModel.status.in_([DebtStatus.PENDING, DebtStatus.PARTIAL])
            ).order_by(DebtModel.created_at).all()
            
            if not debts:
                raise HTTPException(status_code=404, detail="Aucune dette en cours pour ce client")
            
            remaining_payment = request.amount
            debts_updated = []
            
            for debt in debts:
                if remaining_payment <= 0:
                    break
                
                amount_to_apply = min(remaining_payment, debt.remaining_amount)
                
                # Ajouter le paiement
                payments = debt.payments or []
                payments.append({
                    "id": str(uuid.uuid4()),
                    "amount": amount_to_apply,
                    "payment_method": request.payment_method,
                    "notes": request.notes,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "created_by": current_user.get("employee_code", "N/A")
                })
                
                new_remaining = debt.remaining_amount - amount_to_apply
                new_status = DebtStatus.PAID if new_remaining <= 0 else DebtStatus.PARTIAL
                
                debt.remaining_amount = max(0, new_remaining)
                debt.status = new_status
                debt.payments = payments
                debt.updated_at = datetime.now(timezone.utc)
                
                # IMPORTANT: Forcer SQLAlchemy à détecter le changement sur la colonne JSON
                flag_modified(debt, 'payments')
                
                debts_updated.append({
                    "debt_id": str(debt.id),
                    "amount_applied": amount_to_apply,
                    "new_remaining": max(0, new_remaining),
                    "new_status": new_status.value
                })
                
                remaining_payment -= amount_to_apply
            
            session.commit()
            
            return {
                "total_applied": request.amount - remaining_payment,
                "remaining_from_payment": remaining_payment,
                "payments_created": len(debts_updated),
                "debts_updated": debts_updated
            }
    
    @router.get("/payments/history", response_model=List[dict])
    async def get_all_payments_history(
        current_user: dict = Depends(get_current_user),
        customer_id: Optional[str] = None,
        payment_method: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50
    ):
        """Récupérer l'historique de tous les remboursements"""
        from database.repositories import CustomerRepository, UserRepository
        
        with get_session() as session:
            query = session.query(DebtModel)
            
            if customer_id:
                try:
                    query = query.filter(DebtModel.customer_id == uuid.UUID(customer_id))
                except ValueError:
                    pass
            
            debts = query.order_by(desc(DebtModel.created_at)).limit(200).all()
            
            # Charger les clients et utilisateurs pour les noms
            customer_repo = CustomerRepository()
            user_repo = UserRepository()
            customers = {str(c['id']): c for c in customer_repo.get_all()}
            users = {str(u['id']): u for u in user_repo.get_all()}
            
            all_payments = []
            for debt in debts:
                customer = customers.get(str(debt.customer_id), {})
                
                for payment in (debt.payments or []):
                    # Normaliser les champs (certains paiements ont 'date'/'method' au lieu de 'created_at'/'payment_method')
                    payment_date = payment.get('created_at') or payment.get('date', '')
                    payment_method_val = payment.get('payment_method') or payment.get('method', 'cash')
                    
                    # Filtrer par méthode de paiement
                    if payment_method and payment_method_val != payment_method:
                        continue
                    
                    # Filtrer par date
                    if date_from and payment_date and payment_date < date_from:
                        continue
                    if date_to and payment_date and payment_date > date_to:
                        continue
                    
                    payment_copy = {
                        'id': payment.get('id', str(uuid.uuid4())),
                        'debt_id': str(debt.id),
                        'customer_id': str(debt.customer_id) if debt.customer_id else None,
                        'customer_name': customer.get('name', 'Client inconnu'),
                        'amount': payment.get('amount', 0),
                        'payment_method': payment_method_val,
                        'payment_details': payment.get('payment_details') or payment.get('details', {}),
                        'notes': payment.get('notes', ''),
                        'created_at': payment_date,
                        'transaction_type': payment.get('transaction_type', 'payment'),
                    }
                    
                    # Chercher le nom de l'utilisateur qui a créé le paiement
                    created_by_id = payment.get('created_by') or payment.get('user_id')
                    agent_code = payment.get('agent_code', '')
                    if created_by_id:
                        user = users.get(str(created_by_id), {})
                        payment_copy['created_by_name'] = user.get('name', agent_code or 'Utilisateur inconnu')
                    elif agent_code:
                        # Chercher l'utilisateur par employee_code
                        user_by_code = next((u for u in users.values() if u.get('employee_code') == agent_code), None)
                        payment_copy['created_by_name'] = user_by_code.get('name', agent_code) if user_by_code else agent_code
                    else:
                        payment_copy['created_by_name'] = '-'
                    
                    all_payments.append(payment_copy)
            
            all_payments.sort(key=lambda x: x.get('created_at', '') or '', reverse=True)
            return all_payments[:limit]
    
    async def create_debt_from_sale(
        customer_id: str,
        customer_name: str,
        sale_id: str,
        sale_number: str,
        amount: float,
        tenant_id: str,
        created_by: str,
        notes: Optional[str] = None
    ) -> Debt:
        """Créer une dette à partir d'une vente"""
        from database.repositories import SettingsRepository
        
        # Récupérer le paramètre debt_overdue_days depuis les settings
        settings_repo = SettingsRepository()
        settings = settings_repo.get_all()
        debt_overdue_days = settings.get('debt_overdue_days', 90)  # Par défaut 90 jours
        
        # Calculer la date d'échéance automatiquement
        now = datetime.now(timezone.utc)
        due_date = (now + relativedelta(days=debt_overdue_days)).date()
        
        with get_session() as session:
            debt = DebtModel(
                id=uuid.uuid4(),
                customer_id=uuid.UUID(customer_id),
                sale_id=uuid.UUID(sale_id) if sale_id else None,
                original_amount=amount,
                remaining_amount=amount,
                status=DebtStatus.PENDING,
                due_date=due_date,  # Date d'échéance automatique
                notes=notes or f"Dette créée depuis la vente {sale_number}",
                payments=[],
                created_at=now
            )
            session.add(debt)
            session.commit()
            
            return Debt(
                id=str(debt.id),
                customer_id=customer_id,
                customer_name=customer_name,
                sale_id=sale_id,
                sale_number=sale_number,
                original_amount=amount,
                remaining_amount=amount,
                status="pending",
                due_date=due_date.isoformat(),
                notes=notes,
                tenant_id=tenant_id
            )

