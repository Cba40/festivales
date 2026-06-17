import React from 'react';
import { MapPinOff, HelpCircle, X, ShieldAlert } from 'lucide-react';

interface LocationPromptModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LocationPromptModal = ({ isOpen, onClose }: LocationPromptModalProps) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md transition-opacity duration-300">
      {/* Modal Card */}
      <div 
        className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-3xl shadow-2xl p-6 max-w-sm w-full relative overflow-hidden transform transition-all duration-300 scale-100 flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Glow Effect Background */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 dark:bg-primary/20 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-32 h-32 bg-warning/10 dark:bg-warning/20 rounded-full blur-3xl -ml-16 -mb-16 pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-350 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
          aria-label="Cerrar"
        >
          <X size={18} />
        </button>

        {/* Header/Icon */}
        <div className="flex flex-col items-center text-center mt-2 mb-4">
          <div className="relative flex items-center justify-center w-16 h-16 bg-rose-50 dark:bg-rose-950/40 text-rose-500 dark:text-rose-400 rounded-full mb-3 shadow-inner">
            <span className="absolute inline-flex h-full w-full rounded-full bg-rose-400/20 animate-ping opacity-75" />
            <MapPinOff size={28} />
          </div>
          <h3 className="text-xl font-extrabold text-slate-900 dark:text-white leading-tight">
            Activar Ubicación
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 px-1">
            Necesitamos tu ubicación para guiarte en el festival, sugerirte estacionamientos libres y mostrarte servicios cercanos.
          </p>
        </div>

        {/* Guide Steps */}
        <div className="space-y-4 my-2 flex-1">
          <h4 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert size={14} /> Cómo activarla en 3 pasos:
          </h4>
          
          <div className="space-y-3">
            {/* Step 1 */}
            <div className="flex gap-3 items-start">
              <div className="flex-shrink-0 flex items-center justify-center w-6 h-6 text-xs font-black text-primary bg-primary/10 dark:bg-primary/20 dark:text-blue-300 rounded-full">
                1
              </div>
              <div className="text-xs text-slate-650 dark:text-slate-300 leading-normal">
                Toca el botón <span className="font-bold text-slate-800 dark:text-slate-200">🔒 Candado</span> o el icono de <span className="font-bold text-slate-800 dark:text-slate-200">Ajustes</span> al lado de la barra de direcciones en la parte superior.
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-3 items-start">
              <div className="flex-shrink-0 flex items-center justify-center w-6 h-6 text-xs font-black text-primary bg-primary/10 dark:bg-primary/20 dark:text-blue-300 rounded-full">
                2
              </div>
              <div className="text-xs text-slate-650 dark:text-slate-300 leading-normal">
                Busca la opción de <span className="font-bold text-slate-800 dark:text-slate-200">Ubicación</span> y cámbiala a <span className="font-bold text-success">Permitir</span> o <span className="font-bold text-success">Conceder</span>.
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-3 items-start">
              <div className="flex-shrink-0 flex items-center justify-center w-6 h-6 text-xs font-black text-primary bg-primary/10 dark:bg-primary/20 dark:text-blue-300 rounded-full">
                3
              </div>
              <div className="text-xs text-slate-650 dark:text-slate-300 leading-normal">
                Vuelve a la app. Se actualizará sola. Si no, <span className="font-bold text-slate-850 dark:text-slate-200">recarga la página</span> para aplicar los cambios.
              </div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="mt-6">
          <button
            onClick={onClose}
            className="w-full bg-gradient-to-r from-primary to-blue-700 hover:from-blue-700 hover:to-primary text-white font-bold text-sm py-3 px-4 rounded-2xl shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all duration-300 text-center"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
