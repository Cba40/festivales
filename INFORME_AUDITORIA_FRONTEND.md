# AUDITORÍA TÉCNICA DEL FRONTEND
## Plataforma de Asistencia Territorial para Eventos Masivos
**Fecha:** 27 de mayo de 2026  
**Tipo:** Auditoría técnica profunda + Realineamiento MVP  
**Autor:** Análisis arquitectónico de sistemas  

---

## SUMARIO EJECUTIVO

El frontend actual fue construido **antes de consolidar la arquitectura MVP real**. Como resultado:

- ✅ Tiene estructura modular básica **reutilizable**
- ✅ Implementa componentes **con buenas prácticas iniciales**
- ❌ Pero está **sobrepensado** en áreas no MVP
- ❌ Y **subdesarrollado** en arquitectura central
- ❌ Completamente **desacoplado del backend** que será obligatorio

**Diagnóstico:** El frontend requiere **refactorización estructural profunda**, no parches.

**Viabilidad:** 60% del código actual es reutilizable; 40% requiere reescritura.

---

# SECCIÓN 1 — ESTADO ACTUAL DEL FRONTEND

## 1.1 Estructura General

```
Frontend/
├── src/
│   ├── screens/          ✅ Bien organizado (12 pantallas)
│   ├── components/       ✅ Reutilizables pero incompletos
│   ├── data/            ❌ Mock data sin integración backend
│   ├── config/          ❌ Hardcodeado
│   ├── utils/           ✅ Lógica transversal (pero dispersa)
│   ├── hooks/           ✅ useOffline (pero insuficiente)
│   ├── types/           ✅ Tipos básicos definidos
│   ├── App.tsx          ✅ Router bien configurado
│   └── main.tsx         ⚠️ Service worker deshabilitado
```

### Stack Tecnológico Actual

| Capa | Tecnología | Versión | Estado |
|------|-----------|---------|--------|
| Framework | React | 18.3.1 | ✅ OK |
| Lenguaje | TypeScript | 5.5.3 | ✅ OK |
| Routing | React Router | 6.20.0 | ✅ OK |
| Styling | Tailwind CSS | 3.4.1 | ✅ OK |
| Build | Vite | 5.4.2 | ✅ OK |
| UI Icons | Lucide | 0.344.0 | ✅ OK |
| Backend Mock | Supabase JS | 2.57.4 | ❌ **NO USADO** |
| State Management | **NINGUNO** | - | ❌ **FALTA** |
| API Client | **NINGUNO** | - | ❌ **FALTA** |
| Real-time | **NINGUNO** | - | ❌ **FALTA** |

## 1.2 Análisis de Pantallas

### Pantallas Implementadas (12 total)

| Pantalla | Ruta | Estado | MVP | Complejidad |
|----------|------|--------|-----|-------------|
| Home | `/` | ✅ Funcional | ✅ SI | ⭐⭐ |
| Estacionar | `/estacionar` | ✅ Funcional | ✅ SI | ⭐⭐⭐ |
| Emergencia | `/emergencia` | ✅ Funcional | ✅ SI | ⭐⭐ |
| Salir | `/salir` | ✅ Funcional | ✅ SI | ⭐⭐⭐ |
| ResolverAhora | `/resolver-ahora` | ⚠️ Incompleto | ❌ NO | ⭐ |
| Servicios | `/servicios` | ✅ Hub | ⚠️ PARCIAL | ⭐ |
| ServiciosTransporte | `/servicios/transporte` | ✅ Funcional | ❌ NO | ⭐⭐ |
| ServiciosComer | `/servicios/comer` | ✅ Funcional | ❌ NO | ⭐⭐⭐ |
| GastronomiaExpanded | `/servicios/comer/mas` | ✅ Funcional | ❌ NO | ⭐⭐ |
| ServiciosGenerales | `/servicios/generales` | ✅ Funcional | ❌ NO | ⭐⭐ |
| Pernoctar | `/pernoctar` | ✅ Funcional | ❌ NO | ⭐⭐ |
| AsistenteScreen | `/asistente` | ⚠️ Mock | ❌ NO (Futuro) | ⭐⭐⭐ |

### Análisis Cualitativo de Pantallas

#### ✅ PANTALLAS MVP CORE (Mantener, Refactorizar)

**Home.tsx**
- Propósito: Hub de accesos rápidos
- Estado: Funcional pero hardcodeado
- Problemas:
  - "Festival Jesús María" hardcodeado
  - No parametrizable para otros eventos
  - Layout es bueno
- Refactor necesario: Extraer contexto de evento

**Estacionar.tsx**
- Propósito: Recomendación de zonas estacionamiento
- Estado: Muy funcional
- Virtudes:
  - Lógica de scoring completa
  - Estados y modos implementados
  - UX clara (recomendación primaria + fallback)
  - Integración Google Maps
- Problemas:
  - Datos mock sin backend
  - Scoring local sin contexto real
  - Sin actualizaciones realtime
  - Sin datos de usuario

**Emergencia.tsx**
- Propósito: Guía rápida emergencias
- Estado: Funcional
- Virtudes:
  - Flujos diferenciados (niño/herida/ayuda)
  - UX escalada (acción → fallback → llamada)
  - Punto seguro bien integrado
- Problemas:
  - Teléfonos hardcodeados
  - Sin base de datos de puntos reales
  - Sin actualización de disponibilidad

**Salir.tsx**
- Propósito: Guía egreso por tipo transporte
- Estado: Muy completo
- Virtudes:
  - 3 modos: auto / transporte / peatonal
  - Scoring y ordenamiento
  - Session controller para evitar mode thrashing
  - Logging de decisiones
- Problemas:
  - Datos mock
  - Sin flujos reales
  - Sin congestión real-time
  - Lógica parcialmente duplicada

#### ⚠️ PANTALLAS PARCIALMENTE MVP (Simplificar)

**Servicios.tsx**
- Propósito: Hub de servicios adicionales
- MVP real: Debe minimalizarse
- Recomendación: Mantener mínimamente, congelar expansión
- Eliminar: ServiciosGenerales, detalle de categorías

#### ❌ PANTALLAS FUERA DEL MVP (Congelar/Eliminar)

| Pantalla | Razón | Acción |
|----------|-------|--------|
| ServiciosTransporte | No en MVP REAL | CONGELAR |
| ServiciosComer | Gastronomía es futuro | CONGELAR |
| GastronomiaExpanded | Detalle excesivo | CONGELAR |
| ServiciosGenerales | Scope creep | CONGELAR |
| Pernoctar | No en MVP REAL | CONGELAR |
| AsistenteScreen | IA conversacional (futuro) | CONGELAR |
| ResolverAhora | Incompleto, no prioritario | CONGELAR |

## 1.3 Análisis de Componentes Reutilizables

### Componentes Existentes (5 total)

```typescript
Header.tsx
├── Props: title, showBack, onBack, onHome, ubicacion
├── Estado: Bueno
├── Problemas: No parametriza evento
└── Refactor: Necesario

ActionButton.tsx (QuickAction)
├── Props: icon, label, colorScheme, onClick
├── Estado: Funcional
├── Problemas: Solo para accesos rápidos
└── Futuro: Reutilizable

StatusBanner.tsx
├── Props: estado, mensaje
├── Estado: Muy simple
├── Problemas: Poco versatil
└── Refactor: Agregar más contexto

ZonaCard.tsx
├── Props: zona, onClick, actions
├── Estado: Funcional
├── Problemas: Muy específico para estacionamiento
└── Futuro: Generalizarlo

SimpleMap.tsx
├── Props: zona(s), userLocation
├── Estado: Placeholder
├── Problemas: NO IMPLEMENTADO REALMENTE
└── CRÍTICO: Necesita implementación real
```

### Componentes Faltantes (CRÍTICOS)

- **ApiClient / API Integration** — ❌ COMPLETAMENTE AUSENTE
- **Global State Provider** — ❌ COMPLETAMENTE AUSENTE  
- **Real-time Connection** — ❌ COMPLETAMENTE AUSENTE
- **Event Context** — ❌ COMPLETAMENTE AUSENTE
- **User Location Provider** — ⚠️ Sin implementación
- **Loading / Error Boundaries** — ❌ AUSENTES
- **Notification System** — ❌ AUSENTE
- **Bottom Sheet** — ✅ Implementado manualmente (Emergencia)

## 1.4 Análisis de la Capa de Datos

### Estructura Actual

```
data/
├── eventoData.ts         (Single Source of Truth — buena intención)
│   ├── estacionamiento   ✅ Bien estructurado
│   ├── salidas          ✅ Bien estructurado
│   ├── servicios        ❌ Excesivo (gastronomía, transporte)
│   └── emergencia       ✅ Puntos básicos
│
├── mockZones.ts         (DUPLICA eventoData.ts)
├── mockSalidas.ts       (DUPLICA eventoData.ts)
├── mockEmergencia.ts    (DUPLICA eventoData.ts)
├── mockTransporte.ts    (Fuera MVP)
├── mockComer.ts         (Fuera MVP)
├── mockServiciosMap.ts  (Fuera MVP)
├── mockResolver.ts      (Incompleto)
└── mockCorredoresGastronomicos.ts (Fuera MVP)
```

### Problemas Críticos de Datos

1. **DUPLICACIÓN SEVERA**
   - eventoData.ts tiene estacionamiento
   - mockZones.ts replica estacionamiento
   - Ambas son "Single Source of Truth"
   - Riesgo alto de inconsistencia

2. **SIN ESTRUCTURA API**
   - No hay mapeo a endpoints HTTP
   - No hay normalización de datos
   - No hay caching
   - No hay invalidation strategy

3. **DATOS MOCK COMO FIXTURE**
   - Mock data está mezclado con lógica
   - No hay estrategia de reemplazo
   - Cambiar a API requiere refactor masivo

4. **TIPOGRAFÍA INCONSISTENTE**
   ```typescript
   // eventoData.ts
   interface ZonaEstacionamiento {
     distancia_min: number
     disponibilidad: number
     estado: string
   }
   
   // types/index.ts
   interface Zona {
     distancia_min: number
     estado: EstadoZona
     // ... diferente estructura!
   }
   ```

5. **TIMESTAMP INCONSISTENTE**
   - Algunos usan `updatedAt: number` (ms)
   - Algunos usan `timestamp: string`
   - Algunos sin timestamp
   - No hay estrategia unificada

## 1.5 Análisis de la Capa de Lógica

### Utils y Decisión Engine

