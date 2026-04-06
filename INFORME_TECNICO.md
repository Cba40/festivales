# 📋 INFORME TÉCNICO — Festival Jesús María MVP

**Versión:** MVP v1.0  
**Última actualización:** 6 de abril de 2026  
**Estado:** ✅ Fases 3A-3E completadas  
**Build:** ✅ Limpio (260.37 kB)

---

## 1. 🎯 VISIÓN GENERAL DEL PROYECTO

### Propósito
Aplicación PWA de soporte de decisiones en tiempo real para navegación de eventos masivos (Festival Jesús María, Córdoba, Argentina). Orientada a usuarios en la periferia del evento que necesitan resolver necesidades prácticas: estacionamiento, transporte, comida, salida, emergencia y alojamiento.

### Contexto de Uso
- **Evento masivo** con +100,000 asistentes
- **Periferia del evento**: usuarios que llegan/se van durante ventanas horarias críticas
- **Condiciones variables**: saturación de zonas, disponibilidad cambiante, congestión vehicular
- **Uso móvil**: optimizado para smartphones con conexión intermitente (offline detection)

### Principios de Diseño
1. **Máximo 2 opciones** en modos guiados (`guiar`/`asistir`)
2. **Nunca mostrar zonas colapsadas** como alternativa principal
3. **Emergencia siempre prioritaria** con modo `guiar`
4. **Datos separados de lógica**: arquitectura lista para carga externa (JSON/API)
5. **Sin breaking changes**: módulos coexisten sin romper funcionalidad existente

---

## 2. 🏗️ ARQUITECTURA DEL SISTEMA

### Diagrama de Capas

```
┌─────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │  Home    │  │Estacionar│  │  Salir   │  │Emerg.  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │Transp.   │  │  Comer   │  │  Dormir  │  │Serv.   │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    CAPA DE LÓGICA                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │           decisionEngine.ts (CORE)               │   │
│  │  • calcularScore()                               │   │
│  │  • getModo()                                     │   │
│  │  • getUmbralContexto()                           │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │mockZones.ts│  │mockSalidas.ts│  │mockTransporte │   │
│  │  scoring   │  │  scoring     │  │  modos        │   │
│  └────────────┘  └──────────────┘  └───────────────┘   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │mockComer   │  │mockResolver  │  │exitSession    │   │
│  │  modos     │  │  inferencia  │  │  controller   │   │
│  └────────────┘  └──────────────┘  └───────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    CAPA DE DATOS                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │         eventoData.ts (Single Source of Truth)   │   │
│  │  • estacionamiento[]                             │   │
│  │  • transporte[]                                  │   │
│  │  • comer[]                                       │   │
│  │  • salidas[]                                     │   │
│  │  • servicios[]                                   │   │
│  │  • pernoctar[]                                   │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │eventoConfig│  │contextoEvento│  │   tipos       │   │
│  │  fases     │  │  hora        │  │   globales    │   │
│  └────────────┘  └──────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Flujo de Datos entre Módulos

```
1. Usuario abre screen (ej: Estacionar)
   ↓
2. Screen importa datos de eventoData.ts
   ↓
3. Screen importa lógica de mockZones.ts (getZonasOrdenadas, getModoEstacionamiento)
   ↓
4. mockZones.ts usa decisionEngine.ts (calcularScore, getModo, getUmbralContexto)
   ↓
5. decisionEngine.ts calcula scores basados en datos + contexto temporal
   ↓
