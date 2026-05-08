"""
SQLAlchemy Models - Tables Tenant

Modèles pour les données métier stockées dans chaque base tenant.
Ces modèles remplacent les collections MongoDB existantes.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, Date, Time,
    ForeignKey, Enum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from database.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
import enum
from datetime import datetime


# ===================== ENUMS =====================

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PHARMACIST = "pharmacien"
    CASHIER = "caissier"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    ORANGE_MONEY = "orange_money"
    MTN_MONEY = "mtn_money"
    CHECK = "check"
    CREDIT = "credit"
    MIXED = "mixed"


class SaleStatus(str, enum.Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    CREDIT = "credit"
    CANCELLED = "cancelled"


class PrescriptionStatus(str, enum.Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StockMovementType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"
    LOSS = "loss"
    RETURN = "return"


class DebtStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    WRITTEN_OFF = "written_off"



class ReturnStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PromoCodeStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class DiscountRuleType(str, enum.Enum):
    LOYALTY = "loyalty"           # Fidélité client (nb achats)
    VOLUME = "volume"             # Volume d'achat (montant min)
    CATEGORY = "category"         # Catégorie de produits
    EXPIRATION = "expiration"     # Produits proches péremption
    BIRTHDAY = "birthday"         # Anniversaire client
    CUSTOMER_TYPE = "customer_type"  # Type de client (VIP, etc.)


class DiscountType(str, enum.Enum):
    PERCENT = "percent"
    AMOUNT = "amount"


class DiscountSource(str, enum.Enum):
    MANUAL = "manual"             # Rabais manuel par l'agent
    PROMO_CODE = "promo_code"     # Code promo saisi
    AUTOMATIC = "automatic"       # Règle automatique
    PRODUCT = "product"           # Rabais sur produit individuel


# ===================== MODELS =====================

class User(Base, UUIDMixin, TimestampMixin):
    """Utilisateurs de la pharmacie."""
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CASHIER)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relations
    shifts = relationship("Shift", back_populates="user", lazy="dynamic")
    shift_schedules = relationship("ShiftSchedule", back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(email='{self.email}', role='{self.role}')>"


class Category(Base, UUIDMixin, TimestampMixin):
    """Catégories de produits."""
    
    __tablename__ = "categories"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#3B82F6")  # Hex color
    markup_coefficient = Column(Float, default=1.0, nullable=False)
    min_stock = Column(Integer, nullable=True)  # Stock minimum par défaut pour cette catégorie
    
    # Relations
    products = relationship("Product", back_populates="category", lazy="dynamic")
    
    def __repr__(self):
        return f"<Category(name='{self.name}')>"


class Unit(Base, UUIDMixin, TimestampMixin):
    """Unités de mesure."""
    
    __tablename__ = "units"
    
    name = Column(String(100), nullable=False)
    abbreviation = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    
    # Relations
    products = relationship("Product", back_populates="unit", lazy="dynamic")
    
    def __repr__(self):
        return f"<Unit(name='{self.name}')>"


class Product(Base, UUIDMixin, TimestampMixin):
    """Produits (médicaments et autres)."""
    
    __tablename__ = "products"
    
    name = Column(String(255), nullable=False, index=True)
    internal_reference = Column(String(100), unique=True, nullable=True, index=True)
    barcode = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    
    # Prix
    purchase_price = Column(Float, default=0, nullable=False)  # Prix d'achat (cession)
    price = Column(Float, default=0, nullable=False)  # Prix de vente (public)
    
    # Stock
    stock = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=10, nullable=False)
    
    # Péremption
    expiration_date = Column(Date, nullable=True)
    
    # État
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relations
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=True)
    
    category = relationship("Category", back_populates="products")
    unit = relationship("Unit", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product", lazy="dynamic")
    supply_items = relationship("SupplyItem", back_populates="product", lazy="dynamic")
    stock_movements = relationship("StockMovement", back_populates="product", lazy="dynamic")
    
    __table_args__ = (
        Index("idx_product_name_barcode", "name", "barcode"),
    )
    
    def __repr__(self):
        return f"<Product(name='{self.name}', stock={self.stock})>"


class Customer(Base, UUIDMixin, TimestampMixin):
    """Clients de la pharmacie."""
    
    __tablename__ = "customers"
    
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    max_debt_limit = Column(Float, default=0.0, nullable=False)  # Limite de crédit
    
    # Relations
    sales = relationship("Sale", back_populates="customer", lazy="dynamic")
    debts = relationship("Debt", back_populates="customer", lazy="dynamic")
    prescriptions = relationship("Prescription", back_populates="customer", lazy="dynamic")
    
    def __repr__(self):
        return f"<Customer(name='{self.name}')>"


class Supplier(Base, UUIDMixin, TimestampMixin):
    """Fournisseurs."""
    
    __tablename__ = "suppliers"
    
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relations
    supplies = relationship("Supply", back_populates="supplier", lazy="dynamic")
    debts = relationship("SupplierDebt", back_populates="supplier", lazy="dynamic")
    
    def __repr__(self):
        return f"<Supplier(name='{self.name}')>"


class Sale(Base, UUIDMixin, TimestampMixin):
    """Ventes."""
    
    __tablename__ = "sales"
    
    # Référence
    sale_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Montants
    subtotal = Column(Float, nullable=False)
    discount = Column(Float, default=0, nullable=False)
    discount_type = Column(String(20), nullable=True)  # 'percent' ou 'amount'
    discount_value = Column(Float, default=0, nullable=True)  # Valeur saisie par l'utilisateur
    tax_amount = Column(Float, default=0, nullable=False)  # TVA
    total = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0, nullable=False)
    
    # Paiement
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(SaleStatus), default=SaleStatus.COMPLETED, nullable=False)
    
    # Paiement mixte (split payment)
    is_split_payment = Column(Boolean, default=False, nullable=False)
    split_payments = Column(JSON, nullable=True)  # Liste des paiements [{method, amount, details}]
    
    # Info caisse
    shift_id = Column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=True)
    agent_code = Column(String(50), nullable=True)  # Code employé qui a fait la vente
    agent_name = Column(String(255), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    
    customer = relationship("Customer", back_populates="sales")
    shift = relationship("Shift", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    debt = relationship("Debt", back_populates="sale", uselist=False)
    
    __table_args__ = (
        Index("idx_sale_date", "created_at"),
    )
    
    def __repr__(self):
        return f"<Sale(number='{self.sale_number}', total={self.total})>"


class SaleItem(Base, UUIDMixin):
    """Lignes de vente (produits vendus)."""
    
    __tablename__ = "sale_items"
    
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Snapshot des infos produit au moment de la vente
    product_name = Column(String(255), nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    # Rabais par produit
    discount_type = Column(String(20), nullable=True)  # 'percent' ou 'amount'
    discount_value = Column(Float, default=0, nullable=True)  # Valeur saisie (ex: 10 pour 10%)
    discount_amount = Column(Float, default=0, nullable=True)  # Montant calculé en devise
    discount_reason = Column(String(255), nullable=True)  # Motif du rabais
    final_subtotal = Column(Float, nullable=True)  # subtotal - discount_amount
    
    # Relations
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")
    
    def __repr__(self):
        return f"<SaleItem(product='{self.product_name}', qty={self.quantity})>"


class Supply(Base, UUIDMixin, TimestampMixin):
    """Approvisionnements (achats fournisseurs)."""
    
    __tablename__ = "supplies"
    
    # Référence
    supply_number = Column(String(50), unique=True, nullable=False, index=True)
    invoice_number = Column(String(100), nullable=True)
    delivery_note_number = Column(String(100), nullable=True)
    purchase_order_ref = Column(String(100), nullable=True)
    
    # Montants
    total_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0, nullable=False)  # TVA déductible
    
    # Validation
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validated_by = Column(String(50), nullable=True)
    created_by = Column(String(50), nullable=True)
    
    # Dates
    supply_date = Column(Date, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    
    supplier = relationship("Supplier", back_populates="supplies")
    items = relationship("SupplyItem", back_populates="supply", cascade="all, delete-orphan")
    debt = relationship("SupplierDebt", back_populates="supply", uselist=False)
    
    def __repr__(self):
        return f"<Supply(number='{self.supply_number}', total={self.total_amount})>"


class SupplyItem(Base, UUIDMixin):
    """Lignes d'approvisionnement (produits achetés)."""
    
    __tablename__ = "supply_items"
    
    supply_id = Column(UUID(as_uuid=True), ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    product_name = Column(String(255), nullable=True)  # Nom du produit pour affichage
    
    # Infos achat
    quantity = Column(Integer, nullable=False)
    purchase_price = Column(Float, nullable=False)  # Prix unitaire d'achat
    selling_price = Column(Float, nullable=False)  # Prix de vente calculé
    subtotal = Column(Float, nullable=False)
    
    # Lot et péremption
    lot_number = Column(String(100), nullable=True)  # Numéro de lot
    expiration_date = Column(Date, nullable=True)
    
    # Rayon et TVA
    shelf_location = Column(String(100), nullable=True)  # Rayon/Emplacement
    tax_rate = Column(Float, default=0)  # Taux de TVA en pourcentage
    
    # Relations
    supply = relationship("Supply", back_populates="items")
    product = relationship("Product", back_populates="supply_items")
    
    def __repr__(self):
        return f"<SupplyItem(product_id='{self.product_id}', qty={self.quantity})>"


class Shift(Base, UUIDMixin, TimestampMixin):
    """Shifts (sessions de caisse)."""
    
    __tablename__ = "shifts"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Montants
    opening_amount = Column(Float, nullable=False)
    closing_amount = Column(Float, nullable=True)
    expected_amount = Column(Float, nullable=True)
    
    # Dates
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # État
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Alertes affichées (pour éviter les répétitions)
    alert_30min_shown = Column(Boolean, default=False, nullable=False)
    alert_5min_shown = Column(Boolean, default=False, nullable=False)
    alert_end_shown = Column(Boolean, default=False, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    closing_notes = Column(Text, nullable=True)
    
    # Relations
    user = relationship("User", back_populates="shifts")
    sales = relationship("Sale", back_populates="shift", lazy="dynamic")
    
    def __repr__(self):
        return f"<Shift(user_id='{self.user_id}', active={self.is_active})>"


class ShiftSchedule(Base, UUIDMixin, TimestampMixin):
    """Planification des shifts."""
    
    __tablename__ = "shift_schedules"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Infos utilisateur (dénormalisé pour affichage rapide)
    user_code = Column(String(50), nullable=False)
    user_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    
    # Planning
    schedule_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=False)  # Format HH:MM
    end_time = Column(String(5), nullable=False)  # Format HH:MM
    max_duration_hours = Column(Float, default=8.0, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    user = relationship("User", back_populates="shift_schedules")
    
    __table_args__ = (
        UniqueConstraint("user_id", "schedule_date", name="uq_user_schedule_date"),
        Index("idx_schedule_date", "schedule_date"),
    )
    
    def __repr__(self):
        return f"<ShiftSchedule(user='{self.user_code}', date={self.schedule_date})>"


class PendingSale(Base, UUIDMixin, TimestampMixin):
    """Ventes en attente."""
    
    __tablename__ = "pending_sales"
    
    # Client
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(255), nullable=True)
    
    # Agent
    agent_code = Column(String(50), nullable=False)
    agent_name = Column(String(255), nullable=False)
    
    # Panier (stocké en JSON pour flexibilité)
    cart_items = Column(JSON, nullable=False, default=list)
    
    # Totaux
    subtotal = Column(Float, default=0, nullable=False)
    discount = Column(Float, default=0, nullable=False)
    discount_type = Column(String(20), nullable=True)  # 'percent' ou 'amount'
    discount_value = Column(Float, default=0, nullable=True)  # Valeur saisie par l'utilisateur
    total = Column(Float, default=0, nullable=False)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    customer = relationship("Customer")
    
    def __repr__(self):
        return f"<PendingSale(agent='{self.agent_code}', total={self.total})>"


class Debt(Base, UUIDMixin, TimestampMixin):
    """Dettes clients."""
    
    __tablename__ = "debts"
    
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=True, unique=True)
    
    # Montants
    original_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    
    # État
    status = Column(Enum(DebtStatus), default=DebtStatus.PENDING, nullable=False)
    
    # Dates
    due_date = Column(Date, nullable=True)
    
    # Historique des paiements (JSON pour flexibilité)
    payments = Column(JSON, default=list, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    customer = relationship("Customer", back_populates="debts")
    sale = relationship("Sale", back_populates="debt")
    
    def __repr__(self):
        return f"<Debt(customer_id='{self.customer_id}', remaining={self.remaining_amount})>"


class SupplierDebt(Base, UUIDMixin, TimestampMixin):
    """Dettes fournisseurs (créances à payer)."""
    
    __tablename__ = "supplier_debts"
    
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    supply_id = Column(UUID(as_uuid=True), ForeignKey("supplies.id"), nullable=True, unique=True)
    
    # Montants
    original_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    
    # État
    status = Column(Enum(DebtStatus), default=DebtStatus.PENDING, nullable=False)
    
    # Dates
    due_date = Column(Date, nullable=True)  # Date d'échéance (30 jours par défaut)
    
    # Historique des paiements (JSON pour flexibilité)
    # Format: [{"date": "2026-01-15", "amount": 5000, "method": "cash", "reference": "CHQ-001", "notes": "..."}]
    payments = Column(JSON, default=list, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    supplier = relationship("Supplier", back_populates="debts")
    supply = relationship("Supply", back_populates="debt")
    
    __table_args__ = (
        Index("idx_supplier_debt_status", "status"),
        Index("idx_supplier_debt_due_date", "due_date"),
    )
    
    def __repr__(self):
        return f"<SupplierDebt(supplier_id='{self.supplier_id}', remaining={self.remaining_amount})>"


class Prescription(Base, UUIDMixin, TimestampMixin):
    """Ordonnances."""
    
    __tablename__ = "prescriptions"
    
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    
    # Infos ordonnance
    doctor_name = Column(String(255), nullable=False)
    medications = Column(JSON, nullable=False, default=list)  # Liste des médicaments
    
    # État
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.PENDING, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relations
    customer = relationship("Customer", back_populates="prescriptions")
    
    def __repr__(self):
        return f"<Prescription(doctor='{self.doctor_name}', status='{self.status}')>"


class StockMovement(Base, UUIDMixin, TimestampMixin):
    """Mouvements de stock."""
    
    __tablename__ = "stock_movements"
    
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Type et quantité
    movement_type = Column(Enum(StockMovementType), nullable=False)
    quantity = Column(Integer, nullable=False)  # Positif = entrée, négatif = sortie
    
    # Stock après mouvement
    stock_after = Column(Integer, nullable=False)
    
    # Référence (vente, approvisionnement, etc.)
    reference_type = Column(String(50), nullable=True)  # "sale", "supply", "adjustment", etc.
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Agent
    agent_code = Column(String(50), nullable=True)
    
    # Raison (pour ajustements et pertes)
    reason = Column(Text, nullable=True)
    
    # Statut de validation (pour les pertes)
    validation_status = Column(String(20), default='pending', nullable=True)  # pending, validated, rejected
    validated_by = Column(String(50), nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    product = relationship("Product", back_populates="stock_movements")
    
    __table_args__ = (
        Index("idx_movement_date", "created_at"),
        Index("idx_movement_product", "product_id"),
    )
    
    def __repr__(self):
        return f"<StockMovement(type='{self.movement_type}', qty={self.quantity})>"


class Setting(Base, UUIDMixin, TimestampMixin):
    """Paramètres de la pharmacie."""
    
    __tablename__ = "settings"
    
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Setting(key='{self.key}')>"


class SaleReturn(Base, UUIDMixin, TimestampMixin):
    """Retours de ventes."""
    
    __tablename__ = "sale_returns"
    
    return_number = Column(String(50), unique=True, nullable=False, index=True)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id"), nullable=False)
    
    # Montants
    total_refund = Column(Float, default=0, nullable=False)
    
    # Infos
    reason = Column(Text, nullable=True)
    status = Column(String(20), default="completed", nullable=False)
    
    # Items retournés (JSON array)
    items = Column(JSON, default=list)
    
    # Agent qui a fait le retour
    agent_code = Column(String(50), nullable=True)
    agent_name = Column(String(255), nullable=True)
    
    # Relations
    sale = relationship("Sale", backref="returns")
    
    __table_args__ = (
        Index("idx_return_sale", "sale_id"),
        Index("idx_return_date", "created_at"),
    )
    
    def __repr__(self):
        return f"<SaleReturn(number='{self.return_number}\, refund={self.total_refund})>"




class InventorySession(Base, UUIDMixin, TimestampMixin):
    """Sessions d'inventaire physique."""
    
    __tablename__ = "inventory_sessions"
    
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="in_progress")  # in_progress, completed, cancelled
    
    # Statistiques
    total_items = Column(Integer, default=0)
    counted_items = Column(Integer, default=0)
    items_with_discrepancy = Column(Integer, default=0)
    total_positive_discrepancy = Column(Integer, default=0)
    total_negative_discrepancy = Column(Integer, default=0)
    total_discrepancy_value = Column(Float, default=0)
    
    # Validation
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validated_by = Column(String(50), nullable=True)
    validation_notes = Column(Text, nullable=True)
    adjustments_applied = Column(Boolean, default=False)
    
    # Créateur
    created_by = Column(String(50), nullable=True)
    
    # Relations
    items = relationship("InventoryItem", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<InventorySession(name='{self.name}', status='{self.status}')>"


class InventoryItem(Base, UUIDMixin):
    """Items d'une session d'inventaire."""
    
    __tablename__ = "inventory_items"
    
    session_id = Column(UUID(as_uuid=True), ForeignKey("inventory_sessions.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    
    # Infos produit (snapshot)
    product_name = Column(String(255), nullable=True)
    product_code = Column(String(100), nullable=True)
    category_name = Column(String(255), nullable=True)
    
    # Quantités
    theoretical_quantity = Column(Integer, default=0)
    original_theoretical_quantity = Column(Integer, default=0)
    actual_quantity = Column(Integer, nullable=True)
    discrepancy = Column(Integer, nullable=True)
    
    # Valeurs
    unit_cost = Column(Float, default=0)
    discrepancy_value = Column(Float, nullable=True)
    
    # Notes et MAJ auto
    notes = Column(Text, nullable=True)
    theoretical_movement_note = Column(String(255), nullable=True)
    counted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    session = relationship("InventorySession", back_populates="items")
    product = relationship("Product")
    
    def __repr__(self):
        return f"<InventoryItem(product='{self.product_name}', actual={self.actual_quantity})>"



# ===================== DISCOUNT MANAGEMENT MODELS =====================

class PromoCode(Base, UUIDMixin, TimestampMixin):
    """Codes promotionnels."""
    
    __tablename__ = "promo_codes"
    
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Type de rabais
    discount_type = Column(String(20), nullable=False)  # 'percent' ou 'amount'
    discount_value = Column(Float, nullable=False)
    
    # Conditions d'application
    min_purchase_amount = Column(Float, default=0)  # Montant minimum d'achat
    max_discount_amount = Column(Float, nullable=True)  # Plafond du rabais (pour %)
    
    # Validité
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(PromoCodeStatus), default=PromoCodeStatus.ACTIVE)
    
    # Limites d'utilisation
    max_uses = Column(Integer, nullable=True)  # Nombre max d'utilisations total
    max_uses_per_customer = Column(Integer, default=1)  # Par client
    current_uses = Column(Integer, default=0)
    
    # Restrictions
    applicable_categories = Column(JSON, nullable=True)  # Liste des catégories concernées
    applicable_products = Column(JSON, nullable=True)  # Liste des produits concernés
    customer_types = Column(JSON, nullable=True)  # Types de clients autorisés
    first_purchase_only = Column(Boolean, default=False)  # Première commande uniquement
    
    # Créateur
    created_by = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f"<PromoCode(code='{self.code}', value={self.discount_value})>"


class DiscountRule(Base, UUIDMixin, TimestampMixin):
    """Règles de rabais automatiques."""
    
    __tablename__ = "discount_rules"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(Enum(DiscountRuleType), nullable=False)
    
    # Type de rabais
    discount_type = Column(String(20), nullable=False)  # 'percent' ou 'amount'
    discount_value = Column(Float, nullable=False)
    max_discount_amount = Column(Float, nullable=True)  # Plafond
    
    # Conditions selon le type de règle
    conditions = Column(JSON, nullable=True)
    # Exemples de conditions:
    # LOYALTY: {"min_purchases": 50}
    # VOLUME: {"min_amount": 100000}
    # CATEGORY: {"category_ids": [...], "min_quantity": 3}
    # EXPIRATION: {"days_before_expiry": 30}
    # BIRTHDAY: {} (vérifie la date d'anniversaire du client)
    # CUSTOMER_TYPE: {"customer_types": ["vip", "professionnel"]}
    
    # Priorité (si plusieurs règles s'appliquent, prendre celle avec la plus haute priorité)
    priority = Column(Integer, default=0)
    
    # Cumul
    is_cumulative = Column(Boolean, default=False)  # Peut se cumuler avec d'autres rabais?
    
    # Activation
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Créateur
    created_by = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f"<DiscountRule(name='{self.name}', type='{self.rule_type}')>"


class DiscountHistory(Base, UUIDMixin, TimestampMixin):
    """Historique des rabais accordés."""
    
    __tablename__ = "discount_history"
    
    # Référence à la vente
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id", ondelete="SET NULL"), nullable=True)
    sale_number = Column(String(50), nullable=True, index=True)
    
    # Source du rabais
    discount_source = Column(Enum(DiscountSource), nullable=False)
    
    # Références optionnelles
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="SET NULL"), nullable=True)
    promo_code = Column(String(50), nullable=True)
    discount_rule_id = Column(UUID(as_uuid=True), ForeignKey("discount_rules.id", ondelete="SET NULL"), nullable=True)
    rule_name = Column(String(255), nullable=True)
    
    # Produit concerné (si rabais par produit)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=True)
    
    # Client
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    customer_name = Column(String(255), nullable=True)
    
    # Détails du rabais
    discount_type = Column(String(20), nullable=False)  # 'percent' ou 'amount'
    discount_value = Column(Float, nullable=False)  # Valeur (ex: 10 pour 10%)
    discount_amount = Column(Float, nullable=False)  # Montant effectif en devise
    
    # Contexte
    original_amount = Column(Float, nullable=True)  # Montant avant rabais
    final_amount = Column(Float, nullable=True)  # Montant après rabais
    reason = Column(String(255), nullable=True)  # Motif/justification
    
    # Agent
    agent_code = Column(String(50), nullable=True)
    agent_name = Column(String(255), nullable=True)
    
    # Index pour les rapports
    __table_args__ = (
        Index("idx_discount_history_date", "created_at"),
        Index("idx_discount_history_source", "discount_source"),
        Index("idx_discount_history_agent", "agent_code"),
    )
    
    def __repr__(self):
        return f"<DiscountHistory(sale='{self.sale_number}', amount={self.discount_amount})>"


class PromoCodeUsage(Base, UUIDMixin, TimestampMixin):
    """Suivi de l'utilisation des codes promo par client."""
    
    __tablename__ = "promo_code_usages"
    
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    sale_id = Column(UUID(as_uuid=True), ForeignKey("sales.id", ondelete="SET NULL"), nullable=True)
    
    discount_amount = Column(Float, nullable=False)
    
    __table_args__ = (
        Index("idx_promo_usage_code", "promo_code_id"),
        Index("idx_promo_usage_customer", "customer_id"),
    )