```
utils/
├── decisionEngine.ts     ✅ Decisiones (pero dispersas)
├── contextoEvento.ts     ⚠️ Hora = getHours() (PROBLEMA)
├── fases.ts              ✅ Bien estructurado
├── exitSessionController.ts ✅ Buen patrón
├── tipoRecomendado.ts    ⚠️ Vago, sin uso claro
├── pernoctar.ts          ❌ Fuera MVP
├── servicios.ts          ❌ Fuera MVP
├── ventanas.ts           ⚠️ Relacionado a fases, duplicado
├── formatTime.ts         ✅ Helper simple
└── confianza.ts          ✅ Helper simple
```

### Problemas de Lógica

1. **SCORING Y MODOS DISPERSOS**
   - `decisionEngine.ts`: Funciones genéricas
   - `mockZones.ts`: Scoring específico estacionamiento
   - `mockSalidas.ts`: Scoring específico salidas
   - `Estacionar.tsx`: Más lógica local
   - `Salir.tsx`: Más lógica local
   - **Resultado:** Código duplicado, difícil mantener

2. **CONTEXTO DEL EVENTO HARDCODEADO**
   ```typescript
   // contextoEvento.ts
   export const getHoraEvento = (): number => {
     return new Date().getHours()  // ❌ PROBLEMA CRÍTICO
   }
   ```
   - No hay fuente de hora del evento
   - No hay sincronización con backend
   - Fases hardcodeadas para "Jesús María 2024"
   - No multi-evento

3. **SIN STATE MANAGEMENT**
   - No hay Context API
   - No hay Redux/Zustand
   - Cada componente es una isla
   - Imposible compartir estado
   - Imposible persistencia

4. **LÓGICA DE SESIÓN INCOMPLETA**
   - `exitSessionController.ts` solo para modo Salir
   - No hay abstracción general
   - No reutilizable

## 1.6 Summary — Estado Arquitectónico Actual

### Lo QUE FUNCIONA ✅
1. React Router con navegación clara
2. TypeScript con tipos básicos
3. Tailwind para layout responsive
4. Separación pantallas/componentes/data
5. Algunos patrones buenos (exitSessionController)
6. Offline detection hooks
7. Iconografía clara
8. Vite con build rápido

### Lo QUE NO FUNCIONA ❌
1. **Sin backend** — cero integración API
2. **Sin estado global** — componentes aislados
3. **Sin realtime** — solo mock data estática
4. **Sin multi-evento** — hardcodeado para uno
5. **Datos duplicados** — múltiples mock files
6. **Lógica dispersa** — scoring/decisiones por toda la app
7. **Componentes incompletos** — falta API, estado, realtime
8. **Service worker deshabilitado** — sin offline real
9. **Supabase no usado** — dead code en dependencies
10. **Hardcoding extremo** — "Jesús María", horas, teléfonos

### Línea Base Arquitectónica
- **Madurez:** 40% (estructura básica, falta integración)
- **Reutilización:** 60% del código
- **Reescritura necesaria:** 40% del código
- **Esfuerzo refactor:** Alto
- **ROI:** Alto (sentará bases para años)

---

# SECCIÓN 2 — COMPATIBILIDAD CON EL MVP

## 2.1 Mapeo Entidades MVP vs Frontend

### Entidades del MVP REAL Definidas

| Entidad | Campos Mínimos | Frontend | Estado |
|---------|---|---------|--------|
| **Event** | id, name, location, start/end, status | ❌ AUSENTE | ⚠️ CRÍTICO |
| **Zone** | id, type, geometry, saturation, status | ✅ Parcial | ⚠️ Incompleto |
| **Point** | id, type, coordinates, status | ✅ Implementado | ✅ OK |
| **Incident** | id, type, severity, geometry, timestamp | ❌ AUSENTE | ❌ CRÍTICO |
| **Snapshot** | entity_type, entity_id, state, timestamp | ❌ AUSENTE | ❌ CRÍTICO |

### Casos de Uso del MVP vs Pantallas

| Caso de Uso | Descripción | Pantalla | Estado |
|-------------|---|---------|--------|
| Recomendar estacionamiento | Mostrar zonas, saturación, mejor opción | `/estacionar` | ✅ 80% IMPL |
| Guía salida | Sugerir corredor, mostrar flujo | `/salir` | ✅ 80% IMPL |
| Emergencias | Puntos críticos (baño, policía, sanitario) | `/emergencia` | ✅ 90% IMPL |
| Estado operativo | Actualizar saturación, disponibilidad | ❌ AUSENTE | ❌ FALTA |
| Realtime básico | Cambios de estados, incidentes | ❌ AUSENTE | ❌ FALTA |

## 2.2 Análisis de Sobreingeniería

### Funcionalidades IMPLEMENTADAS que NO están en MVP

```
Frontend implementado               MVP REAL
─────────────────────────────────────────────
✗ Gastronomía detallada            (congelada)
✗ Transporte/paradas               (congelada)
✗ Hospedajes/pernoctar             (congelada)
✗ Servicios generales              (congelada)
✗ Asistente IA conversacional       (futuro)
✗ Resolver ahora (contexto)         (incompleto)
✗ Mapas territoriales abstractos    (no impl)
✗ Dashboard municipal              (congelada)
```

**Esfuerzo desperdiciado:** ~30% de code base

### Funcionalidades MVP QUE FALTAN en Frontend

```
MVP REAL necesario                 Frontend
──────────────────────────────────────────
✓ Multi-evento parametrizable      ❌ FALTA
✓ Contexto de evento real          ❌ FALTA (hardcodeado)
✓ Actualización de estados         ❌ FALTA
✓ Reporting de incidentes          ❌ FALTA
✓ Realtime connection              ❌ FALTA
✓ Persistencia de decisiones       ❌ FALTA
✓ Dashboard municipal              ❌ FALTA (nuevo módulo)
✓ API integration layer            ❌ FALTA
✓ Global state management          ❌ FALTA
✓ Telemetría básica                ❌ FALTA
```

## 2.3 Incompatibilidades Conceptuales

### Incompatibilidad 1: Hora del Evento

**MVP define:** Señales temporales como source of truth
**Frontend implementa:** `getHoraEvento() → new Date().getHours()`

**Problema:** 
- App usa hora del SISTEMA
- No sincronizada con evento real
- Fases hardcodeadas para un festival específico
- No es multi-evento

**Impacto:** CRÍTICO
- Recomendaciones basadas en hora falsa
- Testing imposible
- Producción: inconsistencias severas

---

### Incompatibilidad 2: Estados Estáticos vs Dinámicos

**MVP define:** Snapshots históricos, recalcular contexto continuamente
**Frontend implementa:** Mock data estática, sin recalculación

**Problema:**
```typescript
// Frontend
const zonasMock = eventoData.estacionamiento  // Static data
// Nunca cambia a menos que edites el archivo mock

// MVP esperado
// Backend actualiza zona → Frontend recibe update → snapshot histórico
```

**Impacto:** ALTO
- Sin realtime
- Sin histórico
- Sin auditoría temporal

---

### Incompatibilidad 3: Contexto Operacional

**MVP define:** Señales múltiples (clima, incidentes, flujo, operadores)
**Frontend implementa:** Solo disponibilidad y distancia

**Problema:**
```typescript
// Frontend
score = distancia * 1.5 + (100 - disponibilidad) * 1.0 + estado_penalty

// MVP esperado
score = (distancia, disponibilidad, estado, clima, incidentes, 
         congestión, accesibilidad, riesgo, horario, patrón histórico)
```

**Impacto:** MEDIO
- Scoring simplificado (pero funcional para MVP)
- Escalable cuando backend agregue señales

---

### Incompatibilidad 4: Multi-Evento vs Single-Event

**MVP define:** Multi-municipio, multi-evento, parametrizable
**Frontend implementa:** "Festival Jesús María" hardcodeado

**Problema:**
- Header hardcodeado
- Config hardcodeada
- Fases hardcodeadas
- Rutas fijas
- Teléfonos hardcodeados

**Impacto:** BLOQUEADOR
- No escalable
- No validable en otro evento
- Requiere refactor para cada evento

---

## 2.4 Simplificaciones Necesarias

### Pantallas a ELIMINAR

```
CONGELAR INMEDIATAMENTE:
├── ServiciosTransporte    (0% MVP)
├── ServiciosComer         (0% MVP)
├── GastronomiaExpanded    (0% MVP)
├── ServiciosGenerales     (0% MVP)
├── Pernoctar              (0% MVP)
├── AsistenteScreen        (0% MVP)
└── ResolverAhora          (20% completitud)

LÍNEAS A ELIMINAR: ~800-1000
COMPONENTES A ELIMINAR: ~6-8
MOCK FILES A ELIMINAR: mockTransporte, mockComer, mockResolver, etc
```

### Componentes a SIMPLIFICAR

```
SimpleMap
├── Actual: Placeholder no implementado
├── MVP necesario: Mostrar zona + punto de usuario
├── Simplificación: Usar Google Maps API solo para navegación
└── Post-MVP: Mapas territoriales

ActionButton
├── Actual: Funciona bien
├── Simplificación: Mantener como es
└── Nota: Revisar colorScheme options

ZonaCard
├── Actual: Específico para parking
├── Necesario: Generalizar para puntos/salidas
└── Refactor: Hacer reutilizable
```

## 2.5 Alineamiento Requerido

### Antes de Integración Backend

```
BLOQUEOS CRÍTICOS:
1. [ ] Extraer contexto evento a variable global
2. [ ] Reemplazar hora sistema con evento.start_time
3. [ ] Crear event context provider
4. [ ] Remover hardcoding completo
5. [ ] Crear global state (Zustand o Context)
6. [ ] Implementar API client
7. [ ] Eliminar pantallas fuera MVP
8. [ ] Consolidar lógica de scoring
```

### Score de Alineamiento Actual
- **Compatibilidad directa:** 45%
- **Requiere refactor:** 40%
- **Fuera de scope:** 15%

---

# SECCIÓN 3 — REESTRUCTURACIÓN NECESARIA

## 3.1 Nueva Arquitectura Propuesta

### Arquitectura Modular del Frontend

