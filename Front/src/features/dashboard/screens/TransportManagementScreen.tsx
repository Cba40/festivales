import { useCallback, useEffect, useRef, useState } from 'react';
import { isAxiosError } from 'axios';
import { apiClient } from '../../../core/api/client';
import { endpoints } from '../../../core/api/endpoints';

interface TransportLineDTO {
  id: string;
  event_id: string;
  name: string;
  type: string;
  company: string;
  color: string | null;
  active: boolean;
}

interface LineStopDTO {
  id: string;
  line_id: string;
  zone_id: string;
  zone_name: string;
  stop_order: number;
}

interface ScheduleDTO {
  id: string;
  line_stop_id: string;
  day_type: string;
  departure_time: string;
  destination: string;
}

interface TransportZoneDTO {
  id: string;
  name: string;
}

const DAY_TYPE_LABELS: Record<string, string> = {
  weekday: 'Semana',
  saturday: 'Sábado',
  sunday_holiday: 'Domingo / Feriado',
};

type LineModalState =
  | { mode: 'create' }
  | { mode: 'edit'; line: TransportLineDTO }
  | null;

type StopDraft = { zone_id: string; stop_order: number };
type ScheduleDraft = { line_stop_id: string; day_type: string; departure_time: string; destination: string };

function uniqueZoneIds(stops: LineStopDTO[]): string[] {
  return Array.from(new Set(stops.map((s) => s.zone_id)));
}

