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

router = APIRouter(prefix="/shifts", tags=["Shifts"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories_extended import ShiftRepository
    from database.repositories import SettingsRepository, UserRepository
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Shift as ShiftModel
    from sqlalchemy import desc, or_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    @router.get("/paginated")
    async def get_shifts_paginated(
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
            for s in shifts_orm:
                user = users.get(str(s.user_id), {})
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
                    "tenant_id": "pharmacie_centrale",
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
    async def get_current_shift(current_user: dict = Depends(get_current_user)):
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
    async def open_shift(data: ShiftOpen, current_user: dict = Depends(get_current_user)):
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
                    except:
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
    async def close_shift(data: ShiftClose, current_user: dict = Depends(get_current_user)):
        """Fermer le shift actuel."""
        repo = ShiftRepository()
        user_id = current_user['user_id']
        
        # Trouver le shift ouvert
        shift = repo.get_active_by_user_str(user_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Aucun shift ouvert trouvé")
        
        # Calculer le montant attendu en utilisant l'endpoint calculate-expected
        opening_amount = float(shift.get('opening_amount', 0))
        
        # Calculer les ventes espèces du shift
        total_cash_sales = 0
        shift_id = shift.get('id')
        
        try:
            with get_session() as session:
                from database.models_tenant import Sale as SaleModel
                
                # Essayer de filtrer par shift_id
                sales = session.query(SaleModel).filter(
                    SaleModel.shift_id == int(shift_id) if str(shift_id).isdigit() else SaleModel.shift_id == shift_id
                ).all()
                
                for sale in sales:
                    if hasattr(sale, 'payment_method') and sale.payment_method == 'cash':
                        total_cash_sales += float(sale.total or 0)
        except Exception as e:
            print(f"Erreur calcul ventes: {e}")
            # Fallback: utiliser les dates
            try:
                started_at = shift.get('started_at')
                if started_at:
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    
                    with get_session() as session:
                        from database.models_tenant import Sale as SaleModel
                        
                        sales = session.query(SaleModel).filter(
                            SaleModel.created_at >= started_at
                        ).all()
                        
                        for sale in sales:
                            if hasattr(sale, 'payment_method') and sale.payment_method == 'cash':
                                total_cash_sales += float(sale.total or 0)
            except Exception as e2:
                print(f"Erreur fallback: {e2}")
        
        expected_amount = opening_amount + total_cash_sales
        
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
    async def extend_shift(extension_minutes: int = 60, current_user: dict = Depends(get_current_user)):
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
    async def extend_shift_by_id(
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
    async def get_shift_details(shift_id: str, current_user: dict = Depends(get_current_user)):
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
        
        # Calculer les ventes en espèces pour ce shift
        total_cash_sales = 0
        total_sales_count = 0
        
        with get_session() as session:
            from database.models_tenant import Sale as SaleModel
            
            sales = session.query(SaleModel).filter(
                SaleModel.shift_id == uuid.UUID(shift_id)
            ).all()
            
            for sale in sales:
                total_sales_count += 1
                payments = sale.payment_details or []
                for payment in payments:
                    if payment.get('method') == 'cash':
                        total_cash_sales += payment.get('amount', 0)
        
        # Calculer les montants
        opening_amount = float(shift.get('opening_amount', 0))
        closing_amount = float(shift.get('closing_amount') or 0) if shift.get('closing_amount') else None
        expected_amount = float(shift.get('expected_amount') or 0) if shift.get('expected_amount') else None
        
        expected_closing_amount = opening_amount + total_cash_sales
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
            "total_cash_sales": total_cash_sales,
            "total_sales_count": total_sales_count,
            "expected_closing_amount": expected_closing_amount,
            "actual_closing_amount": actual_closing_amount,
            "difference": difference,
            "has_discrepancy": has_discrepancy,
            "is_active": shift.get('is_active', False),
            "notes": shift.get('notes'),
            "closing_notes": shift.get('closing_notes')
        }
    
    @router.get("/summary/{shift_id}")
    async def get_shift_summary(shift_id: str, current_user: dict = Depends(get_current_user)):
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
    async def get_shift_history(
        days: int = 30,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Récupérer l'historique des shifts (Admin)."""
        repo = ShiftRepository()
        
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)
        
        shifts = repo.get_by_date_range(start_date, end_date)
        return shifts
    
    @router.get("/all-open")
    async def get_all_open_shifts(current_user: dict = Depends(require_role(["admin"]))):
        """Récupérer tous les shifts ouverts (Admin)."""
        repo = ShiftRepository()
        return repo.get_all_active()
    
    @router.get("/calculate-expected")
    async def calculate_expected_closing(current_user: dict = Depends(get_current_user)):
        """Calculer le montant attendu en caisse pour la clôture du shift."""
        from database.repositories_extended import SaleRepository
        
        repo = ShiftRepository()
        user_id = current_user['user_id']
        
        # Trouver le shift ouvert
        shift = repo.get_active_by_user_str(user_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Aucun shift ouvert trouvé")
        
        # Récupérer les ventes du shift
        sale_repo = SaleRepository()
        shift_id = shift.get('id')
        opening_amount = float(shift.get('opening_amount', 0))
        
        # Calculer les ventes espèces et le total
        total_cash_sales = 0
        total_sales_count = 0
        
        try:
            # Obtenir les ventes liées au shift
            with get_session() as session:
                from database.models_tenant import Sale as SaleModel
                
                sales = session.query(SaleModel).filter(
                    SaleModel.shift_id == int(shift_id) if str(shift_id).isdigit() else SaleModel.shift_id == shift_id
                ).all()
                
                for sale in sales:
                    total_sales_count += 1
                    # Calculer les ventes espèces
                    if hasattr(sale, 'payments') and sale.payments:
                        for payment in sale.payments:
                            if hasattr(payment, 'method') and payment.method == 'cash':
                                total_cash_sales += float(payment.amount or 0)
                    elif hasattr(sale, 'payment_method'):
                        if sale.payment_method == 'cash':
                            total_cash_sales += float(sale.total or 0)
        except Exception as e:
            print(f"Erreur lors du calcul des ventes: {e}")
            # Essayer avec les dates du shift comme fallback
            try:
                started_at = shift.get('started_at')
                if started_at:
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    
                    with get_session() as session:
                        from database.models_tenant import Sale as SaleModel
                        
                        sales = session.query(SaleModel).filter(
                            SaleModel.created_at >= started_at
                        ).all()
                        
                        for sale in sales:
                            total_sales_count += 1
                            if hasattr(sale, 'payment_method') and sale.payment_method == 'cash':
                                total_cash_sales += float(sale.total or 0)
            except Exception as e2:
                print(f"Erreur fallback: {e2}")
        
        expected_closing_amount = opening_amount + total_cash_sales
        
        return {
            "opening_amount": opening_amount,
            "total_cash_sales": total_cash_sales,
            "total_sales_count": total_sales_count,
            "expected_closing_amount": expected_closing_amount,
            "shift_id": str(shift_id),
            "shift_started_at": shift.get('started_at')
        }

    @router.get("/stats")
    async def get_shifts_stats(
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
    async def get_active_shifts(current_user: dict = Depends(get_current_user)):
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
    async def mark_alert_shown(
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
    async def delete_shift(
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

