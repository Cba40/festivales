import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  formatLocalBucket,
  formatLocalDate,
  formatLocalDateTime,
  buildFilterGroups,
} from './reportFormat.ts';

const ART = 'America/Argentina/Buenos_Aires';

const SVC = (service_category: string, total_consultas: number) => ({
  service_category,
  total_consultas,
});
const FIL = (request_mode: string | null, total: number) => ({ request_mode, total });

test('formatLocalBucket muestra la hora local sin desplazamiento', () => {
  // El bucket llega como hora de pared local (23:30 ART), sin offset.
  assert.equal(formatLocalBucket('2026-07-20T23:30:00'), '20/07/2026 23:30');
});

test('formatLocalBucket no corre la medianoche local al día anterior', () => {
  assert.equal(formatLocalBucket('2026-07-21T00:00:00'), '21/07/2026 00:00');
});

test('formatLocalBucket no corre un bucket tardío al día siguiente', () => {
  assert.equal(formatLocalBucket('2026-07-20T23:59:00'), '20/07/2026 23:59');
});

test('formatLocalBucket agrupa un bucket diario sin hora', () => {
  assert.equal(formatLocalBucket('2026-07-21T00:00:00'), '21/07/2026 00:00');
});

test('formatLocalBucket acepta separador de espacio', () => {
  assert.equal(formatLocalBucket('2026-07-20 23:30'), '20/07/2026 23:30');
});

test('formatLocalBucket no aplica conversión de zona horaria', () => {
  // Mismo instante bucketeado en dos zonas: el bucket es hora de pared y se
  // muestra tal cual, sin pasar por Date ni por la zona del navegador.
  const local = formatLocalBucket('2026-07-21T03:00:00');
  const alreadyZoned = formatLocalBucket('2026-07-21T03:00:00Z');
  assert.equal(local, '21/07/2026 03:00');
  assert.equal(alreadyZoned, local);
});

test('formatLocalBucket devuelve el valor original si no es una fecha', () => {
  assert.equal(formatLocalBucket('no-es-fecha'), 'no-es-fecha');
  assert.equal(formatLocalBucket(''), '');
});

test('formatLocalDate muestra la fecha en la zona operacional, no en UTC', () => {
  // El fin de la jornada del 21/07 ART llega como 22/07T02:59Z: mostrarlo en
  // UTC daría 22/07, que es el día equivocado.
  assert.equal(formatLocalDate('2026-07-22T02:59:59.999Z', ART), '21/07/2026');
  assert.equal(formatLocalDate('2026-07-15T03:00:00.000Z', ART), '15/07/2026');
});

test('formatLocalDate cubre el inicio exacto de la jornada', () => {
  // 00:00:00 ART del 21/07 = 03:00Z: sigue siendo 21/07 local.
  assert.equal(formatLocalDate('2026-07-21T03:00:00.000Z', ART), '21/07/2026');
});

test('formatLocalDate devuelve el valor original si no es una fecha', () => {
  assert.equal(formatLocalDate('no-es-fecha', ART), 'no-es-fecha');
});

test('formatLocalDateTime muestra la hora local sin el bug de ICU', () => {
  // 23:30Z = 20:30 ART. Con toLocaleString('es-AR') el runtime devuelve
  // "08:30" (convierte a 12 h sin AM/PM); formatToParts con h23 devuelve 20:30.
  assert.equal(formatLocalDateTime('2026-07-20T23:30:00Z', ART), '20/07/2026 20:30');
});

test('formatLocalDateTime no corre la fecha local', () => {
  // 02:30Z del 21/07 sigue siendo 20/07 23:30 en Argentina.
  assert.equal(formatLocalDateTime('2026-07-21T02:30:00Z', ART), '20/07/2026 23:30');
});

test('formatLocalDateTime usa ciclo de 24 horas', () => {
  const mediaNoche = formatLocalDateTime('2026-07-21T03:00:00Z', ART);
  assert.equal(mediaNoche, '21/07/2026 00:00');
  const mediodia = formatLocalDateTime('2026-07-21T15:00:00Z', ART);
  assert.equal(mediodia, '21/07/2026 12:00');
});

test('formatLocalDateTime acepta un Date', () => {
  const d = new Date('2026-07-21T15:00:00Z');
  assert.equal(formatLocalDateTime(d, ART), '21/07/2026 12:00');
});

test('formatLocalDateTime devuelve el valor original si no es una fecha', () => {
  assert.equal(formatLocalDateTime('no-es-fecha', ART), 'no-es-fecha');
});

