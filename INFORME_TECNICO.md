# 📊 INFORME TÉCNICO — MVP Festivales Jesús María

> **Fecha de generación:** 3 de abril de 2026
> **Estado del proyecto:** ~85% completado (MVP funcional)
> **Directorio raíz:** `d:\CBA 4.0\Festivales\Front`

---

## 1. 📊 RESUMEN EJECUTIVO

| Campo | Valor |
|-------|-------|
| **Nombre** | Festival Jesús María — Sistema de Decisión |
| **Objetivo** | Guiar asistentes del evento en tiempo real: estacionamiento, emergencias, evacuación |
| **Estado** | MVP funcional con 5 pantallas, PWA base, datos mock |
| **% Completado** | ~85% (núcleo completo, pendiente backend + test offline) |
| **Fecha** | 3 de abril de 2026 |

---

## 2. 🛠️ STACK TECNOLÓGICO

### Frontend
| Tecnología | Versión | Uso |
|------------|---------|-----|
| React | 18.3.1 | UI library |
| TypeScript | 5.5.3 | Tipado estático |
| React Router DOM | 6.20.0 | Navegación SPA |
| Vite | 5.4.2 | Build tool + dev server |
| TailwindCSS | 3.4.1 | Utility-first CSS |
| Lucide React | 0.344.0 | Iconografía |
| PostCSS | — | Procesamiento CSS |
| Autoprefixer | — | Vendor prefixes |

### PWA
| Feature | Archivo |
|---------|---------|
| Manifest | `public/manifest.json` |
| Service Worker | `public/sw.js` |
| Icono 192px | `public/icon-192.svg` |
| Icono 512px | `public/icon-512.svg` |
| Offline Hook | `src/hooks/useOffline.ts` |

### Datos
| Tipo | Archivos |
|------|----------|
| Mock data | `src/data/mockZones.ts`, `mockEmergencia.ts`, `mockSalidas.ts`, `mockResolver.ts` |
| Types | `src/types/index.ts` |

### Herramientas
| Herramienta | Versión |
|-------------|---------|
| Node.js | v22.x |
| npm | — |
| ESLint | 9.9.1 |
| VS Code + Qwen AI | — |

### Dependencias no utilizadas
| Paquete | Versión | Estado |
|---------|---------|--------|
| @supabase/supabase-js | 2.57.4 | Instalado, sin inicializar |

---

## 3. 📁 ESTRUCTURA DE CARPETAS

```
Front/
├── public/
│   ├── manifest.json
│   ├── sw.js
│   ├── icon-192.svg
│   └── icon-512.svg
├── src/
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── ActionButton.tsx
│   │   ├── StatusBanner.tsx
│   │   └── ZonaCard.tsx
│   ├── screens/
│   │   ├── Home.tsx
│   │   ├── Estacionar.tsx
│   │   ├── Emergencia.tsx
│   │   ├── Salir.tsx
│   │   └── ResolverAhora.tsx
│   ├── data/
│   │   ├── mockZones.ts
│   │   ├── mockEmergencia.ts
│   │   ├── mockSalidas.ts
│   │   └── mockResolver.ts
│   ├── types/
│   │   └── index.ts
│   ├── hooks/
│   │   └── useOffline.ts
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   └── vite-env.d.ts
├── .gitignore
├── eslint.config.js
├── index.html
├── package.json
├── package-lock.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
└── vite.config.ts
```

**Total:** 26 archivos fuente (excluyendo node_modules, dist, .git, lock files)

---

## 4. 🖥️ PANTALLAS IMPLEMENTADAS

### 4.1 Home.tsx
| Campo | Valor |
|-------|-------|
| **Propósito** | Punto de entrada principal |
| **Estado local** | Ninguno (solo navegación) |
| **Archivo** | `src/screens/Home.tsx` |

**Componentes usados:**
- `Header` — título "Festival Jesús María" + ubicación "Zona Centro"
- `StatusBanner` — estado "alerta", mensaje "Zona con alta demanda"
- `QuickAction` (x7) — grid de accesos rápidos y servicios
- Botón secundario — "Resolver ahora"

**Navegación:**
| Botón | Ruta destino |
|-------|-------------|
| 🚨 Emergencia | `/emergencia` |
| 🚗 Estacionar | `/estacionar` |
| 🚪 Salir | `/salir` |
| ❓ Resolver ahora | `/resolver-ahora` |
| 🚌 Transporte | `alert('Próximamente')` |
| 🍽 Comer | `alert('Puntos de comida cercanos')` |
| 🛏 Descansar | `alert('Zonas de descanso')` |
| 🧭 Servicios | `alert('Otros servicios')` |

