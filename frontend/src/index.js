import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Enregistrer le service worker pour la PWA
serviceWorkerRegistration.register({
  onSuccess: (registration) => {
    console.log('[App] PWA prête pour une utilisation hors ligne');
  },
  onUpdate: (registration) => {
    console.log('[App] Nouvelle version de l\'application disponible');
  },
});