"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from auth import require_role, get_current_user
from models.shift import Shift, ShiftOpen, ShiftClose, ShiftSummary
import os
import uuid

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")
from database.tenant_context import get_current_tenant


router = APIRouter(prefix="/shifts", tags=["Shifts"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories_extended import ShiftRepository
    from database.repositories import SettingsRepository, UserRepository
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Shift as ShiftModel
    from sqlalchemy import desc, func
    
    def get_session():
        return db_manager.get_tenant_session(get_current_tenant())

    def compute_shift_totals(session, shift: dict) -> dict:
        """Mouvements de caisse d'un shift : ventes encaissées (hors part crédit), remboursements de dettes, retours."""
        from database.models_tenant import Sale as SaleModel, SaleStatus, SaleReturn, Debt as DebtModel
        started_at = shift.get('started_at')
        ended_at = shift.get('ended_at')
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        if isinstance(ended_at, str):
            ended_at = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
        end = ended_at or datetime.now(timezone.utc)
        shift_uuid = uuid.UUID(str(shift['id']))
        agent_code = shift.get('employee_code')

        sales = session.query(SaleModel).filter(
            SaleModel.shift_id == shift_uuid, SaleModel.status != SaleStatus.CANCELLED
        ).all()
        total_sales = sum(float(s.total or 0) for s in sales)
        sale_ids = [s.id for s in sales]
        credit_part = 0.0
        if sale_ids:
            credit_part = float(session.query(func.coalesce(func.sum(DebtModel.original_amount), 0)).filter(
                DebtModel.sale_id.in_(sale_ids)
            ).scalar() or 0)
        cash_in_sales = total_sales - credit_part

        debt_payments = 0.0
        debt_payments_count = 0
        if agent_code and started_at:
            for (payments,) in session.query(DebtModel.payments).filter(DebtModel.payments != None).all():
                for p in payments or []:
                    if p.get('created_by') != agent_code or not p.get('created_at'):
                        continue
                    try:
                        at = datetime.fromisoformat(str(p['created_at']).replace('Z', '+00:00'))
                    except ValueError:
                        continue
                    if at.tzinfo is None:
                        at = at.replace(tzinfo=timezone.utc)
                    if started_at <= at <= end:
                        debt_payments += float(p.get('amount') or 0)
                        debt_payments_count += 1

        returns_q = session.query(SaleReturn).filter(SaleReturn.status == "completed")
        if started_at:
            returns_q = returns_q.filter(SaleReturn.created_at >= started_at, SaleReturn.created_at <= end)
        if agent_code:
            returns_q = returns_q.filter(SaleReturn.agent_code == agent_code)
        returns = returns_q.all()
        returns_refunds = sum(float(r.total_refund or 0) for r in returns)

        opening = float(shift.get('opening_amount') or 0)
        return {
            "total_sales_count": len(sales),
            "total_sales_amount": total_sales,
            "total_credit_sales": credit_part,
            "total_cash_sales": cash_in_sales,
            "debt_payments_amount": debt_payments,
            "debt_payments_count": debt_payments_count,
            "returns_refunds_amount": returns_refunds,
            "returns_count": len(returns),
            "expected_closing_amount": opening + cash_in_sales + debt_payments - returns_refunds,
        }
    
    @router.get("/paginated")
    def get_shifts_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None, description="all, completed, active, discrepancy"),
        user_id: Optional[str] = Query(default=None, description="Filtrer par utilisateur"),
        start_date: Optional[str] = Query(default=None, description="Date début (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(default=None, description="Date fin (YYYY-MM-DD)"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des shifts avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(ShiftModel)
            
            # Filtrer par statut
            if status == 'active' or status == 'open':
                query = query.filter(ShiftModel.is_active == True)
            elif status == 'completed' or status == 'closed':
                query = query.filter(ShiftModel.is_active == False)
            elif status == 'discrepancy':
                # Shifts avec écart (closing_amount != expected_amount)
                query = query.filter(
                    ShiftModel.is_active == False,
                    ShiftModel.closing_amount != None,
                    ShiftModel.expected_amount != None,
                    ShiftModel.closing_amount != ShiftModel.expected_amount
                )
            
            # Filtrer par utilisateur (caissier)
            if user_id and user_id.strip():
                try:
                    query = query.filter(ShiftModel.user_id == uuid.UUID(user_id))
                except ValueError:
                    pass  # ID invalide, ignorer le filtre
            
            # Filtrer par date de début
            if start_date and start_date.strip():
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    query = query.filter(ShiftModel.started_at >= start_dt)
                except ValueError:
                    pass  # Date invalide, ignorer le filtre
            
            # Filtrer par date de fin
            if end_date and end_date.strip():
                try:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    # Ajouter 1 jour pour inclure toute la journée de fin
                    end_dt = end_dt + timedelta(days=1)
                    query = query.filter(ShiftModel.started_at < end_dt)
                except ValueError:
                    pass  # Date invalide, ignorer le filtre
            
            total = query.count()
            query = query.order_by(desc(ShiftModel.started_at))
            
            offset = (page - 1) * limit
            shifts_orm = query.offset(offset).limit(limit).all()
            
            # Charger les noms des utilisateurs
            user_repo = UserRepository()
            users = {str(u['id']): u for u in user_repo.get_all()}
            
            shifts = []
            with get_session() as sess:
                for s in shifts_orm:
                    user = users.get(str(s.user_id), {})
                    totals = compute_shift_totals(sess, {
                        "id": s.id, "started_at": s.started_at, "ended_at": s.ended_at,
                        "opening_amount": s.opening_amount, "employee_code": user.get('employee_code'),
                    })
                    # Calculer la différence si le shift est fermé
                    difference = None
                    if s.closing_amount is not None and s.expected_amount is not None:
                        difference = s.closing_amount - s.expected_amount
                    
                    # Calculer la durée du shift
                    duration_minutes = None
                    if s.started_at and s.ended_at:
                        duration_minutes = int((s.ended_at - s.started_at).total_seconds() / 60)
                    elif s.started_at and s.is_active:
                        duration_minutes = int((datetime.now(timezone.utc) - s.started_at).total_seconds() / 60)
                    
                    shifts.append({
                        **totals,
                        "expected_closing_amount": float(s.expected_amount) if s.expected_amount is not None else totals["expected_closing_amount"],
                        "actual_closing_amount": float(s.closing_amount) if s.closing_amount is not None else None,
                        "has_discrepancy": difference is not None and abs(difference) > 0.01,
                        "id": str(s.id),
                        "user_id": str(s.user_id) if s.user_id else None,
                        "user_name": user.get('name', 'Utilisateur inconnu'),
                        "employee_code": user.get('employee_code', 'N/A'),
                        "opening_amount": float(s.opening_amount or 0),
                        "closing_amount": float(s.closing_amount or 0) if s.closing_amount else None,
                        "expected_amount": float(s.expected_amount or 0) if s.expected_amount else None,
                        "difference": difference,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                        # Alias pour le frontend
                        "closed_at": s.ended_at.isoformat() if s.ended_at else None,
                        "expected_end_time": s.expires_at.isoformat() if s.expires_at else None,
                        "opened_at": s.started_at.isoformat() if s.started_at else None,
                        "duration_minutes": duration_minutes,
                        "is_active": s.is_active,
                        "status": 'open' if s.is_active else 'closed',
                        "tenant_id": get_current_tenant(),
                    })
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": shifts,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.get("/current")
    def get_current_shift(current_user: dict = Depends(get_current_user)):
        """Récupérer le shift ouvert de l'utilisateur actuel."""
        repo = ShiftRepository()
        user_id = current_user['user_id']
        shift = repo.get_active_by_user_str(user_id)
        
        if shift:
            # Normaliser les champs pour le frontend
            shift['expected_end_time'] = shift.get('expires_at')
            shift['opened_at'] = shift.get('started_at')
            shift['user_name'] = current_user.get('name', 'Unknown')
            shift['user_code'] = current_user.get('employee_code', 'N/A')
            shift['employee_code'] = current_user.get('employee_code', 'N/A')
            shift['status'] = 'open' if shift.get('is_active') else 'closed'
        
        return shift
    
    @router.post("/open")
    def open_shift(data: ShiftOpen, current_user: dict = Depends(get_current_user)):
        """Ouvrir un nouveau shift de caisse."""
        repo = ShiftRepository()
        settings_repo = SettingsRepository()
        user_id = current_user['user_id']
        
        # Vérifier qu'aucun shift n'est déjà ouvert
        existing = repo.get_active_by_user_str(user_id)
        if existing:
            raise HTTPException(status_code=400, detail="Vous avez déjà un shift ouvert")
        
        # Calculer l'heure de fin prévue
        now = datetime.now(timezone.utc)
        default_duration = settings_repo.get("shift_max_duration", 8)
        expected_end = now + timedelta(hours=default_duration)
        
        # Utiliser expected_end_time si fourni (convertir si c'est une chaîne)
        if data.expected_end_time:
            if isinstance(data.expected_end_time, str):
                try:
                    # Essayer de parser comme ISO format
                    expected_end = datetime.fromisoformat(data.expected_end_time.replace('Z', '+00:00'))
                except ValueError:
                    # Si c'est au format HH:MM, calculer la date/heure
                    try:
                        hour, minute = map(int, data.expected_end_time.split(':'))
                        expected_end = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if expected_end <= now:
                            expected_end += timedelta(days=1)
                    except Exception:
                        pass  # Garder la valeur par défaut
            else:
                expected_end = data.expected_end_time
        
        shift_data = {
            "user_id": user_id,
            "opening_amount": data.opening_amount,
            "started_at": now,
            "expires_at": expected_end,
        }
        
        result = repo.create(shift_data)
        
        # Normaliser les champs pour le frontend
        result['expected_end_time'] = result.get('expires_at')
        result['opened_at'] = result.get('started_at')
        result['user_name'] = current_user.get('name', 'Unknown')
        result['user_code'] = current_user.get('employee_code', 'N/A')
        result['employee_code'] = current_user.get('employee_code', 'N/A')
        result['status'] = 'open'
        
        return result
    
    @router.post("/close")
    def close_shift(data: ShiftClose, current_user: dict = Depends(get_current_user)):
        """Fermer le shift actuel."""
        repo = ShiftRepository()
        user_id = current_user['user_id']
        
        # Trouver le shift ouvert
        shift = repo.get_active_by_user_str(user_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Aucun shift ouvert trouvé")
        
        # Montant attendu = fond de caisse + ventes encaissées (hors crédit) + remboursements dettes - retours
        opening_amount = float(shift.get('opening_amount', 0))
        shift_for_totals = {**shift, "employee_code": current_user.get('employee_code')}
        with get_session() as session:
            totals = compute_shift_totals(session, shift_for_totals)
        total_cash_sales = totals["total_cash_sales"]
        expected_amount = totals["expected_closing_amount"]
        
        closing_data = {
            "closing_amount": data.actual_closing_amount,
            "expected_amount": expected_amount,
            "closing_notes": data.closing_notes,
        }
        
        result = repo.close_by_id_str(shift['id'], closing_data)
        if not result:
            raise HTTPException(status_code=500, detail="Erreur lors de la fermeture du shift")
        
        # Calculer la différence
        difference = data.actual_closing_amount - expected_amount
        
        return {
            **result,
            "status": "closed",
            "expected_amount": expected_amount,
            "difference": difference,
            "difference_percentage": round((difference / expected_amount * 100), 2) if expected_amount else 0,
        }
    
    @router.post("/extend")
    def extend_shift(extension_minutes: int = 60, current_user: dict = Depends(get_current_user)):
        """Prolonger le shift actuel."""
        repo = ShiftRepository()
        user_id = current_user['user_id']
        
        shift = repo.get_active_by_user_str(user_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Aucun shift ouvert trouvé")
        
        # Calculer la nouvelle heure de fin
        current_expires = shift.get('expires_at')
        if current_expires:
            if isinstance(current_expires, str):
                current_expires = datetime.fromisoformat(current_expires.replace('Z', '+00:00'))
        else:
            current_expires = datetime.now(timezone.utc)
        
        new_expires = current_expires + timedelta(minutes=extension_minutes)
        
        result = repo.extend_by_id_str(shift['id'], new_expires)
        if not result:
            raise HTTPException(status_code=500, detail="Erreur lors de la prolongation")
        
        # Récupérer le nom de l'utilisateur
        user_repo = UserRepository()
        user = user_repo.get_by_id_str(user_id)
        user_name = user.get('name', 'Inconnu') if user else 'Inconnu'
        
        return {
            **result,
            "message": f"Shift prolongé de {extension_minutes} minutes",
            "new_expected_end_time": new_expires.isoformat(),
            "extension_minutes": extension_minutes,
            "user_name": user_name
        }
    
    @router.post("/{shift_id}/extend")
    def extend_shift_by_id(
        shift_id: str,
        extension_minutes: int = 60, 
        current_user: dict = Depends(get_current_user)
    ):
        """Prolonger un shift spécifique par son ID (pour admin)."""
        # Vérifier que l'utilisateur est admin
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Seuls les administrateurs peuvent prolonger les shifts d'autres utilisateurs")
        
        repo = ShiftRepository()
        
        shift = repo.get_by_id_str(shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift non trouvé")
        
        if not shift.get('is_active'):
            raise HTTPException(status_code=400, detail="Ce shift est déjà clôturé")
        
        # Calculer la nouvelle heure de fin
        current_expires = shift.get('expires_at')
        if current_expires:
            if isinstance(current_expires, str):
                current_expires = datetime.fromisoformat(current_expires.replace('Z', '+00:00'))
        else:
            current_expires = datetime.now(timezone.utc)
        
        new_expires = current_expires + timedelta(minutes=extension_minutes)
        
        result = repo.extend_by_id_str(shift_id, new_expires)
        if not result:
            raise HTTPException(status_code=500, detail="Erreur lors de la prolongation")
        
        # Récupérer le nom de l'utilisateur du shift
        user_repo = UserRepository()
        user = user_repo.get_by_id_str(shift.get('user_id'))
        user_name = user.get('name', 'Inconnu') if user else 'Inconnu'
        
        return {
            **result,
            "message": f"Shift prolongé de {extension_minutes} minutes",
            "new_expected_end_time": new_expires.isoformat(),
            "extension_minutes": extension_minutes,
            "user_name": user_name
        }
    
    @router.get("/details/{shift_id}")
    def get_shift_details(shift_id: str, current_user: dict = Depends(get_current_user)):
        """Récupérer les détails complets d'un shift avec calculs."""
        from database.repositories_extended import SaleRepository
        
        repo = ShiftRepository()
        user_repo = UserRepository()
        sale_repo = SaleRepository()
        
        shift = repo.get_by_id_str(shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift non trouvé")
        
        # Récupérer les infos utilisateur
        user = user_repo.get_by_id_str(shift.get('user_id'))
        user_name = user.get('name', 'Inconnu') if user else 'Inconnu'
        employee_code = user.get('employee_code', 'N/A') if user else 'N/A'
        
        with get_session() as session:
            totals = compute_shift_totals(session, {**shift, "employee_code": employee_code})
        total_cash_sales = totals["total_cash_sales"]
        total_sales_count = totals["total_sales_count"]
        
        # Calculer les montants
        opening_amount = float(shift.get('opening_amount', 0))
        closing_amount = float(shift.get('closing_amount') or 0) if shift.get('closing_amount') else None
        expected_amount = float(shift.get('expected_amount') or 0) if shift.get('expected_amount') else None
        
        expected_closing_amount = totals["expected_closing_amount"]
        actual_closing_amount = closing_amount
        
        # Calculer l'écart
        difference = 0
        has_discrepancy = False
        if actual_closing_amount is not None and expected_amount is not None:
            difference = actual_closing_amount - expected_amount
            has_discrepancy = abs(difference) > 0.01
        
        return {
            "id": shift_id,
            "user_id": shift.get('user_id'),
            "user_name": user_name,
            "employee_code": employee_code,
            "opened_at": shift.get('started_at'),
            "closed_at": shift.get('ended_at'),
            "expected_end_time": shift.get('expires_at'),
            "opening_amount": opening_amount,
            "closing_amount": closing_amount,
            "expected_amount": expected_amount,
            **totals,
            "expected_closing_amount": expected_closing_amount,
            "actual_closing_amount": actual_closing_amount,
            "difference": difference,
            "has_discrepancy": has_discrepancy,
            "is_active": shift.get('is_active', False),
            "notes": shift.get('notes'),
            "closing_notes": shift.get('closing_notes')
        }
    
    @router.get("/summary/{shift_id}")
    def get_shift_summary(shift_id: str, current_user: dict = Depends(get_current_user)):
        """Récupérer le résumé d'un shift."""
        repo = ShiftRepository()
        
        shift = repo.get_by_id_str(shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift non trouvé")
        
        # Pour PostgreSQL, résumé simplifié
        return {
            "shift": shift,
            "sales_summary": {
                "total_count": 0,
                "total_amount": 0,
                "by_payment_method": {}
            }
        }
    
    @router.get("/history")
    def get_shift_history(
        days: int = 30,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Récupérer l'historique des shifts (Admin)."""
        repo = ShiftRepository()
        
        from services.tz_service import now_local
        end_date = now_local().date()
        start_date = end_date - timedelta(days=days)
        
        shifts = repo.get_by_date_range(start_date, end_date)
        return shifts
    
    @router.get("/all-open")
    def get_all_open_shifts(current_user: dict = Depends(require_role(["admin"]))):
        """Récupérer tous les shifts ouverts (Admin)."""
        repo = ShiftRepository()
        return repo.get_all_active()
    
    @router.get("/calculate-expected")
    def calculate_expected_closing(current_user: dict = Depends(get_current_user)):
        """Calculer le montant attendu en caisse pour la clôture du shift."""
        repo = ShiftRepository()
        user_id = current_user['user_id']
        
        # Trouver le shift ouvert
        shift = repo.get_active_by_user_str(user_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Aucun shift ouvert trouvé")
        
        shift_id = shift.get('id')
        opening_amount = float(shift.get('opening_amount', 0))
        with get_session() as session:
            totals = compute_shift_totals(session, {**shift, "employee_code": current_user.get('employee_code')})
        expected_closing_amount = totals["expected_closing_amount"]
        
        return {
            "opening_amount": opening_amount,
            **totals,
            "expected_closing_amount": expected_closing_amount,
            "shift_id": str(shift_id),
            "shift_started_at": shift.get('started_at')
        }

    @router.get("/stats")
    def get_shifts_stats(
        period: str = Query(default="week", description="day, week, month"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les statistiques des shifts"""
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        
        if period == "day":
            start_date = now - timedelta(days=1)
        elif period == "month":
            start_date = now - timedelta(days=30)
        else:  # week par défaut
            start_date = now - timedelta(weeks=1)
        
        with get_session() as session:
            shifts = session.query(ShiftModel).filter(
                ShiftModel.started_at >= start_date
            ).all()
            
            total_shifts = len(shifts)
            completed_shifts = sum(1 for s in shifts if not s.is_active)
            active_shifts = sum(1 for s in shifts if s.is_active)
            
            total_opening = sum(float(s.opening_amount or 0) for s in shifts)
            total_closing = sum(float(s.closing_amount or 0) for s in shifts if s.closing_amount)
            
            # Calculer les écarts
            total_positive_diff = 0  # Excédents
            total_negative_diff = 0  # Déficits
            total_discrepancies = 0  # Nombre de shifts avec écart
            
            for s in shifts:
                if s.closing_amount is not None and s.expected_amount is not None:
                    diff = float(s.closing_amount) - float(s.expected_amount)
                    if diff > 0:
                        total_positive_diff += diff
                        total_discrepancies += 1
                    elif diff < 0:
                        total_negative_diff += diff
                        total_discrepancies += 1
            
            total_difference = total_positive_diff + total_negative_diff
            
            # Taux d'écart = pourcentage de shifts avec écart parmi les shifts complétés
            discrepancy_rate = round((total_discrepancies / completed_shifts * 100) if completed_shifts > 0 else 0, 1)
            
            return {
                "period": period,
                "total_shifts": total_shifts,
                "completed_shifts": completed_shifts,
                "active_shifts": active_shifts,
                "total_opening_amount": total_opening,
                "total_closing_amount": total_closing,
                "total_difference": total_difference,
                "average_difference": total_difference / completed_shifts if completed_shifts > 0 else 0,
                # Nouvelles statistiques d'écart
                "total_discrepancies": total_discrepancies,
                "discrepancy_rate": discrepancy_rate,
                "total_positive_diff": total_positive_diff,
                "total_negative_diff": abs(total_negative_diff)  # Valeur absolue pour affichage
            }
    
    @router.get("/active")
    def get_active_shifts(current_user: dict = Depends(get_current_user)):
        """Récupérer tous les shifts actuellement actifs"""
        repo = ShiftRepository()
        active_shifts = repo.get_all_active()
        
        # Enrichir avec les noms des utilisateurs et ajouter les alias
        user_repo = UserRepository()
        users = {str(u['id']): u for u in user_repo.get_all()}
        
        for shift in active_shifts:
            user = users.get(str(shift.get('user_id')), {})
            shift['user_name'] = user.get('name', 'Utilisateur inconnu')
            shift['employee_code'] = user.get('employee_code', 'N/A')
            # Ajouter les alias pour le frontend
            shift['opened_at'] = shift.get('started_at')
            shift['closed_at'] = shift.get('ended_at')
            shift['expected_end_time'] = shift.get('expires_at')
        
        return active_shifts
    
    @router.patch("/mark-alert/{alert_type}")
    def mark_alert_shown(
        alert_type: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Marquer une alerte de shift comme affichée (pour éviter les répétitions)"""
        valid_types = ["30min", "5min", "end"]
        if alert_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Type d'alerte invalide. Valeurs acceptées: {valid_types}")
        
        user_id = current_user.get("id") or current_user.get("user_id")
        
        with get_session() as session:
            # Trouver le shift actif de l'utilisateur
            import uuid
            shift = session.query(ShiftModel).filter(
                ShiftModel.user_id == uuid.UUID(user_id),
                ShiftModel.is_active == True
            ).first()
            
            if shift:
                # Mettre à jour le flag correspondant
                if alert_type == "30min":
                    shift.alert_30min_shown = True
                elif alert_type == "5min":
                    shift.alert_5min_shown = True
                elif alert_type == "end":
                    shift.alert_end_shown = True
                
                session.commit()
        
        return {
            "alert_type": alert_type,
            "marked": True,
            "message": f"Alerte '{alert_type}' marquée comme affichée"
        }

    @router.delete("/{shift_id}")
    def delete_shift(
        shift_id: str,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Supprimer un shift (Admin uniquement)."""
        repo = ShiftRepository()
        
        # Vérifier que le shift existe
        shift = repo.get_by_id_str(shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift non trouvé")
        
        # Empêcher la suppression d'un shift actif
        if shift.get('is_active'):
            raise HTTPException(status_code=400, detail="Impossible de supprimer un shift actif. Clôturez-le d'abord.")
        
        # Supprimer le shift
        try:
            with get_session() as session:
                shift_obj = session.query(ShiftModel).filter(
                    ShiftModel.id == uuid.UUID(shift_id)
                ).first()
                
                if shift_obj:
                    session.delete(shift_obj)
                    session.commit()
                    return {"success": True, "message": "Shift supprimé avec succès", "id": shift_id}
                else:
                    raise HTTPException(status_code=404, detail="Shift non trouvé")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

