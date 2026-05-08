"""
Repositories PostgreSQL - Partie 2

Repositories pour les entités complexes: Ventes, Shifts, etc.
"""

from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date, timedelta
import uuid

from database.config import db_manager
from database.models_tenant import (
    Sale, SaleItem, Shift, ShiftSchedule, PendingSale, 
    Debt, Prescription, StockMovement, Supply, SupplyItem,
    PaymentMethod, SaleStatus, DebtStatus, PrescriptionStatus, StockMovementType
)
from database.repositories import BaseRepository


# ==================== SHIFT REPOSITORY ====================

def _to_dict_shift(shift) -> Dict[str, Any]:
    """Convertit un Shift en dictionnaire."""
    if shift is None:
        return None
    return {
        "id": str(shift.id),
        "user_id": str(shift.user_id),
        "opening_amount": shift.opening_amount,
        "closing_amount": shift.closing_amount,
        "expected_amount": shift.expected_amount,
        "started_at": shift.started_at.isoformat() if shift.started_at else None,
        "ended_at": shift.ended_at.isoformat() if shift.ended_at else None,
        "expires_at": shift.expires_at.isoformat() if shift.expires_at else None,
        "is_active": shift.is_active,
        "notes": shift.notes,
        "closing_notes": shift.closing_notes,
        "created_at": shift.created_at.isoformat() if shift.created_at else None,
        # Flags pour les alertes de fin de shift
        "alert_30min_shown": getattr(shift, 'alert_30min_shown', False) or False,
        "alert_5min_shown": getattr(shift, 'alert_5min_shown', False) or False,
        "alert_end_shown": getattr(shift, 'alert_end_shown', False) or False,
    }