```
Frontend/src/
│
├── core/                          [NUEVA CAPA]
│   ├── api/
│   │   ├── client.ts              (axios/fetch wrapper)
│   │   ├── endpoints.ts           (URLs centralizadas)
│   │   ├── types.ts               (tipos de API)
│   │   └── interceptors.ts        (auth, error handling)
│   │
│   ├── state/                     [NUEVA CAPA]
│   │   ├── EventContext.tsx       (Evento actual)
│   │   ├── UserContext.tsx        (User location, prefs)
│   │   ├── RecommendationStore.ts (Estado recomendaciones)
│   │   └── store.ts               (Zustand store central)
│   │
│   ├── realtime/                  [NUEVA CAPA]
│   │   ├── websocket.ts           (WebSocket connection)
│   │   ├── handlers.ts            (Event handlers)
│   │   └── subscriptions.ts       (Real-time subs)
│   │
│   └── config/
│       └── constants.ts           (URLs, timeouts, etc)
│
├── features/                      [REORGANIZADO]
│   ├── parking/
│   │   ├── screens/
│   │   │   └── ParkingScreen.tsx  (Antes: Estacionar)
│   │   ├── components/
│   │   │   ├── ParkingZoneCard.tsx
│   │   │   └── ParkingRecommendation.tsx
│   │   ├── hooks/
│   │   │   └── useParkingRecommendation.ts
│   │   ├── types.ts
│   │   └── utils.ts
│   │
│   ├── exit/
│   │   ├── screens/
│   │   │   └── ExitScreen.tsx     (Antes: Salir)
│   │   ├── components/
│   │   │   ├── TransportModeSelector.tsx
│   │   │   └── ExitRecommendation.tsx
│   │   ├── hooks/
│   │   │   └── useExitRecommendation.ts
│   │   ├── types.ts
│   │   └── utils.ts
│   │
│   ├── emergency/
│   │   ├── screens/
│   │   │   └── EmergencyScreen.tsx
│   │   ├── components/
│   │   │   ├── EmergencyType.tsx
│   │   │   └── NearbyPoints.tsx
│   │   ├── hooks/
│   │   │   └── useNearbyPoints.ts
│   │   ├── types.ts
│   │   └── utils.ts
│   │
│   └── dashboard/                 [NUEVO MÓDULO - MVP v2]
│       ├── screens/
│       │   └── DashboardScreen.tsx
│       ├── components/
│       │   ├── ZoneSaturationWidget.tsx
│       │   ├── IncidentList.tsx
│       │   └── StatusUpdater.tsx
│       ├── hooks/
│       │   └── useMunicipalDashboard.ts
│       └── types.ts
│
├── shared/                        [REORGANIZADO]
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── StatusBanner.tsx
│   │   ├── LoadingSpinner.tsx     [NUEVO]
│   │   ├── ErrorBoundary.tsx      [NUEVO]
│   │   ├── BottomSheet.tsx        [EXTRAÍDO de Emergencia]
│   │   └── Map.tsx                [NUEVO - proper map impl]
│   │
│   ├── hooks/
│   │   ├── useOffline.ts
│   │   ├── useLocation.ts         [NUEVO]
│   │   ├── useEvent.ts            [NUEVO - context hook]
│   │   ├── useApi.ts              [NUEVO - fetch wrapper]
│   │   └── useRealtime.ts         [NUEVO - websocket]
│   │
│   ├── types/
│   │   ├── api.ts                 [API response types]
│   │   ├── domain.ts              [Domain entities]
│   │   └── ui.ts                  [UI-specific types]
│   │
│   └── utils/
│       ├── scoring.ts             [Lógica de scoring centralizada]
│       ├── formatting.ts
│       ├── distance.ts
│       └── validators.ts
│
├── App.tsx                        [REFACTORIZADO]
├── main.tsx                       [Service worker re-enabled]
└── index.css
```

## 3.2 Cambios Arquitectónicos Clave

### 1. CREAR ESTADO GLOBAL CON ZUSTAND

```typescript
// core/state/store.ts
import { create } from 'zustand'

interface AppState {
  // Evento actual
  event: Event | null
  setEvent: (event: Event) => void
  
  // Usuario
  userLocation: Location | null
  setUserLocation: (loc: Location) => void
  
  // Zonas y puntos
  zones: Zone[]
  points: Point[]
  setZones: (zones: Zone[]) => void
  setPoints: (points: Point[]) => void
  
  // Incidentes
  incidents: Incident[]
  addIncident: (incident: Incident) => void
  
  // Estado realtime
  isConnected: boolean
  setConnected: (connected: boolean) => void
}

export const useAppStore = create<AppState>(...)
```

### 2. CREAR EVENT CONTEXT

```typescript
// core/state/EventContext.tsx
const EventContext = createContext<{
  event: Event | null
  setEvent: (event: Event) => void
}>()

export const EventProvider: React.FC = ({ children }) => {
  const [event, setEvent] = useState<Event | null>(null)
  
  return (
    <EventContext.Provider value={{ event, setEvent }}>
      {children}
    </EventContext.Provider>
  )
}

export const useEvent = () => useContext(EventContext)
```

### 3. API CLIENT CENTRALIZADO

```typescript
// core/api/client.ts
import axios from 'axios'

const client = axios.create({
  baseURL: process.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
})

// Interceptors
client.interceptors.request.use(...)
client.interceptors.response.use(...)

export default client
```

### 4. ENDPOINTS CENTRALIZADOS

```typescript
// core/api/endpoints.ts
export const endpoints = {
  events: {
    list: '/events',
    get: (id: string) => `/events/${id}`,
    current: '/events/current',
  },
  zones: {
    list: (eventId: string) => `/events/${eventId}/zones`,
    get: (eventId: string, zoneId: string) => `/events/${eventId}/zones/${zoneId}`,
    update: (eventId: string, zoneId: string) => `/events/${eventId}/zones/${zoneId}`,
  },
  recommendations: {
    parking: '/recommendations/parking',
    exit: '/recommendations/exit',
  },
  emergency: {
    nearby: '/emergency/nearby',
  },
  realtime: {
    events: (eventId: string) => `/realtime/events/${eventId}`,
  },
}
```

### 5. REALTIME CONNECTION

```typescript
// core/realtime/websocket.ts
export class RealtimeConnection {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  
  connect(eventId: string) {
    const wsUrl = `${process.env.VITE_WS_URL}/realtime/events/${eventId}`
    this.ws = new WebSocket(wsUrl)
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      this.handleMessage(data)
    }
    
    this.ws.onerror = () => this.reconnect(eventId)
  }
  
  private handleMessage(data: any) {
    // Dispatch events, update store
    window.dispatchEvent(new CustomEvent('realtime', { detail: data }))
  }
  
  private reconnect(eventId: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => this.connect(eventId), 1000 * (this.reconnectAttempts + 1))
      this.reconnectAttempts++
    }
  }
}
```

## 3.3 Refactorización de Pantallas MVP

### PANTALLA: Parking (Antes Estacionar)

**Antes:**
```typescript
// screens/Estacionar.tsx — 400+ líneas, todo mezclado
const Estacionar = () => {
  const [selectedZona, setSelectedZona] = useState(...)
  const [mostrarOpciones, setMostrarOpciones] = useState(...)
  
  const zonasMock = eventoData.estacionamiento  // ❌ Mock
  const zonasOrdenadas = getZonasOrdenadas(zonasMock)
  const modo = getModoEstacionamiento(zonasMock)
  
  // 400 líneas de JSX + lógica mezclada
}
```

**Después:**
```typescript
// features/parking/screens/ParkingScreen.tsx
const ParkingScreen = () => {
  const event = useEvent()
  const { userLocation } = useAppStore()
  const { data: recommendation, isLoading, error } = useParkingRecommendation()
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null)
  
  if (!event) return <NoEventError />
  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorBoundary error={error} />
  
  return (
    <>
      <Header title="Estacionar" />
      <ParkingRecommendation 
        recommendation={recommendation}
        onSelectZone={setSelectedZone}
      />
      {selectedZone && (
        <ZoneDetailSheet zone={selectedZone} onClose={() => setSelectedZone(null)} />
      )}
    </>
  )
}
```

### Custom Hook Encapsulación

```typescript
// features/parking/hooks/useParkingRecommendation.ts
export const useParkingRecommendation = () => {
  const { event } = useEvent()
  const { userLocation } = useAppStore()
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null)
  const [isLoading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  
  useEffect(() => {
    if (!event || !userLocation) return
    
    // Fetch recommendation from API
    fetchParkingRecommendation(event.id, userLocation)
      .then(setRecommendation)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [event, userLocation])
  
  return { data: recommendation, isLoading, error }
}
```

## 3.4 Consolidación de Lógica de Scoring

### Centralizar Scoring

**Antes:** Disperso en 3+ archivos
```
decisionEngine.ts   — scoring genérico
mockZones.ts        — scoring parking
mockSalidas.ts      — scoring salidas
Estacionar.tsx      — más scoring local
Salir.tsx           — más scoring local
```

**Después:** Centralizado en `shared/utils/scoring.ts`

```typescript
// shared/utils/scoring.ts
interface ScoringInput {
  distance: number
  saturation: 'bajo' | 'medio' | 'alto' | 'colapsado'
  capacity: number
  weather?: 'clear' | 'rain' | 'storm'
  incidents?: Incident[]
  type: 'parking' | 'exit' | 'food' | 'service'
}

export const calculateScore = (input: ScoringInput): number => {
  const base = input.distance * 1.5 + (100 - input.capacity)
  const saturationPenalty = {
    bajo: 0,
    medio: 5,
    alto: 15,
    colapsado: 30,
  }[input.saturation]
  
  return base + saturationPenalty
}

export const recommendBest = (items: Item[], type: string): Recommendation => {
  // Centralizada lógica de recomendación
}

export const calculateMode = (items: Item[], threshold: number): Mode => {
  // Centralizada lógica de modo (sin_solucion | guiar | asistir | informar)
}
```

## 3.5 Organización de Tipos

### Separación Clara de Tipos

```typescript
// shared/types/domain.ts — Entidades del dominio
export interface Event {
  id: string
  name: string
  location: string
  startDate: Date
  endDate: Date
  status: 'planning' | 'active' | 'completed'
}

export interface Zone {
  id: string
  eventId: string
  type: 'parking' | 'exit' | 'food' | 'service'
  geometry: GeoJSON.Polygon
  saturation: 'bajo' | 'medio' | 'alto' | 'colapsado'
  status: 'active' | 'closed' | 'limited'
}

export interface Point {
  id: string
  eventId: string
  type: 'bathroom' | 'police' | 'medical' | 'water'
  coordinates: GeoJSON.Point
  status: 'available' | 'unavailable'
}

export interface Incident {
  id: string
  eventId: string
  type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  geometry: GeoJSON.Geometry
  timestamp: Date
}

export interface Snapshot {
  id: string
  entityType: 'zone' | 'point' | 'flow'
  entityId: string
  state: Record<string, any>
  timestamp: Date
}

// shared/types/api.ts — Response types de API
export interface ApiResponse<T> {
  data: T
  meta: {
    timestamp: Date
    version: string
  }
}

export interface RecommendationResponse {
  primary: Zone | Point
  fallback?: Zone | Point
  confidence: 'high' | 'medium' | 'low'
  reason: string
}

// shared/types/ui.ts — Tipos específicos UI
export interface ParkingRecommendation {
  zone: Zone
  distance: number
  saturation: 'bajo' | 'medio' | 'alto'
  confidence: number
  eta: number // minutos
}
```

