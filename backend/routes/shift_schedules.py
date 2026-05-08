"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import uuid
import os

from auth import require_role, get_current_user
from models.shift_schedule import (
    ShiftSchedule, 
    ShiftScheduleCreate, 
    ShiftScheduleUpdate,
    ShiftScheduleBulkCreate,
    ShiftEligibility
)

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/shift-schedules", tags=["Shift Schedules"])

DEFAULT_TIMEZONE = "Africa/Conakry"

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import ShiftSchedule as ShiftScheduleModel, User
    from database.repositories import UserRepository, SettingsRepository
    from sqlalchemy import desc, and_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def schedule_to_dict(s) -> dict:
        if s is None:
            return None
        return {
            "id": str(s.id),
            "user_id": str(s.user_id) if s.user_id else None,
            "user_code": s.user_code,
            "user_name": s.user_name,
            "role": s.role,
            "scheduled_date": s.schedule_date.isoformat() if s.schedule_date else None,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "max_duration_hours": s.max_duration_hours,
            "notes": s.notes,
            "is_active": True,
            "created_at": s.created_at,
            "tenant_id": "pharmacie_centrale",
        }
    
    async def get_tenant_timezone(tenant_id: str) -> str:
        """Récupérer le fuseau horaire du tenant"""
        settings_repo = SettingsRepository()
        return settings_repo.get("timezone", DEFAULT_TIMEZONE)
    
    @router.get("")
    async def get_shift_schedules(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les planifications de shifts"""
        role = current_user.get('role', 'caissier')
        
        with get_session() as session:
            query = session.query(ShiftScheduleModel)
            
            if role != 'admin':
                query = query.filter(ShiftScheduleModel.user_id == uuid.UUID(current_user['user_id']))
            elif user_id:
                query = query.filter(ShiftScheduleModel.user_id == uuid.UUID(user_id))
            
            if start_date:
                from datetime import date as date_type
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(ShiftScheduleModel.schedule_date >= start)
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(ShiftScheduleModel.schedule_date <= end)
            
            schedules = query.order_by(ShiftScheduleModel.schedule_date).all()
            return [schedule_to_dict(s) for s in schedules]
    
    @router.get("/calendar")
    async def get_calendar_view(
        year: int,
        month: int,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Vue calendrier mensuelle pour l'admin"""
        from datetime import date as date_type
        
        start_date = date_type(year, month, 1)
        if month == 12:
            end_date = date_type(year + 1, 1, 1)
        else:
            end_date = date_type(year, month + 1, 1)
        
        with get_session() as session:
            schedules = session.query(ShiftScheduleModel).filter(
                and_(
                    ShiftScheduleModel.schedule_date >= start_date,
                    ShiftScheduleModel.schedule_date < end_date
                )
            ).order_by(ShiftScheduleModel.schedule_date).all()
            
            calendar_data = {}
            for s in schedules:
                date_key = s.schedule_date.isoformat()
                if date_key not in calendar_data:
                    calendar_data[date_key] = []
                calendar_data[date_key].append(schedule_to_dict(s))
            
            # Récupérer les utilisateurs planifiables
            user_repo = UserRepository()
            all_users = user_repo.get_all()
            users = [u for u in all_users if u.get('role') in ['caissier', 'pharmacien'] and u.get('is_active', True)]
            
            return {
                "year": year,
                "month": month,
                "schedules": calendar_data,
                "users": users
            }
    
    @router.get("/check-eligibility")
    async def check_shift_eligibility(
        current_user: dict = Depends(get_current_user)
    ):
        """Vérifier si l'utilisateur peut ouvrir un shift"""
        user_id = current_user['user_id']
        role = current_user.get('role', 'caissier')
        
        if role == 'admin':
            return ShiftEligibility(
                is_eligible=True,
                reason=None,
                schedule=None,
                suggested_end_time=None,
                max_duration_hours=8.0
            )
        
        tz_name = await get_tenant_timezone("pharmacie_centrale")
        try:
            local_tz = ZoneInfo(tz_name)
        except Exception:
            local_tz = ZoneInfo(DEFAULT_TIMEZONE)
        
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(local_tz)
        today = now_local.date()
        current_time = now_local.strftime('%H:%M')
        
        with get_session() as session:
            schedule = session.query(ShiftScheduleModel).filter(
                and_(
                    ShiftScheduleModel.user_id == uuid.UUID(user_id),
                    ShiftScheduleModel.schedule_date == today
                )
            ).first()
            
            if not schedule:
                return ShiftEligibility(
                    is_eligible=False,
                    reason=f"Vous n'êtes pas planifié pour travailler aujourd'hui ({today}). Contactez votre administrateur.",
                    schedule=None,
                    suggested_end_time=None,
                    max_duration_hours=None,
                    current_time=current_time
                )
            
            start_time = schedule.start_time or '00:00'
            end_time = schedule.end_time or '23:59'
            
            if current_time < start_time:
                return ShiftEligibility(
                    is_eligible=False,
                    reason=f"Votre shift commence à {start_time}. Il est actuellement {current_time}",
                    schedule=schedule_to_dict(schedule),
                    suggested_end_time=end_time,
                    max_duration_hours=schedule.max_duration_hours,
                    current_time=current_time
                )
            
            if current_time > end_time:
                return ShiftEligibility(
                    is_eligible=False,
                    reason=f"Votre shift s'est terminé à {end_time}. Il est actuellement {current_time}",
                    schedule=schedule_to_dict(schedule),
                    suggested_end_time=end_time,
                    max_duration_hours=schedule.max_duration_hours,
                    current_time=current_time
                )
            
            return ShiftEligibility(
                is_eligible=True,
                reason=None,
                schedule=schedule_to_dict(schedule),
                suggested_end_time=end_time,
                max_duration_hours=schedule.max_duration_hours,
                current_time=current_time
            )
    
    @router.get("/my-schedule")
    async def get_my_schedule(
        date: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer la planification de l'utilisateur courant"""
        user_id = current_user['user_id']
        from datetime import date as date_type
        
        target_date = datetime.strptime(date, '%Y-%m-%d').date() if date else datetime.now(timezone.utc).date()
        
        with get_session() as session:
            schedule = session.query(ShiftScheduleModel).filter(
                and_(
                    ShiftScheduleModel.user_id == uuid.UUID(user_id),
                    ShiftScheduleModel.schedule_date == target_date
                )
            ).first()
            
            return schedule_to_dict(schedule) if schedule else None
    
    @router.post("")
    async def create_shift_schedule(
        data: ShiftScheduleCreate,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Créer une nouvelle planification de shift"""
        user_repo = UserRepository()
        user = user_repo.get_by_id_str(data.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        if user.get('role') == 'admin':
            raise HTTPException(status_code=400, detail="Les administrateurs sont exempts de planification")
        
        from datetime import date as date_type
        schedule_date = datetime.strptime(data.scheduled_date, '%Y-%m-%d').date()
        
        with get_session() as session:
            existing = session.query(ShiftScheduleModel).filter(
                and_(
                    ShiftScheduleModel.user_id == uuid.UUID(data.user_id),
                    ShiftScheduleModel.schedule_date == schedule_date
                )
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail=f"Une planification existe déjà pour cet utilisateur le {data.scheduled_date}")
            
            schedule = ShiftScheduleModel(
                id=uuid.uuid4(),
                user_id=uuid.UUID(data.user_id),
                user_code=user.get('employee_code', 'N/A'),
                user_name=user.get('name', 'Utilisateur'),
                role=user.get('role', 'caissier'),
                schedule_date=schedule_date,
                start_time=data.start_time,
                end_time=data.end_time,
                max_duration_hours=data.max_duration_hours or 8.0,
                notes=data.notes,
                created_at=datetime.now(timezone.utc)
            )
            session.add(schedule)
            session.commit()
            
            return {
                "message": "Planification créée",
                "id": str(schedule.id),
                "schedule": schedule_to_dict(schedule)
            }
    
    @router.post("/bulk")
    async def create_bulk_shift_schedules(
        schedules: List[dict],
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Créer plusieurs planifications en une seule requête"""
        from datetime import datetime as dt
        created = []
        errors = []
        
        with get_session() as session:
            # Charger les utilisateurs pour mapper user_code -> user_id
            users = session.query(User).all()
            user_map = {u.employee_code: u for u in users}
            
            for idx, schedule_data in enumerate(schedules):
                try:
                    user_code = schedule_data.get("user_code")
                    scheduled_date = schedule_data.get("scheduled_date")
                    
                    if not user_code or not scheduled_date:
                        errors.append({"index": idx, "error": "user_code et scheduled_date requis"})
                        continue
                    
                    # Convertir la date si c'est une string
                    if isinstance(scheduled_date, str):
                        scheduled_date = dt.strptime(scheduled_date, "%Y-%m-%d").date()
                    
                    # Trouver l'utilisateur
                    user = user_map.get(user_code)
                    if not user:
                        errors.append({"index": idx, "error": f"Utilisateur {user_code} non trouvé"})
                        continue
                    
                    # Vérifier si une planification existe déjà
                    existing = session.query(ShiftScheduleModel).filter(
                        ShiftScheduleModel.user_code == user_code,
                        ShiftScheduleModel.schedule_date == scheduled_date
                    ).first()
                    
                    if existing:
                        errors.append({
                            "index": idx,
                            "error": f"Planification déjà existante pour {user_code} le {scheduled_date}"
                        })
                        continue
                    
                    schedule = ShiftScheduleModel(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        user_code=user_code,
                        user_name=schedule_data.get("user_name") or user.name,
                        role=schedule_data.get("role") or user.role.value,
                        schedule_date=scheduled_date,
                        start_time=schedule_data.get("start_time") or "08:00",
                        end_time=schedule_data.get("end_time") or "20:00",
                        max_duration_hours=schedule_data.get("max_duration_hours") or 12.0,
                        notes=schedule_data.get("notes")
                    )
                    session.add(schedule)
                    created.append(schedule_to_dict(schedule))
                except Exception as e:
                    errors.append({"index": idx, "error": str(e)})
            
            session.commit()
        
        return {
            "message": f"{len(created)} planification(s) créée(s)",
            "created": created,
            "errors": errors
        }
    
    @router.delete("/date/{date}")
    async def delete_schedules_by_date(
        date: str,
        user_code: Optional[str] = Query(None),
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Supprimer les planifications d'une date (optionnellement pour un utilisateur spécifique)"""
        with get_session() as session:
            query = session.query(ShiftScheduleModel).filter(
                ShiftScheduleModel.schedule_date == date
            )
            
            if user_code:
                query = query.filter(ShiftScheduleModel.user_code == user_code)
            
            count = query.count()
            query.delete()
            session.commit()
            
            return {"message": f"{count} planification(s) supprimée(s)", "date": date}

    @router.delete("/{schedule_id}")
    async def delete_shift_schedule(
        schedule_id: str,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Supprimer une planification"""
        with get_session() as session:
            schedule = session.query(ShiftScheduleModel).filter(
                ShiftScheduleModel.id == uuid.UUID(schedule_id)
            ).first()
            
            if not schedule:
                raise HTTPException(status_code=404, detail="Planification non trouvée")
            
            session.delete(schedule)
            session.commit()
            
            return {"message": "Planification supprimée", "id": schedule_id}

