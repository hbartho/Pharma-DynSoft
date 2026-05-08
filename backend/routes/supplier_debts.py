"""
Routes pour la gestion des dettes fournisseurs.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date, timezone, timedelta
from database.config import db_manager
from database.models_tenant import SupplierDebt, Supplier, Supply, DebtStatus
from auth import get_current_user, require_admin, require_role
import uuid

router = APIRouter(prefix="/api/supplier-debts", tags=["Supplier Debts"])


# ============== Pydantic Models ==============

class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Montant du paiement")
    method: str = Field(default="cash", description="Mode de paiement: cash, transfer, check")
    reference: Optional[str] = Field(None, description="Référence (n° chèque, virement)")
    notes: Optional[str] = None


class WriteOffCreate(BaseModel):
    reason: str = Field(..., description="Raison de l'abandon")
    notes: Optional[str] = None


class SupplierDebtResponse(BaseModel):
    id: str
    supplier_id: str
    supplier_name: str
    supply_id: Optional[str]
    supply_number: Optional[str]
    original_amount: float
    remaining_amount: float
    paid_amount: float
    status: str
    due_date: Optional[date]
    is_overdue: bool
    days_overdue: int
    payments: List[dict]
    notes: Optional[str]
    created_at: datetime


# ============== Helper Functions ==============

def debt_to_dict(debt: SupplierDebt, session) -> dict:
    """Convertit une dette fournisseur en dictionnaire."""
    supplier = session.query(Supplier).filter(Supplier.id == debt.supplier_id).first()
    supply = session.query(Supply).filter(Supply.id == debt.supply_id).first() if debt.supply_id else None
    
    today = date.today()
    is_overdue = False
    days_overdue = 0
    
    if debt.due_date and debt.remaining_amount > 0:
        if debt.due_date < today:
            is_overdue = True
            days_overdue = (today - debt.due_date).days
    
    # Marquer comme en retard si > 90 jours (3 mois)
    status = debt.status.value if debt.status else "pending"
    if is_overdue and days_overdue > 90 and status not in ["paid", "written_off"]:
        status = "overdue"
    
    paid_amount = debt.original_amount - debt.remaining_amount
    
    return {
        "id": str(debt.id),
        "supplier_id": str(debt.supplier_id),
        "supplier_name": supplier.name if supplier else "Inconnu",
        "supply_id": str(debt.supply_id) if debt.supply_id else None,
        "supply_number": supply.supply_number if supply else None,
        "invoice_number": supply.invoice_number if supply else None,
        "original_amount": debt.original_amount,
        "remaining_amount": debt.remaining_amount,
        "paid_amount": paid_amount,
        "status": status,
        "due_date": debt.due_date.isoformat() if debt.due_date else None,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "payments": debt.payments or [],
        "notes": debt.notes,
        "created_at": debt.created_at.isoformat() if debt.created_at else None,
    }


# ============== Routes ==============

@router.get("")
async def get_supplier_debts(
    status: Optional[str] = None,
    supplier_id: Optional[str] = None,
    overdue_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(require_admin)
):
    """
    Liste toutes les dettes fournisseurs.
    Admin uniquement.
    """
    with db_manager.get_tenant_session('default') as session:
        query = session.query(SupplierDebt)
        
        # Filtres
        if status:
            if status == "overdue":
                # Dettes en retard (> 90 jours)
                cutoff_date = date.today() - timedelta(days=90)
                query = query.filter(
                    SupplierDebt.due_date < cutoff_date,
                    SupplierDebt.status.notin_([DebtStatus.PAID, DebtStatus.WRITTEN_OFF])
                )
            else:
                query = query.filter(SupplierDebt.status == status)
        
        if supplier_id:
            query = query.filter(SupplierDebt.supplier_id == uuid.UUID(supplier_id))
        
        if overdue_only:
            today = date.today()
            query = query.filter(
                SupplierDebt.due_date < today,
                SupplierDebt.status.notin_([DebtStatus.PAID, DebtStatus.WRITTEN_OFF])
            )
        
        # Tri par date d'échéance (plus anciennes d'abord)
        query = query.order_by(SupplierDebt.due_date.asc().nullslast())
        
        total = query.count()
        debts = query.offset(skip).limit(limit).all()
        
        # Statistiques
        all_debts = session.query(SupplierDebt).filter(
            SupplierDebt.status.notin_([DebtStatus.PAID, DebtStatus.WRITTEN_OFF])
        ).all()
        
        total_debt = sum(d.remaining_amount for d in all_debts)
        
        today = date.today()
        cutoff_90_days = today - timedelta(days=90)
        overdue_debts = [d for d in all_debts if d.due_date and d.due_date < cutoff_90_days]
        total_overdue = sum(d.remaining_amount for d in overdue_debts)
        
        return {
            "items": [debt_to_dict(d, session) for d in debts],
            "total": total,
            "skip": skip,
            "limit": limit,
            "stats": {
                "total_debt": total_debt,
                "total_overdue": total_overdue,
                "overdue_count": len(overdue_debts),
            }
        }


@router.get("/{debt_id}")
async def get_supplier_debt(
    debt_id: str,
    current_user: dict = Depends(require_admin)
):
    """Récupère une dette fournisseur par ID."""
    with db_manager.get_tenant_session('default') as session:
        debt = session.query(SupplierDebt).filter(SupplierDebt.id == uuid.UUID(debt_id)).first()
        if not debt:
            raise HTTPException(status_code=404, detail="Dette non trouvée")
        return debt_to_dict(debt, session)


@router.post("/{debt_id}/payment")
async def record_payment(
    debt_id: str,
    payment: PaymentCreate,
    current_user: dict = Depends(require_admin)
):
    """
    Enregistre un paiement sur une dette fournisseur.
    Admin uniquement.
    """
    with db_manager.get_tenant_session('default') as session:
        debt = session.query(SupplierDebt).filter(SupplierDebt.id == uuid.UUID(debt_id)).first()
        if not debt:
            raise HTTPException(status_code=404, detail="Dette non trouvée")
        
        if debt.status in [DebtStatus.PAID, DebtStatus.WRITTEN_OFF]:
            raise HTTPException(status_code=400, detail="Cette dette est déjà soldée ou abandonnée")
        
        if payment.amount > debt.remaining_amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Le montant ({payment.amount}) dépasse le restant dû ({debt.remaining_amount})"
            )
        
        # Créer l'entrée de paiement
        payment_entry = {
            "date": datetime.now(timezone.utc).isoformat(),
            "amount": payment.amount,
            "method": payment.method,
            "reference": payment.reference,
            "notes": payment.notes,
            "recorded_by": current_user.get('employee_code', current_user.get('user_id'))
        }
        
        # Mettre à jour la dette
        payments_list = list(debt.payments or [])
        payments_list.append(payment_entry)
        debt.payments = payments_list
        debt.remaining_amount = round(debt.remaining_amount - payment.amount, 2)
        
        # Mettre à jour le statut
        if debt.remaining_amount <= 0:
            debt.status = DebtStatus.PAID
            debt.remaining_amount = 0
        else:
            debt.status = DebtStatus.PARTIAL
        
        debt.updated_at = datetime.now(timezone.utc)
        session.commit()
        
        return {
            "message": "Paiement enregistré",
            "debt": debt_to_dict(debt, session)
        }


@router.post("/{debt_id}/write-off")
async def write_off_debt(
    debt_id: str,
    data: WriteOffCreate,
    current_user: dict = Depends(require_admin)
):
    """
    Abandonne une dette fournisseur.
    Admin uniquement.
    """
    with db_manager.get_tenant_session('default') as session:
        debt = session.query(SupplierDebt).filter(SupplierDebt.id == uuid.UUID(debt_id)).first()
        if not debt:
            raise HTTPException(status_code=404, detail="Dette non trouvée")
        
        if debt.status in [DebtStatus.PAID, DebtStatus.WRITTEN_OFF]:
            raise HTTPException(status_code=400, detail="Cette dette est déjà soldée ou abandonnée")
        
        # Enregistrer l'abandon
        write_off_entry = {
            "date": datetime.now(timezone.utc).isoformat(),
            "type": "write_off",
            "amount": debt.remaining_amount,
            "reason": data.reason,
            "notes": data.notes,
            "recorded_by": current_user.get('employee_code', current_user.get('user_id'))
        }
        
        payments_list = list(debt.payments or [])
        payments_list.append(write_off_entry)
        debt.payments = payments_list
        
        # Mettre à jour le statut
        debt.status = DebtStatus.WRITTEN_OFF
        debt.notes = f"{debt.notes or ''}\n[ABANDON] {data.reason}".strip()
        debt.updated_at = datetime.now(timezone.utc)
        
        session.commit()
        
        return {
            "message": "Dette abandonnée",
            "debt": debt_to_dict(debt, session)
        }


@router.get("/by-supplier/{supplier_id}")
async def get_debts_by_supplier(
    supplier_id: str,
    current_user: dict = Depends(require_admin)
):
    """Récupère toutes les dettes d'un fournisseur."""
    with db_manager.get_tenant_session('default') as session:
        supplier = session.query(Supplier).filter(Supplier.id == uuid.UUID(supplier_id)).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        
        debts = session.query(SupplierDebt).filter(
            SupplierDebt.supplier_id == uuid.UUID(supplier_id)
        ).order_by(SupplierDebt.created_at.desc()).all()
        
        total_remaining = sum(d.remaining_amount for d in debts if d.status not in [DebtStatus.PAID, DebtStatus.WRITTEN_OFF])
        
        return {
            "supplier": {
                "id": str(supplier.id),
                "name": supplier.name,
            },
            "debts": [debt_to_dict(d, session) for d in debts],
            "total_remaining": total_remaining
        }