6. Screen renderiza resultado según modo determinado
```

### decisionEngine como Núcleo Unificado

El `decisionEngine.ts` es el **corazón algorítmico** del sistema. Proporciona:

- **`calcularScore()`**: Fórmula genérica de scoring aplicable a cualquier módulo
- **`getModo()`**: Determina modo de respuesta basado en scores y umbrales
- **`getUmbralContexto()`**: Ajusta umbrales según hora del evento

**Módulos que lo usan:**
- ✅ Estacionar (scoring + modos)
- ✅ Salir (modos, scoring propio)
- ✅ Transporte (scoring + modos)
- ✅ Comer (scoring + modos + offset +10)

---

## 3. 📦 MÓDULOS IMPLEMENTADOS

| Módulo | Tipo | Usa Engine | Estado | Descripción |
|--------|------|-----------|--------|-------------|
| **Emergencia** | Protocolo | ❌ No | ✅ Completo | Pasos predefinidos por tipo de emergencia (extraviado, herido, ayuda general) con sub-clasificación y CTAs a Google Maps/llamada |
| **Estacionar** | Híbrido | ✅ Sí | ✅ Completo | Scoring con disponibilidad + distancia + estado. 4 modos: sin_solucion, guiar, asistir, informar |
| **Salir** | Híbrido | ✅ (modos) | ✅ Completo | exitSessionController con cooldown 60s. Selector de tipo (auto/transporte/peatonal). Scoring por tipo con penalizaciones específicas |
| **Transporte** | Decisión | ✅ Sí | ✅ Completo | Scoring con espera_min + distancia + estado. 4 modos de respuesta |
| **Comer** | Decisión | ✅ Sí | ✅ Completo | Scoring con espera_min + offset +10. 4 modos de respuesta |
| **ResolverAhora** | Inferencia | ✅ Sí | ✅ Completo | Motor de inferencia que deduce necesidad del usuario basado en hora, fase y saturación |
| **Dormir/Pernoctar** | Informativo | ❌ No | ✅ Completo | Listado de alojamiento municipal (hoteles, camping, hostels) con CTAs de llamar/ir |
| **Servicios Generales** | Informativo | ❌ No | ✅ Completo | Grid de servicios (baños, hidratación, descanso, salud) con filtro por subtipo |

---

## 4. 🧠 DECISIONENGINE — ESPECIFICACIÓN TÉCNICA

### Fórmula de Scoring Base

```ts
score = distancia_min * 1.5 + espera_min * 2.5 + penalizaciónEstado

// Penalización por estado
penalizaciónEstado = {
  bajo: 0,
  medio: 5,
  alto: 15,
  colapsado: 30
}
```

**Pesos por variable de dominio:**
- **Distancia**: `1.5` (impacto moderado)
- **Espera**: `2.5` (impacto alto, más importante que distancia)
- **Estado**: penalización fija según nivel de congestión

### Modos de Decisión

| Modo | Condición | Comunicación | Ejemplo |
|------|-----------|--------------|---------|
| `sin_solucion` | score > umbral **O** todas colapsadas | "No hay opciones convenientes" | "Todos los estacionamientos están colapsados" |
| `guiar` | score < umbral, opciones disponibles | "Dirigite ahora" | "Zona Sur tiene disponibilidad, andá ahora" |
| `asistir` | score cercano a umbral, opciones limitadas | "Mejor opción ahora" | "Zona Oeste es la mejor disponible" |
| `informar` | datos insuficientes o todo normal | Lista neutra | "Estas son las opciones disponibles" |

### Algoritmo de Determinación de Modo

```ts
getModo(items, umbral):
  1. Si no hay items → sin_solucion
  2. Si mejor.score > umbral → sin_solucion
  3. Si TODAS colapsadas → sin_solucion
  4. Si TODAS saturadas (alto/colapsado) → guiar
  5. Si MAYORÍA saturadas → asistir
  6. Si resto → informar
```

### Umbrales Contextuales

```ts
getUmbralContexto(hora):
  0-2h   → 100  (salida masiva, umbral alto)
  21-23h → 90   (pico de ingreso, umbral medio-alto)
  resto  → 80   (normal, umbral base)
```

**Racional:** Durante picos de demanda, el sistema es más exigente (umbral más alto) para evitar recomendar zonas saturadas.

### Dominios con Scoring Propio

**Estacionamiento:**
```ts
score = distancia_min * 1.5 + (100 - disponibilidad) * 1.0 + penalizaciónEstado
```

**Salidas (por tipo):**
```ts
score_base = distancia_min <= 5 ? 1 : distancia_min <= 10 ? 2 : 3
score = score_base + congestiónPenalty + ajustesPorTipo