test('buildFilterGroups agrupa los modos de salida dentro de Salidas', () => {
  const groups = buildFilterGroups(
    [SVC('exit', 9)],
    [FIL('mode=peatonal', 4), FIL('mode=vehicular', 3), FIL('mode=transporte', 2)],
  );
  assert.equal(groups.length, 1);
  const salidas = groups.find((g) => g.key === 'exit')!;
  assert.equal(salidas.label, 'Salidas');
  assert.deepEqual(
    salidas.children.map((c) => [c.label, c.total]),
    [['Peatonal', 4], ['Vehicular', 3], ['Transporte Público', 2]],
  );
});

test('buildFilterGroups separa urbano de interurbano en Transporte', () => {
  const groups = buildFilterGroups(
    [SVC('transport', 5)],
    [FIL('transport_type=urbano', 3), FIL('transport_type=interurbano', 2)],
  );
  const transporte = groups.find((g) => g.key === 'transport')!;
  assert.deepEqual(
    transporte.children.map((c) => c.label),
    ['Urbano', 'Interurbano'],
  );
});

test('buildFilterGroups mapea los tipos de hospedaje', () => {
  const groups = buildFilterGroups(
    [SVC('accommodation', 6)],
    [FIL('type=hotel', 2), FIL('type=camping', 1), FIL('type=hostel', 1), FIL('type=other', 1), FIL('type=all', 1)],
  );
  const hospedaje = groups.find((g) => g.key === 'accommodation')!;
  assert.deepEqual(
    hospedaje.children.map((c) => c.label).sort(),
    ['Camping', 'Hostel', 'Hotel', 'Otros', 'Todos'],
  );
});

test('buildFilterGroups usa el catálogo para nombrar los protocolos', () => {
  const groups = buildFilterGroups(
    [SVC('emergency', 2)],
    [FIL('protocolo=abc-123', 1), FIL('protocolo=def-456', 1)],
    { 'abc-123': 'Niño perdido', 'def-456': 'Persona herida' },
  );
  const emergencias = groups.find((g) => g.key === 'emergency')!;
  assert.deepEqual(
    emergencias.children.map((c) => c.label).sort(),
    ['Niño perdido', 'Persona herida'],
  );
});

test('buildFilterGroups cae a un identificador corto si no hay catálogo', () => {
  const groups = buildFilterGroups([SVC('emergency', 1)], [FIL('protocolo=abc-123456', 1)]);
  const emergencias = groups.find((g) => g.key === 'emergency')!;
  assert.equal(emergencias.children[0].label, 'Protocolo abc-1234');
});

test('buildFilterGroups suma los cuatro subtipos en Servicios Generales', () => {
  const groups = buildFilterGroups(
    [SVC('bathroom', 5), SVC('hydration', 3), SVC('rest', 2), SVC('cajeros', 1), SVC('parking', 4)],
    [FIL('banos', 5), FIL('hidratacion', 3), FIL('descanso', 2), FIL('cajeros', 1)],
  );
  const generales = groups.find((g) => g.key === 'Servicios Generales')!;
  assert.equal(generales.label, 'Servicios Generales');
  assert.equal(generales.total, 11);
  assert.deepEqual(
    generales.children.map((c) => [c.label, c.total]),
    [['Baños', 5], ['Hidratación', 3], ['Descanso', 2], ['Cajeros', 1]],
  );
  // Los subtipos crudos no deben aparecer como filtros sueltos FUERA del grupo
  // virtual: ya son sus hijos, y sumarlos otra vez duplicaría el total.
  const outsideVirtual = groups
    .filter((g) => g.key !== 'Servicios Generales')
    .flatMap((g) => g.children);
  for (const raw of ['banos', 'hidratacion', 'descanso', 'cajeros']) {
    assert.equal(
      outsideVirtual.filter((c) => c.key === raw).length,
      0,
      `el subtipo ${raw} no debe aparecer fuera de Servicios Generales`,
    );
  }
  // Parking conserva su propio grupo.
  assert.ok(groups.some((g) => g.key === 'parking'));
});

test('buildFilterGroups agrupa destinos de salida por modalidad', () => {
  const groups = buildFilterGroups(
    [SVC('exit', 9)],
    [
      FIL('mode=vehicular', 1),
      FIL('salida_vehicular=Norte', 5),
      FIL('salida_peatonal=Plaza', 3),
    ],
  );
  const salidas = groups.find((g) => g.key === 'exit')!;
  assert.deepEqual(
    salidas.children.map((c) => [c.label, c.total]),
    [['Vehicular: Norte', 5], ['Peatonal: Plaza', 3], ['Vehicular', 1]],
  );
  // El destino ya NO vive en un grupo compartido.
  assert.equal(groups.some((g) => g.key.includes('destinations')), false);
});