---

# SECCIÓN 4 — INTEGRACIÓN BACKEND

## 4.1 APIs Mínimas Requeridas para MVP

### Event Management

```http
GET /api/events
Response: Event[]

GET /api/events/{id}
Response: Event

GET /api/events/current
Response: Event (evento activo actualmente)
```

### Zone Management

```http
GET /api/events/{eventId}/zones
Response: Zone[]

GET /api/events/{eventId}/zones/{id}
Response: Zone

PATCH /api/events/{eventId}/zones/{id}
Body: { saturation: 'bajo' | 'medio' | 'alto' | 'colapsado' }
Response: Zone (actualizado)
```

### Point Management

```http
GET /api/events/{eventId}/points
Response: Point[]

GET /api/events/{eventId}/points/nearby
Query: ?lat=XX&lng=YY&type=bathroom,police&radius=5000
Response: Point[] (ordenados por distancia)
```

### Recommendations

```http
POST /api/recommendations/parking
Body: {
  eventId: string
  userLocation: { lat, lng }
  transportType?: 'car' | 'walk'
}
Response: {
  primary: Zone
  fallback: Zone
  confidence: number
  reason: string
}

POST /api/recommendations/exit
Body: {
  eventId: string
  userLocation: { lat, lng }
  transportType: 'car' | 'walk' | 'transit'
}
Response: {
  primary: Zone
  fallback: Zone
  confidence: number
  reason: string
}

GET /api/emergency/nearby
Query: ?lat=XX&lng=YY&type=bathroom,police
Response: Point[] (ordenados por distancia)
```

### Incident Management

```http
POST /api/events/{eventId}/incidents
Body: {
  type: string
  severity: 'low' | 'medium' | 'high'
  geometry: GeoJSON
  description: string
}
Response: Incident (creado)

GET /api/events/{eventId}/incidents
Query: ?severity=high&active=true
Response: Incident[]
```

### Snapshots

```http
POST /api/events/{eventId}/snapshots
Body: {
  entityType: 'zone' | 'point'
  entityId: string
  state: Record<string, any>
}
Response: Snapshot (creado)

GET /api/events/{eventId}/snapshots
Query: ?entityType=zone&limit=100
Response: Snapshot[]
```

### Real-time WebSocket

```
WS /api/realtime/events/{eventId}

Mensaje servidor → cliente:
{
  type: 'zone_updated' | 'incident_created' | 'snapshot_recorded',
  data: Zone | Incident | Snapshot
}

Mensaje cliente → servidor (opcional):
{
  type: 'subscribe' | 'unsubscribe',
  entity: 'zones' | 'incidents' | 'points'
}
```

## 4.2 Contrato de Datos API

### Event Entity

```typescript
interface Event {
  id: string                    // UUID
  municipalityId: string        // Multi-tenant
  name: string                  // "Festival Jesús María 2026"
  location: string              // Ubicación textual
  geometry: GeoJSON.Polygon     // Perimetro del evento
  startDate: ISO8601DateTime    // Cuando inicia
  endDate: ISO8601DateTime      // Cuando termina
  status: 'planning' | 'active' | 'completed'
  createdAt: ISO8601DateTime
  updatedAt: ISO8601DateTime
  
  // Metadata
  configuration: {
    timezone: string
    language: string
    features: string[]          // ['parking', 'exit', 'emergency']
  }
}
```

### Zone Entity

```typescript
interface Zone {
  id: string
  eventId: string
  type: 'parking' | 'exit_point' | 'service_point' | 'reference'
  name: string
  description?: string
  
  // Geometría
  geometry: GeoJSON.Polygon
  
  // Configuración
  capacity: number              // Capacidad máxima estimada
  priority: number              // 1-10 para priorización
  
  // Estado Runtime
  saturation: 'bajo' | 'medio' | 'alto' | 'colapsado'
  availableCapacity: number     // Capacidad disponible actual
  status: 'active' | 'closed' | 'limited'
  
  // Temporal
  createdAt: ISO8601DateTime
  updatedAt: ISO8601DateTime
  lastStatusUpdate: ISO8601DateTime
}
```

### Point Entity

```typescript
interface Point {
  id: string
  eventId: string
  type: 'bathroom' | 'police' | 'medical' | 'water' | 'info'
  name: string
  description?: string
  
  // Ubicación exacta
  coordinates: {
    latitude: number
    longitude: number
  }
  
  // Direccional
  address: string
  reference: string            // "Cerca de entrada norte"
  
  // Estado
  status: 'available' | 'unavailable' | 'limited'
  capacity?: number
  currentOccupancy?: number
  
  // Contacto
  phone?: string
  hours?: string               // "9AM-11PM"
  
  // Temporal
  createdAt: ISO8601DateTime
  updatedAt: ISO8601DateTime
  lastStatusUpdate: ISO8601DateTime
}
```

### Recommendation Response

```typescript
interface RecommendationResponse {
  primary: {
    entity: Zone | Point
    distance: number            // en metros
    eta: number                 // en minutos
    saturation: string
    confidence: number          // 0-1
  }
  fallback?: {
    entity: Zone | Point
    distance: number
    eta: number
    saturation: string
    confidence: number
  }
  reasoning: string             // "Zona con menor saturación"
  timestamp: ISO8601DateTime
}
```

### Incident Entity

```typescript
interface Incident {
  id: string
  eventId: string
  type: 'congestion' | 'closure' | 'emergency' | 'accident'
  severity: 'low' | 'medium' | 'high' | 'critical'
  
  // Ubicación
  geometry: GeoJSON.Geometry   // Punto o Polygon
  affectedAreas: string[]       // IDs de zonas afectadas
  
  // Descripción
  title: string
  description: string
  reportedBy: string            // user, operator, system
  
  // Estado
  status: 'active' | 'resolved' | 'monitoring'
  
  // Temporal
  createdAt: ISO8601DateTime
  resolvedAt?: ISO8601DateTime
}
```

### Snapshot Entity

```typescript
interface Snapshot {
  id: string
  eventId: string
  
  // Referencia
  entityType: 'zone' | 'point' | 'flow' | 'event'
  entityId: string
  
  // Estado capturado
  state: Record<string, any>    // Snapshot del estado completo
  
  // Metadata
  timestamp: ISO8601DateTime
  triggeredBy: string           // 'manual', 'system', 'realtime'
  
  // Histórico
  tags?: string[]
  metadata?: Record<string, any>
}
```

## 4.3 Estrategia de Integración Gradual

### Phase 1: Mock → API Sin Realizar Cambios UI

```typescript
// core/api/client.ts
export const useEnvironment = () => {
  const env = process.env.VITE_ENV || 'mock'
  return env
}

// core/api/queries.ts
export const useZones = (eventId: string) => {
  const env = useEnvironment()
  
  const mockData = async () => {
    // Retorna eventoData.estacionamiento, etc
  }
  
  const apiData = async () => {
    // Fetch real del API
  }
  
  const data = env === 'mock' ? mockData() : apiData()
  return useQuery(['zones', eventId], data)
}
```

**Ventaja:** Pueden coexistir ambos sin romper UI

### Phase 2: Reemplazar Llamadas Progresivamente

```typescript
// Antes
const zonasMock = eventoData.estacionamiento

// Después
const { data: zonas } = useZones(eventId)
```

### Phase 3: Eliminar Mock Data Cuando API Estable

```typescript
// Remover eventoData.ts y todos los mock files
```

## 4.4 Error Handling y Resilencia

### API Client con Retry

```typescript
// core/api/client.ts
const client = axios.create({...})

// Retry logic
client.interceptors.response.use(
  response => response,
  async error => {
    const { config } = error
    
    if (error.response?.status === 500 && config.__retryCount < 3) {
      config.__retryCount = (config.__retryCount || 0) + 1
      await delay(1000 * config.__retryCount)
      return client(config)
    }
    
    return Promise.reject(error)
  }
)
```

### Fallback a Mock Data

```typescript
// core/api/fallback.ts
export const useZonesWithFallback = (eventId: string) => {
  const [data, setData] = useState<Zone[]>([])
  const [error, setError] = useState<Error | null>(null)
  
  useEffect(() => {
    fetchZones(eventId)
      .catch(() => {
        // Fallback a mock
        setData(eventoData.estacionamiento)
      })
      .catch(setError)
  }, [eventId])
  
  return { data, error }
}
```

### Offline Detection

```typescript
// core/api/offline.ts
export const useApiWithOffline = () => {
  const isOffline = useOffline()
  
  const fetch = async (endpoint: string) => {
    if (isOffline) {
      // Usar cache local o mock
      return getLocalCache(endpoint) || getMockData(endpoint)
    }
    
    return client.get(endpoint)
  }
  
  return { fetch, isOffline }
}
```

---

# SECCIÓN 5 — DASHBOARD MUNICIPAL

## 5.1 Contexto: ¿Por qué NO está en MVP Actual?

El MVP REAL define:
```
Dashboard Municipal es responsabilidad COMPARTIDA:
- Frontend: interfaz de usuario (NUEVO módulo)
- Backend: control operacional (FastAPI)
- Datos: estados, incidentes, snapshots (DB)
```

El frontend actual **NO tiene infraestructura** para dashboard porque:
1. Sin estado global → no puede sincronizar múltiples usuarios
2. Sin realtime → actualizaciones estáticas
3. Sin API → sin fuente de datos operacionales
4. Sin acceso de operador → todo público
5. Sin persistencia → sin histórico

**Decisión MVP:** Dashboard es **FASE 2** (después de integraciones core)

## 5.2 Especificación Funcional Mínima

### Usuarios del Dashboard
- Operadores municipales
- Coordinadores de evento
- Personal de seguridad

### Funcionalidades Mínimas

| Feature | Descripción | Prioridad |
|---------|---|----------|
| **Actualizar Saturación** | Cambiar estado zona (bajo → alto) | 🔴 CRÍTICA |
| **Reportar Incidente** | Crear incidente (congestión, corte) | 🔴 CRÍTICA |
| **Visualizar Zonas** | Mapa con estados actuales | 🟡 ALTA |
| **Monitorear Estado** | Dashboard en vivo | 🟡 ALTA |
| **Cambiar Status** | Habilitar/deshabilitar zona | 🟡 ALTA |
| **Ver Snapshots** | Histórico de cambios | 🟢 MEDIA |
| **Exportar Datos** | CSV con métricas | 🟢 MEDIA |

