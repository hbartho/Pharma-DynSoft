"""
Routes Payment Methods - PostgreSQL Implementation
Gère les modes de paiement via la table settings
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import json

from models.payment_method import (
    PaymentMethod, PaymentMethodCreate, PaymentMethodUpdate,
    SalePayment, SalePaymentCreate
)
from auth import get_current_user
import os

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])

# Configuration base de données
DATABASE_TYPE = os.environ.get("DB_TYPE", "postgresql")

if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from sqlalchemy import text
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def get_payment_methods_from_db():
        """Récupérer les modes de paiement depuis la table settings"""
        with get_session() as session:
            result = session.execute(
                text("SELECT value FROM public.settings WHERE key = 'payment_methods'")
            ).fetchone()
            
            if result and result[0]:
                methods = result[0] if isinstance(result[0], list) else json.loads(result[0])
                return methods
            
            # Retourner les méthodes par défaut si aucune n'existe
            return get_default_payment_methods()
    
    def save_payment_methods_to_db(methods: List[dict]):
        """Sauvegarder les modes de paiement dans la table settings"""
        with get_session() as session:
            # Vérifier si l'entrée existe
            result = session.execute(
                text("SELECT id FROM public.settings WHERE key = 'payment_methods'")
            ).fetchone()
            
            methods_json = json.dumps(methods)
            
            if result:
                session.execute(
                    text("UPDATE public.settings SET value = :value WHERE key = 'payment_methods'"),
                    {"value": methods_json}
                )
            else:
                session.execute(
                    text("INSERT INTO public.settings (id, key, value, description) VALUES (:id, 'payment_methods', :value, 'Modes de paiement disponibles')"),
                    {"id": str(uuid.uuid4()), "value": methods_json}
                )
            
            session.commit()
    
    def get_default_payment_methods():
        """Retourner les modes de paiement par défaut"""
        return [
            {"id": "cash", "code": "cash", "name": "Espèces", "icon": "banknote", "color": "green", "is_active": True, "display_order": 1, "required_fields": []},
            {"id": "orange_money", "code": "orange_money", "name": "Orange Money", "icon": "smartphone", "color": "orange", "is_active": True, "display_order": 2, "required_fields": [
                {"name": "sender_number", "label": "N° Destinataire", "type": "tel", "required": True, "placeholder": "Ex: 620 XX XX XX", "minLength": 9, "maxLength": 12},
                {"name": "ticket_ref", "label": "Réf. Paiement Marchand", "type": "text", "required": True, "placeholder": "Ex: MP260120.2211.A09378", "minLength": 10}
            ]},
            {"id": "mtn_money", "code": "mtn_money", "name": "MTN Money", "icon": "smartphone", "color": "yellow", "is_active": True, "display_order": 3, "required_fields": [
                {"name": "sender_number", "label": "N° Destinataire", "type": "tel", "required": True, "placeholder": "Ex: 660 XX XX XX", "minLength": 9, "maxLength": 12},
                {"name": "ticket_ref", "label": "Réf. Paiement Marchand", "type": "text", "required": True, "placeholder": "Ex: MP260120.2211.A09378", "minLength": 10}
            ]},
            {"id": "card", "code": "card", "name": "Carte bancaire", "icon": "credit-card", "color": "purple", "is_active": True, "display_order": 4, "required_fields": [
                {"name": "last_digits", "label": "N° Carte (4 derniers chiffres)", "type": "text", "required": True, "maxLength": 4, "placeholder": "Ex: 1234"},
                {"name": "holder_name", "label": "Propriétaire", "type": "text", "required": True, "placeholder": "Ex: Jean Dupont", "minLength": 2},
                {"name": "bank", "label": "Banque", "type": "text", "required": True, "placeholder": "Ex: BICIGUI, SGBG...", "minLength": 2}
            ]},
            {"id": "check", "code": "check", "name": "Chèque", "icon": "file-check", "color": "blue", "is_active": True, "display_order": 5, "required_fields": [
                {"name": "check_number", "label": "N° Chèque", "type": "text", "required": True, "placeholder": "Ex: 0012345", "minLength": 5},
                {"name": "bank", "label": "Banque", "type": "text", "required": True, "placeholder": "Ex: BICIGUI, SGBG...", "minLength": 2}
            ]},
            {"id": "credit", "code": "credit", "name": "Crédit", "icon": "wallet", "color": "red", "is_active": True, "display_order": 6, "required_fields": []}
        ]

    # ============== ROUTES ==============
    
    @router.get("", response_model=List[dict])
    async def get_payment_methods(
        active_only: bool = False,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les modes de paiement"""
        methods = get_payment_methods_from_db()
        
        # Normaliser les données (s'assurer que 'code' existe)
        normalized_methods = []
        for m in methods:
            method = dict(m)
            # Si 'code' n'existe pas, utiliser 'id' comme code
            if not method.get('code'):
                method['code'] = method.get('id', 'unknown')
            normalized_methods.append(method)
        
        if active_only:
            normalized_methods = [m for m in normalized_methods if m.get("is_active", True)]
        
        # Trier par display_order
        normalized_methods.sort(key=lambda x: x.get("display_order", 99))
        
        return normalized_methods

    @router.get("/{method_id}", response_model=dict)
    async def get_payment_method(
        method_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer un mode de paiement par ID"""
        methods = get_payment_methods_from_db()
        
        for method in methods:
            if method.get("id") == method_id or method.get("code") == method_id:
                return method
        
        raise HTTPException(status_code=404, detail="Mode de paiement non trouvé")

    @router.post("", response_model=dict)
    async def create_payment_method(
        method_data: PaymentMethodCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Créer un nouveau mode de paiement (Admin uniquement)"""
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        
        methods = get_payment_methods_from_db()
        
        # Vérifier si le code existe déjà
        for m in methods:
            if m.get("code") == method_data.code:
                raise HTTPException(status_code=400, detail=f"Le code '{method_data.code}' existe déjà")
        
        new_method = {
            "id": str(uuid.uuid4()),
            "code": method_data.code,
            "name": method_data.name,
            "icon": method_data.icon or "credit-card",
            "color": method_data.color or "gray",
            "is_active": True,
            "display_order": len(methods) + 1,
            "required_fields": method_data.required_fields or [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        methods.append(new_method)
        save_payment_methods_to_db(methods)
        
        return new_method

    @router.put("/{method_id}", response_model=dict)
    async def update_payment_method(
        method_id: str,
        method_data: PaymentMethodUpdate,
        current_user: dict = Depends(get_current_user)
    ):
        """Mettre à jour un mode de paiement (Admin uniquement)"""
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        
        methods = get_payment_methods_from_db()
        
        for i, method in enumerate(methods):
            if method.get("id") == method_id or method.get("code") == method_id:
                # Mettre à jour les champs
                update_dict = method_data.model_dump(exclude_unset=True)
                for key, value in update_dict.items():
                    if value is not None:
                        methods[i][key] = value
                
                methods[i]["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                save_payment_methods_to_db(methods)
                return methods[i]
        
        raise HTTPException(status_code=404, detail="Mode de paiement non trouvé")

    @router.delete("/{method_id}")
    async def delete_payment_method(
        method_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Supprimer un mode de paiement (Admin uniquement)"""
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        
        methods = get_payment_methods_from_db()
        
        # Trouver et supprimer la méthode
        original_count = len(methods)
        methods = [m for m in methods if m.get("id") != method_id and m.get("code") != method_id]
        
        if len(methods) == original_count:
            raise HTTPException(status_code=404, detail="Mode de paiement non trouvé")
        
        save_payment_methods_to_db(methods)
        
        return {"message": "Mode de paiement supprimé"}

    # ============== PAIEMENTS DE VENTE ==============
    
    @router.get("/sale/{sale_id}/payments", response_model=List[dict])
    async def get_sale_payments(
        sale_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les paiements d'une vente"""
        # Les paiements sont stockés dans la vente elle-même
        from database.repositories_extended import SaleRepository
        
        repo = SaleRepository()
        sale = repo.get_by_id_str(sale_id)
        
        if not sale:
            return []
        
        # Retourner le paiement principal de la vente
        return [{
            "id": str(uuid.uuid4()),
            "sale_id": sale_id,
            "payment_method_code": sale.get("payment_method", "cash"),
            "amount": sale.get("amount_paid", 0),
            "created_at": sale.get("created_at")
        }]

    @router.post("/sale/payment", response_model=dict)
    async def create_sale_payment(
        payment_data: SalePaymentCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Créer un paiement pour une vente"""
        from database.repositories_extended import SaleRepository
        
        repo = SaleRepository()
        sale = repo.get_by_id_str(payment_data.sale_id)
        
        if not sale:
            raise HTTPException(status_code=404, detail="Vente non trouvée")
        
        # Vérifier que le mode de paiement existe
        methods = get_payment_methods_from_db()
        method = next((m for m in methods if m.get("id") == payment_data.payment_method_id or m.get("code") == payment_data.payment_method_id), None)
        
        if not method:
            raise HTTPException(status_code=404, detail="Mode de paiement non trouvé")
        
        payment = {
            "id": str(uuid.uuid4()),
            "sale_id": payment_data.sale_id,
            "payment_method_id": payment_data.payment_method_id,
            "payment_method_code": method.get("code"),
            "payment_method_name": method.get("name"),
            "amount": payment_data.amount,
            "reference": payment_data.reference,
            "notes": payment_data.notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user.get("id")
        }
        
        return payment



# Routes supplémentaires pour la vérification OTP
payments_router = APIRouter(prefix="/payments", tags=["payments"])

@payments_router.post("/verify-otp")
async def verify_otp(
    otp_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Vérifier un code OTP pour un paiement Mobile Money.
    Note: Ceci est une simulation - en production, intégrer avec l'API réelle du provider.
    """
    phone = otp_data.get("phone")
    otp_code = otp_data.get("otp_code")
    transaction_id = otp_data.get("transaction_id")
    
    if not phone or not otp_code:
        raise HTTPException(status_code=400, detail="Numéro de téléphone et code OTP requis")
    
    # Simulation: accepter le code "123456" pour les tests
    # En production, appeler l'API du provider (Orange Money, MTN, etc.)
    if otp_code == "123456":
        return {
            "success": True,
            "message": "Code OTP vérifié avec succès",
            "transaction_id": transaction_id or str(uuid.uuid4()),
            "verified_at": datetime.now(timezone.utc).isoformat()
        }
    
    raise HTTPException(status_code=400, detail="Code OTP invalide")