// Ajustes por tipo de salida
if tipo == 'auto' && (estado == 'alto' || 'colapsado'):
  score += 3
if tipo == 'transporte':
  score += espera_estimada_min
if tipo == 'peatonal' && es_embudo:
  score += 2
```

---

## 5. 📊 EVENTODATA — FUENTE ÚNICA DE DATOS

### Estructura de Tipos

```ts
// Base compartida
interface PuntoBase {
  id: string
  nombre: string
  lat: number
  lng: number
  referencia: string
  distancia_min: number
  updatedAt: number  // timestamp
}

// Estacionamiento
interface ZonaEstacionamiento extends PuntoBase {
  tipo: 'estacionamiento'
  disponibilidad: number  // 0-100 (%)
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
}

// Transporte
interface ParadaTransporte extends PuntoBase {
  tipo: 'transporte'
  espera_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  calle: string
}

// Comida
interface PuntoComida extends PuntoBase {
  tipo: 'comer'
  espera_min: number
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  categoria: 'rapido' | 'comida' | 'bebida'
}

// Salidas
interface ZonaSalida extends PuntoBase {
  tipo: 'salida'
  transporte: 'auto' | 'transporte' | 'peatonal'
  estado: 'bajo' | 'medio' | 'alto' | 'colapsado'
  espera_min: number
  capacidad_estimada?: number
  es_embudo?: boolean
}

// Servicios
interface PuntoServicio extends PuntoBase {
  tipo: 'servicio'
  subtipo: 'banos' | 'hidratacion' | 'descanso' | 'salud'
}

// Pernoctar
interface PuntoPernoctar extends PuntoBase {
  tipo: 'pernoctar'
  categoria: 'hotel' | 'hostel' | 'camping' | 'hospedaje'
  disponibilidad?: 'disponible' | 'consultar' | 'completo'
  telefono?: string
  web?: string
}
```

### Estructura de eventoData

```ts
export const eventoData = {
  estacionamiento: ZonaEstacionamiento[]
  transporte: ParadaTransporte[]
  comer: PuntoComida[]
  salidas: ZonaSalida[]
  servicios: PuntoServicio[]
  pernoctar: PuntoPernoctar[]
}
```

### Carga de Datos

| Fase | Método | Estado |
|------|--------|--------|
| **MVP (actual)** | JSON estático en `eventoData.ts` | ✅ Implementado |
| **Futuro (4A)** | `evento-data.json` externo cargado dinámicamente | ⏳ Pendiente |
| **Futuro (4B)** | API municipal con panel de administración | ⏳ Pendiente |

**Ventaja de la arquitectura actual:** Los datos están separados de la lógica, permitiendo migrar a carga externa sin modificar el decisionEngine ni las screens.

---

## 6. 🚪 SALIR — EXITSESSIONCONTROLLER

### Propósito
Prevenir cambios frecuentes de modo en la pantalla "Salir" que podrían confundir al usuario durante situaciones de estrés (salida masiva del evento).

### Estado de Sesión

```ts
interface ExitSessionState {
  modoActual: 'sin_solucion' | 'guiar' | 'asistir' | 'informar'
  rutaActual: string | null
  ultimoCambio: number  // timestamp (ms)
}
```

### Reglas de Estabilidad (MVP)

```ts
puedeCambiarModo(nuevoModo, estado):
  1. mismo modo → false (no hacer nada)
  2. cooldown 60s transcurrido → false (esperar)
  3. nuevoModo == 'sin_solucion' → true (seguridad siempre)
  4. resto → true (permitir cambio)
```

### API del Controller

```ts
// Crear estado inicial
crearExitSession(modoInicial: Modo): ExitSessionState

// Verificar si se puede cambiar
puedeCambiarModo(nuevoModo: Modo, estado: ExitSessionState): boolean

