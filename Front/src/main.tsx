import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

const storedTheme = localStorage.getItem('theme');
if (storedTheme === 'dark' || (!storedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
  document.documentElement.classList.add('dark');
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

// ============================================
// SERVICE WORKER — DESACTIVADO temporalmente
// Pantalla blanca por cache corrupto en Vercel
// ============================================

// if ('serviceWorker' in navigator) {
//   if (import.meta.env.PROD) {
//     window.addEventListener('load', () => {
//       navigator.serviceWorker.register('/sw.js');
//     });
//   } else {
//     window.addEventListener('load', async () => {
//       const registrations = await navigator.serviceWorker.getRegistrations();
//       for (const reg of registrations) {
//         await reg.unregister();
//       }
//       const keys = await caches.keys();
//       await Promise.all(keys.map((k) => caches.delete(k)));
//     });
//   }
// }
