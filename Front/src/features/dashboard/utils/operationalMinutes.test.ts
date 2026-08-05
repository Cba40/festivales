import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  minutesToTimeStr,
  timeStrToMinutes,
  resolveOperationalWindow,
  resolveOperationalMinutes,
} from './operationalMinutes.ts';
import type { EventDayPhaseCreatePayload } from '../types.ts';

const PHASE_A = 'phase-a';
const PHASE_B = 'phase-b';

function phase(id: string, start: number | null, end: number | null, intensity = 1): EventDayPhaseCreatePayload {
  return { operational_phase_id: id, start_min: start, end_min: end, intensity };
}

test('minutesToTimeStr / timeStrToMinutes son inversos', () => {
  assert.equal(timeStrToMinutes('08:00'), 480);
  assert.equal(minutesToTimeStr(480), '08:00');
  assert.equal(minutesToTimeStr(1500), '01:00');
});

test('resolveOperationalWindow cruza medianoche cuando fin < inicio', () => {
  assert.deepEqual(resolveOperationalWindow(480, 1080), { start: 480, end: 1080 });
  assert.deepEqual(resolveOperationalWindow(1320, 300), { start: 1320, end: 1740 });
});

test('resolveOperationalMinutes ordena por sort_order y propaga intensity', () => {
  const ops = [
    { id: PHASE_A, sort_order: 1 },
    { id: PHASE_B, sort_order: 2 },
  ];
  const resolved = resolveOperationalMinutes(
    [
      phase(PHASE_B, 60, 120, 0.8),
      phase(PHASE_A, 0, 60, 1.5),
    ],
    0,
    120,
    ops,
  );
  assert.equal(resolved.length, 2);
  assert.equal(resolved[0].operational_phase_id, PHASE_A);
  assert.equal(resolved[0].start_min, 0);
  assert.equal(resolved[0].end_min, 60);
  assert.equal(resolved[0].intensity, 1.5);
  assert.equal(resolved[1].operational_phase_id, PHASE_B);
  assert.equal(resolved[1].intensity, 0.8);
});

test('resolveOperationalMinutes conserva intensidad en fases sin horario', () => {
  const resolved = resolveOperationalMinutes([phase(PHASE_A, null, null, 0.5)], 480, 1080, []);
  assert.equal(resolved[0].intensity, 0.5);
  assert.equal(resolved[0].start_min, null);
  assert.equal(resolved[0].end_min, null);
});