interface GpsModalProps {
  mensaje?: string
  onActivate: () => void
  onClose: () => void
}

export const GpsModal = ({
  mensaje = 'Para mostrarte la opción más cercana, necesitamos tu ubicación GPS.',
  onActivate,
  onClose,
}: GpsModalProps) => (
  <div className="fixed inset-0 bg-black/50 z-[9999] flex items-center justify-center p-4">
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-sm w-full text-center shadow-2xl">
      <p className="text-4xl mb-3">📍</p>
      <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100 mb-2">
        Activa tu ubicación
      </h3>
      <p className="text-sm text-slate-500 dark:text-slate-300 mb-5">{mensaje}</p>
      <button
        onClick={onActivate}
        className="w-full bg-primary text-white py-3 rounded-xl font-bold mb-2 transition-transform active:scale-95"
      >
        Activar GPS
      </button>
      <button
        onClick={onClose}
        className="w-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 py-3 rounded-xl font-bold transition-transform active:scale-95"
      >
        Continuar sin GPS
      </button>
    </div>
  </div>
)