// Aplicar cambio
aplicarCambioModo(nuevoModo: Modo, estado: ExitSessionState): ExitSessionState
```

### Logging para Observación

```ts
// Cambio exitoso
console.log('modo_cambiado', { anterior, nuevo, timestamp })

// Cambio rechazado
console.log('cambio_rechazado', { actual, sugerido, razon })
```

**Nota:** El logging está diseñado para futura integración con analytics (Fase 4D).

---

## 7. 🏠 ESTRUCTURA DE NAVEGACIÓN

```
Home (/)
├─ 🔵 Accesos rápidos
│  ├─ 🚨 Emergencia → /emergencia
│  ├─ 🚗 Estacionar → /estacionar
│  └─ 🚪 Salir → /salir
│
└─ 🟢 Servicios
   ├─ 🚌 Transporte → /servicios/transporte
   ├─ 🍽 Comer → /servicios/comer
   ├─ 🛏 Dormir → /pernoctar
   └─ 🧭 Más servicios → /servicios/generales

🧠 Resolver Ahora → /resolver-ahora (acceso directo inteligente)
```

### Rutas Configuradas

| Ruta | Screen | Tipo | Descripción |
|------|--------|------|-------------|
| `/` | Home | Landing | Accesos rápidos + Servicios |
| `/estacionar` | Estacionar | Decisión | Parking con 4 modos |
| `/emergencia` | Emergencia | Protocolo | Emergencias con sub-clasificación |
| `/salir` | Salir | Decisión + Controller | Salida con selector de tipo |
| `/resolver-ahora` | ResolverAhora | Inferencia | Deduce necesidad del usuario |
| `/servicios` | Servicios | Menu | Menú de servicios |
| `/servicios/transporte` | ServiciosTransporte | Decisión | Transporte con 4 modos |
| `/servicios/comer` | ServiciosComer | Decisión | Comida con 4 modos |
| `/servicios/generales` | ServiciosGenerales | Informativo | Baños, agua, descanso, salud |
| `/pernoctar` | Pernoctar | Informativo | Alojamiento municipal |

---

## 8. 🔧 ARCHIVOS CLAVE DEL PROYECTO

```
Front/src/
├── data/
│   ├── eventoData.ts              # ✅ Single source of truth (datos unificados)
│   ├── mockZones.ts               # ✅ Lógica Estacionar (scoring, modos)
│   ├── mockTransporte.ts          # ✅ Lógica Transporte (scoring, modos)
│   ├── mockComer.ts               # ✅ Lógica Comer (scoring, modos)
│   ├── mockSalidas.ts             # ✅ Lógica Salir (scoring por tipo)
│   ├── mockEmergencia.ts          # ✅ Datos de emergencia (puntos seguros, puestos sanitarios)
│   └── mockResolver.ts            # ✅ Motor de inferencia (ResolverAhora)
│
├── utils/
│   ├── decisionEngine.ts          # ✅ CORE: scoring + modos + umbrales
│   ├── contextoEvento.ts          # ✅ getHoraEvento() (temporal: usa Date)
│   ├── exitSessionController.ts   # ✅ Estado + cooldown para Salir
│   ├── servicios.ts               # ✅ Filtro/orden Servicios Generales
│   ├── pernoctar.ts               # ✅ Orden Alojamiento
│   ├── tipoRecomendado.ts         # ✅ Recomienda auto/transporte/peatonal
│   ├── confianza.ts               # ✅ Mapea estado a nivel de confianza
│   ├── fases.ts                   # ✅ Determina fase actual del evento
│   ├── ventanas.ts                # ✅ Verifica si hora está en ventana
│   └── formatTime.ts              # ✅ Formato de timestamps
│
├── screens/
│   ├── Home.tsx                   # ✅ Landing con accesos rápidos + servicios
│   ├── ResolverAhora.tsx          # ✅ Inferencia de necesidad del usuario
│   ├── Estacionar.tsx             # ✅ Parking con 4 modos
│   ├── Salir.tsx                  # ✅ Salida con exitSessionController
│   ├── Emergencia.tsx             # ✅ Protocolos de emergencia
│   ├── Servicios.tsx              # ✅ Menú de servicios
│   ├── ServiciosTransporte.tsx    # ✅ Transporte con 4 modos
│   ├── ServiciosComer.tsx         # ✅ Comida con 4 modos
│   ├── ServiciosGenerales.tsx     # ✅ Baños, agua, descanso, salud
│   └── Pernoctar.tsx              # ✅ Alojamiento municipal
│
├── config/
│   └── eventoConfig.ts            # ✅ Configuración por evento (fases, umbrales)
│
├── components/
│   ├── Header.tsx                 # ✅ Header con back button
│   ├── ActionButton.tsx           # ✅ Botones de acción reutilizables
│   ├── StatusBanner.tsx           # ✅ Banner de estado (disponible/alerta/crítico)
│   └── ZonaCard.tsx               # ✅ Cards de zonas con variantes
│
├── hooks/
│   └── useOffline.ts              # ✅ Detecta estado de conexión
│
├── types/
│   └── index.ts                   # ✅ Tipos globales (Modo, Estado, Decision, etc.)
│
└── App.tsx                        # ✅ Routing principal
```

---

## 9. 🎯 GUARDRAILS Y REGLAS DE NEGOCIO

### UI (NO negociable)

| Regla | Racional |
|-------|----------|
| ✅ Máximo **2 opciones** en modos `guiar`/`asistir` | Evitar parálisis por análisis en situaciones de estrés |
| ✅ Máximo **3 opciones** en modo `informar` | Mantener lista escaneable |
| ✅ **Nunca** mostrar zonas `colapsadas` como alternativa en `guiar` | Seguridad del usuario primero |
| ✅ Botón **"🗺️ Ir ahora"** siempre presente | Google Maps deep link para navegación inmediata |

### Decisión

| Regla | Racional |
|-------|----------|
| ✅ `emergencia` **siempre prioritaria**, siempre modo `guiar` | Emergencias no pueden esperar |
| ✅ Alternativa solo si `score_alt < umbral * 0.9` | Alternativa debe ser significativamente mejor |
| ✅ `sin_solucion` si score > umbral_contextual **O** todas <10% disponibilidad | Evitar recomendar opciones inviables |
| ✅ Cooldown de **60 segundos** en Salir | Prevenir cambios erráticos durante estrés |

### Arquitectura

| Regla | Racional |
|-------|----------|
| ✅ **NO** usar `new Date().getHours()` fuera de `getHoraEvento()` | Centralizar fuente de tiempo para futuro reemplazo |
| ✅ **NO** hardcodear horarios en lógica de decisión | Horarios deben venir de `eventoConfig` |
| ✅ **NO** modificar `decisionEngine` sin validar impacto en **3+ módulos** | Engine es núcleo crítico, cambios requieren testing exhaustivo |
| ✅ **Datos separados de lógica** | Permitir migración a carga externa sin reescribir lógica |

---

## 10. ⚠️ DEUDAS TÉCNICAS CONOCIDAS

| Archivo | Issue | Impacto | Prioridad | Mitigación |
|---------|-------|---------|-----------|------------|
| **mocks + eventoData** | Duplicación de datos (zonasMock ≈ eventoData.estacionamiento) | Mantenimiento doble, riesgo de inconsistencia | 🟡 Media | Planificar refactor: migrar todo a eventoData, preservar lógica de scoring |
| **contextoEvento.ts** | `getHoraEvento()` usa `Date()` en lugar de fuente real del evento | Funciona en MVP, pero no escala a eventos multi-día | 🟡 Media | Integrar con API de evento o archivo de configuración externo |
| **Salir** | Scoring propio no unificado con decisionEngine | Complejidad adicional, pero dominio distinto justifica divergencia | 🟢 Baja | Documentar diferencias, considerar abstracción futura |
| **Disponibilidad** | Datos estimados en mock, no reales de sensores | Limita precisión de recomendaciones | 🟡 Media | Requiere fuente externa (API municipal, sensores IoT) |
| **Geolocalización** | Distancia calculada manualmente, no usa GPS del usuario | UX menos precisa, requiere input manual | 🟡 Media | Fase 4C: integrar navigator.geolocation |
| **Offline** | useOffline hook existe pero no se usa en todos los screens | Usuario puede ver datos stale sin saberlo | 🟢 Baja | Agregar banner de offline mode en screens críticos |

---

## 11. 🚀 PRÓXIMOS PASOS (FASE 4+)

### Hoja de Ruta

| Fase | Objetivo | Alcance | Dependencias | Estado |
|------|----------|---------|--------------|--------|
| **4A** | Carga de datos externa (JSON editable) | Migrar eventoData.ts a `evento-data.json` cargado dinámicamente | Ninguna | ⏳ Pendiente |
| **4B** | Panel admin mínimo para municipio | CRUD básico para actualizar disponibilidad de zonas | Fase 4A | ⏳ Pendiente |
| **4C** | Geolocalización real del usuario | Integrar `navigator.geolocation` para cálculo automático de distancias | Ninguna | ⏳ Pendiente |
| **4D** | Analytics + métricas de uso | Logging de modos de decisión, tiempos de respuesta, zonas más consultadas | exitSessionController logging | ⏳ Pendiente |
| **4E** | Integración con API municipal | Reemplazar mock data con endpoints reales de tránsito/transporte | Fases 4A-4B | ⏳ Pendiente |
| **5A** | Modo offline completo | Cache de datos + synchronización cuando hay conexión | useOffline hook | ⏳ Pendiente |
| **5B** | Notificaciones push | Alertas de zonas colapsadas, cambios de fase, emergencias | Service Worker | ⏳ Pendiente |

### Criterios de Aceptación para Fase 4A

- [ ] `evento-data.json` externo cargado vía `fetch()`
- [ ] Fallback a datos locales si falla carga
- [ ] Build limpio post-migración
- [ ] Sin cambios en decisionEngine ni en screens (solo cambia fuente de datos)

---

## 12. 📊 ESTADO ACTUAL DEL MVP

### Módulos Completados

| Módulo | Estado | Usa Engine | Datos | UI | Testing |
|--------|--------|-----------|-------|-----|---------|
| **Emergencia** | ✅ Completo | N/A | mockEmergencia | Protocolo con sub-clasificación | ✅ Manual |
| **Estacionar** | ✅ Completo | ✅ Sí | eventoData.estacionamiento | 4 modos (sin_solucion, guiar, asistir, informar) | ✅ Coherencia 3/3 |
| **Salir** | ✅ Completo | ✅ (modos) | eventoData.salidas | 4 modos + exitSessionController | ✅ Coherencia 3/3 |
| **ResolverAhora** | ✅ Completo | ✅ Sí | mockResolver + salidas/zonas | Inferencia + fallback menu | ✅ Manual |
| **Transporte** | ✅ Completo | ✅ Sí | eventoData.transporte | 4 modos | ✅ Manual |
| **Comer** | ✅ Completo | ✅ Sí | eventoData.comer | 4 modos con offset +10 | ✅ Manual |
| **Dormir/Pernoctar** | ✅ Completo | ❌ No | eventoData.pernoctar | Lista + CTAs (llamar/ir) | ✅ Manual |
| **Servicios Generales** | ✅ Completo | ❌ No | eventoData.servicios | Grid con filtro por subtipo | ✅ Manual |

### Métricas del Build

| Métrica | Valor |
|---------|-------|
| **Build status** | ✅ Limpio |
| **Tamaño bundle** | 260.37 kB (gzipped: 65.59 kB) |
| **CSS** | 17.01 kB (gzipped: 3.72 kB) |
| **Módulos transformados** | 1503 |
| **Tiempo de build** | ~11.71s |
| **Archivos eliminados** | 1 (ServiciosDescansar.tsx) |
| **Archivos creados** | 16 (config, data, screens, utils) |
| **Archivos modificados** | 12 |

### Stack Tecnológico

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| React | 18+ | UI framework |
| TypeScript | 5+ | Type safety |
| Vite | 5.4.8 | Build tool + dev server |
| React Router | 6+ | Routing |
| TailwindCSS | 3+ | Styling |
| Lucide React | Latest | Iconos |
| Supabase | @supabase/supabase-js | Dependencia instalada (sin uso activo aún) |

### Git Status

- **Branch:** `main`
- **Último commit:** `87b5ae1` - Merge remote-tracking branch 'origin/main'
- **Remote:** `https://github.com/Cba40/festivales`
- **Commits totales:** 5
- **Working tree:** ✅ Limpio