### Funcionalidades FUERA MVP v1

- Analytics avanzados
- Predicciones
- Reportes automáticos
- Integración con sistemas municipales
- Multi-usuario simultáneo coordinado
- Auditoría granular

## 5.3 Arquitectura del Dashboard

### Estructura de Carpetas

```
features/dashboard/
├── screens/
│   ├── DashboardScreen.tsx        (Hub principal)
│   ├── ZoneManagementScreen.tsx   (CRUD zonas)
│   └── IncidentReportScreen.tsx   (Reportar incidentes)
│
├── components/
│   ├── ZoneSaturationWidget.tsx   (Estado zonas)
│   ├── IncidentList.tsx            (Lista incidentes)
│   ├── StatusUpdater.tsx           (Cambiar estado)
│   ├── IncidentForm.tsx            (Crear incidente)
│   └── HistoryPanel.tsx            (Snapshots históricos)
│
├── hooks/
│   ├── useMunicipalDashboard.ts   (Hook principal)
│   ├── useZoneUpdates.ts          (Actualizar zonas)
│   └── useIncidents.ts            (Gestionar incidentes)
│
├── types.ts
└── utils.ts
```

### Pantalla Principal: Dashboard

```typescript
// features/dashboard/screens/DashboardScreen.tsx
const DashboardScreen = () => {
  const event = useEvent()
  const { zones, incidents, isUpdating } = useMunicipalDashboard()
  
  return (
    <>
      <Header title={`Dashboard: ${event?.name}`} />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
        {/* Zonas en Vivo */}
        <section className="col-span-1">
          <h2 className="text-xl font-bold mb-4">Estado Zonas</h2>
          <ZoneSaturationWidget zones={zones} />
        </section>
        
        {/* Incidentes */}
        <section className="col-span-1">
          <h2 className="text-xl font-bold mb-4">Incidentes Activos</h2>
          <IncidentList incidents={incidents} />
        </section>
        
        {/* Acciones */}
        <section className="col-span-2">
          <h2 className="text-xl font-bold mb-4">Acciones</h2>
          <div className="grid grid-cols-2 gap-4">
            <button className="btn btn-primary">
              + Actualizar Saturación
            </button>
            <button className="btn btn-danger">
              📋 Reportar Incidente
            </button>
          </div>
        </section>
      </div>
    </>
  )
}
```

## 5.4 Componentes Principales del Dashboard

### ZoneSaturationWidget

```typescript
// features/dashboard/components/ZoneSaturationWidget.tsx
interface ZoneSaturationWidgetProps {
  zones: Zone[]
  onUpdate?: (zone: Zone, newSaturation: string) => void
}

const ZoneSaturationWidget: React.FC<ZoneSaturationWidgetProps> = ({ 
  zones, 
  onUpdate 
}) => {
  return (
    <div className="space-y-2">
      {zones.map(zone => (
        <div 
          key={zone.id}
          className="flex items-center justify-between bg-white p-4 rounded-lg border"
        >
          <div>
            <h3 className="font-bold">{zone.name}</h3>
            <p className="text-sm text-gray-500">
              Capacidad: {zone.availableCapacity}/{zone.capacity}
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-sm font-bold
              ${zone.saturation === 'bajo' ? 'bg-green-100 text-green-800' : ''}
              ${zone.saturation === 'medio' ? 'bg-yellow-100 text-yellow-800' : ''}
              ${zone.saturation === 'alto' ? 'bg-orange-100 text-orange-800' : ''}
              ${zone.saturation === 'colapsado' ? 'bg-red-100 text-red-800' : ''}
            `}>
              {zone.saturation.toUpperCase()}
            </span>
            
            <select 
              value={zone.saturation}
              onChange={(e) => onUpdate?.(zone, e.target.value)}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value="bajo">Bajo</option>
              <option value="medio">Medio</option>
              <option value="alto">Alto</option>
              <option value="colapsado">Colapsado</option>
            </select>
          </div>
        </div>
      ))}
    </div>
  )
}
```

### IncidentReportForm

```typescript
// features/dashboard/components/IncidentForm.tsx
const IncidentForm: React.FC = () => {
  const [form, setForm] = useState({
    type: 'congestion',
    severity: 'medium',
    description: '',
    affectedZones: [] as string[]
  })
  
  const { mutate: createIncident, isLoading } = useCreateIncident()
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createIncident(form, {
      onSuccess: () => {
        // Reset form
        setForm({ type: 'congestion', severity: 'medium', description: '', affectedZones: [] })
        // Show success toast
      }
    })
  }
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <select 
        value={form.type}
        onChange={(e) => setForm({ ...form, type: e.target.value })}
      >
        <option value="congestion">Congestión</option>
        <option value="closure">Cierre</option>
        <option value="emergency">Emergencia</option>
      </select>
      
      <select 
        value={form.severity}
        onChange={(e) => setForm({ ...form, severity: e.target.value })}
      >
        <option value="low">Baja</option>
        <option value="medium">Media</option>
        <option value="high">Alta</option>
        <option value="critical">Crítica</option>
      </select>
      
      <textarea
        placeholder="Describir incidente..."
        value={form.description}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
      />
      
      <button 
        type="submit" 
        disabled={isLoading}
        className="btn btn-danger w-full"
      >
        {isLoading ? 'Reportando...' : 'Reportar Incidente'}
      </button>
    </form>
  )
}
```

## 5.5 Integración con Backend del Dashboard

### Endpoints Adicionales para Dashboard

```http
# Actualizar saturación (operador municipal)
PATCH /api/events/{eventId}/zones/{zoneId}
Body: {
  saturation: 'bajo' | 'medio' | 'alto' | 'colapsado',
  updatedBy: 'operator_id',
  reason?: 'string'
}
Response: Zone (actualizado)

# Crear incidente
POST /api/events/{eventId}/incidents
Body: {
  type: string,
  severity: 'low' | 'medium' | 'high' | 'critical',
  description: string,
  affectedZones: string[],
  reportedBy: 'operator_id'
}
Response: Incident

# Listar snapshots históricos
GET /api/events/{eventId}/snapshots?entityType=zone&limit=100&offset=0
Response: Snapshot[]
```

### Hooks para Dashboard

```typescript
// features/dashboard/hooks/useMunicipalDashboard.ts
export const useMunicipalDashboard = () => {
  const { event } = useEvent()
  
  const { data: zones, isLoading: zonesLoading } = useQuery(
    ['zones', event?.id],
    () => fetchZones(event!.id),
    { enabled: !!event }
  )
  
  const { data: incidents, isLoading: incidentsLoading } = useQuery(
    ['incidents', event?.id],
    () => fetchIncidents(event!.id, { active: true }),
    { enabled: !!event }
  )
  
  return {
    zones: zones || [],
    incidents: incidents || [],
    isUpdating: zonesLoading || incidentsLoading
  }
}

export const useUpdateZoneSaturation = () => {
  return useMutation(
    (params: { eventId: string; zoneId: string; saturation: string }) =>
      updateZoneSaturation(params),
    {
      onSuccess: () => {
        // Invalidate zones query
        queryClient.invalidateQueries(['zones'])
      }
    }
  )
}

export const useCreateIncident = () => {
  return useMutation(
    (params: { eventId: string; incident: IncidentInput }) =>
      createIncident(params),
    {
      onSuccess: () => {
        // Invalidate incidents query
        queryClient.invalidateQueries(['incidents'])
      }
    }
  )
}
```

---

# SECCIÓN 6 — PRIORIDADES REALES

## 6.1 Matriz de Decisión

### Criterios

| Criterio | Peso | Descripción |
|----------|------|---|
| **Impacto MVP** | 40% | ¿Es obligatorio para MVP? |
| **Dependencias** | 30% | ¿De qué depende? |
| **Complejidad** | 20% | ¿Cuánto esfuerzo requiere? |
| **Riesgo Técnico** | 10% | ¿Qué tan incierto es? |

### Scoring Tareas

```
TIER 1 - BLOQUEADORES (Hacer PRIMERO)
═════════════════════════════════════════

1. ✅ [CRÍTICA] Crear Global State (Zustand)
   ├─ Impacto: 100% (toda la app depende)
   ├─ Dependencias: ninguna
   ├─ Complejidad: media
   ├─ Esfuerzo: 4-6 horas
   ├─ ROI: Altísimo
   └─ Bloqueador para: API client, realtime, multi-evento

2. ✅ [CRÍTICA] Implementar Event Context
   ├─ Impacto: 100%
   ├─ Dependencias: Global state
   ├─ Complejidad: baja
   ├─ Esfuerzo: 2-3 horas
   ├─ ROI: Altísimo
   └─ Bloqueador para: multi-evento, pantallas MVP

3. ✅ [CRÍTICA] Extraer hardcoding (Jesús María → dinámica)
   ├─ Impacto: 95% (afecta todos los componentes)
   ├─ Dependencias: Event Context
   ├─ Complejidad: media
   ├─ Esfuerzo: 6-8 horas
   ├─ ROI: Altísimo
   └─ Bloqueador para: testing, multi-evento

4. ✅ [CRÍTICA] API Client + Endpoints Centralizados
   ├─ Impacto: 90%
   ├─ Dependencias: Global state
   ├─ Complejidad: baja
   ├─ Esfuerzo: 3-4 horas
   ├─ ROI: Altísimo
   └─ Bloqueador para: integración backend


TIER 2 - CORE MVP (Hacer SEGUNDO)
═════════════════════════════════════════

5. ✅ [ALTA] Refactorizar Parking (Estacionar)
   ├─ Impacto: 80%
   ├─ Dependencias: Global state, API client
   ├─ Complejidad: alta
   ├─ Esfuerzo: 8-12 horas
   ├─ ROI: Alto
   └─ Resultado: Pantalla 100% funcional, API-ready

6. ✅ [ALTA] Refactorizar Exit (Salir)
   ├─ Impacto: 80%
   ├─ Dependencias: Global state, API client
   ├─ Complejidad: alta
   ├─ Esfuerzo: 8-12 horas
   ├─ ROI: Alto
   └─ Resultado: Pantalla 100% funcional, API-ready

7. ✅ [ALTA] Refactorizar Emergency (Emergencia)
   ├─ Impacto: 75%
   ├─ Dependencias: Global state, API client
   ├─ Complejidad: baja
   ├─ Esfuerzo: 4-6 horas
   ├─ ROI: Alto
   └─ Resultado: Pantalla 100% funcional, API-ready

