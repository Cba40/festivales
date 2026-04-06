import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

// Service Worker desactivado temporalmente para testing MVP
// El sw.js no existe actualmente y causa problemas de caché en móvil
// TODO: Re-activar cuando se implemente sw.js correctamente
/*
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js?v=' + Date.now())
      .then((reg) => console.log('SW registrado:', reg.scope))
      .catch((err) => console.log('SW error:', err));
  });
}
*/
