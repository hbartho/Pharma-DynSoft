"""
Repositories PostgreSQL - Couche d'accès aux données

Fournit des méthodes CRUD pour chaque entité utilisant SQLAlchemy.
Les méthodes retournent des dictionnaires pour éviter les problèmes de session détachée.
"""

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, date, timedelta
import uuid

from database.config import db_manager
from database.models_tenant import (
    User, Category, Unit, Product, Customer, Supplier,
    Sale, SaleItem, Supply, SupplyItem, Shift, ShiftSchedule,
    PendingSale, Debt, Prescription, StockMovement, Setting,
    UserRole, PaymentMethod, SaleStatus, DebtStatus, PrescriptionStatus
)


def _to_dict_user(user: User) -> Dict[str, Any]:
    """Convertit un User en dictionnaire."""
    return {
        "id": str(user.id),
        "email": user.email,
        "password": user.password_hash,  # Pour l'authentification
        "name": user.name,
        "employee_code": user.employee_code,
        "role": user.role.value if user.role else "caissier",
        "phone": user.phone,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def _to_dict_category(category: Category) -> Dict[str, Any]:
    """Convertit une Category en dictionnaire."""
    return {
        "id": str(category.id),
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "markup_coefficient": category.markup_coefficient,
        "min_stock": category.min_stock,
        "created_at": category.created_at.isoformat() if category.created_at else None,
    }


def _to_dict_unit(unit: Unit) -> Dict[str, Any]:
    """Convertit une Unit en dictionnaire."""
    return {
        "id": str(unit.id),
        "name": unit.name,
        "abbreviation": unit.abbreviation,
        "description": unit.description,
        "created_at": unit.created_at.isoformat() if unit.created_at else None,
    }


def _to_dict_product(product: Product) -> Dict[str, Any]:
    """Convertit un Product en dictionnaire."""
    return {
        "id": str(product.id),
        "name": product.name,
        "internal_reference": product.internal_reference,
        "barcode": product.barcode,
        "description": product.description,
        "purchase_price": product.purchase_price,
        "price": product.price,
        "stock": product.stock,
        "min_stock": product.min_stock,
        "expiration_date": product.expiration_date.isoformat() if product.expiration_date else None,
        "is_active": product.is_active,
        "category_id": str(product.category_id) if product.category_id else None,
        "unit_id": str(product.unit_id) if product.unit_id else None,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


def _to_dict_customer(customer: Customer) -> Dict[str, Any]:
    """Convertit un Customer en dictionnaire."""
    return {
        "id": str(customer.id),
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "notes": customer.notes,
        "is_active": customer.is_active,
        "max_debt_limit": customer.max_debt_limit if hasattr(customer, 'max_debt_limit') else 0.0,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
    }


def _to_dict_supplier(supplier: Supplier) -> Dict[str, Any]:
    """Convertit un Supplier en dictionnaire."""
    return {
        "id": str(supplier.id),
        "name": supplier.name,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at.isoformat() if supplier.created_at else None,
    }


# ==================== BASE REPOSITORY ====================

class BaseRepository:
    """Repository de base avec méthodes communes."""
    
    def __init__(self, tenant_slug: str = "pharmacie_centrale"):
        self.tenant_slug = tenant_slug
    
    def get_session(self):
        """Récupère une session synchrone."""
        return db_manager.get_tenant_session(self.tenant_slug)


# ==================== USER REPOSITORY ====================

class UserRepository(BaseRepository):
    """Repository pour les utilisateurs."""
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par email."""
        with self.get_session() as session:
            user = session.query(User).filter(User.email == email).first()
            return _to_dict_user(user) if user else None
    
    def get_by_id(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par ID."""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            return _to_dict_user(user) if user else None
    
    def get_by_id_str(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par ID string."""
        try:
            return self.get_by_id(uuid.UUID(user_id))
        except (ValueError, AttributeError):
            return None
    
    def get_by_employee_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Récupère un utilisateur par code employé."""
        with self.get_session() as session:
            user = session.query(User).filter(User.employee_code == code).first()
            return _to_dict_user(user) if user else None
    
    def get_all(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Récupère tous les utilisateurs."""
        with self.get_session() as session:
            query = session.query(User)
            if not include_inactive:
                query = query.filter(User.is_active == True)
            users = query.all()
            return [_to_dict_user(u) for u in users]
    
    def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouvel utilisateur."""
        with self.get_session() as session:
            user = User(
                id=uuid.uuid4(),
                email=user_data['email'],
                password_hash=user_data['password'],
                name=user_data['name'],
                employee_code=user_data['employee_code'],
                role=UserRole(user_data.get('role', 'caissier')),
                phone=user_data.get('phone'),
                is_active=True,
            )
            session.add(user)
            session.flush()
            result = _to_dict_user(user)
            session.commit()
            return result
    
    def update(self, user_id: uuid.UUID, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un utilisateur."""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            for key, value in user_data.items():
                if key == 'role':
                    value = UserRole(value)
                if key == 'password':
                    key = 'password_hash'
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_user(user)
            session.commit()
            return result


# ==================== CATEGORY REPOSITORY ====================

class CategoryRepository(BaseRepository):
    """Repository pour les catégories."""
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Récupère toutes les catégories."""
        with self.get_session() as session:
            categories = session.query(Category).all()
            return [_to_dict_category(c) for c in categories]
    
    def get_by_id(self, category_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère une catégorie par ID UUID."""
        with self.get_session() as session:
            category = session.query(Category).filter(Category.id == category_id).first()
            return _to_dict_category(category) if category else None
    
    def get_by_id_str(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une catégorie par ID string."""
        try:
            return self.get_by_id(uuid.UUID(category_id))
        except (ValueError, AttributeError):
            return None
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée une nouvelle catégorie."""
        with self.get_session() as session:
            category = Category(
                id=data.get('id') or uuid.uuid4(),
                name=data['name'],
                description=data.get('description'),
                color=data.get('color', '#3B82F6'),
                markup_coefficient=float(data.get('markup_coefficient', 1.0)),
                min_stock=data.get('min_stock'),
            )
            session.add(category)
            session.flush()
            result = _to_dict_category(category)
            session.commit()
            return result
    
    def update(self, category_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour une catégorie."""
        with self.get_session() as session:
            category = session.query(Category).filter(Category.id == category_id).first()
            if not category:
                return None
            
            for key, value in data.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            
            category.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_category(category)
            session.commit()
            return result
    
    def update_by_id_str(self, category_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour une catégorie par ID string."""
        try:
            return self.update(uuid.UUID(category_id), data)
        except (ValueError, AttributeError):
            return None
    
    def delete(self, category_id: uuid.UUID) -> bool:
        """Supprime une catégorie."""
        with self.get_session() as session:
            result = session.query(Category).filter(Category.id == category_id).delete()
            session.commit()
            return result > 0
    
    def delete_by_id_str(self, category_id: str) -> bool:
        """Supprime une catégorie par ID string."""
        try:
            return self.delete(uuid.UUID(category_id))
        except (ValueError, AttributeError):
            return False


# ==================== UNIT REPOSITORY ====================

class UnitRepository(BaseRepository):
    """Repository pour les unités."""
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Récupère toutes les unités."""
        with self.get_session() as session:
            units = session.query(Unit).all()
            return [_to_dict_unit(u) for u in units]
    
    def get_by_id(self, unit_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère une unité par ID."""
        with self.get_session() as session:
            unit = session.query(Unit).filter(Unit.id == unit_id).first()
            return _to_dict_unit(unit) if unit else None
    
    def get_by_id_str(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une unité par ID string."""
        try:
            return self.get_by_id(uuid.UUID(unit_id))
        except (ValueError, AttributeError):
            return None
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Récupère une unité par nom (case-insensitive)."""
        with self.get_session() as session:
            unit = session.query(Unit).filter(Unit.name.ilike(name)).first()
            return _to_dict_unit(unit) if unit else None
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée une nouvelle unité."""
        with self.get_session() as session:
            unit = Unit(
                id=data.get('id') or uuid.uuid4(),
                name=data['name'],
                abbreviation=data.get('abbreviation'),
                description=data.get('description'),
            )
            session.add(unit)
            session.flush()
            result = _to_dict_unit(unit)
            session.commit()
            return result
    
    def update(self, unit_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour une unité."""
        with self.get_session() as session:
            unit = session.query(Unit).filter(Unit.id == unit_id).first()
            if not unit:
                return None
            
            for key, value in data.items():
                if hasattr(unit, key):
                    setattr(unit, key, value)
            
            unit.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_unit(unit)
            session.commit()
            return result
    
    def update_by_id_str(self, unit_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour une unité par ID string."""
        try:
            return self.update(uuid.UUID(unit_id), data)
        except (ValueError, AttributeError):
            return None
    
    def delete(self, unit_id: uuid.UUID) -> bool:
        """Supprime une unité."""
        with self.get_session() as session:
            result = session.query(Unit).filter(Unit.id == unit_id).delete()
            session.commit()
            return result > 0
    
    def delete_by_id_str(self, unit_id: str) -> bool:
        """Supprime une unité par ID string."""
        try:
            return self.delete(uuid.UUID(unit_id))
        except (ValueError, AttributeError):
            return False


# ==================== PRODUCT REPOSITORY ====================

class ProductRepository(BaseRepository):
    """Repository pour les produits."""
    
    def get_all(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Récupère tous les produits."""
        with self.get_session() as session:
            query = session.query(Product)
            if not include_inactive:
                query = query.filter(Product.is_active == True)
            products = query.order_by(Product.name).all()
            return [_to_dict_product(p) for p in products]
    
    def get_by_id(self, product_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère un produit par ID."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            return _to_dict_product(product) if product else None
    
    def get_by_id_str(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un produit par ID string."""
        try:
            return self.get_by_id(uuid.UUID(product_id))
        except (ValueError, AttributeError):
            return None
    
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Récupère un produit par nom (case-insensitive)."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.name.ilike(name)).first()
            return _to_dict_product(product) if product else None
    
    def get_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Récupère un produit par code-barres."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.barcode == barcode).first()
            return _to_dict_product(product) if product else None
    
    def get_by_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """Récupère un produit par référence interne."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.internal_reference == reference).first()
            return _to_dict_product(product) if product else None
    
    def get_by_category(self, category_id: str) -> List[Dict[str, Any]]:
        """Récupère les produits d'une catégorie."""
        with self.get_session() as session:
            try:
                cat_uuid = uuid.UUID(category_id)
                products = session.query(Product).filter(Product.category_id == cat_uuid).all()
                return [_to_dict_product(p) for p in products]
            except (ValueError, AttributeError):
                return []
    
    def get_by_unit(self, unit_id: str) -> List[Dict[str, Any]]:
        """Récupère les produits utilisant une unité."""
        with self.get_session() as session:
            try:
                unit_uuid = uuid.UUID(unit_id)
                products = session.query(Product).filter(Product.unit_id == unit_uuid).all()
                return [_to_dict_product(p) for p in products]
            except (ValueError, AttributeError):
                return []
    
    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Recherche des produits par nom, code-barres ou référence."""
        with self.get_session() as session:
            search_pattern = f"%{query}%"
            products = session.query(Product).filter(
                and_(
                    Product.is_active == True,
                    or_(
                        Product.name.ilike(search_pattern),
                        Product.barcode.ilike(search_pattern),
                        Product.internal_reference.ilike(search_pattern)
                    )
                )
            ).limit(limit).all()
            return [_to_dict_product(p) for p in products]
    
    def get_low_stock(self) -> List[Dict[str, Any]]:
        """Récupère les produits en stock bas."""
        with self.get_session() as session:
            products = session.query(Product).filter(
                and_(
                    Product.is_active == True,
                    Product.stock <= Product.min_stock
                )
            ).all()
            return [_to_dict_product(p) for p in products]
    
    def get_expiring_soon(self, days: int = 30) -> List[Dict[str, Any]]:
        """Récupère les produits proches de la péremption."""
        with self.get_session() as session:
            threshold = date.today() + timedelta(days=days)
            products = session.query(Product).filter(
                and_(
                    Product.is_active == True,
                    Product.expiration_date != None,
                    Product.expiration_date <= threshold
                )
            ).all()
            return [_to_dict_product(p) for p in products]
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouveau produit."""
        with self.get_session() as session:
            product = Product(
                id=uuid.uuid4(),
                name=data['name'],
                internal_reference=data.get('internal_reference'),
                barcode=data.get('barcode'),
                description=data.get('description'),
                purchase_price=float(data.get('purchase_price', 0)),
                price=float(data.get('price', 0)),
                stock=int(data.get('stock', 0)),
                min_stock=int(data.get('min_stock', 10)),
                expiration_date=data.get('expiration_date'),
                is_active=True,
                category_id=uuid.UUID(data['category_id']) if data.get('category_id') else None,
                unit_id=uuid.UUID(data['unit_id']) if data.get('unit_id') else None,
            )
            session.add(product)
            session.flush()
            result = _to_dict_product(product)
            session.commit()
            return result
    
    def update(self, product_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un produit."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            for key, value in data.items():
                if key in ['category_id', 'unit_id'] and value:
                    value = uuid.UUID(value) if isinstance(value, str) else value
                if hasattr(product, key):
                    setattr(product, key, value)
            
            product.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_product(product)
            session.commit()
            return result
    
    def update_stock(self, product_id: uuid.UUID, quantity_change: int) -> Optional[Dict[str, Any]]:
        """Met à jour le stock d'un produit."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            product.stock += quantity_change
            if product.stock < 0:
                product.stock = 0
            
            product.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_product(product)
            session.commit()
            return result
    
    def toggle_status(self, product_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Active/désactive un produit."""
        with self.get_session() as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            product.is_active = not product.is_active
            product.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_product(product)
            session.commit()
            return result
    
    def delete(self, product_id: uuid.UUID) -> bool:
        """Supprime un produit."""
        with self.get_session() as session:
            result = session.query(Product).filter(Product.id == product_id).delete()
            session.commit()
            return result > 0
    
    def delete_by_id_str(self, product_id: str) -> bool:
        """Supprime un produit par ID string."""
        try:
            return self.delete(uuid.UUID(product_id))
        except (ValueError, AttributeError):
            return False
    
    def update_by_id_str(self, product_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un produit par ID string."""
        try:
            return self.update(uuid.UUID(product_id), data)
        except (ValueError, AttributeError):
            return None
    
    def toggle_status_by_id_str(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Active/désactive un produit par ID string."""
        try:
            return self.toggle_status(uuid.UUID(product_id))
        except (ValueError, AttributeError):
            return None
    
    def update_stock_by_id_str(self, product_id: str, quantity_change: int) -> Optional[Dict[str, Any]]:
        """Met à jour le stock par ID string."""
        try:
            return self.update_stock(uuid.UUID(product_id), quantity_change)
        except (ValueError, AttributeError):
            return None


# ==================== CUSTOMER REPOSITORY ====================

class CustomerRepository(BaseRepository):
    """Repository pour les clients."""
    
    def get_all(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Récupère tous les clients."""
        with self.get_session() as session:
            query = session.query(Customer)
            if not include_inactive:
                query = query.filter(Customer.is_active == True)
            customers = query.order_by(Customer.name).all()
            return [_to_dict_customer(c) for c in customers]
    
    def get_by_id(self, customer_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère un client par ID."""
        with self.get_session() as session:
            customer = session.query(Customer).filter(Customer.id == customer_id).first()
            return _to_dict_customer(customer) if customer else None
    
    def get_by_id_str(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un client par ID string."""
        try:
            return self.get_by_id(uuid.UUID(customer_id))
        except (ValueError, AttributeError):
            return None
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Recherche des clients par nom ou téléphone."""
        with self.get_session() as session:
            search_pattern = f"%{query}%"
            customers = session.query(Customer).filter(
                and_(
                    Customer.is_active == True,
                    or_(
                        Customer.name.ilike(search_pattern),
                        Customer.phone.ilike(search_pattern)
                    )
                )
            ).all()
            return [_to_dict_customer(c) for c in customers]
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouveau client."""
        with self.get_session() as session:
            customer = Customer(
                id=uuid.uuid4(),
                name=data['name'],
                phone=data.get('phone'),
                email=data.get('email'),
                address=data.get('address'),
                notes=data.get('notes'),
                is_active=True,
            )
            session.add(customer)
            session.flush()
            result = _to_dict_customer(customer)
            session.commit()
            return result
    
    def update(self, customer_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un client."""
        try:
            with self.get_session() as session:
                customer = session.query(Customer).filter(Customer.id == customer_id).first()
                if not customer:
                    return None
                
                for key, value in data.items():
                    if hasattr(customer, key):
                        setattr(customer, key, value)
                
                customer.updated_at = datetime.now(timezone.utc)
                session.flush()
                result = _to_dict_customer(customer)
                session.commit()
                return result
        except Exception as e:
            print(f"[ERROR] CustomerRepository.update: {e}")
            return None
    
    def update_by_id_str(self, customer_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un client par ID string."""
        try:
            return self.update(uuid.UUID(customer_id), data)
        except (ValueError, AttributeError):
            return None
    
    def delete(self, customer_id: uuid.UUID) -> bool:
        """Supprime un client."""
        with self.get_session() as session:
            result = session.query(Customer).filter(Customer.id == customer_id).delete()
            session.commit()
            return result > 0
    
    def delete_by_id_str(self, customer_id: str) -> bool:
        """Supprime un client par ID string."""
        try:
            return self.delete(uuid.UUID(customer_id))
        except (ValueError, AttributeError):
            return False


# ==================== SUPPLIER REPOSITORY ====================

class SupplierRepository(BaseRepository):
    """Repository pour les fournisseurs."""
    
    def get_all(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Récupère tous les fournisseurs."""
        with self.get_session() as session:
            query = session.query(Supplier)
            if not include_inactive:
                query = query.filter(Supplier.is_active == True)
            suppliers = query.order_by(Supplier.name).all()
            return [_to_dict_supplier(s) for s in suppliers]
    
    def get_by_id(self, supplier_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Récupère un fournisseur par ID."""
        with self.get_session() as session:
            supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
            return _to_dict_supplier(supplier) if supplier else None
    
    def get_by_id_str(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un fournisseur par ID string."""
        try:
            return self.get_by_id(uuid.UUID(supplier_id))
        except (ValueError, AttributeError):
            return None
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Crée un nouveau fournisseur."""
        with self.get_session() as session:
            supplier = Supplier(
                id=uuid.uuid4(),
                name=data['name'],
                phone=data.get('phone'),
                email=data.get('email'),
                address=data.get('address'),
                is_active=True,
            )
            session.add(supplier)
            session.flush()
            result = _to_dict_supplier(supplier)
            session.commit()
            return result
    
    def update(self, supplier_id: uuid.UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un fournisseur."""
        with self.get_session() as session:
            supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
            if not supplier:
                return None
            
            for key, value in data.items():
                if hasattr(supplier, key):
                    setattr(supplier, key, value)
            
            supplier.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_supplier(supplier)
            session.commit()
            return result
    
    def update_by_id_str(self, supplier_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Met à jour un fournisseur par ID string."""
        try:
            return self.update(uuid.UUID(supplier_id), data)
        except (ValueError, AttributeError):
            return None
    
    def toggle_status(self, supplier_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Active/désactive un fournisseur."""
        with self.get_session() as session:
            supplier = session.query(Supplier).filter(Supplier.id == supplier_id).first()
            if not supplier:
                return None
            
            supplier.is_active = not supplier.is_active
            supplier.updated_at = datetime.now(timezone.utc)
            session.flush()
            result = _to_dict_supplier(supplier)
            session.commit()
            return result
    
    def toggle_status_by_id_str(self, supplier_id: str) -> Optional[Dict[str, Any]]:
        """Active/désactive un fournisseur par ID string."""
        try:
            return self.toggle_status(uuid.UUID(supplier_id))
        except (ValueError, AttributeError):
            return None
    
    def delete(self, supplier_id: uuid.UUID) -> bool:
        """Supprime un fournisseur."""
        with self.get_session() as session:
            result = session.query(Supplier).filter(Supplier.id == supplier_id).delete()
            session.commit()
            return result > 0
    
    def delete_by_id_str(self, supplier_id: str) -> bool:
        """Supprime un fournisseur par ID string."""
        try:
            return self.delete(uuid.UUID(supplier_id))
        except (ValueError, AttributeError):
            return False


# ==================== SETTINGS REPOSITORY ====================

class SettingsRepository(BaseRepository):
    """Repository pour les paramètres."""
    
    def get_all(self) -> Dict[str, Any]:
        """Récupère tous les paramètres sous forme de dictionnaire."""
        with self.get_session() as session:
            settings = session.query(Setting).all()
            return {s.key: s.value for s in settings}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Récupère un paramètre par clé."""
        with self.get_session() as session:
            setting = session.query(Setting).filter(Setting.key == key).first()
            return setting.value if setting else default
    
    def set(self, key: str, value: Any, description: str = None) -> Dict[str, Any]:
        """Définit un paramètre."""
        with self.get_session() as session:
            setting = session.query(Setting).filter(Setting.key == key).first()
            if setting:
                setting.value = value
                if description:
                    setting.description = description
                setting.updated_at = datetime.now(timezone.utc)
            else:
                setting = Setting(
                    id=uuid.uuid4(),
                    key=key,
                    value=value,
                    description=description,
                )
                session.add(setting)
            
            session.commit()
            return {"key": key, "value": value}
    
    def delete(self, key: str) -> bool:
        """Supprime un paramètre."""
        with self.get_session() as session:
            result = session.query(Setting).filter(Setting.key == key).delete()
            session.commit()
            return result > 0
