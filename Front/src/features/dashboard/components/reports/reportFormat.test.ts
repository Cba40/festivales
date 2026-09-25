import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatLocalBucket } from './reportFormat.ts';

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
