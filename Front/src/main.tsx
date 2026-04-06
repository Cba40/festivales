import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

// ============================================
// SERVICE WORKER — MVP TEMPORAL
// Desregistrar SWs existentes para limpiar caché vieja
// ============================================

if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      // 1. Desregistrar TODOS los service workers existentes
      const registrations = await navigator.serviceWorker.getRegistrations()
      for (const registration of registrations) {
        await registration.unregister()
        console.log('✅ SW desregistrado:', registration.scope)
      }
      
      // 2. Limpiar caches de Cache API (si existen)
      const cacheNames = await caches.keys()
      for (const cacheName of cacheNames) {
        await caches.delete(cacheName)
        console.log('🗑️ Cache eliminado:', cacheName)
      }
      
      console.log('✅ Limpieza de SW/caché completada')
    } catch (err) {
      console.warn('⚠️ Error limpiando SW:', err)
    }
  })
}

// ✅ NO registrar nuevo SW por ahora (MVP testing)
// TODO: Re-activar registro cuando sw.js esté implementado correctamente