**Estructura visual:**
```
Header → StatusBanner → Accesos Rápidos (3-col) → Servicios (4-col) → Resolver Ahora (secundario)
```

---

### 4.2 Estacionar.tsx
| Campo | Valor |
|-------|-------|
| **Propósito** | Guiar usuario a zona de estacionamiento disponible |
| **Archivo** | `src/screens/Estacionar.tsx` (~420 líneas) |
| **Estado local** | `selectedZone: Zona \| null` |
| **Datos** | `mockZones.ts` (4 zonas) |

**4 modos de renderizado condicional:**

| Modo | Condición | UI |
|------|-----------|-----|
| **INFORMAR** | `!getModoGuiar()` | Lista de zonas disponibles como cards clickeables |
| **ASISTIR** | Zonas disponibles, no todas colapsadas | Zona recomendada (ZonaCard primaria) + fallback (ZonaCard fallback) + lista otras zonas |
| **GUIAR** | Todas colapsadas | Advertencia + 2 estrategias (ir lejos / esperar 15-20 min) |
| **GUIAR COMPLETO** | 6 bloques | Estado zona actual + acción principal + tiempo estimado + riesgo + fallback + advertencia + botón mapa |

**Lógica de scoring:**
```typescript
Score = disponibilidadScore + tendenciaScore + (distancia_min * -1)

disponibilidadScore: bajo=100, medio=60, alto=20, colapsado=0
tendenciaScore: bajando=+20, estable=0, subiendo=-10
```

**Flujo:**
```
Home → Estacionar → Calcula score → Determina modo → Muestra zonas
→ Click en zona → Bottom sheet → "Iniciar ruta" → Google Maps
```

**Coordenadas reales (Jesús María, Córdoba):**
| Zona | Lat | Lng | Referencia |
|------|-----|-----|------------|
| Zona Centro (actual) | -30.978107 | -64.094779 | Plaza Principal / Iglesia |
| Zona Norte | -30.973313 | -64.088529 | Barrio Norte / Terminal |
| Zona Oeste | -30.981249 | -64.099398 | Parque Autódromo |
| Zona Sur | -30.985337 | -64.094209 | Predio Ferial / Costanera |

---

### 4.3 Emergencia.tsx
| Campo | Valor |
|-------|-------|
| **Propósito** | Protocolo de acción en emergencia |
| **Archivo** | `src/screens/Emergencia.tsx` (~440 líneas) |
| **Estado local** | `selectedType`, `helpSubType`, `inconsciente`, `bottomSheet`, `mostrarLlamar` |
| **Datos** | `mockEmergencia.ts` |

**3 tipos de emergencia:**
| Tipo | Emoji | Protocolo |
|------|-------|-----------|
| Niño Perdido | 👶 | "QUEDATE EN EL LUGAR" → Buscar personal seguridad → Fallback: punto seguro |
| Persona Herida | 🤕 | "NO LA MUEVAS" → Toggle inconsciente (alerta pulsante) → Buscar ayuda → Fallback: puesto sanitario |
| Necesito Ayuda | 🆘 | Sub-tipos: Seguridad / Salud / Orientación |

**Patrón de timeout:**
```typescript
useEffect(() => {
  const timer = setTimeout(() => setMostrarLlamar(true), 5000)
  return () => clearTimeout(timer)
}, [])
```
Botón "Llamar ahora" aparece después de 5 segundos de inactividad.

**Datos de emergencia:**
| Recurso | Cantidad | Ejemplo |
|---------|----------|---------|
| Puntos Seguros | 3 | Destacamento Policial, Puesto de Salud Municipal, Oficina de Información |
| Puestos Sanitarios | 2 | Puesto Sanitario Principal, Posta Médica Norte |

**Flujo:**
```
Home → Emergencia → Selección tipo → Sub-tipo (si aplica)
→ Protocolo específico → Llamar / Ver punto seguro → Google Maps
```

---

### 4.4 Salir.tsx
| Campo | Valor |
|-------|-------|
| **Propósito** | Evacuación del evento |
| **Archivo** | `src/screens/Salir.tsx` |
| **Estado local** | `tipo: 'auto' \| 'transporte' \| 'peatonal'`, `selectedZona: ZonaSalida \| null` |
| **Datos** | `mockSalidas.ts` (5 zonas) |