class ShiftRepository(BaseRepository):
    """Repository pour les shifts."""
    
    def get_active_by_user(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère le shift actif d'un utilisateur."""
        with self.get_session() as session:
            shift = session.query(Shift).filter(
                and_(
                    Shift.user_id == user_id,
                    Shift.is_active == True
                )
            ).first()
            return _to_dict_shift(shift)
    
    def get_active_by_user_str(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le shift actif d'un utilisateur par ID string."""
        try:
            return self.get_active_by_user(uuid.UUID(user_id))
        except (ValueError, AttributeError):
            return None
    
    def get_by_id(self, shift_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère un shift par ID."""
        with self.get_session() as session:
            shift = session.query(Shift).filter(Shift.id == shift_id).first()
            return _to_dict_shift(shift)
    
    def get_by_id_str(self, shift_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un shift par ID string."""
        try:
            return self.get_by_id(uuid.UUID(shift_id))
        except (ValueError, AttributeError):
            return None
    
    def get_all_active(self) -> List[Dict[str, Any]]:
        """Récupère tous les shifts actifs."""
        with self.get_session() as session:
            shifts = session.query(Shift).filter(Shift.is_active == True).all()
            return [_to_dict_shift(s) for s in shifts]
    
    def get_by_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Récupère les shifts dans une période."""
        with self.get_session() as session:
            shifts = session.query(Shift).filter(
                and_(
                    func.date(Shift.started_at) >= start_date,
                    func.date(Shift.started_at) <= end_date
                )
            ).order_by(desc(Shift.started_at)).all()
            return [_to_dict_shift(s) for s in shifts]
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouveau shift."""
        with self.get_session() as session:
            shift = Shift(
                id=uuid.uuid4(),
                user_id=uuid.UUID(data['user_id']) if isinstance(data['user_id'], str) else data['user_id'],
                opening_amount=float(data.get('opening_amount', 0)),
                started_at=data.get('started_at', datetime.now(timezone.utc)),
                expires_at=data.get('expires_at'),
                is_active=True,
                notes=data.get('notes'),
            )
            session.add(shift)
            session.flush()
            result = _to_dict_shift(shift)
            session.commit()
            return result
    
    def close(self, shift_id: uuid.UUID, closing_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ferme un shift."""
        with self.get_session() as session:
            shift = session.query(Shift).filter(Shift.id == shift_id).first()
            if not shift:
                return None
            
            shift.closing_amount = float(closing_data.get('closing_amount', 0))
            shift.expected_amount = float(closing_data.get('expected_amount', 0))
            shift.ended_at = datetime.now(timezone.utc)
            shift.is_active = False
            shift.closing_notes = closing_data.get('closing_notes')
            shift.updated_at = datetime.now(timezone.utc)
            
            session.flush()
            result = _to_dict_shift(shift)
            session.commit()
            return result
    
    def close_by_id_str(self, shift_id: str, closing_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ferme un shift par ID string."""
        try:
            return self.close(uuid.UUID(shift_id), closing_data)
        except (ValueError, AttributeError):
            return None
    
    def extend(self, shift_id: uuid.UUID, new_expires_at: datetime) -> Optional[Dict[str, Any]]:
        """Prolonge un shift et réinitialise les flags d'alerte."""
        with self.get_session() as session:
            shift = session.query(Shift).filter(Shift.id == shift_id).first()
            if not shift:
                return None
            
            shift.expires_at = new_expires_at
            shift.updated_at = datetime.now(timezone.utc)
            
            # Réinitialiser les flags d'alerte pour permettre de nouvelles notifications
            shift.alert_30min_shown = False
            shift.alert_5min_shown = False
            shift.alert_end_shown = False
            
            session.flush()
            result = _to_dict_shift(shift)
            session.commit()
            return result
    
    def extend_by_id_str(self, shift_id: str, new_expires_at: datetime) -> Optional[Dict[str, Any]]:
        """Prolonge un shift par ID string."""
        try:
            return self.extend(uuid.UUID(shift_id), new_expires_at)
        except (ValueError, AttributeError):
            return None


# ==================== SHIFT SCHEDULE REPOSITORY ====================

class ShiftScheduleRepository(BaseRepository):
    """Repository pour les planifications de shifts."""
    
    def get_by_user_and_date(self, user_id: uuid.UUID, schedule_date: date) -> Optional[ShiftSchedule]:
        """Récupère la planification d'un utilisateur pour une date."""
        with self.get_session() as session:
            return session.query(ShiftSchedule).filter(
                and_(
                    ShiftSchedule.user_id == user_id,
                    ShiftSchedule.schedule_date == schedule_date
                )
            ).first()
    
    def get_by_date(self, schedule_date: date) -> List[ShiftSchedule]:
        """Récupère toutes les planifications pour une date."""
        with self.get_session() as session:
            return session.query(ShiftSchedule).filter(
                ShiftSchedule.schedule_date == schedule_date
            ).all()
    
    def get_by_date_range(self, start_date: date, end_date: date) -> List[ShiftSchedule]:
        """Récupère les planifications dans une période."""
        with self.get_session() as session:
            return session.query(ShiftSchedule).filter(
                and_(
                    ShiftSchedule.schedule_date >= start_date,
                    ShiftSchedule.schedule_date <= end_date
                )
            ).order_by(ShiftSchedule.schedule_date).all()
    
    def get_by_user(self, user_id: uuid.UUID) -> List[ShiftSchedule]:
        """Récupère toutes les planifications d'un utilisateur."""
        with self.get_session() as session:
            return session.query(ShiftSchedule).filter(
                ShiftSchedule.user_id == user_id
            ).order_by(desc(ShiftSchedule.schedule_date)).all()
    
    def create(self, data: Dict[str, Any]) -> ShiftSchedule:
        """Crée une nouvelle planification."""
        with self.get_session() as session:
            schedule = ShiftSchedule(
                id=uuid.uuid4(),
                user_id=uuid.UUID(data['user_id']) if isinstance(data['user_id'], str) else data['user_id'],
                user_code=data['user_code'],
                user_name=data['user_name'],
                role=data['role'],
                schedule_date=data['schedule_date'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                max_duration_hours=float(data.get('max_duration_hours', 8.0)),
                notes=data.get('notes'),
            )
            session.add(schedule)
            session.commit()
            session.refresh(schedule)
            return schedule
    
    def update(self, schedule_id: uuid.UUID, data: Dict[str, Any]) -> Optional[ShiftSchedule]:
        """Met à jour une planification."""
        with self.get_session() as session:
            schedule = session.query(ShiftSchedule).filter(ShiftSchedule.id == schedule_id).first()
            if not schedule:
                return None
            
            for key, value in data.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            
            schedule.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(schedule)
            return schedule
    
    def delete(self, schedule_id: uuid.UUID) -> bool:
        """Supprime une planification."""
        with self.get_session() as session:
            result = session.query(ShiftSchedule).filter(ShiftSchedule.id == schedule_id).delete()
            session.commit()
            return result > 0
    
    def to_dict(self, schedule: ShiftSchedule) -> Dict[str, Any]:
        """Convertit un ShiftSchedule en dictionnaire."""
        return {
            "id": str(schedule.id),
            "user_id": str(schedule.user_id),
            "user_code": schedule.user_code,
            "user_name": schedule.user_name,
            "role": schedule.role,
            "schedule_date": schedule.schedule_date.isoformat() if schedule.schedule_date else None,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "max_duration_hours": schedule.max_duration_hours,
            "notes": schedule.notes,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
        }


# ==================== SALE REPOSITORY ====================

class SaleRepository(BaseRepository):
    """Repository pour les ventes."""
    
    def get_by_id(self, sale_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère une vente par ID."""
        with self.get_session() as session:
            sale = session.query(Sale).filter(Sale.id == sale_id).first()
            return self.to_dict(sale, include_items=True) if sale else None
    
    def get_by_id_str(self, sale_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une vente par ID string."""
        try:
            return self.get_by_id(uuid.UUID(sale_id))
        except (ValueError, AttributeError):
            return None
    
    def get_by_number(self, sale_number: str) -> Optional[Dict[str, Any]]:
        """Récupère une vente par numéro."""
        with self.get_session() as session:
            sale = session.query(Sale).filter(Sale.sale_number == sale_number).first()
            return self.to_dict(sale, include_items=True) if sale else None
    
    def get_all(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Récupère toutes les ventes."""
        with self.get_session() as session:
            sales = session.query(Sale).order_by(desc(Sale.created_at)).limit(limit).all()
            return [self.to_dict(s, include_items=True) for s in sales]
    
    def get_paginated(
        self, 
        page: int = 1, 
        limit: int = 20,
        search: str = None,
        date_from: date = None,
        date_to: date = None,
        payment_method: str = None,
        agent_code: str = None,
        customer_id: str = None,
        status: str = None
    ) -> Dict[str, Any]:
        """
        Récupère les ventes avec pagination et filtres.
        
        Returns:
            {
                "items": [...],
                "total": int,
                "page": int,
                "limit": int,
                "pages": int
            }
        """
        with self.get_session() as session:
            # Query de base
            query = session.query(Sale)
            
            # Filtres
            filters = []
            
            # Filtre par date
            if date_from:
                filters.append(func.date(Sale.created_at) >= date_from)
            if date_to:
                filters.append(func.date(Sale.created_at) <= date_to)
            
            # Filtre par mode de paiement
            if payment_method:
                payment_map = {
                    'cash': PaymentMethod.CASH,
                    'card': PaymentMethod.CARD,
                    'orange_money': PaymentMethod.ORANGE_MONEY,
                    'mtn_money': PaymentMethod.MTN_MONEY,
                    'check': PaymentMethod.CHECK,
                    'credit': PaymentMethod.CREDIT,
                    'mixed': PaymentMethod.MIXED,
                }
                if payment_method.lower() in payment_map:
                    filters.append(Sale.payment_method == payment_map[payment_method.lower()])
            
            # Filtre par agent
            if agent_code:
                filters.append(Sale.agent_code == agent_code)
            
            # Filtre par client
            if customer_id:
                try:
                    filters.append(Sale.customer_id == uuid.UUID(customer_id))
                except ValueError:
                    pass
            
            # Filtre par statut
            if status and status != 'all':
                status_map = {
                    'completed': SaleStatus.COMPLETED,
                    'partial': SaleStatus.PARTIAL,
                    'credit': SaleStatus.CREDIT,
                    'cancelled': SaleStatus.CANCELLED
                }
                if status in status_map:
                    filters.append(Sale.status == status_map[status])
            
            # Recherche textuelle (numéro de vente, nom d'agent, ou nom de client via relation)
            if search:
                from database.models_tenant import Customer
                
                # Sous-requête pour trouver les IDs des clients correspondants
                customer_subquery = session.query(Customer.id).filter(
                    Customer.name.ilike(f"%{search}%")
                ).subquery()
                
                search_filter = or_(
                    Sale.sale_number.ilike(f"%{search}%"),
                    Sale.agent_name.ilike(f"%{search}%"),
                    Sale.agent_code.ilike(f"%{search}%"),
                    Sale.customer_id.in_(customer_subquery)
                )
                filters.append(search_filter)
            
            # Appliquer les filtres
            if filters:
                query = query.filter(and_(*filters))
            
            # Compter le total
            total = query.count()
            
            # Pagination
            offset = (page - 1) * limit
            sales = query.order_by(desc(Sale.created_at)).offset(offset).limit(limit).all()
            
            # Calculer le nombre de pages
            pages = (total + limit - 1) // limit  # Arrondi supérieur
            
            return {
                "items": [self.to_dict(s, include_items=True) for s in sales],
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages
            }
    
    def get_by_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Récupère les ventes dans une période."""
        with self.get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    func.date(Sale.created_at) >= start_date,
                    func.date(Sale.created_at) <= end_date
                )
            ).order_by(desc(Sale.created_at)).all()
            return [self.to_dict(s, include_items=True) for s in sales]
    
    def get_by_shift(self, shift_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Récupère les ventes d'un shift."""
        with self.get_session() as session:
            sales = session.query(Sale).filter(Sale.shift_id == shift_id).all()
            return [self.to_dict(s, include_items=True) for s in sales]
    
    def get_today_sales(self) -> List[Dict[str, Any]]:
        """Récupère les ventes du jour."""
        today = date.today()
        return self.get_by_date_range(today, today)
    
    def generate_sale_number(self) -> str:
        """Génère un numéro de vente unique (format VNT-XXXXXXXX)."""
        unique_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
        return f"VNT-{unique_id}"
    
    def create(self, data: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Crée une nouvelle vente avec ses lignes."""
        with self.get_session() as session:
            # Mapper le mode de paiement
            payment_str = data.get('payment_method', 'cash').lower()
            payment_map = {
                'cash': PaymentMethod.CASH,
                'card': PaymentMethod.CARD,
                'orange_money': PaymentMethod.ORANGE_MONEY,
                'mtn_money': PaymentMethod.MTN_MONEY,
                'check': PaymentMethod.CHECK,
                'credit': PaymentMethod.CREDIT,
                'mixed': PaymentMethod.MIXED,
                'debt': PaymentMethod.CREDIT,  # debt est mappé sur credit
            }
            payment_method = payment_map.get(payment_str, PaymentMethod.CASH)
            
            # Mapper le statut
            has_debt = data.get('has_debt', False)
            debt_amount = data.get('debt_amount', 0)
            amount_paid = data.get('amount_paid', data.get('total', 0))
            
            if has_debt and debt_amount >= data.get('total', 0):
                status = SaleStatus.CREDIT
            elif has_debt:
                status = SaleStatus.PARTIAL
            else:
                status = SaleStatus.COMPLETED
            
            sale = Sale(
                id=uuid.uuid4(),
                sale_number=data.get('sale_number') or self.generate_sale_number(),
                subtotal=float(data.get('subtotal', data.get('total', 0))),
                discount=float(data.get('discount_amount', 0)),
                discount_type=data.get('discount_type'),
                discount_value=float(data.get('discount_value', 0)) if data.get('discount_value') else None,
                tax_amount=float(data.get('tva_total', 0)),
                total=float(data.get('total', 0)),
                amount_paid=float(amount_paid),
                payment_method=payment_method,
                status=status,
                shift_id=uuid.UUID(data['shift_id']) if data.get('shift_id') else None,
                customer_id=uuid.UUID(data['customer_id']) if data.get('customer_id') else None,
                agent_code=data.get('employee_code'),
                agent_name=data.get('user_name'),
                notes=data.get('notes'),
                # Paiements mixtes (split payments)
                is_split_payment=data.get('is_split_payment', False),
                split_payments=data.get('split_payments'),
            )
            session.add(sale)
            session.flush()  # Pour obtenir l'ID
            
            # Ajouter les lignes de vente
            for item_data in items:
                sale_item = SaleItem(
                    id=uuid.uuid4(),
                    sale_id=sale.id,
                    product_id=uuid.UUID(item_data['product_id']) if isinstance(item_data['product_id'], str) else item_data['product_id'],
                    product_name=item_data.get('product_name', 'Produit inconnu'),
                    unit_price=float(item_data.get('unit_price', 0)),
                    quantity=int(item_data.get('quantity', 0)),
                    subtotal=float(item_data.get('subtotal', 0)),
                )
                session.add(sale_item)
            
            session.commit()
            
            # Recharger avec items
            session.refresh(sale)
            return self.to_dict(sale, include_items=True)
    
    def get_statistics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Récupère les statistiques de vente pour une période."""
        with self.get_session() as session:
            sales = session.query(Sale).filter(
                and_(
                    func.date(Sale.created_at) >= start_date,
                    func.date(Sale.created_at) <= end_date,
                    Sale.status != SaleStatus.CANCELLED
                )
            ).all()
            
            total_sales = len(sales)
            total_revenue = sum(s.total for s in sales)
            total_cash = sum(s.total for s in sales if s.payment_method == PaymentMethod.CASH)
            total_card = sum(s.total for s in sales if s.payment_method == PaymentMethod.CARD)
            total_orange = sum(s.total for s in sales if s.payment_method == PaymentMethod.ORANGE_MONEY)
            total_mtn = sum(s.total for s in sales if s.payment_method == PaymentMethod.MTN_MONEY)
            total_credit = sum(s.total for s in sales if s.payment_method == PaymentMethod.CREDIT)
            
            return {
                "total_sales": total_sales,
                "total_revenue": total_revenue,
                "by_payment_method": {
                    "cash": total_cash,
                    "card": total_card,
                    "orange_money": total_orange,
                    "mtn_money": total_mtn,
                    "credit": total_credit,
                }
            }
    
    def to_dict(self, sale: Sale, include_items: bool = True) -> Dict[str, Any]:
        """Convertit une Sale en dictionnaire."""
        if sale is None:
            return None
        
        result = {
            "id": str(sale.id),
            "sale_number": sale.sale_number,
            "subtotal": sale.subtotal,
            "discount": sale.discount,
            "discount_amount": sale.discount,
            "discount_type": getattr(sale, 'discount_type', None),
            "discount_value": getattr(sale, 'discount_value', None),
            "tax_amount": sale.tax_amount,
            "tva_total": sale.tax_amount,
            "total": sale.total,
            "total_ht": sale.subtotal - sale.discount if sale.subtotal else sale.total,
            "amount_paid": sale.amount_paid,
            "debt_amount": max(0, (sale.total or 0) - (sale.amount_paid or 0)),
            "has_debt": (sale.total or 0) > (sale.amount_paid or 0),
            "payment_method": sale.payment_method.value if sale.payment_method else "cash",
            "status": sale.status.value if sale.status else "completed",
            "shift_id": str(sale.shift_id) if sale.shift_id else None,
            "customer_id": str(sale.customer_id) if sale.customer_id else None,
            "customer_name": None,  # Sera enrichi plus tard si nécessaire
            "employee_code": sale.agent_code,
            "agent_code": sale.agent_code,
            "agent_name": sale.agent_name,
            "user_name": sale.agent_name,
            "notes": sale.notes,
            "created_at": sale.created_at if sale.created_at else None,
            # Paiement mixte
            "is_split_payment": getattr(sale, 'is_split_payment', False) or False,
            "split_payments": getattr(sale, 'split_payments', None),
        }
        
        if include_items and sale.items:
            result["items"] = [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "unit_price": item.unit_price,
                    "quantity": item.quantity,
                    "subtotal": item.subtotal,
                }
                for item in sale.items
            ]
        else:
            result["items"] = []
        
        return result


# ==================== PENDING SALE REPOSITORY ====================

class PendingSaleRepository(BaseRepository):
    """Repository pour les ventes en attente."""
    
    def get_all(self) -> List[PendingSale]:
        """Récupère toutes les ventes en attente non expirées."""
        with self.get_session() as session:
            now = datetime.now(timezone.utc)
            return session.query(PendingSale).filter(
                PendingSale.expires_at > now
            ).order_by(desc(PendingSale.created_at)).all()
    
    def get_by_id(self, pending_sale_id: uuid.UUID) -> Optional[PendingSale]:
        """Récupère une vente en attente par ID."""
        with self.get_session() as session:
            return session.query(PendingSale).filter(PendingSale.id == pending_sale_id).first()
    
    def create(self, data: Dict[str, Any]) -> PendingSale:
        """Crée une nouvelle vente en attente."""
        with self.get_session() as session:
            pending_sale = PendingSale(
                id=uuid.uuid4(),
                customer_id=uuid.UUID(data['customer_id']) if data.get('customer_id') else None,
                customer_name=data.get('customer_name'),
                agent_code=data['agent_code'],
                agent_name=data['agent_name'],
                cart_items=data.get('cart_items', []),
                subtotal=float(data.get('subtotal', 0)),
                discount=float(data.get('discount', 0)),
                total=float(data.get('total', 0)),
                expires_at=data.get('expires_at', datetime.now(timezone.utc) + timedelta(hours=24)),
                notes=data.get('notes'),
            )
            session.add(pending_sale)
            session.commit()
            session.refresh(pending_sale)
            return pending_sale
    
    def delete(self, pending_sale_id: uuid.UUID) -> bool:
        """Supprime une vente en attente."""
        with self.get_session() as session:
            result = session.query(PendingSale).filter(PendingSale.id == pending_sale_id).delete()
            session.commit()
            return result > 0
    
    def cleanup_expired(self) -> int:
        """Supprime les ventes en attente expirées."""
        with self.get_session() as session:
            now = datetime.now(timezone.utc)
            result = session.query(PendingSale).filter(
                PendingSale.expires_at <= now
            ).delete()
            session.commit()
            return result
    
    def to_dict(self, pending_sale: PendingSale) -> Dict[str, Any]:
        """Convertit une PendingSale en dictionnaire."""
        return {
            "id": str(pending_sale.id),
            "customer_id": str(pending_sale.customer_id) if pending_sale.customer_id else None,
            "customer_name": pending_sale.customer_name,
            "agent_code": pending_sale.agent_code,
            "agent_name": pending_sale.agent_name,
            "cart_items": pending_sale.cart_items,
            "subtotal": pending_sale.subtotal,
            "discount": pending_sale.discount,
            "total": pending_sale.total,
            "expires_at": pending_sale.expires_at.isoformat() if pending_sale.expires_at else None,
            "notes": pending_sale.notes,
            "created_at": pending_sale.created_at.isoformat() if pending_sale.created_at else None,
        }


# ==================== DEBT REPOSITORY ====================

class DebtRepository(BaseRepository):
    """Repository pour les dettes."""
    
    def get_all(self, status: str = None) -> List[Debt]:
        """Récupère toutes les dettes."""
        with self.get_session() as session:
            query = session.query(Debt)
            if status:
                status_enum = DebtStatus(status)
                query = query.filter(Debt.status == status_enum)
            return query.order_by(desc(Debt.created_at)).all()
    
    def get_by_customer(self, customer_id: uuid.UUID) -> List[Debt]:
        """Récupère les dettes d'un client."""
        with self.get_session() as session:
            return session.query(Debt).filter(Debt.customer_id == customer_id).all()
    
    def get_by_id(self, debt_id: uuid.UUID) -> Optional[Debt]:
        """Récupère une dette par ID."""
        with self.get_session() as session:
            return session.query(Debt).filter(Debt.id == debt_id).first()
    
    def create(self, data: Dict[str, Any]) -> Debt:
        """Crée une nouvelle dette."""
        with self.get_session() as session:
            debt = Debt(
                id=uuid.uuid4(),
                customer_id=uuid.UUID(data['customer_id']) if isinstance(data['customer_id'], str) else data['customer_id'],
                sale_id=uuid.UUID(data['sale_id']) if data.get('sale_id') else None,
                original_amount=float(data['original_amount']),
                remaining_amount=float(data['remaining_amount']),
                status=DebtStatus.PENDING,
                due_date=data.get('due_date'),
                payments=[],
                notes=data.get('notes'),
            )
            session.add(debt)
            session.commit()
            session.refresh(debt)
            return debt
    
    def add_payment(self, debt_id: uuid.UUID, payment_data: Dict[str, Any]) -> Optional[Debt]:
        """Ajoute un paiement à une dette."""
        with self.get_session() as session:
            debt = session.query(Debt).filter(Debt.id == debt_id).first()
            if not debt:
                return None
            
            # Ajouter le paiement
            payments = list(debt.payments or [])
            payments.append({
                "amount": payment_data['amount'],
                "date": datetime.now(timezone.utc).isoformat(),
                "method": payment_data.get('method', 'cash'),
                "notes": payment_data.get('notes'),
            })
            debt.payments = payments
            
            # Mettre à jour le montant restant
            debt.remaining_amount -= float(payment_data['amount'])
            if debt.remaining_amount <= 0:
                debt.remaining_amount = 0
                debt.status = DebtStatus.PAID
            elif debt.remaining_amount < debt.original_amount:
                debt.status = DebtStatus.PARTIAL
            
            debt.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(debt)
            return debt
    
    def write_off(self, debt_id: uuid.UUID) -> Optional[Debt]:
        """Abandonne une dette."""
        with self.get_session() as session:
            debt = session.query(Debt).filter(Debt.id == debt_id).first()
            if not debt:
                return None
            
            debt.status = DebtStatus.WRITTEN_OFF
            debt.remaining_amount = 0
            debt.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(debt)
            return debt
    
    def to_dict(self, debt: Debt) -> Dict[str, Any]:
        """Convertit une Debt en dictionnaire."""
        return {
            "id": str(debt.id),
            "customer_id": str(debt.customer_id),
            "sale_id": str(debt.sale_id) if debt.sale_id else None,
            "original_amount": debt.original_amount,
            "remaining_amount": debt.remaining_amount,
            "status": debt.status.value if debt.status else "pending",
            "due_date": debt.due_date.isoformat() if debt.due_date else None,
            "payments": debt.payments,
            "notes": debt.notes,
            "created_at": debt.created_at.isoformat() if debt.created_at else None,
        }


# ==================== PRESCRIPTION REPOSITORY ====================

class PrescriptionRepository(BaseRepository):
    """Repository pour les ordonnances."""
    
    def get_all(self, status: str = None) -> List[Prescription]:
        """Récupère toutes les ordonnances."""
        with self.get_session() as session:
            query = session.query(Prescription)
            if status:
                status_enum = PrescriptionStatus(status)
                query = query.filter(Prescription.status == status_enum)
            return query.order_by(desc(Prescription.created_at)).all()
    
    def get_by_id(self, prescription_id: uuid.UUID) -> Optional[Prescription]:
        """Récupère une ordonnance par ID."""
        with self.get_session() as session:
            return session.query(Prescription).filter(Prescription.id == prescription_id).first()
    
    def get_by_customer(self, customer_id: uuid.UUID) -> List[Prescription]:
        """Récupère les ordonnances d'un client."""
        with self.get_session() as session:
            return session.query(Prescription).filter(Prescription.customer_id == customer_id).all()
    
    def create(self, data: Dict[str, Any]) -> Prescription:
        """Crée une nouvelle ordonnance."""
        with self.get_session() as session:
            prescription = Prescription(
                id=uuid.uuid4(),
                customer_id=uuid.UUID(data['customer_id']) if isinstance(data['customer_id'], str) else data['customer_id'],
                doctor_name=data['doctor_name'],
                medications=data.get('medications', []),
                status=PrescriptionStatus.PENDING,
                notes=data.get('notes'),
            )
            session.add(prescription)
            session.commit()
            session.refresh(prescription)
            return prescription
    
    def update(self, prescription_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Prescription]:
        """Met à jour une ordonnance."""
        with self.get_session() as session:
            prescription = session.query(Prescription).filter(Prescription.id == prescription_id).first()
            if not prescription:
                return None
            
            for key, value in data.items():
                if key == 'status':
                    value = PrescriptionStatus(value)
                if hasattr(prescription, key):
                    setattr(prescription, key, value)
            
            prescription.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(prescription)
            return prescription
    
    def fulfill(self, prescription_id: uuid.UUID) -> Optional[Prescription]:
        """Marque une ordonnance comme traitée."""
        with self.get_session() as session:
            prescription = session.query(Prescription).filter(Prescription.id == prescription_id).first()
            if not prescription:
                return None
            
            prescription.status = PrescriptionStatus.FULFILLED
            prescription.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            session.refresh(prescription)
            return prescription
    
    def delete(self, prescription_id: uuid.UUID) -> bool:
        """Supprime une ordonnance."""
        with self.get_session() as session:
            result = session.query(Prescription).filter(Prescription.id == prescription_id).delete()
            session.commit()
            return result > 0
    
    def to_dict(self, prescription: Prescription) -> Dict[str, Any]:
        """Convertit une Prescription en dictionnaire."""
        return {
            "id": str(prescription.id),
            "customer_id": str(prescription.customer_id),
            "doctor_name": prescription.doctor_name,
            "medications": prescription.medications,
            "status": prescription.status.value if prescription.status else "pending",
            "notes": prescription.notes,
            "created_at": prescription.created_at.isoformat() if prescription.created_at else None,
        }


# ==================== STOCK MOVEMENT REPOSITORY ====================

class StockMovementRepository(BaseRepository):
    """Repository pour les mouvements de stock."""
    
    def get_by_product(self, product_id: uuid.UUID, limit: int = 50) -> List[StockMovement]:
        """Récupère les mouvements de stock d'un produit."""
        with self.get_session() as session:
            return session.query(StockMovement).filter(
                StockMovement.product_id == product_id
            ).order_by(desc(StockMovement.created_at)).limit(limit).all()
    
    def create(self, data: Dict[str, Any]) -> StockMovement:
        """Crée un nouveau mouvement de stock."""
        with self.get_session() as session:
            movement_type_str = data.get('movement_type', 'adjustment').lower()
            movement_type_map = {
                'in': StockMovementType.IN,
                'out': StockMovementType.OUT,
                'adjustment': StockMovementType.ADJUSTMENT,
                'loss': StockMovementType.LOSS,
                'return': StockMovementType.RETURN,
            }
            movement_type = movement_type_map.get(movement_type_str, StockMovementType.ADJUSTMENT)
            
            movement = StockMovement(
                id=uuid.uuid4(),
                product_id=uuid.UUID(data['product_id']) if isinstance(data['product_id'], str) else data['product_id'],
                movement_type=movement_type,
                quantity=int(data['quantity']),
                stock_after=int(data['stock_after']),
                reference_type=data.get('reference_type'),
                reference_id=uuid.UUID(data['reference_id']) if data.get('reference_id') else None,
                agent_code=data.get('agent_code'),
                reason=data.get('reason'),
            )
            session.add(movement)
            session.commit()
            session.refresh(movement)
            return movement
    
    def to_dict(self, movement: StockMovement) -> Dict[str, Any]:
        """Convertit un StockMovement en dictionnaire."""
        return {
            "id": str(movement.id),
            "product_id": str(movement.product_id),
            "movement_type": movement.movement_type.value if movement.movement_type else "adjustment",
            "quantity": movement.quantity,
            "stock_after": movement.stock_after,
            "reference_type": movement.reference_type,
            "reference_id": str(movement.reference_id) if movement.reference_id else None,
            "agent_code": movement.agent_code,
            "reason": movement.reason,
            "created_at": movement.created_at.isoformat() if movement.created_at else None,
        }
