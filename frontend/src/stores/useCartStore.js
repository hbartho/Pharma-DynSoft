/**
 * Zustand Store - Panier de vente
 * Gère le panier de vente en cours
 */

import { create } from 'zustand';

const useCartStore = create((set, get) => ({
  // ============================================
  // Cart State
  // ============================================
  items: [],
  customer: null,
  discount: 0,
  notes: '',
  prescriptionId: null,

  // ============================================
  // Item Actions
  // ============================================
  addItem: (product, quantity = 1) => set((state) => {
    const existingIndex = state.items.findIndex((item) => item.product_id === product.id);
    
    if (existingIndex >= 0) {
      // Mettre à jour la quantité
      const newItems = [...state.items];
      const maxQty = product.quantity_in_stock || 999;
      newItems[existingIndex] = {
        ...newItems[existingIndex],
        quantity: Math.min(newItems[existingIndex].quantity + quantity, maxQty),
      };
      return { items: newItems };
    }
    
    // Ajouter un nouvel item
    return {
      items: [
        ...state.items,
        {
          product_id: product.id,
          product_name: product.name,
          unit_price: product.selling_price,
          purchase_price: product.purchase_price,
          quantity,
          max_quantity: product.quantity_in_stock || 999,
          unit: product.unit || 'unité',
        },
      ],
    };
  }),

  updateItemQuantity: (productId, quantity) => set((state) => {
    if (quantity <= 0) {
      return { items: state.items.filter((item) => item.product_id !== productId) };
    }
    return {
      items: state.items.map((item) =>
        item.product_id === productId
          ? { ...item, quantity: Math.min(quantity, item.max_quantity) }
          : item
      ),
    };
  }),

  removeItem: (productId) => set((state) => ({
    items: state.items.filter((item) => item.product_id !== productId),
  })),

  // ============================================
  // Customer Actions
  // ============================================
  setCustomer: (customer) => set({ customer }),
  clearCustomer: () => set({ customer: null }),

  // ============================================
  // Discount & Notes
  // ============================================
  setDiscount: (discount) => set({ discount: Math.max(0, Math.min(100, discount)) }),
  setNotes: (notes) => set({ notes }),
  setPrescriptionId: (prescriptionId) => set({ prescriptionId }),

  // ============================================
  // Calculations
  // ============================================
  getSubtotal: () => {
    return get().items.reduce((sum, item) => sum + item.unit_price * item.quantity, 0);
  },

  getDiscountAmount: () => {
    const subtotal = get().getSubtotal();
    return (subtotal * get().discount) / 100;
  },

  getTotal: () => {
    return get().getSubtotal() - get().getDiscountAmount();
  },

  getItemCount: () => {
    return get().items.reduce((sum, item) => sum + item.quantity, 0);
  },

  getMargin: () => {
    return get().items.reduce((sum, item) => {
      const margin = (item.unit_price - item.purchase_price) * item.quantity;
      return sum + margin;
    }, 0);
  },

  // ============================================
  // Cart Actions
  // ============================================
  clearCart: () => set({
    items: [],
    customer: null,
    discount: 0,
    notes: '',
    prescriptionId: null,
  }),

  // Préparer les données pour l'API
  getSaleData: () => {
    const state = get();
    return {
      customer_id: state.customer?.id || null,
      items: state.items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
      discount_percentage: state.discount,
      notes: state.notes,
      prescription_id: state.prescriptionId,
    };
  },

  // Vérifier si le panier est vide
  isEmpty: () => get().items.length === 0,

  // Vérifier si un produit est dans le panier
  hasProduct: (productId) => get().items.some((item) => item.product_id === productId),

  // Obtenir la quantité d'un produit dans le panier
  getProductQuantity: (productId) => {
    const item = get().items.find((item) => item.product_id === productId);
    return item?.quantity || 0;
  },
}));

export default useCartStore;