**Estructura visual (orden exacto):**
```
1. Selector (Auto / Transporte / Caminando) — grid 3 columnas
2. Mensaje principal — "Dirigite ahora a {nombre}"
3. Bloque principal (compacto) — referencia, distancia, congestión, timestamp, tiempo estimado
4. Alternativa — "Si está saturado → {nombre}"
5. Advertencia — zona colapsada (si aplica)
6. Acción — "Iniciar ruta" → Google Maps
```

**Lógica de scoring diferenciada por tipo:**
```typescript
Score base: distancia <= 5min → 1, <= 10min → 2, > 10min → 3
Penalización congestión: baja=1, media=2, alta=4, colapsado=6

Ajuste por tipo:
  Auto:        +3 si congestión alta/colapsado (evitar calles trabadas)
  Transporte:  +espera_estimada_min (considerar demora)
  Peatonal:    +2 si es_embudo (evitar cuellos de botella)
```

**Filtrado cruzado por tipo:**
| Tipo seleccionado | Zonas incluidas |
|-------------------|-----------------|
| Auto | `tipo === 'auto'` + `tipo === 'peatonal'` |
| Transporte | `tipo === 'transporte'` + `tipo === 'peatonal'` |
| Peatonal | `tipo === 'peatonal'` + `tipo === 'auto'` |

**Zonas de salida (coordenadas reales):**
| Zona | Tipo | Lat | Lng | Referencia | Congestión |
|------|------|-----|-----|------------|------------|
| Salida Norte | auto | -30.973313 | -64.088529 | Terminal de Ómnibus | media |
| Salida Sur | transporte | -30.985337 | -64.094209 | Predio Ferial | baja |
| Salida Este | peatonal | -30.981249 | -64.075000 | Av. Colón y Costanera | baja |
| Salida Oeste | auto | -30.981249 | -64.099398 | Parque Autódromo | alta |
| Salida Centro | peatonal | -30.978107 | -64.094779 | Plaza Principal / Iglesia | colapsado |

**Confirmación: cambiar tipo cambia la recomendación**
| Tipo | Mejor zona | Score aproximado |
|------|-----------|-----------------|
| Auto | Salida Norte | 2 (distancia) + 2 (congestión) = 4 |
| Transporte | Salida Sur | 2 (distancia) + 1 (congestión) + 2 (espera) = 5 |
| Peatonal | Salida Este | 2 (distancia) + 1 (congestión) = 3 |

---

### 4.5 ResolverAhora.tsx
| Campo | Valor |
|-------|-------|
| **Propósito** | Decisión automática sin preguntar al usuario |
| **Archivo** | `src/screens/ResolverAhora.tsx` |
| **Estado local** | `selectedZona: ZonaSalida \| Zona \| null` |
| **Datos** | `mockResolver.ts` + `mockZones.ts` + `mockSalidas.ts` |

**7 reglas de inferencia:**

| # | Regla | Condición | Tipo | Modo | Confianza |
|---|-------|-----------|------|------|-----------|
| 1 | Llegada | 18:00–21:00 | estacionar | guiar | alta |
| 2 | Pico/Ingreso | 21:00–23:00 | estacionar | guiar | alta |
| 3 | Dentro evento | 22:00–01:00 | salir | asistir | media |
| 4 | Salida masiva | 00:00–02:00 | salir | guiar | alta |
| 5 | Colapsado total | saturación = colapsada | salir | guiar | baja |
| 6 | Repite acción | ultimaAccion = 'estacionar' | estacionar | asistir | media |
| 7 | Fallback | ninguna aplica | fallback | informar | baja |

**Estructura visual — Inferencia exitosa (80%):**
```
1. Contexto (zona, hora, saturación) — texto pequeño
2. Mensaje principal — bg-primary, texto grande
3. Zona principal — bg-success, clickable → bottom sheet
4. Alternativa — bg-slate-100, clickable
5. Botón "Iniciar ruta" — Google Maps
6. Indicador de confianza — ✅ / ⚠️
```

**Estructura visual — Fallback (20%):**
```
Contexto → "No estoy seguro qué necesitás..." → 3 opciones máximo:
  🚗 Moverme → /estacionar
  🚪 Salir → /salir
  🚨 Emergencia → /emergencia
```

---

## 5. 🧠 LÓGICA DE NEGOCIO

### 5.1 Scoring System — Estacionar