test('buildFilterGroups agrupa destinos de transporte por tipo', () => {
  const groups = buildFilterGroups(
    [SVC('transport', 12)],
    [
      FIL('transporte_urbano=Los Nogales', 5),
      FIL('transporte_interurbano=Córdoba', 7),
    ],
  );
  const transporte = groups.find((g) => g.key === 'transport')!;
  assert.deepEqual(
    transporte.children.map((c) => [c.label, c.total]),
    [['Interurbano: Córdoba', 7], ['Urbano: Los Nogales', 5]],
  );
});

test('buildFilterGroups normaliza modalidades desconocidas', () => {
  const groups = buildFilterGroups([SVC('exit', 1)], [FIL('salida_moto=Santa Rosa', 1)]);
  const salidas = groups.find((g) => g.key === 'exit')!;
  assert.equal(salidas.children[0].label, 'Moto: Santa Rosa');
});

test('buildFilterGroups separa los destinos por prefijo sin duplicarlos', () => {
  const groups = buildFilterGroups(
    [SVC('exit', 5), SVC('transport', 7)],
    [FIL('salida_peatonal=Centro', 5), FIL('transporte_urbano=Norte', 7)],
  );
  const salidas = groups.find((g) => g.key === 'exit')!;
  const transporte = groups.find((g) => g.key === 'transport')!;
  assert.equal(salidas.children.length, 1);
  assert.equal(salidas.children[0].label, 'Peatonal: Centro');
  assert.equal(transporte.children.length, 1);
  assert.equal(transporte.children[0].label, 'Urbano: Norte');
  // Ningún destino aparece en el grupo equivocado.
  assert.equal(
    salidas.children.some((c) => c.key.startsWith('transporte_')),
    false,
  );
});

test('buildFilterGroups conserva los destinos legacy sin atribuirlos', () => {
  const groups = buildFilterGroups(
    [SVC('exit', 4), SVC('transport', 2)],
    [FIL('destination=Plaza', 2)],
  );
  const legacy = groups.find((g) => g.key === 'legacy-destinations')!;
  assert.equal(legacy.label, 'Destinos sin atribución (registros previos)');
  assert.equal(legacy.children[0].label, 'Plaza');
  assert.equal(legacy.total, 2);
  // No se imputan a Salidas ni a Transporte.
  assert.equal(groups.find((g) => g.key === 'exit')!.children.length, 0);
  assert.equal(groups.find((g) => g.key === 'transport')!.children.length, 0);
});

test('buildFilterGroups agrupa zonas compartidas y las conserva sin duplicar', () => {
  const groups = buildFilterGroups(
    [SVC('parking', 3), SVC('bathroom', 2)],
    [FIL('zona=z-1', 3), FIL('zona=z-2', 2)],
  );
  const zonas = groups.find((g) => g.key === 'shared-zones')!;
  assert.equal(zonas.label, 'Zonas (estacionamiento y baños)');
  assert.equal(zonas.total, 5);
  assert.deepEqual(
    zonas.children.map((c) => [c.label, c.total]),
    [['z-1', 3], ['z-2', 2]],
  );
  assert.equal(
    groups.find((g) => g.key === 'parking')!.children.length,
    0,
  );
});

test('buildFilterGroups resuelve el nombre de zona del catálogo', () => {
  const groups = buildFilterGroups(
    [SVC('parking', 3), SVC('bathroom', 2)],
    [FIL('zona=z-1', 3), FIL('zona=z-2', 2)],
    {},
    { 'z-1': 'Estacionamiento Norte', 'z-2': 'Baños Centro' },
  );
  const zonas = groups.find((g) => g.key === 'shared-zones')!;
  assert.deepEqual(
    zonas.children.map((c) => [c.label, c.total]),
    [
      ['Estacionamiento Norte', 3],
      ['Baños Centro', 2],
    ],
  );
});

test('buildFilterGroups cae al id crudo si el catálogo no tiene la zona', () => {
  const groups = buildFilterGroups(
    [SVC('parking', 1)],
    [FIL('zona=z-desconocida', 1)],
    {},
    { 'z-1': 'Otra zona' },
  );
  const zonas = groups.find((g) => g.key === 'shared-zones')!;
  assert.deepEqual(
    zonas.children.map((c) => c.label),
    ['z-desconocida'],
  );
});

test('buildFilterGroups ordena los grupos por total descendente', () => {
  const groups = buildFilterGroups(
    [SVC('parking', 1), SVC('exit', 10), SVC('gastronomy', 5)],
    [],
  );
  assert.deepEqual(
    groups.map((g) => g.key),
    ['exit', 'gastronomy', 'parking'],
  );
});

test('buildFilterGroups tolera filtros ausentes', () => {
  const groups = buildFilterGroups([SVC('exit', 3)], null);
  assert.equal(groups.length, 1);
  assert.equal(groups[0].children.length, 0);
  assert.deepEqual(buildFilterGroups([], undefined), []);
});
