# 🎯 GUÍA PASO A PASO - FIX VERCEL PARA MONOREPO

## 🚨 PROBLEMA RAÍZ

Tu repo tiene esta estructura:
```
festivales/
├── Front/          ← React + Vite app (TU FRONTEND)
├── Back/           ← Backend (si existe)
└── vercel.json     ← Configuración de Vercel
```

**Vercel está buscando en la raíz del repo** pero tu frontend está en `Front/`.

---

## ✅ SOLUCIÓN: Configurar Root Directory en Vercel

### PASO 1: Ir a Vercel Dashboard

**URL:** https://vercel.com/Cba40/festivales/settings/general

### PASO 2: Cambiar Root Directory

1. Buscar **"Root Directory"** (Directorio Raíz)
2. Click en **"Edit"**
3. Escribir: `Front`
4. Click **"Save"**

**Screenshot esperado:**
```
Root Directory: Front/
```

### PASO 3: Verificar Build Settings

En la misma página, verificar que diga:
```
Framework: Other
Build Command: npm run build
Output Directory: dist
Install Command: npm install
```

Si no coincide, cambiar manualmente.

### PASO 4: Eliminar Production Override (si existe)

1. Buscar **"Production Overrides"** en Settings
2. Si hay alguna override, eliminarla con 🗑️
3. Click **"Save"**

### PASO 5: Forzar Redeploy

1. Ir a: https://vercel.com/Cba40/festivales/deployments
2. Click en el deploy más reciente
3. Click **"Redeploy"** (botón arriba a la derecha)
4. Confirmar

---

## 🧪 VALIDACIÓN

### En Vercel Build Logs:

**✅ Lo que DEBES ver:**
```
✅ Changing to directory: Front/
✅ Running "npm install"
✅ Running "npm run build"
✅ > tsc && vite build
✓ 1503 modules transformed.
✓ built in ~30-60s
✅ dist/ generado con 7 archivos
✅ Deployment Ready (verde)
```

**❌ Lo que NO debe aparecer:**
```
❌ "Compilación completada en 54ms"
❌ "Se omite la carga de la caché"
❌ "Skip build"
❌ "No build files found"
❌ "Changing to directory: /"  ← DEBE decir Front/
```

### En Navegador:

1. Abrir: https://festivales-mocha.vercel.app/
2. ✅ Homepage carga correctamente
3. ✅ Navegar a `/salir`, `/estacionar`, `/emergencia`
4. ✅ Recargar página (F5) → NO debe dar 404
5. ✅ Console (F12) → SIN errores rojos
6. ✅ Test en celular → debe funcionar

---

## 📋 CHECKLIST FINAL

- [ ] Root Directory configurado a `Front` en Vercel Settings
- [ ] Production Override eliminada (si existía)
- [ ] Build Settings verificados (build, output, install)
- [ ] Redeploy forzado desde Dashboard
- [ ] Build Logs muestran "Changing to directory: Front/"
- [ ] Build tarda ~30-60s (NO 54ms)
- [ ] dist/ generado con 7 archivos
- [ ] App carga en https://festivales-mocha.vercel.app/
- [ ] Rutas internas funcionan (/salir, /estacionar)
- [ ] Recargar página NO da 404
- [ ] Console sin errores rojos

---

## 🔗 LINKS IMPORTANTES

- **Settings:** https://vercel.com/Cba40/festivales/settings/general
- **Deployments:** https://vercel.com/Cba40/festivales/deployments
- **App:** https://festivales-mocha.vercel.app/
- **Repo:** https://github.com/Cba40/festivales

---

## 📞 SI SIGUE FALLANDO

### Pasá este output para diagnóstico:

```bash
# 1. Mostrar estructura del repo
cd d:\CBA 4.0\Festivales
dir /s /b package.json vite.config.ts

# 2. Mostrar contenido de Front/package.json (scripts)
cd Front
cat package.json | grep -A 5 "scripts"

# 3. Build local
npm run build
dir dist /b
```

---

**Próximo paso:** Seguir los 5 pasos de arriba y confirmar resultado. 🚀