**Archivo:** `src/data/mockZones.ts`

```typescript
Score = disponibilidadScore + tendenciaScore + (distancia_min * -1)

disponibilidadScore:
  bajo → 100
  medio → 60
  alto → 20
  colapsado → 0

tendenciaScore:
  bajando → +20
  estable → 0
  subiendo → -10
```

Mayor score = mejor opción. Se ordena descendente.

### 5.2 Scoring System — Salir

**Archivo:** `src/data/mockSalidas.ts`

```typescript
Score base:
  distancia <= 5 min → 1
  distancia <= 10 min → 2
  distancia > 10 min → 3

Penalización congestión:
  baja → 1
  media → 2
  alta → 4
  colapsado → 6

Ajuste por tipo:
  Auto:        +3 si congestión alta/colapsado
  Transporte:  +espera_estimada_min
  Peatonal:    +2 si es_embudo
```

Menor score = mejor opción. Se ordena ascendente.

### 5.3 Inferencia — Resolver Ahora

**Archivo:** `src/data/mockResolver.ts`

```typescript
function inferirNecesidad(hora, saturacion, zonaActual, ultimaAccion): ResultadoInferencia

Reglas (se evalúan en orden, primera que aplica gana):
  1. hora 18-21 → estacionar (llegada)
  2. hora 21-23 → estacionar guiar (pico)
  3. hora 22-01 → salir asistir (dentro evento)
  4. hora 00-02 → salir guiar (salida masiva)
  5. saturacion colapsada → salir guiar (zona lejana)
  6. ultimaAccion === 'estacionar' → estacionar asistir
  7. fallback → 3 opciones
```

### 5.4 Modos de Respuesta

| Modo | Cuándo se activa | UI resultante |
|------|------------------|---------------|
| **INFORMAR** | Baja saturación, zonas disponibles | Lista de opciones clickeables |
| **ASISTIR** | Media saturación, algunas zonas disponibles | 1 recomendada + 1 alternativa |
| **GUIAR** | Alta/Colapsada saturación | Decisión directiva + alternativas limitadas |
| **FALLBACK** | Ninguna regla de inferencia aplica | 3 opciones máximo |

---

## 6. 🔄 FLUJOS CRÍTICOS

```
┌─────────────────────────────────────────────────────────────────┐
│                              HOME                                │
│  Header + StatusBanner + Accesos Rápidos + Servicios + Resolver  │
└─────────────────────────────────────────────────────────────────┘
                               │
    ┌──────────────────────────┼──────────────────────────┐
    ▼                          ▼                          ▼
┌──────────┐          ┌──────────────┐          ┌──────────────┐
│Emergencia│          │ Estacionar   │          │    Salir     │
│ 3 tipos  │          │ 4 modos      │          │ 3 tipos trans│
└──────────┘          └──────────────┘          └──────────────┘
    │                          │                          │
    ▼                          ▼                          ▼
┌──────────┐          ┌──────────────┐          ┌──────────────┐
│Protocolo │          │ Score +      │          │ Score por    │
│ Acción   │          │ ZonaCard     │          │ tipo + cards │
│ Timeout  │          │ Bottom Sheet │          │ Bottom Sheet │
│ 5 seg    │          └──────────────┘          └──────────────┘
└──────────┘                   │                          │
    │                          └──────────┬───────────────┘
    ▼                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Google Maps (window.open)                     │
│  https://www.google.com/maps/dir/?api=1&destination=lat,lng     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        Resolver Ahora                            │
│  Inferencia automática (7 reglas por hora + saturación + zona)  │
│  → 80%: 1 decisión + 1 alternativa → Google Maps                │
│  → 20%: 3 opciones máximo → rutas existentes                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 🎨 SISTEMA DE DISEÑO

### Colores (tailwind.config.js)

| Token | Hex | Uso |
|-------|-----|-----|
| `primary` | `#1e3a8a` | Headers, botones principales, navegación |
| `success` | `#22c55e` | Zonas disponibles, estado positivo |
| `warning` | `#f59e0b` | Banners alerta, estado "alto" |
| `danger` | `#dc2626` | Emergencias, estado crítico, colapsado |

**Escala secundaria:**
| Uso | Clases Tailwind |
|-----|-----------------|
| Fondo claro | `bg-gray-50`, `bg-white` |
| Fondo oscuro | `dark:bg-slate-800`, `dark:bg-slate-900` |
| Texto secundario | `text-slate-500`, `text-slate-600` |
| Bordes | `border-slate-200`, `border-slate-300` |

