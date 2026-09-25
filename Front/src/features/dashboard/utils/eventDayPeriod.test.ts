import { test } from 'node:test';
import assert from 'node:assert/strict';
import { eventDayToPeriod, ACCUMULATED_PERIOD } from './eventDayPeriod.ts';

const ART = 'America/Argentina/Buenos_Aires';
const UTC = 'UTC';

test('eventDayToPeriod abre la jornada a las 00:00:00 local (ART)', () => {
  const period = eventDayToPeriod('2026-07-15', ART);
  // ART es UTC-3 todo el año: 00:00 local => 03:00Z del mismo día.
  assert.equal(period.start, '2026-07-15T03:00:00.000Z');
});

test('eventDayToPeriod cierra la jornada a las 23:59:59 local (ART)', () => {
  const period = eventDayToPeriod('2026-07-15', ART);
  // 23:59:59.999 local => 02:59:59.999Z del día siguiente.
  assert.equal(period.end, '2026-07-16T02:59:59.999Z');
});

test('eventDayToPeriod cubre el día completo hasta la precisión de milisegundos', () => {
  const period = eventDayToPeriod('2026-07-15', ART);
  const spanMs = Date.parse(period.end) - Date.parse(period.start);
  // 00:00:00.000 → 23:59:59.999 son 24h menos el último milisegundo:
  // JS Date no representa microsegundos.
  assert.equal(spanMs, 24 * 60 * 60 * 1000 - 1);
});

test('eventDayToPeriod en UTC no desplaza la fecha', () => {
  const period = eventDayToPeriod('2026-07-15', UTC);
  assert.equal(period.start, '2026-07-15T00:00:00.000Z');
  assert.equal(period.end, '2026-07-15T23:59:59.999Z');
});

test('eventDayToPeriod funciona al cierre y apertura de mes/año', () => {
  assert.equal(eventDayToPeriod('2026-01-01', ART).start, '2026-01-01T03:00:00.000Z');
  assert.equal(eventDayToPeriod('2026-12-31', ART).end, '2027-01-01T02:59:59.999Z');
  assert.equal(eventDayToPeriod('2024-02-29', ART).start, '2024-02-29T03:00:00.000Z');
});

test('eventDayToPeriod respeta zonas con desplazamiento positivo', () => {
  const period = eventDayToPeriod('2026-07-15', 'Asia/Tokyo');
  assert.equal(period.start, '2026-07-14T15:00:00.000Z');
  assert.equal(period.end, '2026-07-15T14:59:59.999Z');
});

test('eventDayToPeriod rechaza fechas mal formadas o inexistentes', () => {
  assert.throws(() => eventDayToPeriod('15/07/2026', ART), /inválida/);
  assert.throws(() => eventDayToPeriod('2026-7-15', ART), /inválida/);
  assert.throws(() => eventDayToPeriod('2026-02-30', ART), /inexistente/);
  assert.throws(() => eventDayToPeriod('2026-13-01', ART), /inexistente/);
});

test('eventDayToPeriod rechaza una zona horaria inválida', () => {
  assert.throws(() => eventDayToPeriod('2026-07-15', 'Not/AZone'), /Zona horaria inválida/);
});

test('el período acumulado no declara extremos', () => {
  assert.deepEqual(ACCUMULATED_PERIOD, { start: null, end: null });
});
