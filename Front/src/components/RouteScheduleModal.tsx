import { X } from 'lucide-react'

interface ScheduleItem {
  day_type: string
  departure_time: string
  destination: string
}

interface RouteScheduleModalProps {
  isOpen: boolean
  onClose: () => void
  schedules: ScheduleItem[]
  lineName: string
}

const DAY_GROUPS: {
  key: string
  label: string
  emoji: string
}[] = [
  { key: 'weekday', label: 'Lunes a Viernes', emoji: '📅' },
  { key: 'saturday', label: 'Sábados', emoji: '📆' },
  { key: 'sunday_holiday', label: 'Domingos y Feriados', emoji: '🏖️' },
]

export const RouteScheduleModal = ({
  isOpen,
  onClose,
  schedules,
  lineName,
}: RouteScheduleModalProps) => {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[10000] bg-black/60 flex items-end sm:items-center justify-center p-4">
      <div className="absolute inset-0" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full sm:max-w-lg bg-white dark:bg-slate-800 rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-start justify-between gap-3 p-5 pb-3 border-b border-slate-100 dark:border-slate-700">
          <div className="min-w-0">
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 truncate">
              {lineName || 'Línea de transporte'}
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-300 mt-0.5 truncate">
              Todos los horarios programados
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-colors shrink-0"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto p-5 space-y-5">
          {schedules.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-slate-500 dark:text-slate-300">
                Este recorrido no tiene horarios cargados todavía.
              </p>
            </div>
          ) : (
            DAY_GROUPS.map((group) => {
              const times = schedules
                .filter((t) => t.day_type === group.key)
                .map((t) => t.departure_time)
              if (times.length === 0) return null
              return (
                <div key={group.key}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm">{group.emoji}</span>
                    <h4 className="text-sm font-bold text-slate-700 dark:text-slate-200">
                      {group.label}
                    </h4>
                    <span className="text-xs text-slate-400">
                      ({times.length} horario{times.length === 1 ? '' : 's'})
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {times.map((time) => (
                      <span
                        key={time}
                        className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-700/60 border border-slate-200 dark:border-slate-600 text-sm font-semibold text-slate-700 dark:text-slate-200 text-center font-mono"
                      >
                        {time}
                      </span>
                    ))}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}