### Componentes Reutilizables

| Componente | Archivo | Props principales |
|------------|---------|-------------------|
| **Header** | `components/Header.tsx` | `title`, `showBack?`, `onBack?`, `ubicacion?` |
| **ActionButton** | `components/ActionButton.tsx` | `icon`, `label`, `onClick`, `variant?`, `size?` |
| **QuickAction** | `components/ActionButton.tsx` | `emoji`, `label`, `onClick` |
| **StatusBanner** | `components/StatusBanner.tsx` | `estado`, `mensaje` |
| **ZonaCard** | `components/ZonaCard.tsx` | `zona`, `tipo`, `distanciaTexto?`, `accionTexto?` |

### Patrones UX

| Principio | Implementación |
|-----------|---------------|
| Texto imperativo | "Dirigite a...", "Quedate en el lugar", "No la muevas" (<5 palabras) |
| Máximo 2 opciones | Principal + alternativa en Estacionar/Salir/ResolverAhora |
| Mapa como apoyo | Botón secundario, nunca automático |
| Timeout emergencia | Botón "Llamar" aparece a los 5 segundos |
| Bottom sheet consistente | Backdrop + panel fijo + drag handle en todas las pantallas |

### Dark Mode

Implementado vía `darkMode: 'media'` en Tailwind (sigue preferencia del SO).
Todas las pantallas tienen variantes `dark:` en colores, fondos y bordes.

---

## 8. 📱 PWA FEATURES

| Feature | Estado | Archivo | Detalle |
|---------|--------|---------|---------|
| Manifest | ✅ | `public/manifest.json` | short_name: "Festival JM", display: standalone, orientation: portrait |
| Service Worker | ✅ | `public/sw.js` | Cache: `festival-jm-v1` |
| Iconos | ✅ | `public/icon-192.svg`, `icon-512.svg` | purpose: `any maskable` |
| Offline Hook | ✅ | `src/hooks/useOffline.ts` | Hook `useOffline()` → boolean |
| Registro SW | ✅ | `src/main.tsx` | `navigator.serviceWorker.register('/sw.js')` |

### Service Worker — Estrategias de caché

| Tipo de request | Estrategia |
|-----------------|------------|
| Navegación (HTML) | Cache-first |
| Assets estáticos (`.js`, `.css`, `/assets/`) | Cache-first |
| API (`/api/`) | Network-first con fallback a caché |
| Default | Network |

### Ciclo de vida del SW

1. **Install:** Precachea `/`, `/index.html`, `/manifest.json`, iconos → `skipWaiting()`
2. **Activate:** Borra caches viejos → `clients.claim()`
3. **Fetch:** Intercepta requests y aplica estrategia según tipo

---

## 9. ✅ FEATURES IMPLEMENTADAS

| Módulo | Estado | Validado | Notas |
|--------|--------|----------|-------|
| Home | ✅ | ✅ | 8 quick actions, botón secundario |
| Estacionar | ✅ | ✅ | 4 modos, scoring, bottom sheet |
| Emergencia | ✅ | ✅ | 3 tipos, sub-tipos, timeout 5s |
| Salir | ✅ | ✅ | 3 tipos, score diferenciado, 5 zonas |
| Resolver Ahora | ✅ | ✅ | 7 reglas inferencia, fallback 3 opciones |
| PWA Base | ✅ | ⚠️ | SW registrado, pendiente test offline real |
| Rutas | ✅ | ✅ | 5 rutas en React Router |
| Dark Mode | ✅ | ✅ | Todas las pantallas |
| Google Maps | ✅ | ✅ | `window.open` con coordenadas reales |
| Backend Supabase | ❌ | — | Dependencia instalada, sin usar |

---

## 10. 📋 PENDIENTES

| Feature | Prioridad | Tiempo Est. | Detalle |
|---------|-----------|-------------|---------|
| Test offline real | Alta | 15 min | F12 → Offline → recargar → verificar SW |
| Backend Supabase | Alta | 3-4 hs | Reemplazar mock data con tablas reales |
| Panel municipal | Media | 3-4 hs | Interfaz para actualizar estados de zonas |
| Pantallas secundarias (Comer/Descansar) | Baja | 1-2 hs | Actualmente solo `alert()` placeholders |
| Tests automatizados | Baja | 2-3 hs | Vitest/Jest + React Testing Library |
| Extraer BottomSheet como componente | Baja | 30 min | Patrón duplicado en 3 pantallas |
| Geolocalización real | Media | 1-2 hs | Reemplazar zona fija con GPS del dispositivo |

