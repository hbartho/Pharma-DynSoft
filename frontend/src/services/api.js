import axios from 'axios';
import { getUserData, clearUserData } from './indexedDB';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  headers: {
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Expires': '0'
  }
});

// Request interceptor to add token
api.interceptors.request.use(
  async (config) => {
    const userData = await getUserData();
    if (userData && userData.token) {
      config.headers.Authorization = `Bearer ${userData.token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const errorDetail = error.response?.data?.detail || '';
      
      // Vérifier si c'est une session invalidée (connexion depuis un autre appareil)
      if (errorDetail.includes('SESSION_INVALIDATED')) {
        // Effacer les données locales
        await clearUserData();
        
        // Afficher un message et rediriger
        alert('Votre session a été invalidée car vous vous êtes connecté depuis un autre appareil.');
        window.location.href = '/login';
      } else {
        // Token expiré ou invalide - rediriger simplement
        await clearUserData();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;