export function TransportManagementScreen({ eventId }: { eventId: string }) {
  const [lines, setLines] = useState<TransportLineDTO[]>([]);
  const [linesLoading, setLinesLoading] = useState(true);
  const [linesError, setLinesError] = useState<string | null>(null);

  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);

  const [transporteZones, setTransporteZones] = useState<TransportZoneDTO[]>([]);
  const [selectedStops, setSelectedStops] = useState<LineStopDTO[]>([]);
  const [selectedStopsLoading, setSelectedStopsLoading] = useState(false);
  const [selectedSchedules, setSelectedSchedules] = useState<ScheduleDTO[]>([]);
  const [selectedSchedulesLoading, setSelectedSchedulesLoading] = useState(false);

  const [lineModal, setLineModal] = useState<LineModalState>(null);
  const [lineName, setLineName] = useState('');
  const [lineType, setLineType] = useState<'urbano' | 'interurbano'>('urbano');
  const [lineCompany, setLineCompany] = useState('');
  const [lineColor, setLineColor] = useState('#2563eb');
  const [lineActive, setLineActive] = useState(true);
  const [lineModalSaving, setLineModalSaving] = useState(false);
  const [lineModalError, setLineModalError] = useState<string | null>(null);

  const [stopsModalOpen, setStopsModalOpen] = useState(false);
  const [stopsDraft, setStopsDraft] = useState<StopDraft[]>([]);
  const [stopsSaving, setStopsSaving] = useState(false);
  const [stopsError, setStopsError] = useState<string | null>(null);

  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [scheduleDraft, setScheduleDraft] = useState<ScheduleDraft[]>([]);
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  const [csvImporting, setCsvImporting] = useState(false);
  const [csvResult, setCsvResult] = useState<string | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);

  const cargarLines = useCallback(async () => {
    try {
      const res = await apiClient.get<TransportLineDTO[]>(
        endpoints.transportAdmin.lines.list(eventId)
      );
      setLines(res.data);
      setLinesError(null);
    } catch {
      setLinesError('No se pudieron cargar las líneas de transporte.');
    } finally {
      setLinesLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void cargarLines();
  }, [cargarLines]);

  const cargarZonasTransporte = useCallback(async () => {
    try {
      const res = await apiClient.get<{ id: string; name: string; type: string }[]>(
        endpoints.zones.list(eventId)
      );
      const transporte = res.data
        .filter((z) => z.type === 'transporte')
        .map((z) => ({ id: z.id, name: z.name }))
        .sort((a, b) => a.name.localeCompare(b.name));
      setTransporteZones(transporte);
    } catch {
      setLinesError('No se pudieron cargar las zonas de transporte.');
    }
  }, [eventId]);

  useEffect(() => {
    void cargarZonasTransporte();
  }, [cargarZonasTransporte]);

  const cargarDetalle = useCallback(
    async (lineId: string) => {
      setSelectedStopsLoading(true);
      setSelectedSchedulesLoading(true);
      try {
        const [stopsRes, schedulesRes] = await Promise.all([
          apiClient.get<LineStopDTO[]>(endpoints.transportAdmin.stops.list(eventId, lineId)),
          apiClient.get<ScheduleDTO[]>(endpoints.transportAdmin.schedules.list(eventId, lineId)),
        ]);
        setSelectedStops(stopsRes.data);
        setSelectedSchedules(schedulesRes.data);
      } catch {
        setLinesError('No se pudieron cargar las paradas y horarios.');
      } finally {
        setSelectedStopsLoading(false);
        setSelectedSchedulesLoading(false);
      }
    },
    [eventId]
  );

  const toggleSelectLine = (lineId: string) => {
    if (selectedLineId === lineId) {
      setSelectedLineId(null);
      setSelectedStops([]);
      setSelectedSchedules([]);
    } else {
      setSelectedLineId(lineId);
      void cargarDetalle(lineId);
    }
  };

  // ----- Modal de línea -----

  const abrirCrearLinea = () => {
    setLineName('');
    setLineType('urbano');
    setLineCompany('');
    setLineColor('#2563eb');
    setLineActive(true);
    setLineModalError(null);
    setLineModal({ mode: 'create' });
  };

  const abrirEditarLinea = (line: TransportLineDTO) => {
    setLineName(line.name);
    setLineType(line.type === 'interurbano' ? 'interurbano' : 'urbano');
    setLineCompany(line.company);
    setLineColor(line.color ?? '#2563eb');
    setLineActive(line.active);
    setLineModalError(null);
    setLineModal({ mode: 'edit', line });
  };

  const guardarLinea = async () => {
    const nombre = lineName.trim();
    if (!nombre) {
      setLineModalError('El nombre de la línea es obligatorio.');
      return;
    }
    setLineModalSaving(true);
    setLineModalError(null);
    try {
      if (lineModal?.mode === 'edit') {
        await apiClient.put(
          endpoints.transportAdmin.lines.update(eventId, lineModal.line.id),
          {
            name: nombre,
            type: lineType,
            company: lineCompany.trim() || nombre,
            color: lineColor,
            active: lineActive,
          }
        );
      } else {
        await apiClient.post(endpoints.transportAdmin.lines.create(eventId), {
          name: nombre,
          type: lineType,
          company: lineCompany.trim() || nombre,
          color: lineColor,
          active: lineActive,
        });
      }
      setLineModal(null);
      await cargarLines();
    } catch (err) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      setLineModalError(
        status === 409
          ? 'Ya existe una línea con ese nombre en este evento.'
          : 'No se pudo guardar la línea.'
      );
    } finally {
      setLineModalSaving(false);
    }
  };

  const alternarActivoLinea = async (line: TransportLineDTO) => {
    try {
      await apiClient.put(endpoints.transportAdmin.lines.update(eventId, line.id), {
        active: !line.active,
      });
      await cargarLines();
    } catch {
      setLinesError('No se pudo actualizar el estado de la línea.');
    }
  };

  const eliminarLinea = async (line: TransportLineDTO) => {
    const confirmado = window.confirm(
      `¿Eliminar la línea "${line.name}"? También se eliminarán sus paradas y horarios. Esta acción no se puede deshacer.`
    );
    if (!confirmado) return;
    try {
      await apiClient.delete(endpoints.transportAdmin.lines.delete(eventId, line.id));
      if (selectedLineId === line.id) {
        setSelectedLineId(null);
        setSelectedStops([]);
        setSelectedSchedules([]);
      }
      await cargarLines();
    } catch {
      setLinesError('No se pudo eliminar la línea.');
    }
  };

  // ----- Paradas -----

  const abrirModalStops = () => {
    const base = selectedStops.map((s) => ({ zone_id: s.zone_id, stop_order: s.stop_order }));
    setStopsDraft(uniqueZoneIds(selectedStops).length === base.length ? base : base);
    setStopsError(null);
    setStopsModalOpen(true);
  };

  const toggleStopZone = (zoneId: string) => {
    setStopsDraft((prev) => {
      const exists = prev.find((s) => s.zone_id === zoneId);
      if (exists) {
        return prev.filter((s) => s.zone_id !== zoneId);
      }
      const maxOrder = prev.reduce((max, s) => Math.max(max, s.stop_order), 0);
      return [...prev, { zone_id: zoneId, stop_order: maxOrder + 1 }];
    });
  };

  const setStopOrder = (zoneId: string, order: number) => {
    setStopsDraft((prev) =>
      prev.map((s) => (s.zone_id === zoneId ? { ...s, stop_order: order } : s))
    );
  };

  const guardarStops = async () => {
    if (!selectedLineId) return;
    setStopsSaving(true);
    setStopsError(null);
    try {
      await apiClient.put(endpoints.transportAdmin.stops.update(eventId, selectedLineId), {
        stops: stopsDraft,
      });
      setStopsModalOpen(false);
      await cargarDetalle(selectedLineId);
    } catch {
      setStopsError('No se pudieron guardar las paradas.');
    } finally {
      setStopsSaving(false);
    }
  };

  // ----- Horarios -----

  const abrirModalHorarios = () => {
    setScheduleDraft(
      selectedSchedules.map((s) => ({
        line_stop_id: s.line_stop_id,
        day_type: s.day_type,
        departure_time: s.departure_time,
        destination: s.destination,
      }))
    );
    setScheduleError(null);
    setScheduleModalOpen(true);
  };

  const agregarHorario = () => {
    if (selectedStops.length === 0) return;
    setScheduleDraft((prev) => [
      ...prev,
      {
        line_stop_id: selectedStops[0].id,
        day_type: 'weekday',
        departure_time: '08:00',
        destination: '',
      },
    ]);
  };

  const updateHorario = (index: number, patch: Partial<ScheduleDraft>) => {
    setScheduleDraft((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const quitarHorario = (index: number) => {
    setScheduleDraft((prev) => prev.filter((_, i) => i !== index));
  };

  const guardarHorarios = async () => {
    if (!selectedLineId) return;
    const limpiado = scheduleDraft.filter((s) => s.destination.trim());
    setScheduleSaving(true);
    setScheduleError(null);
    try {
      await apiClient.put(endpoints.transportAdmin.schedules.update(eventId, selectedLineId), {
        schedules: limpiado,
      });
      setScheduleModalOpen(false);
      await cargarDetalle(selectedLineId);
    } catch {
      setScheduleError('No se pudieron guardar los horarios. Verificá que todos los campos estén completos.');
    } finally {
      setScheduleSaving(false);
    }
  };

  // ----- Importación CSV -----

  const importarCsv = async (file: File, refreshDetail: boolean) => {
    const formData = new FormData();
    formData.append('file', file);
    setCsvImporting(true);
    setCsvResult(null);
    setCsvError(null);
    try {
      const res = await apiClient.post(endpoints.transportAdmin.importCsv(eventId), formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const r = res.data as {
        lines_created: number;
        lines_updated: number;
        stops_created: number;
        schedules_created: number;
        errors: string[];
      };
      const resumen = [
        `Líneas creadas: ${r.lines_created}`,
        `Líneas actualizadas: ${r.lines_updated}`,
        `Paradas creadas: ${r.stops_created}`,
        `Horarios creados: ${r.schedules_created}`,
      ].join(' · ');
      setCsvResult(r.errors.length ? `${resumen} — Errores: ${r.errors.join('; ')}` : resumen);
      await cargarLines();
      if (refreshDetail && selectedLineId) await cargarDetalle(selectedLineId);
    } catch {
      setCsvError('No se pudo importar el archivo CSV. Verificá el formato.');
    } finally {
      setCsvImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (globalCsvInputRef.current) globalCsvInputRef.current.value = '';
    }
  };

  const onCsvFile = async (file: File) => {
    if (!selectedLineId) return;
    await importarCsv(file, true);
  };

  const onGlobalCsvFile = async (file: File) => {
    await importarCsv(file, false);
  };

  const fileInputRef = useRef<HTMLInputElement>(null);
  const globalCsvInputRef = useRef<HTMLInputElement>(null);

  const descargarPlantilla = async () => {
    try {
      const res = await apiClient.get<Blob>(endpoints.transportAdmin.csvTemplate(eventId), {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'plantilla-transporte.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setCsvError('No se pudo descargar la plantilla.');
    }
  };

  const selectedLine = lines.find((l) => l.id === selectedLineId) ?? null;

  return (
    <div className="space-y-10">
      {/* Sección A: Líneas */}
      <section>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-slate-700">Líneas de Transporte ({lines.length})</h2>
          <div className="flex gap-2">
            <button
              onClick={abrirCrearLinea}
              className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors"
            >
              + Nueva Línea
            </button>
            <label className="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors cursor-pointer">
              {csvImporting ? 'Importando...' : '📥 Importar CSV'}
              <input
                ref={globalCsvInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                disabled={csvImporting}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void onGlobalCsvFile(file);
                }}
              />
            </label>
          </div>
        </div>

        {csvError && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
            {csvError}
          </p>
        )}
        {csvResult && (
          <p className="mb-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-md p-3">
            {csvResult}
          </p>
        )}

        {linesError && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">
            {linesError}
          </p>
        )}

        {linesLoading ? (
          <p className="text-sm text-slate-500 italic">Cargando líneas...</p>
        ) : lines.length === 0 ? (
          <p className="text-sm text-slate-500 italic text-center py-8 bg-white border border-slate-200 rounded-lg">
            No hay líneas registradas. Creá la primera con "+ Nueva Línea".
          </p>
        ) : (
          <div className="bg-white rounded-lg border border-slate-200 divide-y divide-slate-100">
            {lines.map((line) => (
              <div
                key={line.id}
                className={`px-4 py-3 ${selectedLineId === line.id ? 'bg-blue-50' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => toggleSelectLine(line.id)}
                    className="flex items-center gap-3 text-left flex-1"
                  >
                    {line.color && (
                      <span
                        className="inline-block w-4 h-4 rounded-full border border-slate-300 shrink-0"
                        style={{ backgroundColor: line.color }}
                      />
                    )}
                    <div>
                      <div className="font-medium text-slate-800">
                        {line.name}
                        {!line.active && (
                          <span className="ml-2 text-xs text-slate-500">(desactivada)</span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500">
                        {line.type === 'urbano' ? 'Urbano' : 'Interurbano'} · {line.company}
                      </div>
                    </div>
                  </button>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirEditarLinea(line)}
                      className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => void alternarActivoLinea(line)}
                      className="text-sm text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded-md transition-colors"
                    >
                      {line.active ? 'Desactivar' : 'Activar'}
                    </button>
                    <button
                      onClick={() => void eliminarLinea(line)}
                      className="text-sm text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-md transition-colors"
                    >
                      Eliminar
                    </button>
                  </div>
                </div>

                {selectedLineId === line.id && (
                  <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Sección B: Paradas */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="font-semibold text-slate-800">
                          Paradas ({selectedStops.length})
                        </h3>
                        <button
                          onClick={abrirModalStops}
                          className="text-sm bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 py-1.5 px-3 rounded-md transition-colors"
                        >
                          Editar Paradas
                        </button>
                      </div>
                      {selectedStopsLoading ? (
                        <p className="text-sm text-slate-500 italic">Cargando...</p>
                      ) : selectedStops.length === 0 ? (
                        <p className="text-sm text-slate-500 italic">
                          Sin paradas asignadas.
                        </p>
                      ) : (
                        <ol className="space-y-1.5">
                          {selectedStops.map((s) => (
                            <li key={s.id} className="flex items-center gap-2 text-sm">
                              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs">
                                {s.stop_order}
                              </span>
                              <span className="text-slate-700">{s.zone_name}</span>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>

                    {/* Sección C: Horarios */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="font-semibold text-slate-800">
                          Horarios ({selectedSchedules.length})
                        </h3>
                        <div className="flex gap-2">
                          <button
                            onClick={() => void descargarPlantilla()}
                            className="text-sm bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 py-1.5 px-3 rounded-md transition-colors"
                          >
                            📥 Descargar Plantilla CSV
                          </button>
                          <label className="text-sm bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 py-1.5 px-3 rounded-md transition-colors cursor-pointer">
                            {csvImporting ? 'Importando...' : 'Importar CSV'}
                            <input
                              ref={fileInputRef}
                              type="file"
                              accept=".csv"
                              className="hidden"
                              disabled={csvImporting}
                              onChange={(e) => {
                                const f = e.target.files?.[0];
                                if (f) void onCsvFile(f);
                              }}
                            />
                          </label>
                          <button
                            onClick={abrirModalHorarios}
                            className="text-sm bg-blue-600 hover:bg-blue-700 text-white py-1.5 px-3 rounded-md transition-colors"
                          >
                            Editar Horarios
                          </button>
                        </div>
                      </div>
                      {csvError && (
                        <p className="mb-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-md p-2">
                          {csvError}
                        </p>
                      )}
                      {csvResult && (
                        <p className="mb-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md p-2">
                          {csvResult}
                        </p>
                      )}
                      {selectedSchedulesLoading ? (
                        <p className="text-sm text-slate-500 italic">Cargando...</p>
                      ) : selectedSchedules.length === 0 ? (
                        <p className="text-sm text-slate-500 italic">Sin horarios registrados.</p>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm table-fixed">
                            <colgroup>
                              <col className="w-[120px]" />
                              <col className="w-[100px]" />
                              <col className="w-[auto]" />
                            </colgroup>
                            <thead>
                              <tr className="text-left text-slate-500">
                                <th className="pb-1 font-medium">Día</th>
                                <th className="pb-1 font-medium">Hora</th>
                                <th className="pb-1 font-medium">Destino</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200">
                              {selectedSchedules.map((s) => (
                                <tr key={s.id}>
                                  <td className="py-1.5 text-slate-700">
                                    {DAY_TYPE_LABELS[s.day_type] ?? s.day_type}
                                  </td>
                                  <td className="py-1.5 text-slate-700">{s.departure_time}</td>
                                  <td className="py-1.5 text-slate-700 break-words">{s.destination}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Modal línea */}
      {lineModal && (
        <ModalFrame title={lineModal.mode === 'create' ? 'Nueva Línea' : 'Editar Línea'} onClose={() => setLineModal(null)}>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nombre</label>
            <input
              type="text"
              value={lineName}
              onChange={(e) => setLineName(e.target.value)}
              placeholder="Ej: Línea 10"
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tipo</label>
            <select
              value={lineType}
              onChange={(e) => setLineType(e.target.value as 'urbano' | 'interurbano')}
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="urbano">Urbano</option>
              <option value="interurbano">Interurbano</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Empresa</label>
            <input
              type="text"
              value={lineCompany}
              onChange={(e) => setLineCompany(e.target.value)}
              placeholder="Ej: Coniferal"
              className="w-full border-slate-300 rounded-md py-2 px-3 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Color</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={lineColor}
                onChange={(e) => setLineColor(e.target.value)}
                className="w-12 h-9 border border-slate-300 rounded cursor-pointer"
              />
              <span className="text-sm text-slate-500">{lineColor}</span>
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={lineActive}
              onChange={(e) => setLineActive(e.target.checked)}
              className="accent-emerald-600"
            />
            Activa (visible en el mapa de transporte)
          </label>
          {lineModalError && <FormError message={lineModalError} />}
          <ModalFooter
            saving={lineModalSaving}
            savingLabel="Guardando..."
            onCancel={() => setLineModal(null)}
            onSave={() => void guardarLinea()}
          />
        </ModalFrame>
      )}

      {/* Modal paradas */}
      {stopsModalOpen && selectedLine && (
        <ModalFrame title={`Paradas de ${selectedLine.name}`} onClose={() => setStopsModalOpen(false)}>
          {transporteZones.length === 0 ? (
            <p className="text-sm text-slate-500 italic">
              No hay zonas tipo "transporte" registradas. Creálas desde la solapa "Zonas".
            </p>
          ) : (
            <div className="max-h-80 overflow-y-auto space-y-1.5">
              {transporteZones.map((zona) => {
                const sel = stopsDraft.find((s) => s.zone_id === zona.id);
                return (
                  <div
                    key={zona.id}
                    className="flex items-center justify-between gap-3 px-3 py-2 rounded-md border cursor-pointer select-none bg-slate-50 hover:bg-slate-100"
                  >
                    <label className="flex items-center gap-2 text-sm text-slate-700 flex-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!sel}
                        onChange={() => toggleStopZone(zona.id)}
                        className="accent-emerald-600"
                      />
                      <span>{zona.name}</span>
                    </label>
                    <label className="flex items-center gap-1 text-xs text-slate-500">
                      Orden
                      <input
                        type="number"
                        min={1}
                        value={sel?.stop_order ?? ''}
                        disabled={!sel}
                        onChange={(e) => setStopOrder(zona.id, Number(e.target.value))}
                        className="w-16 border-slate-300 rounded-md py-1 px-2 disabled:opacity-40"
                      />
                    </label>
                  </div>
                );
              })}
            </div>
          )}
          {stopsError && <FormError message={stopsError} />}
          <ModalFooter
            saving={stopsSaving}
            savingLabel="Guardando..."
            onCancel={() => setStopsModalOpen(false)}
            onSave={() => void guardarStops()}
          />
        </ModalFrame>
      )}

      {/* Modal horarios */}
      {scheduleModalOpen && selectedLine && (
        <ModalFrame title={`Horarios de ${selectedLine.name}`} onClose={() => setScheduleModalOpen(false)}>
          {selectedStops.length === 0 ? (
            <p className="text-sm text-slate-500 italic">
              Asigná paradas a la línea antes de cargar horarios.
            </p>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {scheduleDraft.map((s, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  <select
                    value={s.line_stop_id}
                    onChange={(e) => updateHorario(i, { line_stop_id: e.target.value })}
                    className="col-span-4 border-slate-300 rounded-md py-1.5 px-2 text-sm"
                  >
                    {selectedStops.map((st) => (
                      <option key={st.id} value={st.id}>
                        {st.zone_name}
                      </option>
                    ))}
                  </select>
                  <select
                    value={s.day_type}
                    onChange={(e) => updateHorario(i, { day_type: e.target.value })}
                    className="col-span-3 border-slate-300 rounded-md py-1.5 px-2 text-sm"
                  >
                    {Object.entries(DAY_TYPE_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="time"
                    value={s.departure_time}
                    onChange={(e) => updateHorario(i, { departure_time: e.target.value })}
                    className="col-span-2 border-slate-300 rounded-md py-1.5 px-2 text-sm"
                  />
                  <input
                    type="text"
                    value={s.destination}
                    onChange={(e) => updateHorario(i, { destination: e.target.value })}
                    placeholder="Destino"
                    className="col-span-2 border-slate-300 rounded-md py-1.5 px-2 text-sm"
                  />
                  <button
                    onClick={() => quitarHorario(i)}
                    className="col-span-1 text-sm text-red-600 hover:bg-red-50 rounded-md py-1.5"
                    title="Quitar horario"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={agregarHorario}
                className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1.5 rounded-md transition-colors"
              >
                + Agregar horario
              </button>
            </div>
          )}
          {scheduleError && <FormError message={scheduleError} />}
          <ModalFooter
            saving={scheduleSaving}
            savingLabel="Guardando..."
            onCancel={() => setScheduleModalOpen(false)}
            onSave={() => void guardarHorarios()}
          />
        </ModalFrame>
      )}
    </div>
  );
}

function ModalFrame({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl p-6 mx-4 space-y-4">
        <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
        {children}
      </div>
    </div>
  );
}

function FormError({ message }: { message: string }) {
  return <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3">{message}</p>;
}

function ModalFooter({
  saving,
  savingLabel,
  onCancel,
  onSave,
}: {
  saving: boolean;
  savingLabel: string;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <div className="flex justify-end gap-3 pt-2">
      <button
        type="button"
        onClick={onCancel}
        className="py-2 px-4 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
      >
        Cancelar
      </button>
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="py-2 px-4 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition-colors"
      >
        {saving ? savingLabel : 'Guardar'}
      </button>
    </div>
  );
}
