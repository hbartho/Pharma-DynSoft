"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
import os
import uuid

from auth import require_role, get_current_user
from models.prescription import Prescription, PrescriptionCreate, PrescriptionUpdate

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import ProductRepository, CustomerRepository
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Prescription as PrescriptionModel, PrescriptionStatus
    from sqlalchemy import desc, or_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def prescription_to_dict(p) -> dict:
        if p is None:
            return None
        return {
            "id": str(p.id),
            "customer_id": str(p.customer_id) if p.customer_id else None,
            "customer_name": p.customer.name if p.customer else "Client inconnu",
            "doctor_name": p.doctor_name,
            "items": p.medications or [],
            "medications": p.medications or [],
            "notes": p.notes,
            "status": p.status.value if p.status else "pending",
            "created_at": p.created_at,
            "tenant_id": "pharmacie_centrale",
        }
    
    @router.get("/stats")
    async def get_prescriptions_stats(
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les statistiques des ordonnances"""
        with get_session() as session:
            # Total = pending + fulfilled (exclure les annulées)
            pending = session.query(PrescriptionModel).filter(
                PrescriptionModel.status == PrescriptionStatus.PENDING
            ).count()
            fulfilled = session.query(PrescriptionModel).filter(
                or_(
                    PrescriptionModel.status == PrescriptionStatus.FULFILLED,
                    PrescriptionModel.status == PrescriptionStatus.COMPLETED
                )
            ).count()
            cancelled = session.query(PrescriptionModel).filter(
                PrescriptionModel.status == PrescriptionStatus.CANCELLED
            ).count()
            
            # Le total est la somme des ordonnances actives (pending + fulfilled)
            total = pending + fulfilled
            
            return {
                "total": total,
                "pending": pending,
                "fulfilled": fulfilled,
                "cancelled": cancelled
            }
    
    @router.get("/paginated")
    async def get_prescriptions_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None, description="all, pending, fulfilled, cancelled"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les ordonnances avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(PrescriptionModel)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        PrescriptionModel.doctor_name.ilike(search_term),
                        PrescriptionModel.customer_name.ilike(search_term)
                    )
                )
            
            if status == 'pending':
                query = query.filter(PrescriptionModel.status == PrescriptionStatus.PENDING)
            elif status == 'fulfilled':
                query = query.filter(
                    or_(
                        PrescriptionModel.status == PrescriptionStatus.FULFILLED,
                        PrescriptionModel.status == PrescriptionStatus.COMPLETED
                    )
                )
            elif status == 'cancelled':
                query = query.filter(PrescriptionModel.status == PrescriptionStatus.CANCELLED)
            
            total = query.count()
            query = query.order_by(PrescriptionModel.status, desc(PrescriptionModel.created_at))
            
            offset = (page - 1) * limit
            prescriptions_orm = query.offset(offset).limit(limit).all()
            
            prescriptions = []
            for p in prescriptions_orm:
                data = prescription_to_dict(p)
                data['tenant_id'] = 'pharmacie_centrale'
                prescriptions.append(data)
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": prescriptions,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.post("", response_model=Prescription)
    async def create_prescription(prescription_data: PrescriptionCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Create a new prescription"""
        with get_session() as session:
            prescription = PrescriptionModel(
                id=uuid.uuid4(),
                customer_id=uuid.UUID(prescription_data.customer_id) if prescription_data.customer_id else None,
                customer_name=prescription_data.customer_name,
                doctor_name=prescription_data.doctor_name,
                items=prescription_data.items,
                notes=prescription_data.notes,
                status=PrescriptionStatus.PENDING,
                created_at=datetime.now(timezone.utc)
            )
            session.add(prescription)
            session.commit()
            session.refresh(prescription)
            
            result = prescription_to_dict(prescription)
            result['tenant_id'] = 'pharmacie_centrale'
            return Prescription(**result)
    
    @router.get("", response_model=List[Prescription])
    async def get_prescriptions(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Get all prescriptions - pending first, then by date descending"""
        with get_session() as session:
            # Récupérer toutes les ordonnances, triées par statut puis par date
            prescriptions = session.query(PrescriptionModel).order_by(
                PrescriptionModel.status,  # PENDING vient avant FULFILLED alphabétiquement
                desc(PrescriptionModel.created_at)
            ).all()
            
            result = []
            for p in prescriptions:
                data = prescription_to_dict(p)
                data['tenant_id'] = 'pharmacie_centrale'
                result.append(Prescription(**data))
            return result
    
    @router.put("/{prescription_id}/status")
    async def update_prescription_status(prescription_id: str, new_status: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Update prescription status"""
        with get_session() as session:
            prescription = session.query(PrescriptionModel).filter(
                PrescriptionModel.id == uuid.UUID(prescription_id)
            ).first()
            
            if not prescription:
                raise HTTPException(status_code=404, detail="Prescription not found")
            
            # Mapper le statut
            status_map = {
                'pending': PrescriptionStatus.PENDING,
                'fulfilled': PrescriptionStatus.FULFILLED,
                'cancelled': PrescriptionStatus.CANCELLED,
            }
            prescription.status = status_map.get(new_status.lower(), PrescriptionStatus.PENDING)
            session.commit()
            
            return {"message": "Prescription updated successfully"}
    
    @router.put("/{prescription_id}/edit", response_model=Prescription)
    async def edit_prescription(prescription_id: str, prescription_data: PrescriptionUpdate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Edit a prescription"""
        with get_session() as session:
            prescription = session.query(PrescriptionModel).filter(
                PrescriptionModel.id == uuid.UUID(prescription_id)
            ).first()
            
            if not prescription:
                raise HTTPException(status_code=404, detail="Prescription not found")
            
            # Mettre à jour uniquement les champs fournis
            if prescription_data.customer_id is not None:
                prescription.customer_id = uuid.UUID(prescription_data.customer_id)
            if prescription_data.doctor_name is not None:
                prescription.doctor_name = prescription_data.doctor_name
            if prescription_data.medications is not None:
                prescription.medications = prescription_data.medications
            if prescription_data.notes is not None:
                prescription.notes = prescription_data.notes
            if prescription_data.status is not None:
                prescription.status = PrescriptionStatus(prescription_data.status)
            
            prescription.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(prescription)
            
            result = prescription_to_dict(prescription)
            result['tenant_id'] = 'pharmacie_centrale'
            return Prescription(**result)
    
    @router.delete("/{prescription_id}")
    async def delete_prescription(prescription_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Delete a prescription"""
        with get_session() as session:
            prescription = session.query(PrescriptionModel).filter(
                PrescriptionModel.id == uuid.UUID(prescription_id)
            ).first()
            
            if not prescription:
                raise HTTPException(status_code=404, detail="Prescription not found")
            
            session.delete(prescription)
            session.commit()
            
            return {"message": "Prescription deleted successfully"}