8. ✅ [ALTA] Centralizar Scoring Logic
   ├─ Impacto: 70%
   ├─ Dependencias: ninguna
   ├─ Complejidad: baja
   ├─ Esfuerzo: 3-4 horas
   ├─ ROI: Alto (DRY, mantenibilidad)
   └─ Bloqueador para: testing, refactorizaciones


TIER 3 - INFRAESTRUCTURA (Hacer TERCERO)
═════════════════════════════════════════

9. ✅ [ALTA] Implementar Real-time (WebSocket)
   ├─ Impacto: 85%
   ├─ Dependencias: Global state, API client
   ├─ Complejidad: media-alta
   ├─ Esfuerzo: 8-10 horas
   ├─ ROI: Alto
   └─ Bloqueador para: actualización en vivo, dashboard

10. ✅ [ALTA] Refactorizar Home Screen
    ├─ Impacto: 60%
    ├─ Dependencias: Event context, parametrización
    ├─ Complejidad: baja
    ├─ Esfuerzo: 2-3 horas
    ├─ ROI: medio
    └─ Resultado: Home dinámico, multi-evento

11. ✅ [MEDIA] Crear Error Boundaries + Loading States
    ├─ Impacto: 70%
    ├─ Dependencias: ninguna
    ├─ Complejidad: baja
    ├─ Esfuerzo: 3-4 horas
    ├─ ROI: Alto (UX + estabilidad)
    └─ Requisito para: producción


TIER 4 - LIMPIEZA (Hacer CUARTO)
═════════════════════════════════════════

12. ✅ [MEDIA] Eliminar Pantallas Fuera MVP
    ├─ Impacto: 20% (limpieza)
    ├─ Dependencias: refactorizaciones de Tier 2
    ├─ Complejidad: baja
    ├─ Esfuerzo: 2-3 horas
    ├─ ROI: medio (reducir ruido)
    └─ Archivos: ServiciosComer, Transport, Pernoctar, Gastro, etc

13. ✅ [MEDIA] Consolidar Mock Data
    ├─ Impacto: 30%
    ├─ Dependencias: API client
    ├─ Complejidad: baja
    ├─ Esfuerzo: 2-3 horas
    ├─ ROI: medio
    └─ Resultado: Single source of truth

14. ✅ [MEDIA] Refactor Type System
    ├─ Impacto: 40%
    ├─ Dependencias: consolidación mock data
    ├─ Complejidad: media
    ├─ Esfuerzo: 4-6 horas
    ├─ ROI: alto (mantenibilidad)
    └─ Resultado: types/ bien organizados


TIER 5 - NUEVO MÓDULO (Hacer QUINTO)
═════════════════════════════════════════

15. ✅ [MEDIA] Crear Dashboard Municipal
    ├─ Impacto: 60%
    ├─ Dependencias: realtime, API client, Tier 2 completo
    ├─ Complejidad: alta
    ├─ Esfuerzo: 12-16 horas
    ├─ ROI: Alto (operacional)
    └─ Nota: Fase 2 después de core MVP
```

## 6.2 Lista de Tareas Ordenada por Prioridad

### SPRINT 1 — Foundation (1-2 semanas)

```markdown
## Semana 1

- [ ] **Day 1-2:** Global State Setup (Zustand)
      └─ 4-6h: Crear store.ts, hooks contexto
      
- [ ] **Day 2:** Event Context Provider
      └─ 2-3h: Crear EventContext.tsx + useEvent hook
      
- [ ] **Day 3-4:** API Client + Endpoints
      └─ 3-4h: axios client, endpoints centralizados, types
      
- [ ] **Day 4-5:** Extraer Hardcoding
      └─ 6-8h: Header, config, rutas, teléfonos → dinámicos

Total Semana 1: ~18-25h

## Semana 2

- [ ] **Day 6:** Centralizar Scoring Logic
      └─ 3-4h: shared/utils/scoring.ts
      
- [ ] **Day 6-7:** Crear Error Boundaries + Loading
      └─ 3-4h: ErrorBoundary.tsx, LoadingSpinner.tsx
      
- [ ] **Day 8-10:** Refactorizar Parking Screen
      └─ 8-12h: features/parking/ completo

Total Semana 2: ~17-24h

**Sprint 1 Total: ~35-49h (4-6 días de trabajo full-time)**
```

### SPRINT 2 — Core Pantallas (1-2 semanas)

```markdown
## Semana 3

- [ ] **Day 11-13:** Refactorizar Exit Screen
      └─ 8-12h: features/exit/ completo
      
- [ ] **Day 13-14:** Refactorizar Emergency Screen
      └─ 4-6h: features/emergency/ completo

Total Semana 3: ~16-22h

## Semana 4

- [ ] **Day 15:** Home Screen Refactor
      └─ 2-3h: Hacerlo dinámico
      
- [ ] **Day 15-17:** Real-time WebSocket
      └─ 8-10h: core/realtime/, handlers
      
- [ ] **Day 18:** Testing de pantallas MVP
      └─ 4-6h: Manual testing con mock API

Total Semana 4: ~18-25h

**Sprint 2 Total: ~34-47h (4-6 días de trabajo full-time)**
```

### SPRINT 3 — Limpieza + Dashboard (1-2 semanas)

```markdown
## Semana 5

- [ ] **Day 19-20:** Eliminar pantallas fuera MVP
      └─ 2-3h: Remover ServiciosComer, Transport, etc
      
- [ ] **Day 20-21:** Consolidar Mock Data
      └─ 2-3h: Unificar en single source of truth
      
- [ ] **Day 22:** Refactor Type System
      └─ 4-6h: domain.ts, api.ts, ui.ts

Total Semana 5: ~12-17h

## Semana 6

- [ ] **Day 23-28:** Dashboard Municipal
      └─ 12-16h: features/dashboard/ completo

Total Semana 6: ~12-16h

**Sprint 3 Total: ~24-33h (3-4 días de trabajo full-time)**
```

## 6.3 QUÉ CONGELAR INMEDIATAMENTE

```
❌ NO TOCAR (Congeladas para MVP v2+):

1. ServiciosTransporte
   └─ Depende de API de transporte público (no existe)
   
2. ServiciosComer
   └─ Depende de comercios reales (fuera MVP)
   
3. GastronomiaExpanded
   └─ Expansión innecesaria
   
4. ServiciosGenerales
   └─ Scope creep
   
5. Pernoctar
   └─ No en MVP REAL
   
6. AsistenteScreen
   └─ IA conversacional (futuro)
   
7. ResolverAhora (parcialmente)
   └─ Incompleto, congelar hasta que haya contexto claro
   
8. Gastronomía en Home
   └─ Remover del hub de accesos rápidos

LÍNEAS TOTALES A REMOVER: ~1500-2000
ARCHIVOS A ELIMINAR: 8-10
RUTAS A ELIMINAR: 7-8
```

## 6.4 QUÉ ELIMINAR PERMANENTEMENTE

```
❌ CÓDIGO MUERTO - REMOVER:

1. @supabase/supabase-js (package.json)
   └─ NO ESTÁ IMPLEMENTADO
   └─ Acción: npm uninstall @supabase/supabase-js

2. Componentes no utilizados
   └─ SimpleMap.tsx (placeholder)
   └─ Partes de StatusBanner poco usadas

3. Mock files duplicados
   └─ mockZones.ts (DUPLICA eventoData.ts)
   └─ mockResolver.ts (incompleto)
   └─ mockCorredoresGastronomicos.ts

4. CSS no utilizado
   └─ Revisar index.css para clases muertas

ESTIMADO: ~500-800 líneas de code dead code
```

---

# SECCIÓN 7 — PLAN DE ACCIÓN TÉCNICO

## 7.1 Roadmap General

```
┌─────────────────────────────────────────────────────────────────┐
│         ROADMAP DE IMPLEMENTACIÓN MVP FRONTEND REAL             │
│                 Cronograma: 8-10 semanas                        │
└─────────────────────────────────────────────────────────────────┘

FASE 1: FOUNDATION (Semanas 1-2) [35-49h]
├─ Global State Setup ✓
├─ Event Context ✓
├─ API Client ✓
├─ Extraer Hardcoding ✓
└─ Centralizar Lógica ✓

FASE 2: CORE MVP (Semanas 3-4) [34-47h]
├─ Refactor Parking ✓
├─ Refactor Exit ✓
├─ Refactor Emergency ✓
├─ Home Dinámico ✓
└─ Real-time WebSocket ✓

FASE 3: LIMPIEZA + DASHBOARD (Semanas 5-6) [24-33h]
├─ Eliminar Pantallas No-MVP ✓
├─ Consolidar Datos ✓
├─ Refactor Tipos ✓
└─ Dashboard Municipal (MVP v1) ✓

FASE 4: INTEGRACIÓN BACKEND (Semanas 7-8) [20-30h]
├─ Conectar API reales ✓
├─ Testing end-to-end ✓
├─ Error handling ✓
└─ Offline mode ✓

FASE 5: ESTABILIZACIÓN (Semanas 9-10) [15-25h]
├─ Performance ✓
├─ Accesibilidad ✓
├─ Testing real event ✓
└─ Deploy MVP ✓

TOTAL: 128-184 horas (16-24 días developer full-time)
EQUIPO MÍNIMO: 1-2 developers
TIMELINE REALISTA: 8-10 semanas con equipo de 1-2 personas
```

## 7.2 Checklist de Implementación Detallada

### FASE 1 — FOUNDATION

#### Task 1.1: Global State Setup

```markdown
### 1.1.1 Crear Zustand Store

[ ] Instalar zustand: `npm install zustand`
[ ] Crear `core/state/store.ts`
[ ] Definir AppState interface
[ ] Implementar acciones principales
[ ] Crear typed hooks (useAppStore)

**Archivo:** core/state/store.ts (80-120 líneas)

### 1.1.2 Crear Contextos Complementarios

[ ] EventContext.tsx (event actual)
[ ] UserContext.tsx (ubicación usuario)
[ ] RecommendationStore (estado recomendaciones)

**Archivos:** 3 x 40-60 líneas c/u

### 1.1.3 Integrar Store en App.tsx

[ ] Wrappear App con providers
[ ] Conectar Zustand dev tools
[ ] Testing básico en console

**Tiempo estimado:** 4-6 horas
**Validación:** `console.log(useAppStore())` debe mostrar store
```

#### Task 1.2: Event Context Provider

```markdown
### 1.2.1 Implementar EventProvider

