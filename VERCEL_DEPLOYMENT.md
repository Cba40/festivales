# ✅ VERCEL DEPLOYMENT CHECKLIST — BUILD FIX APLICADO

## 🚨 PROBLEMA DIAGNOSTICADA

**Síntoma:** Build completado en 54ms (imposible para React+Vite)  
**Causa raíz:** Vercel NO estaba ejecutando `npm run build`  
**Razón:** Auto-detección de framework fallaba

---

## 📋 Cambios Aplicados (Commit `c0a1c86`)

### 1. ✅ `vercel.json` (REESCRITO)
- `"framework": null` → fuerza comandos explícitos
- `"version": 2` → versión explícita
- Build commands explícitos
- Rewrites para SPA routing

### 2. ✅ `vite.config.ts` (MODIFICADO)
- `emptyOutDir: true` → limpia dist/ antes de build
- `outDir: 'dist'` → coincide con vercel.json
- Configuración simplificada

### 3. ✅ `package.json` (MODIFICADO)
- Script `vercel-build` agregado (fallback de Vercel)
- Build ahora incluye `tsc` (typecheck antes de build)

### 4. ✅ `.nvmrc` (NUEVO)
- Node 18.18.0 para compatibilidad
- Evita problemas de versión en Vercel

---

## 🚀 Estado del Deploy

**Commit:** `c0a1c86` - fix: forzar build correcto en Vercel con framework null  
**Push:** ✅ Completado  
**Branch:** `main` → `origin/main`  
**Vercel:** Auto-deploy triggerado (esperar ~2-3 minutos)

**URL:** https://festivales-mocha.vercel.app/

**Build local:** ✅ 12.66s (vs 54ms anterior)  
**dist/ generado:** ✅ Con index.html + assets

---

## 🧪 VALIDACIÓN POST-DEPLOY

### ✅ Lo que DEBES ver en los logs de Vercel:

```
✅ Running "npm install"
✅ Running "npm run build" (o "npm run vercel-build")
✅ "tsc && vite build" → debe tardar ~30-60s (NO 54ms)
✅ dist/ generado con archivos
✅ Rewrites aplicados
✅ Deployment Ready (verde)
```

### ❌ Lo que NO debe aparecer:

```
❌ "Compilación completada en 54ms"
❌ "Se omite la carga de la caché"
❌ "No build files found"
❌ Skip build
```

### Test en navegador (desktop):

1. **Abrir URL:** https://festivales-mocha.vercel.app/
2. **Navegar a rutas internas:**
   - `/estacionar`
   - `/salir`
   - `/emergencia`
   - `/servicios/transporte`
3. **Recargar página (F5) en cada ruta** → NO debe dar 404
4. **Abrir DevTools Console** → NO debe haber errores rojos

### Test en celular (móvil):

1. Abrir URL en Chrome/Safari
2. Navegar a `/salir`
3. **Recargar página** → debe funcionar
4. Probar botón "🗺️ Ir ahora" → debe abrir Google Maps
5. Verificar que no hay pantalla blanca

### Test de service worker (PWA):

1. Abrir DevTools → Application → Service Workers
2. Verificar que `sw.js` está registrado
3. Test offline mode (opcional)

---

## 🔍 DIAGNÓSTICO DE ERRORES

### Si hay 404 en rutas internas:

**Causa:** vercel.json no se aplicó correctamente  
**Fix:** Verificar que `vercel.json` está en la raíz del repo (Front/)

```bash
# Verificar que el archivo existe
ls Front/vercel.json

# Verificar contenido
cat Front/vercel.json
```

### Si hay pantalla blanca:

**Causa:** `base` incorrecto en vite.config.ts  
**Fix:** Confirmar que es `base: '/'` y NO `base: '/festivales-mocha'`

```bash
# Verificar configuración
cat Front/vite.config.ts
```

### Si el build falla en Vercel:

**Causa:** Node version o dependencias  
**Fix:** Verificar logs de build en Vercel Dashboard

1. Ir a: https://vercel.com/Cba40/festivales
2. Click en el deploy fallido
3. Revisar "Build Logs"

### Si los assets no cargan:

**Causa:** Paths relativos mal resueltos  
**Fix:** Verificar que `base: '/'` está configurado

---

## 📊 EXPECTATIVA

### ✅ Deploy Exitoso:

- [ ] Homepage carga correctamente
- [ ] Todas las rutas internas funcionan
- [ ] Recargar página NO da 404
- [ ] Console sin errores rojos
- [ ] App funcional en móvil
- [ ] Botones "Ir ahora" abren Google Maps

### ⚠️ Si algo falla:

Proporcionar para diagnóstico:
1. URL exacta donde falla
2. Error en Console (F12)
3. Vercel Build Logs (si hay error de build)
4. Screenshot del problema

---

## 🕐 TIEMPO ESTIMADO

- **Deploy en Vercel:** ~2-3 minutos
- **Propagación DNS:** Inmediato (ya está configurado)
- **Validación completa:** ~5 minutos

**Próxima verificación:** Abrir https://festivales-mocha.vercel.app/ en 2-3 minutos

---

**Última actualización:** 6 de abril de 2026  
**Commit:** `c0a1c86`  
**Build local:** 12.66s (tsc + vite build)  
**Próxima verificación:** Revisar logs de Vercel en 2-3 minutos

---

## 🔗 LINKS IMPORTANTES

- **Dashboard Vercel:** https://vercel.com/Cba40/festivales
- **Deploy en curso:** https://vercel.com/Cba40/festivales/deployments
- **Build Logs:** Click en el deployment más reciente → "Build Logs"
- **App:** https://festivales-mocha.vercel.app/