---

## 13. 📖 GLOSARIO DE TÉRMINOS

| Término | Definición |
|---------|------------|
| **Modo** | Estado de respuesta del sistema: `sin_solucion`, `guiar`, `asistir`, `informar` |
| **Score** | Puntaje calculado que determina conveniencia de una opción (menor es mejor) |
| **Umbral** | Límite contextual que determina cambio de modo |
| **Fase** | Período del evento con características propias (llegada, pico, dentro, salida) |
| **Saturación** | Nivel de congestión: `bajo`, `medio`, `alto`, `colapsado` |
| **Cooldown** | Período de espera forzada para prevenir cambios erráticos (60s en Salir) |
| **Inferencia** | Deducción de necesidad del usuario basada en contexto (hora, fase, saturación) |
| **Single Source of Truth** | Patrón donde `eventoData.ts` es la única fuente de datos unificada |

---

## 14. 🔍 DIAGNÓSTICO DE COHERENCIA (FASE 3A)

### Casos de Prueba Validados

**Escenario: Estacionar a las 19h (fase llegada)**
- ✅ Todas colapsadas → `sin_solucion` (recomienda ir directo)
- ✅ Todas <10% disponibilidad → `guiar` (recomenda ir a opción disponible)
- ✅ Mejor opción con score < umbral → `informar` (muestra opciones)