[ ] Crear EventContext.tsx
[ ] Context.Provider en App.tsx
[ ] useEvent() hook
[ ] TypeScript types para Event

### 1.2.2 Testear Context

[ ] Header debe usar useEvent()
[ ] console.log(useEvent()) debe mostrar evento
[ ] Cambiar evento debe actualizar toda la app

**Tiempo estimado:** 2-3 horas
**Validación:** Evento debe ser accesible en cualquier componente
```

#### Task 1.3: API Client Setup

```markdown
### 1.3.1 Crear API Client

[ ] core/api/client.ts
[ ] axios con baseURL
[ ] Interceptors para auth
[ ] Error handling

### 1.3.2 Centralizar Endpoints

[ ] core/api/endpoints.ts
[ ] URLs de eventos, zonas, puntos, etc
[ ] Tipos de respuesta (ApiResponse<T>)

### 1.3.3 Crear Hooks de Fetch

[ ] useApi.ts hook genérico
[ ] useQuery pattern (SWR o React Query)
[ ] Manejo de loading/error

**Archivos:**
- core/api/client.ts (50-70 líneas)
- core/api/endpoints.ts (80-100 líneas)
- core/api/types.ts (100-150 líneas)
- shared/hooks/useApi.ts (60-80 líneas)

**Tiempo estimado:** 3-4 horas
**Validación:** `const data = useApi('/events')` debe funcionar
```

#### Task 1.4: Extraer Hardcoding

```markdown
### 1.4.1 Parametrizar Header

[ ] Remover "Festival Jesús María" hardcodeado
[ ] Usar event.name desde EventContext
[ ] Ubicación dinámica

### 1.4.2 Parametrizar Config

[ ] Mover eventoConfig.ts → dinámica desde backend
[ ] Fases parametrizadas por evento
[ ] Umbrales configurables

### 1.4.3 Parametrizar Rutas y Teléfonos

[ ] Teléfonos de emergencia → desde API
[ ] Puntos seguros → desde API
[ ] Referencias geográficas → dinámica

### 1.4.4 Multi-evento

[ ] Event selector en home (si hay múltiples eventos)
[ ] Cambiar evento debe actualizar toda la app
[ ] Router debe incluir eventId

**Tiempo estimado:** 6-8 horas
**Validación:** App debe funcionar sin hardcoding, parametrizable
```

#### Task 1.5: Centralizar Scoring

```markdown
### 1.5.1 Consolidar en shared/utils/scoring.ts

[ ] calculateScore() — generic
[ ] recommendBest() — generic
[ ] calculateMode() — generic

### 1.5.2 Remover duplicados

[ ] Remover scoring de mockZones.ts
[ ] Remover scoring de mockSalidas.ts
[ ] Actualizar componentes para usar shared/utils

### 1.5.3 Testear Scoring

[ ] Unit tests para scoring
[ ] Validar que resultados son iguales

**Archivo:** shared/utils/scoring.ts (100-150 líneas)

**Tiempo estimado:** 3-4 horas
**Validación:** Resultados de scoring idénticos a antes
```

### FASE 2 — CORE MVP

#### Task 2.1: Refactor Parking Screen

```markdown
### 2.1.1 Crear Estructura de Carpetas

[ ] features/parking/screens/ParkingScreen.tsx
[ ] features/parking/components/
[ ] features/parking/hooks/
[ ] features/parking/types.ts
[ ] features/parking/utils.ts

### 2.1.2 Implementar Pantalla

[ ] Extraer lógica de Estacionar.tsx
[ ] Conectar a API (zones endpoint)
[ ] Usar global state
[ ] Mantener UX igual

### 2.1.3 Implementar Componentes

[ ] ParkingRecommendation.tsx
[ ] ParkingZoneCard.tsx
[ ] MapSheet.tsx

### 2.1.4 Hook Principal

[ ] useParkingRecommendation() → fetch + scoring

### 2.1.5 Testing

[ ] Con mock API
[ ] Con API real (cuando esté disponible)
[ ] Flujos de usuario completos

**Archivos:** 5-6 archivos nuevos
**Líneas nuevas:** 300-400
**Líneas eliminadas:** 400 (Estacionar.tsx)

**Tiempo estimado:** 8-12 horas
**Validación:** Funcionalidad idéntica, código limpio, API-ready
```

#### Task 2.2: Refactor Exit Screen

```markdown
### 2.2.1 Crear Estructura

[ ] features/exit/screens/ExitScreen.tsx
[ ] features/exit/components/
[ ] features/exit/hooks/
[ ] features/exit/types.ts

### 2.2.2 Implementar Pantalla

[ ] Extraer Salir.tsx
[ ] Mantener exitSessionController pattern
[ ] Conectar a API (zones endpoint)
[ ] 3 modos: auto / transporte / peatonal

### 2.2.3 Componentes

[ ] TransportModeSelector.tsx
[ ] ExitRecommendation.tsx
[ ] ExitOption.tsx

### 2.2.4 Hook Principal

[ ] useExitRecommendation(type)
[ ] exitSessionController integrado

**Tiempo estimado:** 8-12 horas
**Validación:** Igual a Salir.tsx pero refactorizado
```

#### Task 2.3: Refactor Emergency Screen

```markdown
### 2.3.1 Crear Estructura

[ ] features/emergency/screens/EmergencyScreen.tsx
[ ] features/emergency/components/
[ ] features/emergency/hooks/
[ ] features/emergency/types.ts

### 2.3.2 Implementar Pantalla

[ ] Extraer Emergencia.tsx
[ ] Conectar a API (points endpoint)
[ ] Mantener flujos diferenciados

### 2.3.3 Componentes

[ ] EmergencyTypeSelector.tsx
[ ] NearbyPoints.tsx
[ ] BottomSheet (extraído)

### 2.3.4 Hook Principal

[ ] useNearbyPoints(type)
[ ] Filtering y sorting

**Tiempo estimado:** 4-6 horas
**Validación:** Igual funcionalidad, menos código
```

#### Task 2.4: Home Screen Refactor

```markdown
### 2.4.1 Dinamizar Header

[ ] event.name desde EventContext
[ ] ubicacion desde evento

### 2.4.2 Dinamizar Botones

[ ] Accesos rápidos basados en evento
[ ] Ocultar servicios fuera MVP

### 2.4.3 Testing

[ ] Con múltiples eventos (mock)

**Tiempo estimado:** 2-3 horas
**Impacto:** Bajo (UI change)
```

#### Task 2.5: Real-time WebSocket

```markdown
### 2.5.1 Crear WebSocket Connection

[ ] core/realtime/websocket.ts
[ ] Connection management
[ ] Reconnect logic
[ ] Event handlers

### 2.5.2 Subscribir a Eventos

[ ] Zone updates
[ ] Incident updates
[ ] Status changes

### 2.5.3 Update Global State

[ ] Recibir mensaje → update store
[ ] Trigger re-render automático

### 2.5.4 Testing

[ ] Mock WebSocket server
[ ] Validar updates en tiempo real

**Archivo:** core/realtime/websocket.ts (150-200 líneas)

**Tiempo estimado:** 8-10 horas
**Validación:** Updates en vivo sin refresh manual
```

### FASE 3 — LIMPIEZA + DASHBOARD

#### Task 3.1: Eliminar Pantallas No-MVP

```markdown
### 3.1.1 Identificar Archivos

[ ] ServiciosTransporte.tsx → DELETE
[ ] ServiciosComer.tsx → DELETE
[ ] GastronomiaExpanded.tsx → DELETE
[ ] ServiciosGenerales.tsx → DELETE
[ ] Pernoctar.tsx → DELETE
[ ] AsistenteScreen.tsx → DELETE
[ ] ResolverAhora.tsx → CONGELAR (no eliminar)

### 3.1.2 Limpiar App.tsx

[ ] Remover rutas de pantallas eliminadas
[ ] Remover imports

### 3.1.3 Limpiar Mock Data

[ ] mockTransporte.ts → DELETE
[ ] mockComer.ts → DELETE
[ ] mockCorredoresGastronomicos.ts → DELETE
[ ] mockResolver.ts → DELETE

### 3.1.4 Validación

[ ] App debe compilar sin errores
[ ] Rutas muertas deben dar 404

**Tiempo estimado:** 2-3 horas
**Resultado:** Codebase 30% más limpio
```

#### Task 3.2: Consolidar Mock Data

```markdown
### 3.2.1 Auditar Duplicación

[ ] eventoData.ts vs mockZones.ts
[ ] eventoData.ts vs mockSalidas.ts
[ ] Identificar inconsistencias

### 3.2.2 Crear Single Source of Truth

[ ] Mantener eventoData.ts SOLAMENTE
[ ] Migrar datos faltantes
[ ] Mantener mockEmergencia.ts (puntos de emergencia)

### 3.2.3 Actualizar Imports

[ ] Cambiar mockZones → eventoData
[ ] Cambiar mockSalidas → eventoData

### 3.2.4 Validación

[ ] Todos los datos disponibles
[ ] No hay inconsistencias
[ ] Tipos correctos

**Tiempo estimado:** 2-3 horas
**Resultado:** Data centralizada, mantenible
```

#### Task 3.3: Refactor Type System

```markdown
### 3.3.1 Reorganizar Types

[ ] Crear shared/types/domain.ts (entidades)
[ ] Crear shared/types/api.ts (respuestas)
[ ] Crear shared/types/ui.ts (componentes)

### 3.3.2 Consolidar Tipos Duplicados

[ ] Zona: unificar EstadoZona, ZonaEstacionamiento, etc
[ ] Point: unificar tipos de puntos
[ ] Incident: crear interface única

### 3.3.3 Actualizar Imports

[ ] Todos los archivos deben importar de shared/types

### 3.3.4 Validation

[ ] TypeScript strict mode sin errores
[ ] No redundancia de tipos

**Archivos:** 3 nuevos, 5-6 a modificar
**Tiempo estimado:** 4-6 horas
**Resultado:** Sistema de tipos coherente
```

#### Task 3.4: Crear Dashboard Municipal

```markdown
### 3.4.1 Crear Estructura

[ ] features/dashboard/screens/
[ ] features/dashboard/components/
[ ] features/dashboard/hooks/
[ ] features/dashboard/types.ts

### 3.4.2 Pantalla Principal

[ ] features/dashboard/screens/DashboardScreen.tsx
[ ] Grid con zonas + incidentes + acciones
[ ] Real-time updates

### 3.4.3 Componentes