---

## 11. 📊 MÉTRICAS DEL PROYECTO

| Métrica | Valor |
|---------|-------|
| **Archivos fuente** | 26 |
| **Líneas de código (estimado)** | ~2,200-2,500 |
| **Pantallas** | 5 principales |
| **Componentes reutilizables** | 4 (Header, ActionButton, StatusBanner, ZonaCard) |
| **Archivos mock data** | 4 (mockZones, mockEmergencia, mockSalidas, mockResolver) |
| **Rutas React Router** | 5 (`/`, `/estacionar`, `/emergencia`, `/salir`, `/resolver-ahora`) |
| **Zonas con coordenadas reales** | 4 estacionamiento + 5 salidas = 9 total |
| **Reglas de inferencia** | 7 |
| **Modos de respuesta** | 4 (informar, asistir, guiar, fallback) |
| **Dependencias npm** | 11 (5 prod + 6 dev) |

### Coordenadas reales utilizadas (Jesús María, Córdoba, Argentina)

| Punto | Latitud | Longitud | Referencia |
|-------|---------|----------|------------|
| Plaza Principal / Iglesia | -30.978107 | -64.094779 | Centro del evento |
| Barrio Norte / Terminal | -30.973313 | -64.088529 | Zona Norte |
| Parque Autódromo | -30.981249 | -64.099398 | Zona Oeste |
| Predio Ferial / Costanera | -30.985337 | -64.094209 | Zona Sur |
| Av. Colón y Costanera | -30.981249 | -64.075000 | Salida Este |
| Destacamento Policial | -30.978500 | -64.095000 | Punto seguro |
| Puesto Sanitario Principal | -30.978200 | -64.094500 | Puesto sanitario |

---

## 12. 🚀 PRÓXIMOS PASOS RECOMENDADOS

### Inmediatos (hoy)
1. **Test offline real** — Abrir en Chrome → F12 → Application → Service Workers → Offline → recargar
2. **Verificar PWA installable** — Chrome Lighthouse → PWA audit

### Corto plazo (esta semana)
3. **Conectar Supabase** — Crear tablas `zonas`, `zonas_salida`, `puntos_seguros`, `puestos_sanitarios`
4. **Reemplazar mock data** — Crear hooks `useZones()`, `useSalidas()` que lean de Supabase
5. **Geolocalización real** — Usar `navigator.geolocation` para calcular distancia real del usuario

### Mediano plazo
6. **Panel municipal** — Interfaz web para que el operador actualice estados de zonas en tiempo real
7. **Pantallas secundarias** — Comer, Descansar, Servicios (actualmente placeholders)
8. **Deploy producción** — Vercel o Netlify con dominio propio

---

## 13. 📂 RUTAS DE LA APLICACIÓN

| Ruta | Componente | Propósito |
|------|-----------|-----------|
| `/` | Home | Punto de entrada |
| `/estacionar` | Estacionar | Buscar estacionamiento |
| `/emergencia` | Emergencia | Protocolo emergencia |
| `/salir` | Salir | Evacuación del evento |
| `/resolver-ahora` | ResolverAhora | Decisión automática |

---

## 14. 🔧 ARCHIVOS DE CONFIGURACIÓN CLAVE

### `vite.config.ts`
- Plugin: `@vitejs/plugin-react`
- Alias: `@` → `./src`
- Exclude: `lucide-react` de optimizeDeps

### `tailwind.config.js`
- Dark mode: `media`
- Content: `index.html` + `src/**/*.{js,ts,jsx,tsx}`
- Custom colors: primary, success, warning, danger

### `tsconfig.app.json`
- Target: ES2020, Module: ESNext
- Strict: true, noUnusedLocals: true, noUnusedParameters: true
- Path alias: `@/*` → `./src/*`

### `package.json` — Scripts
| Script | Comando |
|--------|---------|
| `dev` | `vite` |
| `build` | `vite build` |
| `lint` | `eslint .` |
| `preview` | `vite preview` |
| `typecheck` | `tsc --noEmit -p tsconfig.app.json` |

---

> **Fin del informe.** Documento generado el 3 de abril de 2026.
> Cualquier desarrollador con este documento puede continuar el proyecto sin contexto adicional.