**Escenario: Salir a las 1h (fase salida masiva)**
- ✅ Todas colapsadas → `sin_solucion` (recomienda esperar/alternativa)
- ✅ Mix de estados → `asistir` (recomenda mejor opción)
- ✅ Cooldown activo → rechaza cambio de modo (<60s)

**Escenario: ResolverAhora con saturación alta**
- ✅ Fase `pico` + saturación `colapsada` → `estacionar` con modo `guiar`
- ✅ Fase `dentro` + sin acción clara → `fallback` con menú

### Cobertura de Testing

| Módulo | Cobertura | Tipo |
|--------|-----------|------|
| decisionEngine | ✅ Alta (unit testing manual de fórmula + modos) | Manual |
| exitSessionController | ✅ Media (testing de reglas de cooldown) | Manual |
| mockResolver | ✅ Media (testing de inferencia con escenarios) | Manual |
| Screens | ✅ Baja (render testing visual) | Manual |

**Recomendación:** Implementar tests automatizados con Vitest/Jest en Fase 5+.

---

## 15. 📞 CONTACTO Y CONTRIBUCIÓN

### Repositorio
- **URL:** `https://github.com/Cba40/festivales`
- **Branch principal:** `main`
- **Directorio Front:** `Front/`
- **Framework:** React + TypeScript + Vite

### Cómo Ejecutar

```bash
# Instalar dependencias
cd Front && npm install

# Modo desarrollo
npm run dev

# Build de producción
npm run build

# Verificar código (lint)
npm run lint
```

### Estructura de Commits

```
tipo: descripción corta

## Detalles:
- Cambio 1
- Cambio 2

## Build: ✅ Limpio
```

**Tipos:** `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

---

**Fin del informe técnico**  
**Documento mantenido por:** Equipo de desarrollo CBA 4.0  
**Próxima revisión:** Fase 4A (carga de datos externa)