[ ] ZoneSaturationWidget.tsx
[ ] IncidentList.tsx
[ ] IncidentForm.tsx
[ ] HistoryPanel.tsx

### 3.4.4 Hooks

[ ] useMunicipalDashboard()
[ ] useUpdateZoneSaturation()
[ ] useCreateIncident()
[ ] useIncidents()

### 3.4.5 Autenticación + Permisos

[ ] Validar que sea operador (JWT)
[ ] Admin-only features

### 3.4.6 Integración Realtime

[ ] Actualizar zonas en vivo
[ ] Nuevos incidentes en vivo
[ ] Snapshots históricos

### 3.4.7 Testing

[ ] Crear incidente
[ ] Actualizar saturación
[ ] Ver histórico
[ ] Real-time updates

**Archivos:** 6-8 nuevos
**Líneas:** 800-1200
**Tiempo estimado:** 12-16 horas
**Validación:** Dashboard funcional, operacional
```

### FASE 4 — INTEGRACIÓN BACKEND

#### Task 4.1: Conectar API Reales

```markdown
### 4.1.1 Verificar Backend Disponible

[ ] Backend FastAPI debe estar corriendo
[ ] Endpoints deben estar implementados
[ ] CORS configurado correctamente

### 4.1.2 Probar Endpoints Individuales

[ ] GET /events → lista eventos
[ ] GET /events/{id} → evento específico
[ ] GET /zones → zonas
[ ] GET /points/nearby → puntos cercanos

### 4.1.3 Reemplazar Mock Data Gradualmente

[ ] Semana 1: Zones (parking)
[ ] Semana 2: Salidas
[ ] Semana 3: Puntos (emergency)
[ ] Semana 4: Incidentes

### 4.1.4 Validación

[ ] Datos correctos en frontend
[ ] No hay breaking changes en UI

**Tiempo estimado:** 8-12 horas
**Riesgo:** Bajo si backend está listo
```

#### Task 4.2: Testing End-to-End

```markdown
### 4.2.1 Escenario Parking

[ ] Usuario abre app
[ ] Selecciona estacionar
[ ] API retorna zonas
[ ] Se muestra recomendación
[ ] Usuario puede navegar

### 4.2.2 Escenario Exit

[ ] Usuario selecciona modo (auto/transporte/peatonal)
[ ] API retorna salidas
[ ] Se muestra recomendación
[ ] Usuario puede navegar

### 4.2.3 Escenario Emergency

[ ] Usuario selecciona tipo emergencia
[ ] API retorna puntos cercanos
[ ] Se muestra punto seguro + alternativas
[ ] Usuario puede navegar

### 4.2.4 Escenario Dashboard

[ ] Operador ve zonas en vivo
[ ] Operador actualiza saturación
[ ] API persiste cambio
[ ] Otros usuarios ven actualización (realtime)
[ ] Snapshot se crea

**Tiempo estimado:** 6-8 horas
**Validación:** Toda la app funcional end-to-end
```

#### Task 4.3: Error Handling

```markdown
### 4.3.1 API Errors

[ ] 404 - Evento no existe
[ ] 401 - No autenticado
[ ] 500 - Error del servidor
[ ] Timeout - Sin respuesta

### 4.3.2 Network Errors

[ ] Offline → fallback a mock
[ ] Conexión lenta → timeout
[ ] WebSocket reconecta automáticamente

### 4.3.3 Componentes

[ ] ErrorBoundary global
[ ] Error messages claros
[ ] Retry logic

### 4.3.4 Testing

[ ] Simular errores de API
[ ] Validar UX en error cases

**Tiempo estimado:** 4-6 horas
**Validación:** App resiliente a errores
```

### FASE 5 — ESTABILIZACIÓN

#### Task 5.1: Performance

```markdown
### 5.1.1 Auditar Performance

[ ] Lighthouse score
[ ] Bundle size
[ ] Rendering performance

### 5.1.2 Optimizaciones

[ ] Code splitting (React.lazy)
[ ] Memoization (React.memo)
[ ] useCallback donde necesario
[ ] Image optimization

### 5.1.3 Caching

[ ] HTTP caching headers
[ ] Local storage para datos offline
[ ] Session cache

**Tiempo estimado:** 4-6 horas
**Métrica:** Lighthouse > 90
```

#### Task 5.2: Accesibilidad

```markdown
### 5.2.1 Auditar Accesibilidad

[ ] ARIA labels
[ ] Keyboard navigation
[ ] Color contrast
[ ] Screen reader testing

### 5.2.2 Fixes

[ ] Agregar alt text
[ ] Mejorar contrast
[ ] Hacer teclado-navegable
[ ] WCAG 2.1 AA compliance

**Tiempo estimado:** 3-5 horas
**Standard:** WCAG 2.1 AA mínimo
```

#### Task 5.3: Testing Real Event

```markdown
### 5.3.1 Preparación

[ ] Crear evento de prueba en backend
[ ] Cargar datos realistas
[ ] Configucar teams/operadores

### 5.3.2 Testing Manual

[ ] Usuarios finales prueban
[ ] Operadores prueban dashboard
[ ] Scenarios simulados:
   - Peak hour (saturación alta)
   - Incident (congestión)
   - Weather change

### 5.3.3 Data Validation

[ ] Datos correctos
[ ] Recomendaciones sensatas
[ ] Histórico se crea

### 5.3.4 Feedback

[ ] Recolectar feedback
[ ] Bugs → fix inmediato
[ ] UX improvements

**Tiempo estimado:** 6-8 horas
**Validación:** Sistema funciona en evento real (simulado)
```

## 7.3 Definiciones de Listo (Definition of Done)

### Feature Completa
```
✅ Código escrito y formateado (Prettier)
✅ TypeScript sin errores (strict mode)
✅ Tests unitarios (si es necesario)
✅ Tests integración (manual o automated)
✅ Code review aprobado
✅ Documentation actualizada
✅ No breaking changes
✅ Ready para producción
```

### Sprint Completo
```
✅ Todos los items "Done"
✅ Codebase compilable
✅ Sin warnings de TypeScript
✅ Testing del sprint exitoso
✅ Documentación de cambios
✅ Ready para merge a main
```

## 7.4 Métricas de Éxito

```
MÉTRICA                          TARGET         BASELINE
─────────────────────────────────────────────────────────
Lines of Code (total)            < 8000         ~10000
Code Duplication                 < 10%          ~30%
Type Coverage                     > 95%          ~70%
Test Coverage (crítico)           > 80%          ~0%
Bundle Size                       < 250KB        ~280KB
Lighthouse (avg)                 > 90           ~65

VELOCIDAD MVP:
─────────────────────────────────────────────────────────
Home → Recomendación Parking     < 500ms        variable
Home → Emergencia                < 300ms        variable
Dashboard → Actualizar Zona      < 1000ms       N/A

CONFIABILIDAD:
─────────────────────────────────────────────────────────
Uptime (testing)                 > 99%          N/A
Error rate                       < 1%           N/A
WebSocket reconexión             < 5s           N/A
```

## 7.5 Riesgos y Mitigación

```
RIESGO                           PROBABILIDAD   IMPACTO   MITIGACIÓN
──────────────────────────────────────────────────────────────────────
Backend no ready a tiempo        MEDIA          ALTO      Mock API en paralelo
WebSocket inestable              MEDIA          ALTO      Retry logic + fallback
Scope creep en dashboard         ALTA           BAJO      Sprint discipline
Browser compatibility            BAJA           MEDIO     Testing en 3 browsers
Performance issues con realtime  MEDIA          MEDIO     Performance audit temprano
Tipo system no unificado         BAJA           BAJO      Code review fuerte

MITIGACIÓN GENERAL:
1. Arquitectura desacoplada → cambios sin romper
2. Mock API paralela → no depender de backend
3. Type safety → menos bugs
4. Sprint cortos → feedback rápido
5. Testing temprano → encontrar issues pronto
```

---

## 7.6 Conclusiones y Próximos Pasos

### Línea Base de la Auditoría

| Aspecto | Estado | Score |
|---------|--------|-------|
| **Arquitectura** | 40% implementada | 4/10 |
| **State Management** | Completamente ausente | 0/10 |
| **Backend Integration** | Completamente ausente | 0/10 |
| **Real-time** | Completamente ausente | 0/10 |
| **Code Quality** | Básica, duplicada | 5/10 |
| **Type Safety** | Presente, incompleta | 6/10 |
| **Testing** | Ausente | 0/10 |
| **Documentation** | Mínima | 2/10 |
| **UX/UI** | Funcional | 7/10 |
| **Performance** | Aceptable | 6/10 |

**Score Promedio General:** 3.0/10  
**Veredicto:** Refactor arquitectónico OBLIGATORIO

### Plan Ejecutable

1. ✅ **AHORA:** Empezar FASE 1 (Foundation)
   - Tiene dependencias mínimas
   - Desbloquea todo lo demás
   - Estimado: 4-6 días

2. ✅ **LUEGO:** FASE 2 (Core MVP)
   - Depende de FASE 1
   - Estabiliza pantallas principales
   - Estimado: 4-6 días

3. ✅ **DESPUÉS:** FASE 3-4 (Limpieza + Integración)
   - Depende de FASE 2
   - Limpia código muerto
   - Estimado: 5-7 días

4. ✅ **FINAL:** FASE 5 (Estabilización)
   - Pulido final
   - Testing real event
   - Estimado: 3-4 días

**Timeline Total:** 8-10 semanas con 1-2 developers

### Recomendación Final

> **Este refactor NO es opcional.** El frontend actual no puede escalar a producción sin estas modificaciones arquitectónicas. Los cambios propuestos no son "nice-to-have"—son **estructurales y obligatorios** para:
>
> 1. Integrar con backend real
> 2. Soportar multi-evento
> 3. Implementar realtime
> 4. Mantener código en el tiempo
> 5. Validar MVP en evento real
>
> **La inversión en refactor temprano evita deuda técnica severa más adelante.**

---

### Documentos de Referencia Utilizados

Este análisis se basa en la arquitectura conceptual definida en:

1. ✅ `Plataforma de Asistencia Territorial para Eventos Masivos.md` — Visión general
2. ✅ `Modelo de Dominio Backend.md` — Entidades y relaciones
3. ✅ `Event Flows y Lifecycle Operacional.md` — Flujos de datos
4. ✅ `Arquitectura Técnica Real.md` — Stack y decisiones técnicas
5. ✅ `MVP REAL.md` — Alcance concreto del MVP

Este análisis debe revisarse junto con esos documentos para contexto completo.

---

**FIN DEL INFORME**  
Próxima revisión recomendada: Al completar FASE 1

