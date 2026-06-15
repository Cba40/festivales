import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/Header'
import { Phone, MapPin, Navigation, Clock, List, Info, Map } from 'lucide-react'
import { useAppStore } from '@/core/state/store'
import { mapZonesToEmergencia, type PuntoSeguro, type PuestoSanitario } from '@/data/mappers'
import { InteractiveMap } from '@/components/InteractiveMap'
import { getDistancias, haversine } from '@/utils/geo'

type EmergencyType = 'nino-perdido' | 'persona-herida' | 'necesito-ayuda' | null
type HelpSubType = 'seguridad' | 'salud' | 'orientacion' | null

type BottomSheetData =
  | { type: 'punto-seguro'; data: PuntoSeguro }
  | { type: 'puesto-sanitario'; data: PuestoSanitario }

const Emergencia = () => {
  const navigate = useNavigate()
  const zones = useAppStore(s => s.zones)
  const [selectedType, setSelectedType] = useState<EmergencyType>(null)
  const [helpSubType, setHelpSubType] = useState<HelpSubType>(null)
  const [inconsciente, setInconsciente] = useState(false)
  const [bottomSheet, setBottomSheet] = useState<BottomSheetData | null>(null)
  const [mostrarLlamar, setMostrarLlamar] = useState(false)
  const [showMap, setShowMap] = useState(false)
  const userLocation = useAppStore(s => s.userLocation)

  const { puntoSeguro, puestoSanitario, zonasReferencia } = useMemo(() => mapZonesToEmergencia(zones), [zones])

  const todosPuntosEmergencia = useMemo(() => {
    const puntos = zones
      .filter((z) => z.type === 'emergencia')
      .map((z) => ({
        id: z.id,
        nombre: z.name,
        lat: z.lat ?? 0,
        lng: z.lng ?? 0,
        referencia: z.referencia ?? '',
        direccion: z.direccion ?? '',
        distancia_min: z.distancia_min ?? 5,
        horario: z.horario ?? '24hs',
        telefono: z.telefono ?? '',
        servicios: z.servicios ?? ['Primeros auxilios'],
        updatedAt: Date.now()
      }))

    if (userLocation) {
      return [...puntos].sort((a, b) => {
        if (a.lat && a.lng && b.lat && b.lng) {
          const distA = haversine(userLocation[0], userLocation[1], a.lat, a.lng)
          const distB = haversine(userLocation[0], userLocation[1], b.lat, b.lng)
          return distA - distB
        }
        return 0
      })
    }
    return puntos
  }, [zones, userLocation])

  // Timeout: show call button after 5s of inactivity
  useEffect(() => {
    if (!selectedType) {
      setMostrarLlamar(false)
      return
    }
    setMostrarLlamar(false)
    const timer = setTimeout(() => setMostrarLlamar(true), 5000)
    return () => clearTimeout(timer)
  }, [selectedType, helpSubType])

  const handleOpenMaps = (lat: number, lng: number) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
    window.open(url, '_blank')
  }

  const handleCall = (phone: string) => {
    window.open(`tel:${phone}`, '_self')
  }

  // Bottom Sheet Helper (Renderizado Inline en cada modo)
  const renderBottomSheet = bottomSheet ? (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-[9999]"
        onClick={() => setBottomSheet(null)}
      />
      {/* Sheet */}
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-2xl p-4 z-[10000] max-w-md mx-auto shadow-2xl">
        <div
          className="w-12 h-1 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-4 cursor-pointer"
          onClick={() => setBottomSheet(null)}
        />

        <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3">
          {bottomSheet.data.nombre}
        </h3>

        <div className="space-y-3 mb-6">
          <div className="flex items-start gap-3">
            <MapPin size={20} className="text-primary mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                {bottomSheet.data.direccion}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-300">
                {bottomSheet.data.referencia}
              </p>
            </div>
          </div>

          {(() => {
            const dist = getDistancias(bottomSheet.data.lat, bottomSheet.data.lng, userLocation, bottomSheet.data.distancia_min)
            return (
              <div className="space-y-1.5 pl-8">
                <p className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  🚶 <span>Caminando:</span> <span className="font-semibold text-slate-800 dark:text-slate-200">{dist.walking}</span>
                </p>
                <p className="text-sm text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  🚗 <span>En auto:</span> <span className="font-semibold text-slate-800 dark:text-slate-200">{dist.driving}</span>
                </p>
              </div>
            )
          })()}

          <div className="flex items-center gap-3">
            <Clock size={20} className="text-primary flex-shrink-0" />
            <p className="text-sm text-slate-700 dark:text-slate-300">
              Horario: {bottomSheet.data.horario}
            </p>
          </div>

          {bottomSheet.type === 'puesto-sanitario' && 'servicios' in bottomSheet.data && (
            <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
              <p className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-2">
                Servicios:
              </p>
              <div className="flex flex-wrap gap-2">
                {(bottomSheet.data as PuestoSanitario).servicios.map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-medium"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <button
          onClick={() => handleOpenMaps(bottomSheet.data.lat, bottomSheet.data.lng)}
          className="w-full bg-primary text-white py-4 rounded-xl text-lg font-bold flex items-center justify-center gap-2 mb-3 active:scale-95 transition-transform"
        >
          <Navigation size={20} />
          Iniciar ruta
        </button>

        <button
          onClick={() => setBottomSheet(null)}
          className="w-full bg-white border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 py-3 rounded-xl font-semibold active:scale-95 transition-transform"
        >
          Cerrar
        </button>
      </div>
    </>
  ) : null

  // MAPA COMPLETO
  if (showMap) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Puestos de Ayuda" showBack onBack={() => setShowMap(false)} />

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          <InteractiveMap
            puntos={todosPuntosEmergencia
              .filter(p => p.lat && p.lng)
              .map(p => ({
                id: p.id,
                nombre: p.nombre,
                lat: p.lat,
                lng: p.lng,
                referencia: p.referencia,
                tipo: 'salud',
                originalData: p
              }))}
            onSelectPunto={(p) => {
              const item = p as any
              setBottomSheet({
                type: item.servicios ? 'puesto-sanitario' : 'punto-seguro',
                data: item
              })
            }}
            onUserLocationUpdate={() => {}}
          />

          {/* Lista de puestos de ayuda */}
          <div className="space-y-2 pb-16">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300 px-1 flex justify-between">
              <span>📍 {todosPuntosEmergencia.length} puestos de ayuda disponibles</span>
              {userLocation && <span className="text-blue-500 text-[10px] font-semibold">📡 Ubicación GPS activa</span>}
            </p>
            {todosPuntosEmergencia.map(p => {
              const isSanitario = p.servicios && p.servicios.length > 0;
              const dist = getDistancias(p.lat, p.lng, userLocation, p.distancia_min)
              return (
                <button
                  key={p.id}
                  onClick={() => setBottomSheet({
                    type: isSanitario ? 'puesto-sanitario' : 'punto-seguro',
                    data: p
                  })}
                  className="w-full text-left bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group shadow-sm flex items-start gap-2"
                >
                  <span className="text-lg mt-0.5">{isSanitario ? '🏥' : '👮'}</span>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-slate-800 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">
                      {p.nombre}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-center">
                      <span>🚶 {dist.walking}</span>
                      <span className="opacity-50">·</span>
                      <span>🚗 {dist.driving}</span>
                      <span className="opacity-50">·</span>
                      <span className="truncate">{p.referencia}</span>
                    </p>
                  </div>
                  <Info size={16} className="text-slate-400 flex-shrink-0" />
                </button>
              );
            })}
          </div>
        </div>

        {/* Botón flotante para alternar Mapa/Lista */}
        <button
          onClick={() => setShowMap(false)}
          className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
        >
          <List size={20} />
          Ver lista
        </button>

        {renderBottomSheet}
      </div>
    )
  }

  // Niño Perdido Protocol
  if (selectedType === 'nino-perdido') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Niño Perdido" showBack onBack={() => setSelectedType(null)} />

        <div className="flex-1 p-4 space-y-4 pb-24">
          {/* 1. ACCIÓN INMEDIATA (lo primero, más grande) */}
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-2xl font-bold mb-2">🛑 QUEDATE EN EL LUGAR</p>
            <p className="text-sm opacity-90">No te muevas de donde estás</p>
          </div>

          {/* 2. ACCIÓN SECUNDARIA */}
          <div className="bg-primary text-white p-4 rounded-xl text-center">
            <p className="text-lg font-bold">👮 Buscá personal de seguridad visible</p>
            <p className="text-sm opacity-90">Uniformados o puestos de información</p>
          </div>

          {/* 3. DERIVACIÓN (fallback) */}
          <div className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-4 rounded-xl">
            <p className="text-slate-800 dark:text-slate-200 font-bold mb-2">
              Si no encontrás → Punto seguro
            </p>
            <p className="text-slate-600 dark:text-slate-300 text-sm">📍 {puntoSeguro.nombre}</p>
            {(() => {
              const dist = getDistancias(puntoSeguro.lat, puntoSeguro.lng, userLocation, puntoSeguro.distancia_min)
              return (
                <p className="text-slate-600 dark:text-slate-300 text-sm flex gap-3">
                  <span>🚶 {dist.walking}</span>
                  <span>🚗 {dist.driving}</span>
                </p>
              )
            })()}
            <p className="text-slate-400 dark:text-slate-400 text-xs mt-1">
              {puntoSeguro.referencia}
            </p>
          </div>

          {/* Timeout button */}
          {mostrarLlamar && (
            <button
              onClick={() => handleCall(puntoSeguro.telefono)}
              className="w-full bg-danger text-white py-5 rounded-xl font-bold animate-pulse active:scale-95 transition-transform shadow-lg"
            >
              📞 Llamar ahora
            </button>
          )}
        </div>

        {/* 4. BOTÓN PRINCIPAL (fijo, siempre visible) */}
        <div className="sticky bottom-4 p-4 bg-gray-50 dark:bg-slate-900">
          <button
            onClick={() => handleCall(puntoSeguro.telefono)}
            className="w-full bg-danger text-white py-5 rounded-xl text-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform shadow-lg"
          >
            <Phone size={24} />
            📞 Llamar ahora
          </button>

          <button
            onClick={() => setBottomSheet({ type: 'punto-seguro', data: puntoSeguro })}
            className="w-full bg-white dark:bg-slate-800 border-2 border-primary text-primary dark:text-blue-400 py-3 rounded-xl font-bold mt-3 flex items-center justify-center gap-2 active:scale-95 transition-transform"
          >
            <MapPin size={20} />
            🗺️ Ver punto seguro
          </button>
        </div>
        {renderBottomSheet}
      </div>
    )
  }

  // Persona Herida Protocol
  if (selectedType === 'persona-herida') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Persona Herida" showBack onBack={() => { setSelectedType(null); setInconsciente(false); }} />

        <div className="flex-1 p-4 space-y-4 pb-24">
          {/* 1. ACCIÓN INMEDIATA (lo más grande, dominante) */}
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-2xl font-bold mb-2">🛑 NO LA MUEVAS</p>
            <p className="text-sm opacity-90">Si no puede levantarse sola</p>
          </div>

          {/* 2. MICRO-ALERTA (toggle opcional) */}
          <button
            onClick={() => setInconsciente(!inconsciente)}
            className={`w-full p-4 rounded-xl text-center border-2 transition-all ${
              inconsciente
                ? 'bg-danger/20 border-danger text-danger'
                : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300'
            }`}
          >
            <p className="font-bold text-lg">
              {inconsciente ? '⚠️' : '❓'} ¿Está inconsciente?
            </p>
          </button>

          {inconsciente && (
            <div className="bg-danger/20 border-2 border-danger text-danger p-4 rounded-xl text-center animate-pulse">
              <p className="font-bold text-lg">⚠️ Si está inconsciente → LLAMÁ AHORA</p>
            </div>
          )}

          {/* 3. ACCIÓN SECUNDARIA */}
          <div className="bg-primary text-white p-4 rounded-xl text-center">
            <p className="text-lg font-bold">📢 Buscá ayuda inmediata alrededor</p>
            <p className="text-sm opacity-90">Seguridad • Personal del evento • Personas cercanas</p>
          </div>

          {/* 4. DERIVACIÓN (solo si puede moverse) */}
          <div className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-4 rounded-xl">
            <p className="text-slate-800 dark:text-slate-200 font-bold mb-2">
              Si puede moverse → Puesto sanitario
            </p>
            <p className="text-slate-600 dark:text-slate-300 text-sm">📍 {puestoSanitario.nombre}</p>
            {(() => {
              const dist = getDistancias(puestoSanitario.lat, puestoSanitario.lng, userLocation, puestoSanitario.distancia_min)
              return (
                <p className="text-slate-600 dark:text-slate-300 text-sm flex gap-3">
                  <span>🚶 {dist.walking}</span>
                  <span>🚗 {dist.driving}</span>
                </p>
              )
            })()}
            <p className="text-slate-400 dark:text-slate-400 text-xs mt-1">
              {puestoSanitario.referencia}
            </p>
          </div>

          {/* Timeout button */}
          {mostrarLlamar && (
            <button
              onClick={() => handleCall(puestoSanitario.telefono)}
              className="w-full bg-danger text-white py-5 rounded-xl font-bold animate-pulse active:scale-95 transition-transform shadow-lg"
            >
              🚑 Llamar asistencia
            </button>
          )}
        </div>

        {/* 5. BOTÓN PRINCIPAL (fijo, siempre visible) */}
        <div className="sticky bottom-4 p-4 bg-gray-50 dark:bg-slate-900">
          <button
            onClick={() => handleCall(puestoSanitario.telefono)}
            className="w-full bg-danger text-white py-5 rounded-xl text-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform shadow-lg"
          >
            <Phone size={24} />
            🚑 Llamar asistencia
          </button>

          <button
            onClick={() => setBottomSheet({ type: 'puesto-sanitario', data: puestoSanitario })}
            className="w-full bg-white dark:bg-slate-800 border-2 border-primary text-primary dark:text-blue-400 py-3 rounded-xl font-bold mt-3 flex items-center justify-center gap-2 active:scale-95 transition-transform"
          >
            <MapPin size={20} />
            🗺️ Ver puesto sanitario
          </button>
        </div>
        {renderBottomSheet}
      </div>
    )
  }

  // Necesito Ayuda - Micro-clasificación
  if (selectedType === 'necesito-ayuda' && !helpSubType) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Ayuda" showBack onBack={() => setSelectedType(null)} />

        <div className="flex-1 p-4 space-y-4">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white text-center mb-6">
            ¿Qué tipo de ayuda necesitás?
          </h1>

          <button
            onClick={() => setHelpSubType('seguridad')}
            className="w-full p-6 bg-slate-800 dark:bg-slate-700 text-white rounded-xl text-lg font-bold active:scale-95 transition-transform shadow-lg"
          >
            🛡️ Seguridad
          </button>

          <button
            onClick={() => setHelpSubType('salud')}
            className="w-full p-6 bg-slate-800 dark:bg-slate-700 text-white rounded-xl text-lg font-bold active:scale-95 transition-transform shadow-lg"
          >
            💚 Salud
          </button>

          <button
            onClick={() => setHelpSubType('orientacion')}
            className="w-full p-6 bg-slate-800 dark:bg-slate-700 text-white rounded-xl text-lg font-bold active:scale-95 transition-transform shadow-lg"
          >
            🧭 Orientación
          </button>
        </div>
      </div>
    )
  }

  // SEGURIDAD sub-type
  if (selectedType === 'necesito-ayuda' && helpSubType === 'seguridad') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Seguridad" showBack onBack={() => setHelpSubType(null)} />

        <div className="flex-1 p-4 space-y-4 pb-24">
          {/* 1. ACCIÓN INMEDIATA */}
          <div className="bg-danger text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">👮 Buscá personal de seguridad visible</p>
          </div>

          {/* 2. DERIVACIÓN */}
          <div className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-4 rounded-xl">
            <p className="font-bold text-slate-800 dark:text-slate-200">Punto seguro más cercano</p>
            {(() => {
              const dist = getDistancias(puntoSeguro.lat, puntoSeguro.lng, userLocation, puntoSeguro.distancia_min)
              return (
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
                  {puntoSeguro.nombre} · 🚶 {dist.walking} · 🚗 {dist.driving}
                </p>
              )
            })()}
          </div>

          {/* Timeout button */}
          {mostrarLlamar && (
            <button
              onClick={() => handleCall(puntoSeguro.telefono)}
              className="w-full bg-danger text-white py-5 rounded-xl font-bold animate-pulse active:scale-95 transition-transform shadow-lg"
            >
              📞 Llamar ahora
            </button>
          )}
        </div>

        {/* BOTÓN PRINCIPAL */}
        <div className="sticky bottom-4 p-4 bg-gray-50 dark:bg-slate-900">
          <button
            onClick={() => handleOpenMaps(puntoSeguro.lat, puntoSeguro.lng)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform shadow-lg"
          >
            <Navigation size={20} />
            🗺️ Ver ruta
          </button>

          <button
            onClick={() => handleCall(puntoSeguro.telefono)}
            className="w-full bg-white dark:bg-slate-800 border-2 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 py-3 rounded-xl font-bold mt-3 flex items-center justify-center gap-2 active:scale-95 transition-transform"
          >
            📞 Llamar asistencia
          </button>
        </div>
        {renderBottomSheet}
      </div>
    )
  }

  // SALUD sub-type
  if (selectedType === 'necesito-ayuda' && helpSubType === 'salud') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Salud" showBack onBack={() => setHelpSubType(null)} />

        <div className="flex-1 p-4 space-y-4 pb-24">
          {/* 1. ACCIÓN INMEDIATA */}
          <div className="bg-primary text-white p-6 rounded-xl text-center">
            <p className="text-xl font-bold">🏥 Dirigite al puesto sanitario</p>
          </div>

          {/* 2. DERIVACIÓN */}
          <div className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-4 rounded-xl">
            <p className="font-bold text-slate-800 dark:text-slate-200">{puestoSanitario.nombre}</p>
            {(() => {
              const dist = getDistancias(puestoSanitario.lat, puestoSanitario.lng, userLocation, puestoSanitario.distancia_min)
              return (
                <p className="text-sm text-slate-600 dark:text-slate-300 mt-1 flex gap-3">
                  <span>🚶 {dist.walking}</span>
                  <span>🚗 {dist.driving}</span>
                  <span>{puestoSanitario.referencia}</span>
                </p>
              )
            })()}
          </div>

          {/* Timeout button */}
          {mostrarLlamar && (
            <button
              onClick={() => handleCall(puestoSanitario.telefono)}
              className="w-full bg-danger text-white py-5 rounded-xl font-bold animate-pulse active:scale-95 transition-transform shadow-lg"
            >
              🚑 Llamar asistencia
            </button>
          )}
        </div>

        {/* BOTÓN PRINCIPAL */}
        <div className="sticky bottom-4 p-4 bg-gray-50 dark:bg-slate-900">
          <button
            onClick={() => setBottomSheet({ type: 'puesto-sanitario', data: puestoSanitario })}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform shadow-lg"
          >
            <Navigation size={20} />
            🗺️ Ver ruta
          </button>
        </div>
        {renderBottomSheet}
      </div>
    )
  }

  // ORIENTACIÓN sub-type
  if (selectedType === 'necesito-ayuda' && helpSubType === 'orientacion') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
        <Header title="Orientación" showBack onBack={() => setHelpSubType(null)} />

        <div className="flex-1 p-4 space-y-4 pb-24">
          {/* 1. INFO DE UBICACIÓN */}
          <div className="bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-600 p-6 rounded-xl text-center">
            <p className="text-lg font-bold text-slate-800 dark:text-slate-200">📍 Estás en: {zonasReferencia.nombre}</p>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-3">
              🚪 Salida más cercana: {zonasReferencia.salidaCercana} ({zonasReferencia.distanciaSalida} min)
            </p>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-2">
              🌳 Zona tranquila: {zonasReferencia.zonaTranquila} ({zonasReferencia.distanciaTranquila} min)
            </p>
          </div>

          {/* Timeout button */}
          {mostrarLlamar && (
            <button
              onClick={() => handleCall(puntoSeguro.telefono)}
              className="w-full bg-danger text-white py-5 rounded-xl font-bold animate-pulse active:scale-95 transition-transform shadow-lg"
            >
              🚑 Llamar asistencia
            </button>
          )}
        </div>

        {/* BOTÓN PRINCIPAL */}
        <div className="sticky bottom-4 p-4 bg-gray-50 dark:bg-slate-900">
          <button
            onClick={() => handleOpenMaps(puntoSeguro.lat, puntoSeguro.lng)}
            className="w-full bg-primary text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-transform shadow-lg"
          >
            <Navigation size={20} />
            🗺️ Ver en mapa
          </button>
        </div>
        {renderBottomSheet}
      </div>
    )
  }

  // Selection Screen (default)
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex flex-col">
      <Header title="Emergencia" showBack onBack={() => navigate('/')} />

      <div className="flex-1 p-4 space-y-4">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white text-center mb-6">
          ¿Qué está pasando?
        </h1>

        <button
          onClick={() => setSelectedType('nino-perdido')}
          className="w-full p-6 bg-danger text-white rounded-xl text-xl font-bold active:scale-95 transition-transform shadow-lg"
        >
          🚨 Niño perdido
        </button>

        <button
          onClick={() => setSelectedType('persona-herida')}
          className="w-full p-6 bg-warning text-white rounded-xl text-xl font-bold active:scale-95 transition-transform shadow-lg"
        >
          🚑 Persona herida
        </button>

        <button
          onClick={() => setSelectedType('necesito-ayuda')}
          className="w-full p-6 bg-primary text-white rounded-xl text-xl font-bold active:scale-95 transition-transform shadow-lg"
        >
          🆘 Necesito ayuda
        </button>
      </div>

      {/* Botón flotante para alternar Mapa/Lista */}
      <button
        onClick={() => setShowMap(true)}
        className="fixed bottom-4 right-4 bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 px-4 rounded-full font-bold shadow-lg flex items-center gap-2 z-30 transition-transform active:scale-95 text-sm"
      >
        <Map size={20} />
        Ver mapa completo
      </button>

      {renderBottomSheet}
    </div>
  )
}

export default Emergencia
